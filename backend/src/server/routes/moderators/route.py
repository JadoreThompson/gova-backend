from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from db_models import Moderators
from server.dependencies import depends_db_sess, depends_jwt
from server.models import PaginatedResponse
from server.typing import JWTPayload
from .models import (
    ModeratorBase,
    ModeratorCreate,
    ModeratorResponse,
    ModeratorUpdate,
)


router = APIRouter(prefix="/moderators", tags=["Moderators"])


@router.post("/", response_model=ModeratorResponse)
async def create_moderator(
    body: ModeratorCreate,
    jwt: JWTPayload = Depends(depends_jwt),
    db: AsyncSession = Depends(depends_db_sess),
):
    result = await db.scalar(
        insert(Moderators)
        .values(user_id=jwt.sub, name=body.name, guideline_id=body.guideline_id)
        .returning(Moderators)
    )
    rsp_body = ModeratorResponse(
        name=body.name, guideline_id=body.guideline_id, created_at=result.created_at
    )
    await db.commit()
    return rsp_body


@router.get("/")
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
                name=m.name, guidline_id=m.guideline_id, created_at=m.created_at
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
        name=mod.name, guideline_id=mod.guideline_id, created_at=mod.created_at
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
