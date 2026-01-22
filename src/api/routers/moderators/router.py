import json
from datetime import timedelta
from uuid import UUID
from typing import Literal

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    CSVQuery,
    depends_db_sess,
    depends_jwt,
    depends_kafka_producer,
)
from api.models import PaginatedResponse
from api.routers.actions.models import ActionResponse
from api.types import JWTPayload
from config import KAFKA_MODERATOR_EVENTS_TOPIC, PAGE_SIZE, PricingTierLimits
from db_models import Moderators, EvaluationEvents, ActionEvents, Users
from engine.configs.discord import DiscordModeratorConfig
from enums import ActionStatus, MessagePlatform, ModeratorStatus
from events.moderator import (
    StartModeratorEvent,
    StopModeratorEvent,
    UpdateConfigModeratorEvent,
)
from infra.kafka import AsyncKafkaProducer
from services.discord import DiscordService
from services.encryption import EncryptionService
from utils import build_config, get_datetime
from .models import (
    ModeratorCreate,
    ModeratorResponse,
    ModeratorUpdate,
    ModeratorStats,
    BarChartData,
    BehaviorScoreResponse,
)


router = APIRouter(prefix="/moderators", tags=["Moderators"])


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

    existing = await db_sess.scalar(
        select(Moderators.moderator_id).where(
            Moderators.platform_server_id == body.platform_server_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Moderator already configured for platform server {body.platform_server_id}",
        )

    try:
        build_config(body.platform, body.conf)
    except NotImplementedError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        "1w": (now - timedelta(days=6), "day"),
        "1m": (now - timedelta(days=29), "week"),
        "1y": (now - timedelta(days=364), "month"),
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
            func.date_trunc(bucket_type, ActionEvents.created_at).label("bucket"),
            func.count(ActionEvents.action_id).label("count"),
        )
        .where(
            ActionEvents.moderator_id == moderator_id,
            ActionEvents.created_at >= start_date,
        )
        .group_by("bucket")
    )
    act_result = await db_sess.execute(act_buckets_query)

    act_buckets = {row.bucket.date(): row.count for row in act_result}

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
            error_msg=act.error_msg,
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
    kafka_producer: AsyncKafkaProducer = Depends(depends_kafka_producer),
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

    status_code = 200
    event = None
    if body.conf is not None:
        try:
            validated_config = build_config(moderator.platform, body.conf)
        except NotImplementedError as e:
            raise HTTPException(status_code=500, detail=str(e))

        if moderator.status != ModeratorStatus.OFFLINE:
            dumped_config = validated_config.model_dump(mode="json")
            event = UpdateConfigModeratorEvent(
                moderator_id=moderator_id, config=dumped_config
            ).model_dump(mode="json")
            status_code = 202
        else:
            moderator.conf = body.conf

    if body.name is not None:
        moderator.name = body.name
    if body.description is not None:
        moderator.description = body.description

    await db_sess.commit()

    if event is not None:
        await kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, json.dumps(event).encode()
        )

    return JSONResponse(
        status_code=status_code,
        content=ModeratorResponse(
            moderator_id=moderator.moderator_id,
            name=moderator.name,
            description=moderator.description,
            platform=MessagePlatform(moderator.platform),
            platform_server_id=moderator.platform_server_id,
            conf=moderator.conf,
            status=ModeratorStatus(moderator.status),
            created_at=moderator.created_at,
        ).model_dump(mode="json"),
    )


