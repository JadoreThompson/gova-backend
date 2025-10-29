from datetime import date, timedelta
from uuid import UUID, uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import KAFKA_DEPLOYMENT_EVENTS_TOPIC, PAGE_SIZE
from core.enums import MessagePlatformType
from core.events import CreateDeploymentEvent
from db_models import (
    Messages,
    ModeratorDeployments,
    ModeratorDeploymentLogs,
    Moderators,
)
from engine.discord.config import DiscordConfig
from server.dependencies import depends_db_sess, depends_jwt, depends_kafka_producer
from server.models import PaginatedResponse
from server.shared.models import (
    DeploymentResponse,
    DiscordConfigResponse,
    MessageChartData,
)
from server.typing import JWTPayload
from utils.db import get_datetime
from utils.kafka import dump_model
from .controllers import fetch_moderators_with_platforms
from .models import (
    ModeratorCreate,
    ModeratorResponse,
    ModeratorUpdate,
    ModeratorStats,
    DeploymentCreate,
)

router = APIRouter(prefix="/moderators", tags=["Moderators"])


@router.post("/", response_model=ModeratorResponse)
async def create_moderator(
    body: ModeratorCreate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    mod = await db_sess.scalar(
        insert(Moderators)
        .values(user_id=jwt.sub, name=body.name, guideline_id=body.guideline_id)
        .returning(Moderators)
    )

    res = await fetch_moderators_with_platforms(
        db_sess, user_id=jwt.sub, moderator_id=mod.moderator_id
    )

    mod_obj, platforms = res[0] if res else (mod, [])
    rsp_body = ModeratorResponse(
        moderator_id=mod_obj.moderator_id,
        name=mod_obj.name,
        guideline_id=mod_obj.guideline_id,
        created_at=mod_obj.created_at,
        deployment_platforms=platforms if platforms and platforms[0] else [],
    )

    await db_sess.commit()

    return rsp_body


@router.post("/{moderator_id}/deploy", response_model=DeploymentResponse)
async def deploy_moderator(
    moderator_id: UUID,
    body: DeploymentCreate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    mod = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub
        )
    )
    if not mod:
        raise HTTPException(status_code=404, detail="Moderator not found.")

    conf = None
    if body.platform == MessagePlatformType.DISCORD:
        conf = DiscordConfig(**body.conf)
    else:
        raise HTTPException(status_code=400, detail="Unknown message platform.")

    name = body.name or str(uuid4())
    dep = await db_sess.scalar(
        insert(ModeratorDeployments)
        .values(
            moderator_id=moderator_id,
            platform=body.platform.value,
            conf=conf.to_serialisable_dict(),
            name=name,
        )
        .returning(ModeratorDeployments)
    )

    rsp_body = DeploymentResponse(
        deployment_id=dep.deployment_id,
        moderator_id=moderator_id,
        platform=dep.platform,
        name=dep.name,
        conf=DiscordConfigResponse(
            guild_id=conf.guild_id,
            allowed_actions=conf.allowed_actions,
            allowed_channels=conf.allowed_channels,
        ),
        status=dep.status,
        created_at=dep.created_at,
    )

    ev = CreateDeploymentEvent(
        deployment_id=dep.deployment_id,
        moderator_id=dep.moderator_id,
        platform=body.platform,
        conf=conf,
    )
    await db_sess.commit()

    await kafka_producer.send(KAFKA_DEPLOYMENT_EVENTS_TOPIC, dump_model(ev))
    return rsp_body


@router.get("/", response_model=PaginatedResponse[ModeratorResponse])
async def list_moderators(
    name: str | None = None,
    page: int = Query(ge=1),
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    mods = await fetch_moderators_with_platforms(
        db_sess=db_sess,
        user_id=jwt.sub,
        name=name,
        page=page,
    )

    n = len(mods)

    return PaginatedResponse[ModeratorResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            ModeratorResponse(
                moderator_id=m.moderator_id,
                guideline_id=m.guideline_id,
                name=m.name,
                created_at=m.created_at,
                deployment_platforms=platforms if platforms and platforms[0] else [],
            )
            for m, platforms in mods[:PAGE_SIZE]
        ],
    )


@router.get("/{moderator_id}", response_model=ModeratorResponse)
async def get_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await fetch_moderators_with_platforms(
        db_sess=db_sess,
        user_id=jwt.sub,
        moderator_id=moderator_id,
    )

    if not res:
        raise HTTPException(status_code=404, detail="Moderator not found")

    mod, platforms = res[0]
    return ModeratorResponse(
        moderator_id=mod.moderator_id,
        name=mod.name,
        guideline_id=mod.guideline_id,
        created_at=mod.created_at,
        deployment_platforms=platforms if platforms and platforms[0] else [],
    )


