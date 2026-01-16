from datetime import timedelta
from uuid import UUID
from typing import Literal

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    CSVQuery,
    depends_db_sess,
    depends_jwt,
    depends_kafka_producer,
)
from api.models import PaginatedResponse
from api.types import JWTPayload
from config import KAFKA_MODERATOR_EVENTS_TOPIC, PAGE_SIZE, PricingTierLimits
from db_models2 import Moderators, EvaluationEvents, ActionEvents
from enums import ActionStatus, MessagePlatform, ModeratorStatus
from events.moderator import (
    StartModeratorEvent,
    StopModeratorEvent,
    UpdateConfigModeratorEvent,
)
from infra.kafka import AsyncKafkaProducer
from utils import get_datetime
from .controller import validate_config
from .models import (
    ModeratorCreate,
    ModeratorResponse,
    ModeratorUpdate,
    ActionResponse,
    ModeratorStats,
    BarChartData,
)


router = APIRouter(prefix="/moderators", tags=["Moderators"])
kafka_producer = AsyncKafkaProducer()


@router.post("/", response_model=ModeratorResponse)
async def create_moderator(
    body: ModeratorCreate,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Create a new moderator for the authenticated user."""
    count = await db_sess.scalar(
        select(func.count(Moderators.moderator_id)).where(Moderators.user_id == jwt.sub)
    )
    if count >= PricingTierLimits.get(jwt.pricing_tier).max_moderators:
        raise HTTPException(status_code=400, detail="Max moderators reached.")

    try:
        validate_config(body.platform, body.conf)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    moderator = Moderators(
        user_id=jwt.sub,
        name=body.name,
        description=body.description,
        platform=body.platform.value,
        platform_server_id=body.platform_server_id,
        conf=body.conf,
        status=ModeratorStatus.OFFLINE.value,
    )
    db_sess.add(moderator)
    await db_sess.commit()
    await db_sess.refresh(moderator)

    return ModeratorResponse(
        moderator_id=moderator.moderator_id,
        name=moderator.name,
        description=moderator.description,
        platform=MessagePlatform(moderator.platform),
        platform_server_id=moderator.platform_server_id,
        conf=moderator.conf,
        status=ModeratorStatus(moderator.status),
        created_at=moderator.created_at,
    )


@router.get("/{moderator_id}", response_model=ModeratorResponse)
async def get_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Get a moderator by ID."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    return ModeratorResponse(
        moderator_id=moderator.moderator_id,
        name=moderator.name,
        description=moderator.description,
        platform=MessagePlatform(moderator.platform),
        platform_server_id=moderator.platform_server_id,
        conf=moderator.conf,
        status=ModeratorStatus(moderator.status),
        created_at=moderator.created_at,
    )


@router.get("/", response_model=PaginatedResponse[ModeratorResponse])
async def list_moderators(
    skip: int = Query(0, ge=0),
    limit: int = Query(PAGE_SIZE, ge=1, le=100),
    platform: list[MessagePlatform] | None = CSVQuery("platform", MessagePlatform),
    name: str | None = Query(None, min_length=1),
    status: list[ModeratorStatus] | None = CSVQuery("status", ModeratorStatus),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """List moderators with filtering and pagination."""
    query = select(Moderators).where(Moderators.user_id == jwt.sub)

    if platform:
        query = query.where(Moderators.platform.in_([p.value for p in platform]))

    if name:
        query = query.where(Moderators.name.ilike(f"%{name}%"))

    if status:
        query = query.where(Moderators.status.in_([s.value for s in status]))

    query = query.order_by(Moderators.created_at.desc()).offset(skip).limit(limit + 1)

    result = await db_sess.execute(query)
    moderators = result.scalars().all()

    has_next = len(moderators) > limit
    data = [
        ModeratorResponse(
            moderator_id=mod.moderator_id,
            name=mod.name,
            description=mod.description,
            platform=MessagePlatform(mod.platform),
            platform_server_id=mod.platform_server_id,
            conf=mod.conf,
            status=ModeratorStatus(mod.status),
            created_at=mod.created_at,
        )
        for mod in moderators[:limit]
    ]

    return PaginatedResponse[ModeratorResponse](
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(data),
        has_next=has_next,
        data=data,
    )


@router.get("/{moderator_id}/stats", response_model=ModeratorStats)
async def get_moderator_stats(
    moderator_id: UUID,
    timeframe: Literal["1w", "1m", "1y"] = Query("1w"),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Get moderator statistics for a given timeframe."""
    moderator = await db_sess.scalar(
        select(Moderators.moderator_id).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    now = get_datetime()
    period_map = {
        "1w": (now - timedelta(days=7), "day"),
        "1m": (now - timedelta(weeks=4), "week"),
        "1y": (now - timedelta(days=365), "month"),
    }
    start_date, bucket_type = period_map[timeframe]

    evaluations_count_query = select(func.count(EvaluationEvents.event_id)).where(
        EvaluationEvents.moderator_id == moderator_id,
        EvaluationEvents.created_at >= start_date,
    )
    evaluations_count = await db_sess.scalar(evaluations_count_query) or 0

    actions_count_query = select(func.count(ActionEvents.action_id)).where(
        ActionEvents.moderator_id == moderator_id,
        ActionEvents.created_at >= start_date,
    )
    actions_count = await db_sess.scalar(actions_count_query) or 0

    if bucket_type == "day":
        date_trunc = func.date_trunc("day", EvaluationEvents.created_at)
        bucket_format = "%Y-%m-%d"
        date_range = [start_date + timedelta(days=i) for i in range(7)]
    elif bucket_type == "week":
        date_trunc = func.date_trunc("week", EvaluationEvents.created_at)
        bucket_format = "%Y-%W"
        date_range = [start_date + timedelta(weeks=i) for i in range(4)]
    else:
        date_trunc = func.date_trunc("month", EvaluationEvents.created_at)
        bucket_format = "%Y-%m"
        date_range = [start_date + timedelta(days=30 * i) for i in range(12)]

    ev_buckets_query = (
        select(
            date_trunc.label("bucket"),
            func.count(EvaluationEvents.event_id).label("count"),
        )
        .where(
            EvaluationEvents.moderator_id == moderator_id,
            EvaluationEvents.created_at >= start_date,
        )
        .group_by("bucket")
    )
    ev_result = await db_sess.execute(ev_buckets_query)
    ev_buckets = {
        row.bucket.date() if hasattr(row.bucket, "date") else row.bucket: row.count
        for row in ev_result
    }

    act_buckets_query = (
        select(
            date_trunc.label("bucket"),
            func.count(ActionEvents.action_id).label("count"),
        )
        .where(
            ActionEvents.moderator_id == moderator_id,
            ActionEvents.created_at >= start_date,
        )
        .group_by("bucket")
    )
    act_result = await db_sess.execute(act_buckets_query)
    act_buckets = {
        row.bucket.date() if hasattr(row.bucket, "date") else row.bucket: row.count
        for row in act_result
    }

    bar_chart = []
    for d in date_range:
        bucket_date = d.date() if hasattr(d, "date") else d
        ev_count = ev_buckets.get(bucket_date, 0)
        act_count = act_buckets.get(bucket_date, 0)
        bar_chart.append(
            BarChartData(
                date=bucket_date,
                evaluations_count=ev_count,
                actions_count=act_count,
            )
        )

    return ModeratorStats(
        evaluations_count=evaluations_count,
        actions_count=actions_count,
        bar_chart=bar_chart,
    )


@router.get("/{moderator_id}/actions", response_model=PaginatedResponse[ActionResponse])
async def list_moderator_actions(
    moderator_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(PAGE_SIZE, ge=1, le=100),
    status: list[ActionStatus] | None = CSVQuery("status", ActionStatus),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """List actions for a moderator with filtering and pagination."""
    moderator_exists = await db_sess.scalar(
        select(Moderators.moderator_id).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator_exists:
        raise HTTPException(status_code=404, detail="Moderator not found")

    query = select(ActionEvents).where(ActionEvents.moderator_id == moderator_id)

    if status:
        query = query.where(ActionEvents.status.in_([s.value for s in status]))

    query = query.order_by(ActionEvents.created_at.desc()).offset(skip).limit(limit + 1)

    result = await db_sess.execute(query)
    actions = result.scalars().all()

    has_next = len(actions) > limit
    data = [
        ActionResponse(
            action_id=act.action_id,
            moderator_id=act.moderator_id,
            platform_user_id=act.platform_user_id,
            action_type=act.action_type,
            action_params=act.action_params,
            context=act.context,
            status=ActionStatus(act.status),
            reason=act.reason,
            created_at=act.created_at,
            updated_at=act.updated_at,
            executed_at=act.executed_at,
        )
        for act in actions[:limit]
    ]

    return PaginatedResponse[ActionResponse](
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(data),
        has_next=has_next,
        data=data,
    )


@router.patch("/{moderator_id}", response_model=ModeratorResponse)
async def update_moderator(
    moderator_id: UUID,
    body: ModeratorUpdate,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Update a moderator's name, description, or configuration."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    if moderator.status != ModeratorStatus.OFFLINE.value:
        raise HTTPException(
            status_code=400, detail="Moderator must be offline to update"
        )

    event = None
    if body.conf is not None:
        try:
            validated_config = validate_config(moderator.platform, body.conf)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        event = UpdateConfigModeratorEvent(
            moderator_id=moderator_id, config=validated_config
        )

    if body.name is not None:
        moderator.name = body.name
    if body.description is not None:
        moderator.description = body.description

    await db_sess.commit()
    await db_sess.refresh(moderator)

    if event is not None:
        await kafka_producer.send(KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json())

    return ModeratorResponse(
        moderator_id=moderator.moderator_id,
        name=moderator.name,
        description=moderator.description,
        platform=MessagePlatform(moderator.platform),
        platform_server_id=moderator.platform_server_id,
        conf=moderator.conf,
        status=ModeratorStatus(moderator.status),
        created_at=moderator.created_at,
    )


@router.post("/{moderator_id}/start", status_code=202)
async def start_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    """Start a moderator."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    if moderator.status != ModeratorStatus.OFFLINE:
        raise HTTPException(status_code=400, detail="Moderator is not offline")

    online_count = await db_sess.scalar(
        select(func.count(Moderators.moderator_id)).where(
            Moderators.user_id == jwt.sub,
            Moderators.status == ModeratorStatus.ONLINE.value,
        )
    )
    tier_limits = PricingTierLimits.get(jwt.pricing_tier)
    max_running = tier_limits.max_concurrent
    if online_count >= max_running:
        raise HTTPException(status_code=400, detail="Max running moderators reached")

    event = StartModeratorEvent(
        moderator_id=moderator_id,
        platform=MessagePlatform(moderator.platform),
        conf=moderator.conf,
    )

    await kafka_producer.send(
        KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
    )

    return {"message": "Moderator start request sent"}


@router.post("/{moderator_id}/stop", status_code=202)
async def stop_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
    kafka_producer: AIOKafkaProducer = Depends(depends_kafka_producer),
):
    """Stop a running moderator."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    if moderator.status == ModeratorStatus.OFFLINE.value:
        raise HTTPException(status_code=400, detail="Moderator is already offline")

    event = StopModeratorEvent(moderator_id=moderator_id, reason="User requested stop")

    await kafka_producer.send(
        KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
    )

    return {"message": "Moderator stop request sent"}
