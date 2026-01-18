from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import depends_db_sess, depends_jwt
from api.types import JWTPayload
from db_models import ActionEvents, Moderators
from engine.actions.discord import DiscordActionType
from engine.contexts.discord import DiscordMessageContext
from engine.params.discord import (
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
    DiscordPerformedActionParamsKick,
)
from enums import ActionStatus, MessagePlatform
from utils import get_datetime
from .models import ActionResponse
from .controller import get_discord_handler


router = APIRouter(prefix="/actions", tags=["Actions"])


@router.post("/{action_id}/approve", response_model=ActionResponse)
async def approve_action(
    action_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Approve and execute an action that is awaiting approval."""
    res = await db_sess.execute(
        select(ActionEvents, Moderators.platform, Moderators.conf)
        .join(Moderators, Moderators.moderator_id == ActionEvents.moderator_id)
        .where(Moderators.user_id == jwt.sub, ActionEvents.action_id == action_id)
    )

    data = res.first()
    if not data:
        raise HTTPException(status_code=404, detail="Action not found")

    action, platform, _ = data

    if action.status != ActionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Action not awaiting approval")

    if platform != MessagePlatform.DISCORD:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    handler = get_discord_handler()
    ctx = DiscordMessageContext(**action.context)
    success = False

    try:
        action_type = action.action_type
        params = action.action_params or {}

        if action_type == DiscordActionType.REPLY.value:
            reply_params = DiscordPerformedActionParamsReply(**params)
            await handler.handle_reply(reply_params, ctx)
            success = True

        elif action_type == DiscordActionType.TIMEOUT.value:
            timeout_params = DiscordPerformedActionParamsTimeout(**params)
            await handler.handle_timeout(timeout_params, ctx)
            success = True

        elif action_type == DiscordActionType.KICK.value:
            kick_params = DiscordPerformedActionParamsKick(**params)
            await handler.handle_kick(kick_params, ctx)
            success = True

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown action type: {action_type}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to execute action: {str(e)}"
        )

    new_status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
    now = get_datetime()

    action.status = new_status
    action.executed_at = now
    action.updated_at = now
    db_sess.add(action)
    
    await db_sess.commit()

    return ActionResponse(
        action_id=action.action_id,
        event_id=action.event_id,
        moderator_id=action.moderator_id,
        platform_user_id=action.platform_user_id,
        action_type=action.action_type,
        action_params=action.action_params,
        context=action.context,
        status=ActionStatus(action.status),
        reason=action.reason,
        created_at=action.created_at,
        updated_at=action.updated_at,
        executed_at=action.executed_at,
    )


@router.post("/{action_id}/reject", response_model=ActionResponse)
async def reject_action(
    action_id: UUID,
    jwt: JWTPayload = Depends(depends_jwt()),
    db_sess: AsyncSession = Depends(depends_db_sess),
):
    """Reject an action that is awaiting approval."""
    res = await db_sess.execute(
        select(ActionEvents, Moderators.platform)
        .join(Moderators, Moderators.moderator_id == ActionEvents.moderator_id)
        .where(Moderators.user_id == jwt.sub, ActionEvents.action_id == action_id)
    )

    data = res.first()
    if not data:
        raise HTTPException(status_code=404, detail="Action not found")

    action, _ = data

    if action.status != ActionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Action not awaiting approval")

    now = get_datetime()

    action.status = ActionStatus.REJECTED.value
    action.updated_at = now
    db_sess.add(action)

    await db_sess.commit()

    return ActionResponse(
        action_id=action.action_id,
        event_id=action.event_id,
        moderator_id=action.moderator_id,
        platform_user_id=action.platform_user_id,
        action_type=action.action_type,
        action_params=action.action_params,
        context=action.context,
        status=ActionStatus(action.status),
        reason=action.reason,
        created_at=action.created_at,
        updated_at=action.updated_at,
        executed_at=action.executed_at,
    )

