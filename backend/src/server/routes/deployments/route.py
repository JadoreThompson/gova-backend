from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from core.enums import MessagePlatformType, ModeratorDeploymentStatus
from db_models import ModeratorDeployments, Moderators
from server.dependencies import depends_db_sess, depends_jwt
from server.models import PaginatedResponse
from server.typing import JWTPayload
from .models import DeploymentUpdate, DeploymentResponse


router = APIRouter(prefix="/deployments", tags=["Moderator Deployments"])


@router.get("/", response_model=PaginatedResponse[DeploymentResponse])
async def list_deployments(
    page: int = Query(ge=1),
    name: str | None = None,
    status: list[ModeratorDeploymentStatus] | None = None,
    platform: list[MessagePlatformType] | None = None,
    jwt: JWTPayload = Depends(depends_jwt),
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
        query = query.where(ModeratorDeployments.state.in_([s.value for s in status]))
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
                status=d.state,
                created_at=d.created_at,
            )
            for d in deployments[:PAGE_SIZE]
        ],
    )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
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
        status=dep.state,
        created_at=dep.created_at,
    )


@router.put("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    body: DeploymentUpdate,
    jwt: JWTPayload = Depends(depends_jwt),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    vals = body.model_dump(exclude_unset=True, exclude_none=True)
    if not vals:
        raise HTTPException(status_code=400, detail="No update fields provided.")

    dep = await db_sess.scalar(
        update(ModeratorDeployments)
        .where(
            ModeratorDeployments.deployment_id == deployment_id,
            ModeratorDeployments.moderator_id.in_(
                select(Moderators.moderator_id).where(Moderators.user_id == jwt.sub)
            ),
        )
        .values(**vals)
        .returning(ModeratorDeployments)
    )
    if not dep:
        raise HTTPException(
            status_code=404, detail="Deployment not found or unauthorized."
        )

    # TODO: Emit event to kafka channel

    await db_sess.commit()

    return DeploymentResponse(
        deployment_id=dep.deployment_id,
        moderator_id=dep.moderator_id,
        platform=dep.platform,
        name=dep.name,
        conf=dep.conf,
        status=dep.state,
        created_at=dep.created_at,
    )


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt),
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
