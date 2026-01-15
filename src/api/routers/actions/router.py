from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import ActionStatus, MessagePlatformType
from engine.discord.action_handler import DiscordActionHandler
from db_models import ModeratorEventLogs, Moderators
from engine.discord.actions import BanAction, DiscordActionType, KickAction, MuteAction
from engine.discord.context import DiscordMessageContext
from api.dependencies import (
    depends_db_sess,
    depends_jwt,
    depends_discord_action_handler,
)
from api.shared.models import ActionResponse
from api.types import JWTPayload
from .models import ActionUpdate


router = APIRouter(prefix="/actions", tags=["Actions"])


@router.patch("/{log_id}", response_model=ActionResponse)
async def update_action_status(
    log_id: UUID,
    body: ActionUpdate,
    jwt: JWTPayload = Depends(depends_jwt()),
    session: AsyncSession = Depends(depends_db_sess),
    action_handler: DiscordActionHandler = Depends(depends_discord_action_handler),
):
    res = await session.execute(
        select(ModeratorEventLogs, Moderators.platform)
        .join(Moderators, Moderators.moderator_id == ModeratorEventLogs.moderator_id)
        .where(Moderators.user_id == jwt.sub, ModeratorEventLogs.log_id == log_id)
    )

    data = res.first()
    if not data:
        raise HTTPException(status_code=404, detail="Action log not found")

    log, platform = data
    if log.action_status != ActionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Action not awaiting approval.")

    if body.status == ActionStatus.APPROVED:
        if platform == MessagePlatformType.DISCORD:
            params = log.action_params
            act_typ = params.get("type")

            if act_typ == DiscordActionType.BAN:
                action = BanAction(**params)
            elif act_typ == DiscordActionType.KICK:
                action = KickAction(**params)
            elif act_typ == DiscordActionType.MUTE:
                action = MuteAction(**params)
            else:
                raise HTTPException(
                    status_code=500, detail="Unknown discord action type."
                )

            ctx = DiscordMessageContext(**log.context)
            success = await action_handler.handle(action, ctx)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown platform '{platform}'."
            )

        new_status = ActionStatus.SUCCESS if success else ActionStatus.FAILED
    else:
        new_status = body.status

    log.status = new_status.value
    rsp_body = ActionResponse(
        log_id=log.log_id,
        action_params=log.action_params,
        action_type=log.action_type,
        status=new_status,
        created_at=log.created_at,
    )
    await session.commit()

    return rsp_body
