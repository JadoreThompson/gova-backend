from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from db_models import Guidelines
from server.dependencies import depends_db_sess, depends_jwt
from server.models import PaginatedResponse
from server.typing import JWTPayload
from .controllers import get_breach_types
from .models import GuidelineCreate, GuidelineUpdate, GuidelineResponse


router = APIRouter(prefix="/guidelines", tags=["Guidelines"])


@router.post("/", response_model=GuidelineResponse)
async def create_guideline(
    body: GuidelineCreate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    breach_types = await get_breach_types("Guidelines:\n" + body.text)
    res = await db_sess.scalar(
        insert(Guidelines)
        .values(
            user_id=jwt.sub, name=body.name, text=body.text, breach_types=breach_types
        )
        .returning(Guidelines)
    )

    if not res:
        raise HTTPException(status_code=500, detail="Failed to create guideline")

    rsp_body = GuidelineResponse(
        guideline_id=res.guideline_id,
        name=res.name,
        text=res.text,
        breach_types=res.breach_types,
        created_at=res.created_at,
    )

    await db_sess.commit()
    return rsp_body


@router.get("/", response_model=PaginatedResponse[GuidelineResponse])
async def list_guidelines(
    page: int = Query(ge=1),
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    result = await db_sess.scalars(
        select(Guidelines)
        .where(Guidelines.user_id == jwt.sub)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE + 1)
    )
    rows = result.all()
    n = len(rows)

    return PaginatedResponse[GuidelineResponse](
        page=page,
        size=min(n, PAGE_SIZE),
        has_next=n > PAGE_SIZE,
        data=[
            GuidelineResponse(
                guideline_id=g.guideline_id,
                name=g.name,
                text=g.text,
                breach_types=g.breach_types,
                created_at=g.created_at,
            )
            for g in rows[:PAGE_SIZE]
        ],
    )


@router.get("/{guideline_id}", response_model=GuidelineResponse)
async def get_guideline(
    guideline_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await db_sess.scalar(
        select(Guidelines).where(
            Guidelines.guideline_id == guideline_id,
            Guidelines.user_id == jwt.sub,
        )
    )
    if not res:
        raise HTTPException(status_code=404, detail="Guideline not found")

    return GuidelineResponse(
        guideline_id=res.guideline_id,
        name=res.name,
        text=res.text,
        breach_types=res.breach_types,
        created_at=res.created_at,
    )


@router.put("/{guideline_id}", response_model=GuidelineResponse)
async def update_guideline(
    guideline_id: UUID,
    body: GuidelineUpdate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    vals = body.model_dump(exclude_unset=True, exclude_none=True)
    if not vals:
        raise HTTPException(
            status_code=400, detail="Either name or text must be provided."
        )

    updated = await db_sess.scalar(
        update(Guidelines)
        .where(Guidelines.guideline_id == guideline_id, Guidelines.user_id == jwt.sub)
        .values(**vals)
        .returning(Guidelines)
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Guideline not found")

    rsp_body = GuidelineResponse(
        guideline_id=updated.guideline_id,
        name=updated.name,
        text=updated.text,
        breach_types=updated.breach_types,
        created_at=updated.created_at,
    )
    await db_sess.commit()
    return rsp_body


@router.delete("/{guideline_id}")
async def delete_guideline(
    guideline_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    res = await db_sess.scalar(
        delete(Guidelines)
        .where(Guidelines.guideline_id == guideline_id, Guidelines.user_id == jwt.sub)
        .returning(Guidelines.guideline_id)
    )

    if not res:
        raise HTTPException(status_code=404, detail="Guideline not found")

    await db_sess.commit()
    return {"message": "Guideline deleted successfully"}
