import logging
import uuid
import asyncio
from collections import defaultdict, deque

from pydantic import BaseModel

from config import KAFKA_MODERATOR_EVENTS_TOPIC
from engine.action_handlers.discord.exceptions import DiscordActionHandlerError
from engine.actions.discord import BaseDiscordPerformedAction, DiscordActionType
from engine.actions.registry import PerformedActionRegistry
from engine.action_handlers.discord import DiscordActionHandler
from engine.agents.chat_summary import ChatSummaryAgent
from engine.agents.review import ReviewAgent
from engine.configs.discord import DiscordModeratorConfig
from engine.contexts.discord import DiscordMessageContext
from engine.params.discord import (
    DiscordPerformedActionParamsKick,
    DiscordPerformedActionParamsReply,
    DiscordPerformedActionParamsTimeout,
)
from enums import ActionStatus
from events.moderator import (
    ActionPerformedModeratorEvent,
    DeadModeratorEvent,
    EvaluationCreatedModeratorEvent,
)
from infra.kafka.client import AsyncKafkaProducer
from .models import DiscordReviewAgentOutput


class DiscordModerator:
    _type_2_action_definition = {
        DiscordActionType.REPLY: {
            "type": DiscordActionType.REPLY,
            "params": DiscordPerformedActionParamsReply.model_fields,
            "summary": "This action allows you to send a message in the channel.",
        },
        DiscordActionType.TIMEOUT: {
            "type": DiscordActionType.TIMEOUT,
            "params": DiscordPerformedActionParamsTimeout.model_fields,
            "summary": """\
This action allows you to block the user from sending messages \
for `duration` seconds.
            """,
        },
        DiscordActionType.KICK: {
            "type": DiscordActionType.KICK,
            "params": DiscordPerformedActionParamsKick.model_fields,
            "summary": "This action allows you to kick the user from the server.",
        },
    }

    def __init__(
        self,
        moderator_id: uuid.UUID,
        config: DiscordModeratorConfig,
        client_id: int,
        action_handler: DiscordActionHandler,
        kafka_producer: AsyncKafkaProducer | None = None,
        max_channel_msgs: int = 100,
    ):
        """Initialize a Discord moderator instance.

        Args:
            moderator_id: Unique identifier for the moderator.
            config: Configuration object containing guild, channels, and actions.
            action_handler: Interface used to perform the actions
            max_channel_msgs: Maximum number of messages to keep in memory per channel
        """
        self._moderator_id = moderator_id
        self._client_id = client_id
        self._config = config
        self._action_handler = action_handler
        self._kafka_producer = kafka_producer

        self._guild_id = config.guild_id
        self._channels = set(config.channel_ids)

        self._channel_msgs: dict[int, deque[DiscordMessageContext]] = defaultdict(
            lambda: deque(maxlen=max_channel_msgs)
        )
        self._channel_summaries: dict[int, str] = {}
        self._channel_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        self._action_params = [
            self.__class__._type_2_action_definition[action.type]
            for action in self._config.actions
        ]
        self._type_2_defined_action = {
            action.type: action for action in self._config.actions
        }
        self._prev_actions: list[BaseDiscordPerformedAction] = deque(maxlen=10_000)

        self._review_agent = ReviewAgent(output_type=DiscordReviewAgentOutput)
        self._chat_summary_agent = ChatSummaryAgent()

        self._closed = False
        self._closed_lock = asyncio.Lock()

        self._logger = logging.getLogger(f"{type(self).__name__}-{moderator_id}")

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
                chat_summary=self._channel_summaries.get(channel_id),
            )
            res = await self._chat_summary_agent.run(user_prompt)
            channel_summary = res.output.summary
            self._channel_summaries[channel_id] = channel_summary

            # Fetching review
            user_prompt = self._review_agent.build_user_prompt(
                user_id=self._client_id,
                server_summary=server_summary,
                channel_summary=channel_summary,
                guidelines=self._config.guidelines,
                message=ctx,
                action_params=self._action_params,
                prev_actions=[
                    act.model_dump(mode="json") for act in self._prev_actions
                ],
                instructions=self._config.instructions,
            )
            res = await self._review_agent.run(user_prompt)
            review_output = res.output

        eval_event = EvaluationCreatedModeratorEvent(
            moderator_id=self._moderator_id,
            user_id=str(ctx.user_id),
            severity_score=review_output.severity_score,
            ctx=ctx,
        )
        await self._emit_event(eval_event)

        if review_output.action is None:
            return

        # Performing action
        action_type = review_output.action.type
        if action_type == DiscordActionType.REPLY:
            params = DiscordPerformedActionParamsReply(**review_output.action.params)
            handler = self._action_handler.handle_reply
        elif action_type == DiscordActionType.TIMEOUT:
            params = DiscordPerformedActionParamsTimeout(**review_output.action.params)
            handler = self._action_handler.handle_timeout
        elif action_type == DiscordActionType.KICK:
            params = DiscordPerformedActionParamsKick(**review_output.action.params)
            handler = self._action_handler.handle_kick
        else:
            self._logger.error(f"Handler for action '{action_type}' not configured")
            return

        defined_action = self._type_2_defined_action[review_output.action.type]

        error_msg = None
        if defined_action.requires_approval:
            status = ActionStatus.AWAITING_APPROVAL
        else:
            try:
                await handler(params, ctx)
                status = ActionStatus.COMPLETED
            except DiscordActionHandlerError as e:
                status = ActionStatus.FAILED
                error_msg = str(e)

        performed_action = PerformedActionRegistry.build(
            planned_action=review_output.action,
            defined_action=defined_action,
            reason=review_output.reason,
            status=status,
        )
        performed_action.error_msg = error_msg
        self._prev_actions.append(performed_action)

        action_event = ActionPerformedModeratorEvent(
            moderator_id=self._moderator_id,
            action=performed_action,
            ctx=ctx,
            evaluation_id=eval_event.id,
        )
        await self._emit_event(action_event)

    async def _emit_event(self, event: BaseModel) -> None:
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC, event.model_dump_json().encode()
        )

    async def close(self, reason: str | None = None):
        """Close the moderator and stop processing messages.

        Args:
            reason: Optional reason for closing the moderator.
        """
        async with self._closed_lock:
            self._closed = True
            event = DeadModeratorEvent(moderator_id=self._moderator_id, reason=reason)
            await self._emit_event(event)