@router.get(
    "/{moderator_id}/deployments", response_model=PaginatedResponse[DeploymentResponse]
)
async def get_deployments(
    moderator_id: UUID,
    page: int = Query(1, ge=1),
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    deps = (
        await db_sess.scalars(
            select(ModeratorDeployments)
            .join(
                Moderators, Moderators.moderator_id == ModeratorDeployments.moderator_id
            )
            .where(
                Moderators.user_id == jwt.sub,
                ModeratorDeployments.moderator_id == moderator_id,
            )
            .order_by(ModeratorDeployments.created_at.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE + 1)
        )
    ).all()

    n = len(deps)

    return PaginatedResponse[DeploymentResponse](
        page=page,
        size=n,
        has_next=n > PAGE_SIZE,
        data=[
            DeploymentResponse(
                deployment_id=d.deployment_id,
                moderator_id=d.moderator_id,
                platform=d.platform,
                name=d.name,
                conf=DiscordConfigResponse(**d.conf),
                status=d.status,
                created_at=d.created_at,
            )
            for d in deps
        ],
    )


@router.get("/{moderator_id}/stats", response_model=ModeratorStats)
async def get_moderator_stats(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    moderator_exists = await db_sess.scalar(
        select(Moderators.moderator_id).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator_exists:
        raise HTTPException(status_code=404, detail="Moderator not found")

    today = get_datetime().date()
    week_starts = [
        today - timedelta(weeks=i, days=today.weekday()) for i in reversed(range(6))
    ]
    earliest_week = week_starts[0]

    total_messages = await db_sess.scalar(
        select(func.count(Messages.message_id)).where(
            Messages.moderator_id == moderator_id
        )
    )
    total_messages = total_messages or 0

    total_actions = await db_sess.scalar(
        select(func.count(ModeratorDeploymentLogs.log_id)).where(
            ModeratorDeploymentLogs.moderator_id == moderator_id
        )
    )
    total_actions = total_actions or 0

    weekly_result = await db_sess.execute(
        select(
            Messages.platform.label("platform"),
            func.date_trunc("week", Messages.created_at).label("week_start"),
            func.count(Messages.message_id).label("frequency"),
        )
        .where(
            Messages.moderator_id == moderator_id,
            Messages.created_at >= earliest_week,
        )
        .group_by("platform", "week_start")
        .order_by("platform", "week_start")
    )

    all_platforms = await db_sess.scalars(
        select(func.distinct(Messages.platform)).where(
            Messages.moderator_id == moderator_id
        )
    )
    all_platform_list = list(all_platforms.all())

    data_map: dict[str, dict[date, int]] = {}
    for row in weekly_result.all():
        platform = row.platform
        week_start = row.week_start.date()
        if platform not in data_map:
            data_map[platform] = {}
        data_map[platform][week_start] = row.frequency

    message_chart: list[MessageChartData] = []

    for week_start in week_starts:
        counts = {
            platform: data_map.get(platform, {}).get(week_start, 0)
            for platform in all_platform_list
        }
        message_chart.append(MessageChartData(date=week_start, counts=counts))

    return ModeratorStats(
        total_messages=total_messages,
        total_actions=total_actions,
        message_chart=message_chart,
    )


@router.put("/{moderator_id}", response_model=ModeratorResponse)
async def update_moderator(
    moderator_id: UUID,
    body: ModeratorUpdate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    vals = body.model_dump(exclude_unset=True, exclude_none=True)
    if not vals:
        raise HTTPException(
            status_code=400, detail="Either name or guideline id must be provided."
        )

    if vals.get("name"):
        rsp = await db_sess.scalar(
            select(Moderators).where(
                Moderators.name == vals["name"], Moderators.user_id == jwt.sub
            )
        )
        if rsp:
            raise HTTPException(
                status_code=409,
                detail=f"Moderator with name {vals['name']} already exists.",
            )

    if vals.get("guideline_id"):
        rsp = await db_sess.scalar(
            select(Moderators).where(
                Moderators.name == vals["guideline_id"], Moderators.user_id == jwt.sub
            )
        )
        if rsp:
            raise HTTPException(status_code=409, detail=f"Guideline doesn't exist.")

    updated = await db_sess.scalar(
        update(Moderators)
        .where(Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub)
        .values(**vals)
        .returning(Moderators)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Moderator not found")

    await db_sess.commit()

    res = await fetch_moderators_with_platforms(
        db_sess, user_id=jwt.sub, moderator_id=moderator_id
    )
    mod_obj, platforms = res[0] if res else (updated, [])

    return ModeratorResponse(
        moderator_id=mod_obj.moderator_id,
        name=mod_obj.name,
        guideline_id=mod_obj.guideline_id,
        created_at=mod_obj.created_at,
        deployment_platforms=platforms if platforms and platforms[0] else [],
    )


@router.delete("/{moderator_id}")
async def delete_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await db_sess.scalar(
        delete(Moderators)
        .where(Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub)
        .returning(Moderators.moderator_id)
    )
    if not res:
        raise HTTPException(status_code=404, detail="Moderator not found")

    await db_sess.commit()
    return {"message": "Moderator deleted successfully"}
