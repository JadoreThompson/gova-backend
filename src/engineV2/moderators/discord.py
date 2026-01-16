import uuid
import asyncio
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from engineV2.actions.discord import BaseDiscordPerformedAction, DiscordActionType
from engineV2.actions.registry import PerformedActionRegistry
from engineV2.agents.chat_summary import ChatSummaryAgent
from engineV2.agents.review import ReviewAgent, ReviewAgentAction, ReviewAgentOutput
from engineV2.configs.discord import DiscordModeratorConfig
from engineV2.contexts.discord import DiscordMessageContext
from engineV2.params.discord import (
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
    DiscordPerformedActionParamsKick,
)


class DiscordReviewAgentAction(ReviewAgentAction[DiscordActionType]):
    pass


class DiscordReviewAgentOutput(ReviewAgentOutput):
    action: DiscordReviewAgentAction | None = None


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
        max_channel_msgs: int = 100,
        on_action_performed: (
            Callable[[BaseDiscordPerformedAction], Awaitable[Any]] | None
        ) = None,
        on_evaluation_created: Callable[[int, float], Awaitable[Any]] | None = None,
        on_closed: Callable[[str | None], Awaitable[Any]] | None = None,
    ):
        self._moderator_id = moderator_id
        self._config = config
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
        return self._moderator_id

    @property
    def guild_id(self) -> int:
        return self._guild_id

    async def is_closed(self) -> bool:
        async with self._closed_lock:
            return self._closed

    async def process_message(self, ctx: DiscordMessageContext) -> None:
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
            await self.on_evaluation_created(ctx.user_id, review_output.severity_score)

        if self.on_action_performed is not None:
            await self.on_action_performed(performed_action)

    async def close(self, reason: str | None = None):
        async with self._closed_lock:
            self._closed = True
            if self.on_closed is not None:
                await self.on_closed(reason)

    def __eq__(self, value):
        if not isinstance(value, DiscordModerator):
            return False
        return value._moderator_id == self._moderator_id
