from datetime import timedelta
from uuid import UUID

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import KAFKA_DEPLOYMENT_EVENTS_TOPIC, PAGE_SIZE
from core.enums import MessagePlatformType, ModeratorDeploymentStatus
from core.events import StartModeratorDeploymentEvent, StopModeratorDeploymentEvent
from db_models import (
    Messages,
    ModeratorDeployments,
    ModeratorDeploymentEventLogs,
    Moderators,
)
from server.dependencies import depends_db_sess, depends_jwt, depends_kafka_producer
from server.models import PaginatedResponse
from server.shared.models import (
    DeploymentAction,
    DeploymentResponse,
    MessageChartData,
    MessageChartData,
)
from server.typing import JWTPayload
from utils.db import get_datetime
from utils.kafka import dump_model
from .models import DeploymentStatsResponse, DeploymentStatsResponse


router = APIRouter(prefix="/deployments", tags=["Moderator Deployments"])


@router.get("/", response_model=PaginatedResponse[DeploymentResponse])
async def list_deployments(
    page: int = Query(ge=1),
    name: str | None = None,
    status: list[ModeratorDeploymentStatus] | None = None,
    platform: list[MessagePlatformType] | None = None,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    query = (
        select(ModeratorDeployments)
        .join(Moderators, ModeratorDeployments.moderator_id == Moderators.moderator_id)
        .where(Moderators.user_id == jwt.sub)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
    )

    if name:
        query = query.where(ModeratorDeployments.name.like(f"%{name}%"))
    if status is not None:
        query = query.where(ModeratorDeployments.status.in_([s.value for s in status]))
    if platform is not None:
        query = query.where(
            ModeratorDeployments.platform.in_([p.value for p in platform])
        )

    res = await db_sess.scalars(query)

    deployments = res.all()
    n = len(deployments)

    return PaginatedResponse[DeploymentResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            DeploymentResponse(
                deployment_id=d.deployment_id,
                moderator_id=d.moderator_id,
                platform=d.platform,
                name=d.name,
                conf=d.conf,
                status=d.status,
                created_at=d.created_at,
            )
            for d in deployments[:PAGE_SIZE]
        ],
    )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    dep = await db_sess.scalar(
        select(ModeratorDeployments)
        .join(Moderators, ModeratorDeployments.moderator_id == Moderators.moderator_id)
        .where(
            ModeratorDeployments.deployment_id == deployment_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return DeploymentResponse(
        deployment_id=dep.deployment_id,
        moderator_id=dep.moderator_id,
        platform=dep.platform,
        name=dep.name,
        conf=dep.conf,
        status=dep.status,
        created_at=dep.created_at,
    )


@router.get("/{deployment_id}/stats", response_model=DeploymentStatsResponse)
async def get_deployment_stats(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    deployment = await db_sess.scalar(
        select(ModeratorDeployments)
        .join(Moderators, ModeratorDeployments.moderator_id == Moderators.moderator_id)
        .where(
            ModeratorDeployments.deployment_id == deployment_id,
            Moderators.user_id == jwt.sub,
        )
    )

    if not deployment:
        raise HTTPException(
            status_code=404, detail="Deployment not found or unauthorized"
        )

    total_messages = (
        await db_sess.scalar(
            select(func.count(Messages.message_id)).where(
                Messages.deployment_id == deployment.deployment_id,
                Messages.platform == deployment.platform,
            )
        )
        or 0
    )

    total_actions = (
        await db_sess.scalar(
            select(func.count(ModeratorDeploymentEventLogs.log_id)).where(
                ModeratorDeploymentEventLogs.deployment_id == deployment.deployment_id
            )
        )
        or 0
    )

    today = get_datetime().date()
    week_starts = [
        today - timedelta(weeks=i, days=today.weekday()) for i in reversed(range(6))
    ]
    earliest_week = week_starts[0]

    weekly_result = await db_sess.execute(
        select(
            func.date_trunc("week", Messages.created_at).label("week_start"),
            func.count(Messages.message_id).label("frequency"),
        )
        .where(
            Messages.deployment_id == deployment.deployment_id,
            Messages.platform == deployment.platform,
            Messages.created_at >= earliest_week,
        )
        .group_by("week_start")
        .order_by("week_start")
    )

    week_map = {row.week_start.date(): row.frequency for row in weekly_result.all()}

    message_chart: list[MessageChartData] = []
    for week_start in week_starts:
        counts = {deployment.platform: week_map.get(week_start, 0)}
        message_chart.append(MessageChartData(date=week_start, counts=counts))

    return DeploymentStatsResponse(
        total_messages=total_messages,
        total_actions=total_actions,
        message_chart=message_chart,
    )


@router.get(
    "/{deployment_id}/actions", response_model=PaginatedResponse[DeploymentAction]
)
async def get_deployment_actions(
    deployment_id: UUID,
    page: int = Query(1, ge=1),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """
    Get all actions (ModeratorLogs) for a specific deployment.
    Fully type-safe and paginated.
    """

    deployment = await db_sess.scalar(
        select(ModeratorDeployments)
        .join(Moderators, ModeratorDeployments.moderator_id == Moderators.moderator_id)
        .where(
            ModeratorDeployments.deployment_id == deployment_id,
            Moderators.user_id == jwt.sub,
        )
    )

    if not deployment:
        raise HTTPException(
            status_code=404, detail="Deployment not found or unauthorized"
        )

    logs = (
        await db_sess.scalars(
            select(ModeratorDeploymentEventLogs)
            .where(ModeratorDeploymentEventLogs.deployment_id == deployment_id)
            .order_by(ModeratorDeploymentEventLogs.created_at.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE + 1)
        )
    ).all()
    n = len(logs)

    return PaginatedResponse[DeploymentAction](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            DeploymentAction(
                log_id=log.log_id,
                deployment_id=log.deployment_id,
                action_type=log.action_type,
                action_params=log.action_params,
                status=log.status,
                created_at=log.created_at,
            )
            for log in logs[:PAGE_SIZE]
        ],
    )


@router.post("/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    dep = await db_sess.scalar(
        select(ModeratorDeployments)
        .join(Moderators, Moderators.moderator_id == ModeratorDeployments.moderator_id)
        .where(
            Moderators.user_id == jwt.sub,
            ModeratorDeployments.deployment_id == deployment_id,
        )
    )
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found.")
    if dep.status != ModeratorDeploymentStatus.ONLINE.value:
        raise HTTPException(status_code=400, detail="Deployment is not online.")

    ev = StopModeratorDeploymentEvent(
        type="stop",
        deployment_id=dep.deployment_id,
    )
    await kafka_producer.send(KAFKA_DEPLOYMENT_EVENTS_TOPIC, dump_model(ev))

    dep.status = ModeratorDeploymentStatus.PENDING.value
    await db_sess.commit()


@router.post("/{deployment_id}/start")
async def stop_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    dep = await db_sess.scalar(
        select(ModeratorDeployments)
        .join(Moderators, Moderators.moderator_id == ModeratorDeployments.moderator_id)
        .where(
            Moderators.user_id == jwt.sub,
            ModeratorDeployments.deployment_id == deployment_id,
        )
    )
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found.")
    if dep.status != ModeratorDeploymentStatus.OFFLINE.value:
        raise HTTPException(status_code=400, detail="Deployment is not offline.")

    ev = StopModeratorDeploymentEvent(deployment_id=dep.deployment_id)
    await kafka_producer.send(KAFKA_DEPLOYMENT_EVENTS_TOPIC, dump_model(ev))

    dep.status = ModeratorDeploymentStatus.PENDING.value
    await db_sess.commit()


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await db_sess.scalar(
        delete(ModeratorDeployments)
        .where(
            ModeratorDeployments.deployment_id == deployment_id,
            ModeratorDeployments.moderator_id.in_(
                select(Moderators.moderator_id).where(Moderators.user_id == jwt.sub)
            ),
        )
        .returning(ModeratorDeployments.deployment_id)
    )

    if not res:
        raise HTTPException(
            status_code=404, detail="Deployment not found or unauthorized."
        )

    await db_sess.commit()
    return {"message": "Deployment deleted successfully"}
