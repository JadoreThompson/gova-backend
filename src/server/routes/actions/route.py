from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import ActionStatus, MessagePlatformType
from engine.discord.action_handler import DiscordActionHandler
from db_models import ModeratorDeploymentEventLogs, ModeratorDeployments, Moderators
from engine.discord.actions import BanAction, DiscordActionType, KickAction, MuteAction
from engine.discord.context import DiscordMessageContext
from server.dependencies import depends_db_sess, depends_jwt, depends_discord_action_handler
from server.shared.models import DeploymentAction
from server.typing import JWTPayload
from .models import ActionUpdate


router = APIRouter(prefix="/actions", tags=["Actions"])


@router.patch("/{log_id}")
async def update_action_status(
    log_id: UUID,
    body: ActionUpdate,
    jwt: JWTPayload = Depends(depends_jwt()),
    session: AsyncSession = Depends(depends_db_sess),
    action_handler: DiscordActionHandler = Depends(depends_discord_action_handler),
):
    res = await session.execute(
        select(ModeratorDeploymentEventLogs, ModeratorDeployments.platform)
        .join(
            Moderators, Moderators.moderator_id == ModeratorDeploymentEventLogs.moderator_id
        )
        .join(ModeratorDeployments, ModeratorDeployments.deployment_id == ModeratorDeploymentEventLogs.deployment_id)
        .where(Moderators.user_id == jwt.sub, ModeratorDeploymentEventLogs.log_id == log_id)
    )

    data = res.first()
    if not data:
        raise HTTPException(status_code=404, detail="Action log not found")
    
    log, platform = data

    if body.status == ActionStatus.APPROVED:
        # Fulfilling action
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
                raise HTTPException(status_code=500, detail="Unknown discord action type.")

            ctx = DiscordMessageContext(**log.context)
            success = await action_handler.handle(action, ctx)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown platform '{platform}'."
            )

        status = ActionStatus.SUCCESS if success else ActionStatus.FAILED
    else:
        status = body.status

    log.status = status.value
    rsp_body = DeploymentAction(
        log_id=log.log_id,
        deployment_id=log.deployment_id,
        action_params=log.action_params,
        action_type=log.action_type,
        status=status,
        created_at=log.created_at,
    )
    await session.commit()

    return rsp_body

