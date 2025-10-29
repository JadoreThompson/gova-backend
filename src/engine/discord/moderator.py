import asyncio
import json
from typing import Any, Literal
from uuid import UUID

import discord
from aiohttp import ClientError

import engine.discord.actions as actions_module
from config import FINAL_PROMPT_TEMPLATE, FINAL_SYSTEM_PROMPT
from core.models import CustomBaseModel
from engine.base_moderator import BaseModerator
from engine.base_action import BaseActionDefinition
from engine.discord.actions import (
    BanAction,
    DiscordAction,
    DiscordActionType,
    MuteAction,
)
from engine.discord.action_handler import DiscordActionHandler
from engine.discord.context import DiscordMessageContext
from engine.enums import MaliciousState
from engine.models import TopicEvaluation, MessageEvaluation
from engine.prompt_validator import PromptValidator
from engine.task_pool import TaskPool
from utils.llm import fetch_response, parse_to_json
from .config import DiscordConfig
from .stream import DiscordStream


class DiscordModerator(BaseModerator):
    def __init__(
        self,
        deployment_id: UUID,
        moderator_id: UUID,
        action_handler: DiscordActionHandler = None,
        logger=None,
        *,
        token: str,
        config: DiscordConfig,
    ):
        super().__init__(deployment_id, moderator_id, action_handler, logger)
        self._token = token
        self._config = config
        self._client: discord.Client | None = None
        self._stream: DiscordStream | None = None
        self._allowed_action_formats: list[dict] | None = None

    async def moderate(self) -> None:
        self._logger.info("Launching moderation...")

        self._task_pool = TaskPool(size=20)
        self._stream = DiscordStream(
            self._config.guild_id, self._config.allowed_channels
        )

        async with self._background_executor:
            async with self._task_pool:
                async for ctx in self._stream:
                    if self._client is None:
                        self._client = self._stream.client
                        self._action_handler = DiscordActionHandler(
                            self._client, self._logger
                        )

                    await self._task_pool.submit(self._handle_context(ctx))

    async def _evaluate(
        self, ctx: DiscordMessageContext, max_attempts: int = 3
    ) -> MessageEvaluation | None:
        self._logger.info("Validating prompt")
        mal_state = await PromptValidator.validate_prompt(ctx.content)

        if mal_state == MaliciousState.MALICIOUS:
            self._logger.critical(f'Malicious content "{ctx.content}"')
            return None

        self._logger.info("Checking guidelines.")
        if not self._guidelines:
            self._guidelines, self._topics = await self._fetch_guidelines()

        self._logger.info("Building actions list.")
        if self._allowed_action_formats is None:
            self._allowed_action_formats = self._build_action_formats(
                self._config.allowed_actions
            )

        self._logger.info("Fetching evaluation.")
        attempt = 0
        while attempt < max_attempts:
            try:
                similars = await self._fetch_similar(ctx.content)
                topic_scores = (
                    await self._handle_similars(ctx, similars)
                    if similars
                    else await self._fetch_topic_scores(ctx, self._topics)
                )

                prompt = FINAL_PROMPT_TEMPLATE.format(
                    guidelines=self._guidelines,
                    topics=self._topics,
                    topic_scores=topic_scores,
                    message=ctx.content,
                    action_formats=self._allowed_action_formats,
                    context=ctx.to_serialisable_dict(),
                )

                content = await fetch_response(
                    [
                        {"role": "system", "content": FINAL_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=1
                )
                data = parse_to_json(content["choices"][0]["message"]["content"])

                action_data = data.get("action")
                action = None
                if action_data:
                    action_data["requires_approval"] = (
                        False  # TODO: Match this with the definition
                    )
                    action = self._build_action(action_data)

                return MessageEvaluation(
                    evaluation_score=data["evaluation_score"],
                    action=action,
                    topic_evaluations=[
                        TopicEvaluation(topic=k, topic_score=v)
                        for k, v in topic_scores.items()
                    ],
                )

            except (
                ClientError,
                asyncio.TimeoutError,
                json.JSONDecodeError,
                ValueError,
            ) as e:
                self._logger.warning(
                    f"Attempt {attempt + 1} failed. Error: {type(e).__name__} - {str(e)}"
                )
                import traceback

                traceback.print_exc()
            finally:
                attempt += 1

        return None

    def _build_action(self, data: dict[str, Any]) -> DiscordAction:
        """Instantiate the correct DiscordAction subclass based on type."""
        typ = data.get("type")

        if typ == DiscordActionType.BAN:
            return BanAction(**data)
        if typ == DiscordActionType.MUTE:
            return MuteAction(**data)

        raise NotImplementedError(f"Action type '{typ}' not implemented.")

    def _build_action_formats(
        self, action_defs: list[BaseActionDefinition | Literal["*"]]
    ) -> list[dict]:
        """Generate JSON schemas for allowed Discord actions."""
        formats: list[dict] = []
        mod_dict = actions_module.__dict__

        if action_defs[0] == "*":
            for key, _cls in mod_dict.items():
                if key.endswith("Definition") and issubclass(_cls, CustomBaseModel):
                    formats.append(_cls.model_json_schema())
        else:
            for ac_def in action_defs:
                key = ac_def.__class__.__name__.replace("Definition", "")
                ac_cls: CustomBaseModel = mod_dict.get(key)
                if ac_cls:
                    formats.append(ac_cls.model_json_schema())

        return formats

    async def __aexit__(self, exc_type, exc_value, tcb):
        """Cleanup client and stream on shutdown."""
        self._client = None
        self._stream = None
        await super().__aexit__(exc_type, exc_value, tcb)
