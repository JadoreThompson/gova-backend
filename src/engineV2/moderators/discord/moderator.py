import uuid
import asyncio
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from engineV2.action_handlers.discord.exceptions import DiscordActionHandlerError
from engineV2.actions.discord import BaseDiscordPerformedAction, DiscordActionType
from engineV2.actions.registry import PerformedActionRegistry
from engineV2.action_handlers.discord import DiscordActionHandler
from engineV2.agents.chat_summary import ChatSummaryAgent
from engineV2.agents.review import ReviewAgent
from engineV2.configs.discord import DiscordModeratorConfig
from engineV2.contexts.discord import DiscordMessageContext
from engineV2.params.discord import (
    DiscordPerformedActionParamsKick,
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
)
from enums import ActionStatus
from .models import DiscordReviewAgentOutput


class DiscordModerator:
    _type_2_action_definition = {
        DiscordActionType.REPLY: {
            "type": DiscordActionType.REPLY,
            "params": DiscordPerformedActionParamsReply.model_fields,
        },
        DiscordActionType.TIMEOUT: {
            "type": DiscordActionType.TIMEOUT,
            "params": DiscordPerformedActionParamsTimeout.model_fields,
        },
        DiscordActionType.KICK: {
            "type": DiscordActionType.KICK,
            "params": DiscordPerformedActionParamsKick.model_fields,
        },
    }

    def __init__(
        self,
        moderator_id: uuid.UUID,
        config: DiscordModeratorConfig,
        action_handler: DiscordActionHandler,
        max_channel_msgs: int = 100,
        on_action_performed: (
            Callable[
                [BaseDiscordPerformedAction, DiscordMessageContext], Awaitable[Any]
            ]
            | None
        ) = None,
        on_evaluation_created: Callable[[int, float], Awaitable[Any]] | None = None,
        on_closed: Callable[[str | None], Awaitable[Any]] | None = None,
    ):
        """Initialize a Discord moderator instance.

        Args:
            moderator_id: Unique identifier for the moderator.
            config: Configuration object containing guild, channels, and actions.
            action_handler: Interface used to perform the actions
            max_channel_msgs: Maximum number of messages to keep in memory per channel.
            on_action_performed: Callback triggered when an action is performed.
            on_evaluation_created: Callback triggered when an evaluation is created.
            on_closed: Callback triggered when the moderator is closed.
        """
        self._moderator_id = moderator_id
        self._config = config
        self._action_handler = action_handler
        self._guild_id = config.guild_id
        self._channels = set(config.channel_ids)
        self.on_action_performed = on_action_performed
        self.on_evaluation_created = on_evaluation_created
        self.on_closed = on_closed

        self._channel_msgs: dict[int, deque[DiscordMessageContext]] = defaultdict(
            lambda: deque(maxlen=max_channel_msgs)
        )
        self._channel_summaries: dict[int, str] = {}
        self._channel_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        self._action_params = [
            self.__class__._type_2_action_definition[action.type]
            for action in self._config.actions
        ]
        self._type_2_action = {action.type: action for action in self._config.actions}

        self._review_agent = ReviewAgent(output_type=DiscordReviewAgentOutput)
        self._chat_summary_agent = ChatSummaryAgent()

        self._closed = False
        self._closed_lock = asyncio.Lock()

    @property
    def moderator_id(self) -> uuid.UUID:
        """Get the moderator's unique identifier.

        Returns:
            The moderator's UUID.
        """
        return self._moderator_id

    @property
    def guild_id(self) -> int:
        """Get the Discord guild ID this moderator is managing.

        Returns:
            The Discord guild ID.
        """
        return self._guild_id

    async def is_closed(self) -> bool:
        """Check if the moderator is closed.

        Returns:
            True if the moderator is closed, False otherwise.
        """
        async with self._closed_lock:
            return self._closed

    async def process_message(self, ctx: DiscordMessageContext) -> None:
        """Process a Discord message and determine if moderation action is needed.

        This method analyzes the message in the context of recent messages,
        generates a channel summary, and uses the review agent to determine
        if any moderation action should be taken.

        Args:
            ctx: The Discord message context containing message details.
        """
        if await self.is_closed():
            return

        channel_id = ctx.channel_id
        if channel_id not in self._channels:
            return

        async with self._channel_locks[channel_id]:
            if await self.is_closed():
                return

            server_summary = self._config.guild_summary
            msgs = self._channel_msgs[channel_id]
            msgs.append(ctx)  # Added to window

            # Fetching summary
            user_prompt = self._chat_summary_agent.build_user_prompt(
                server_summary=server_summary,
                messages=list(msgs),
                channel_summary=self._channel_summaries.get(channel_id),
            )
            res = await self._chat_summary_agent.run(user_prompt)
            channel_summary = res.output.summary
            self._channel_summaries[channel_id] = channel_summary

            # Fetching review
            user_prompt = self._review_agent.build_user_prompt(
                server_summary=server_summary,
                channel_summary=channel_summary,
                guidelines=self._config.guidelines,
                message=ctx,
                action_params=self._action_params,
            )
            res = await self._review_agent.run(user_prompt)
            review_output = res.output

            if review_output.action is None:
                return

            defined_action = self._type_2_action[review_output.action.type]
            performed_action = PerformedActionRegistry.build(
                planned_action=review_output.action,
                defined_action=defined_action,
                reason=review_output.reason,
            )

        if self.on_evaluation_created is not None:
            await self.on_evaluation_created(
                ctx.user_id, review_output.severity_score, ctx
            )

        error_msg = None
        try:
            action_type = performed_action.type
            if action_type == DiscordActionType.REPLY:
                await self._action_handler.handle_reply(performed_action.params, ctx)
            elif action_type == DiscordActionType.TIMEOUT:
                await self._action_handler.handle_timeout(performed_action.params, ctx)
            elif action_type == DiscordActionType.KICK:
                await self._action_handler.handle_kick(performed_action.params, ctx)
            else:
                error_msg = "Handler for action '{action_type}' not configured"
        except DiscordActionHandlerError as e:
            error_msg = str(e)
            pass

        if self.on_action_performed is not None:
            if error_msg:
                performed_action.status = ActionStatus.FAILED
                performed_action.error_msg = error_msg

            await self.on_action_performed(performed_action, ctx)

    async def close(self, reason: str | None = None):
        """Close the moderator and stop processing messages.

        Args:
            reason: Optional reason for closing the moderator.
        """
        async with self._closed_lock:
            self._closed = True
            if self.on_closed is not None:
                await self.on_closed(reason)

    def __eq__(self, value) -> bool:
        if not isinstance(value, DiscordModerator):
            return False
        return value._moderator_id == self._moderator_id
