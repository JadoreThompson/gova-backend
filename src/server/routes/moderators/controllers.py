from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import Moderators, ModeratorDeployments
from config import PAGE_SIZE


async def fetch_moderators_with_platforms(
    db_sess: AsyncSession,
    user_id: UUID,
    moderator_id: UUID | None = None,
    name: str | None = None,
    page: int | None = None,
):
    """
    Reusable query to fetch moderators with aggregated deployment platforms.
    Supports filtering by moderator_id, name, and pagination.
    """
    query = (
        select(
            Moderators,
            func.array_agg(func.distinct(ModeratorDeployments.platform)).label(
                "platforms"
            ),
        )
        .join(
            ModeratorDeployments,
            ModeratorDeployments.moderator_id == Moderators.moderator_id,
            isouter=True,
        )
        .where(Moderators.user_id == user_id)
        .group_by(Moderators.moderator_id)
        .order_by(Moderators.created_at.desc())
    )

    if moderator_id:
        query = query.where(Moderators.moderator_id == moderator_id)
    if name:
        query = query.where(Moderators.name.like(f"%{name}%"))
    if page is not None:
        query = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)

    res = await db_sess.execute(query)
    return res.all()
