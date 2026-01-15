import uuid
from typing import Any, Awaitable, Callable

from engineV2.actions.discord import BaseDiscordPerformedAction, DiscordActionType
from engineV2.agents import ReviewAgent
from engineV2.agents.review import ReviewAgentAction, ReviewAgentOutput
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
        on_action_performed: Callable[
            [BaseDiscordPerformedAction], Awaitable[Any]
        ] = None,
    ):
        self._moderator_id = moderator_id
        self._config = config
        self._guild_id = config.guild_id
        self._channels = set(config.channel_ids)
        self._action_params = [
            self.__class__._type_2_action_definition[action.type]
            for action in self._config.actions
        ]
        self.on_action_performed = on_action_performed

        self._review_agent = ReviewAgent(output_type=DiscordReviewAgentOutput)
        self._stopped = False

    @property
    def moderator_id(self) -> uuid.UUID:
        return self._moderator_id

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def stopped(self) -> bool:
        return self._stopped

    async def process_message(self): ...

    async def process_messages(self, msgs: list[DiscordMessageContext]) -> None:
        # - Must abide by guidelines
        # - Track this conversational thread

        for msg in msgs:
            user_prompt = self._review_agent.build_user_prompt(
                self._config.guild_summary,
                self._config.guidelines,
                msg,
                self._action_params,
            )
            res = await self._review_agent.run(user_prompt)
            output = res.output

    def stop(self):
        self._stopped = True

    def __eq__(self, value):
        if not isinstance(value, DiscordModerator):
            return False
        return (value._moderator_id == self._moderator_id) or super().__eq__(value)
