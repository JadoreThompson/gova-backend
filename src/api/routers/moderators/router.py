from datetime import date, timedelta
from uuid import UUID

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import KAFKA_MODERATOR_EVENTS_TOPIC, PAGE_SIZE, PRICING_TIER_LIMITS
from enums import ActionStatus, CoreEventType, ModeratorEventType, ModeratorStatus
from core.events import CoreEvent, KillModeratorEvent, StartModeratorEvent
from db_models import Messages, ModeratorEventLogs, Moderators
from api.dependencies import (
    CSVQuery,
    depends_db_sess,
    depends_jwt,
    depends_kafka_producer,
)
from api.models import PaginatedResponse
from api.shared.models import ActionResponse
from api.types import JWTPayload
from utils import get_datetime
from utils.kafka import dump_model
from .models import (
    ModeratorCreate,
    ModeratorResponse,
    DiscordConfigBody,
    MessageChartData,
    ModeratorStats,
)


router = APIRouter(prefix="/moderators", tags=["Moderators"])


@router.post("/", response_model=ModeratorResponse)
async def create_moderator(
    body: ModeratorCreate,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    count = await db_sess.scalar(
        select(func.count(Moderators.moderator_id)).where(Moderators.user_id == jwt.sub)
    )
    if count >= PRICING_TIER_LIMITS[jwt.pricing_tier]["max_moderators"]:
        raise HTTPException(status_code=400, detail="Max moderators reached.")

    mod = await db_sess.scalar(
        insert(Moderators)
        .values(user_id=jwt.sub, **body.model_dump())
        .returning(Moderators)
    )

    rsp_body = ModeratorResponse(
        moderator_id=mod.moderator_id,
        name=mod.name,
        guideline_id=mod.guideline_id,
        platform=mod.platform,
        platform_api_id=mod.platform_api_id,
        conf=DiscordConfigBody(**mod.conf),
        status=mod.status,
        created_at=mod.created_at,
    )

    await db_sess.commit()

    return rsp_body


@router.post("/{moderator_id}/start", status_code=202)
async def start_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
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

    live_count = await db_sess.scalar(
        select(func.count(Moderators.moderator_id)).where(
            Moderators.user_id == jwt.sub,
            Moderators.platform_api_id == mod.platform_api_id,
            Moderators.status != ModeratorStatus.OFFLINE.value,
        )
    )
    if live_count:
        raise HTTPException(status_code=400, detail="Moderator already running in api")

    # Resitricting access
    online_count = await db_sess.scalar(
        select(func.count(Moderators.moderator_id)).where(
            Moderators.user_id == jwt.sub,
            Moderators.status != ModeratorStatus.OFFLINE.value,
        )
    )

    max_messages = PRICING_TIER_LIMITS[jwt.pricing_tier]["max_messages"]
    if online_count >= max_messages:
        raise HTTPException(status_code=400, detail="Max deployments reached.")

    event = StartModeratorEvent(
        moderator_id=mod.moderator_id, platform=mod.platform, conf=mod.conf
    )

    await kafka_producer.send(
        KAFKA_MODERATOR_EVENTS_TOPIC,
        dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
    )


@router.post("/{moderator_id}/stop", status_code=202)
async def stop_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt(True)),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    mod = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub
        )
    )
    if not mod:
        raise HTTPException(status_code=400, detail="Moderator not found.")

    event = KillModeratorEvent(moderator_id=moderator_id, reason="User requested stop")
    await kafka_producer.send(
        KAFKA_MODERATOR_EVENTS_TOPIC,
        dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
    )


@router.get("/", response_model=PaginatedResponse[ModeratorResponse])
async def list_moderators(
    name: str | None = None,
    page: int = Query(ge=1),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    query = select(Moderators).where(Moderators.user_id == jwt.sub)
    if name:
        query = query.where(Moderators.name.like(f"%{name}%"))

    res = await db_sess.scalars(
        query.order_by(Moderators.created_at.desc())
        .offset((page - 1) * 10)
        .limit(PAGE_SIZE + 1)
    )
    mods = res.all()
    n = len(mods)

    return PaginatedResponse[ModeratorResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            ModeratorResponse(
                moderator_id=mod.moderator_id,
                name=mod.name,
                guideline_id=mod.guideline_id,
                platform=mod.platform,
                platform_api_id=mod.platform_api_id,
                conf=DiscordConfigBody(**mod.conf),
                status=mod.status,
                created_at=mod.created_at,
            )
            for mod in mods[:PAGE_SIZE]
        ],
    )


@router.get("/{moderator_id}", response_model=ModeratorResponse)
async def get_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    mod = await db_sess.scalar(
        select(Moderators)
        .where(Moderators.user_id == jwt.sub, Moderators.moderator_id == moderator_id)
        .order_by(Moderators.created_at.desc())
    )

    if not mod:
        raise HTTPException(status_code=404, detail="Moderator not found")

    return ModeratorResponse(
        moderator_id=mod.moderator_id,
        name=mod.name,
        guideline_id=mod.guideline_id,
        platform=mod.platform,
        platform_api_id=mod.platform_api_id,
        conf=DiscordConfigBody(**mod.conf),
        status=mod.status,
        created_at=mod.created_at,
    )


@router.get("/{moderator_id}/stats", response_model=ModeratorStats)
async def get_moderator_stats(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
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
        select(func.count(ModeratorEventLogs.log_id)).where(
            ModeratorEventLogs.moderator_id == moderator_id,
            ModeratorEventLogs.event_type == ModeratorEventType.ACTION_PERFORMED.value,
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


@router.get("/{moderator_id}/actions", response_model=PaginatedResponse[ActionResponse])
async def list_moderator_actions(
    moderator_id: UUID,
    page: int = Query(1, ge=1),
    status: list[ActionStatus] | None = CSVQuery("status", ActionStatus),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    exists = await db_sess.scalar(
        select(Moderators.moderator_id).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Moderator not found")

    query = select(ModeratorEventLogs).where(
        ModeratorEventLogs.moderator_id == moderator_id,
        ModeratorEventLogs.event_type == ModeratorEventType.ACTION_PERFORMED.value,
    )

    if status is not None:
        query = query.where(
            ModeratorEventLogs.action_status.in_((s.value for s in status))
        )

    res = await db_sess.scalars(
        query.order_by(ModeratorEventLogs.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
    )

    logs = res.all()
    n = len(logs)

    data = [
        ActionResponse(
            log_id=log.log_id,
            moderator_id=log.moderator_id,
            action_type=log.action_type,
            action_params=log.action_params,
            status=log.action_status,
            created_at=log.created_at,
        )
        for log in logs[:PAGE_SIZE]
    ]

    return PaginatedResponse[ActionResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=data,
    )


@router.delete("/{moderator_id}")
async def delete_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    mod = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub
        )
    )
    if not mod:
        raise HTTPException(status_code=404, detail="Moderator not found")

    if mod.status != ModeratorStatus.OFFLINE.value:
        raise HTTPException(status_code=400, detail="Moderator must be offline")

    event = await db_sess.scalar(
        select(ModeratorEventLogs)
        .where(ModeratorEventLogs.moderator_id == mod.moderator_id)
        .order_by(ModeratorEventLogs.created_at.desc())
        .limit(1)
    )
    if event is not None and event.event_type != ModeratorEventType.DEAD.value:
        raise HTTPException(status_code=400, detail="Modertor must be offline")

    await db_sess.delete(mod)

    await db_sess.commit()
    return {"message": "Moderator deleted successfully"}
