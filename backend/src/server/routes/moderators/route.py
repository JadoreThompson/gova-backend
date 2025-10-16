from uuid import UUID, uuid4

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import KAFKA_DEPLOYMENT_EVENTS_TOPIC, PAGE_SIZE
from core.enums import MessagePlatformType
from core.events import DeploymentEvent
from db_models import ModeratorDeployments, Moderators
from engine.discord.config import DiscordConfig
from server.dependencies import depends_db_sess, depends_jwt, depends_kafka_producer
from server.models import PaginatedResponse
from server.typing import JWTPayload
from utils.kafka import dump_model
from .models import (
    ModeratorCreate,
    ModeratorDeploymentResponse,
    ModeratorResponse,
    ModeratorUpdate,
    ModeratorDeploymentCreate,
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
    rsp_body = ModeratorResponse(
        moderator_id=mod.moderator_id,
        name=body.name,
        guideline_id=body.guideline_id,
        created_at=mod.created_at,
    )
    await db_sess.commit()
    return rsp_body


@router.post("/deploy/{moderator_id}", response_model=ModeratorDeploymentResponse)
async def deploy_moderator(
    moderator_id: UUID,
    body: ModeratorDeploymentCreate,
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

    rsp_body = ModeratorDeploymentResponse(
        deployment_id=dep.deployment_id,
        moderator_id=moderator_id,
        platform=dep.platform,
        conf=conf,
        state=dep.state,
        created_at=dep.created_at,
    )

    ev = DeploymentEvent(
        deployment_id=dep.deployment_id, platform=body.platform, conf=conf
    )
    await db_sess.commit()

    await kafka_producer.send(KAFKA_DEPLOYMENT_EVENTS_TOPIC, dump_model(ev))

    return rsp_body


@router.get("/", response_model=PaginatedResponse[ModeratorResponse])
async def list_moderators(
    page: int = Query(ge=1),
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await db_sess.scalars(
        select(Moderators)
        .where(Moderators.user_id == jwt.sub)
        .offset((page - 1) * 10)
        .limit(PAGE_SIZE + 1)
    )
    
    mods = res.all()
    n = len(res)

    return PaginatedResponse[ModeratorResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            ModeratorResponse(
                moderator_id=m.moderator_id,
                name=m.name,
                guidline_id=m.guideline_id,
                created_at=m.created_at,
            )
            for m in mods[:PAGE_SIZE]
        ],
    )


@router.get("/{moderator_id}")
async def get_moderator(
    moderator_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    mod = await db_sess.scalar(
        select(Moderators).where(
            Moderators.moderator_id == moderator_id, Moderators.user_id == jwt.sub
        )
    )
    if not mod:
        raise HTTPException(status_code=404, detail="Moderator not found")
    return ModeratorResponse(
        moderator_id=mod.moderator_id,
        name=mod.name,
        guideline_id=mod.guideline_id,
        created_at=mod.created_at,
    )


@router.put("/{moderator_id}")
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

    await db_sess.commit()
    return ModeratorResponse(
        moderator_id=updated.moderator_id,
        name=updated.name,
        guideline_id=updated.guideline_id,
        created_at=updated.created_at,
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