@router.delete("/{moderator_id}", status_code=204)
async def delete_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Delete a moderator. Only allowed if moderator is offline."""
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
            status_code=400,
            detail="Cannot delete moderator that is not offline. Stop the moderator first.",
        )

    await db_sess.delete(moderator)
    await db_sess.commit()


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


@router.get(
    "/{moderator_id}/scores", response_model=PaginatedResponse[BehaviorScoreResponse]
)
async def list_behavior_scores(
    moderator_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(PAGE_SIZE, ge=1, le=100),
    order: Literal["asc", "desc"] | None = Query(None),
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """List behavior scores for all users in a moderator's guild with pagination."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user or not user.discord_oauth_payload:
        raise HTTPException(status_code=400, detail="Discord OAuth not configured")

    oauth_payload = EncryptionService.decrypt(
        user.discord_oauth_payload, str(user.user_id)
    )
    refreshed_payload = await DiscordService.refresh_token(oauth_payload)

    if refreshed_payload != oauth_payload:
        user.discord_oauth_payload = json.dumps(refreshed_payload)
        await db_sess.commit()

    access_token = refreshed_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Invalid OAuth token")

    subquery = (
        select(
            EvaluationEvents.platform_user_id,
            func.max(EvaluationEvents.created_at).label("latest_created_at"),
        )
        .where(EvaluationEvents.moderator_id == moderator_id)
        .group_by(EvaluationEvents.platform_user_id)
        .subquery()
    )

    query = (
        select(EvaluationEvents.platform_user_id, EvaluationEvents.behaviour_score)
        .join(
            subquery,
            (EvaluationEvents.platform_user_id == subquery.c.platform_user_id)
            & (EvaluationEvents.created_at == subquery.c.latest_created_at),
        )
        .where(EvaluationEvents.moderator_id == moderator_id)
    )

    if order == "asc":
        query = query.order_by(EvaluationEvents.behaviour_score.asc())
    elif order == "desc":
        query = query.order_by(EvaluationEvents.behaviour_score.desc())

    query = query.offset(skip).limit(limit + 1)

    result = await db_sess.execute(query)
    scores = result.all()

    has_next = len(scores) > limit
    scores_data = scores[:limit]

    data = []
    for score in scores_data:
        username = "Unknown"

        if moderator.platform == MessagePlatform.DISCORD.value:
            member_data = await DiscordService.fetch_guild_member_by_bot(
                moderator.platform_server_id, score.platform_user_id
            )
            if member_data and "user" in member_data:
                username = member_data["user"].get("username", "Unknown")

        data.append(
            BehaviorScoreResponse(
                user_id=score.platform_user_id,
                username=username,
                behaviour_score=score.behaviour_score,
            )
        )

    return PaginatedResponse[BehaviorScoreResponse](
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(data),
        has_next=has_next,
        data=data,
    )


@router.get("/{moderator_id}/scores/{user_id}", response_model=BehaviorScoreResponse)
async def get_user_behavior_score(
    moderator_id: UUID,
    user_id: str,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Get behavior score for a specific user in a moderator's guild."""
    moderator = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id,
            Moderators.user_id == jwt.sub,
        )
    )
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator not found")

    user = await db_sess.scalar(select(Users).where(Users.user_id == jwt.sub))
    if not user or not user.discord_oauth_payload:
        raise HTTPException(status_code=400, detail="Discord OAuth not configured")

    oauth_payload = EncryptionService.decrypt(
        user.discord_oauth_payload, str(user.user_id)
    )
    refreshed_payload = await DiscordService.refresh_token(oauth_payload)

    if refreshed_payload != oauth_payload:
        user.discord_oauth_payload = json.dumps(refreshed_payload)
        await db_sess.commit()

    access_token = refreshed_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Invalid OAuth token")

    latest_evaluation = await db_sess.scalar(
        select(EvaluationEvents)
        .where(
            EvaluationEvents.moderator_id == moderator_id,
            EvaluationEvents.platform_user_id == user_id,
        )
        .order_by(EvaluationEvents.created_at.desc())
        .limit(1)
    )

    if latest_evaluation is None:
        raise HTTPException(status_code=404, detail="User score not found")

    username = "Unknown"

    if moderator.platform == MessagePlatform.DISCORD.value:
        member_data = await DiscordService.fetch_guild_member_by_bot(
            moderator.platform_server_id, user_id
        )
        if member_data and "user" in member_data:
            username = member_data["user"].get("username", "Unknown")

    return BehaviorScoreResponse(
        user_id=user_id,
        username=username,
        behaviour_score=latest_evaluation.behaviour_score,
    )
