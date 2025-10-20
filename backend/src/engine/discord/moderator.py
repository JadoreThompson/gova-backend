import asyncio
import json
import logging
from typing import Any, Literal
from uuid import UUID

import discord
from aiohttp import ClientError

import engine.discord.actions as actions_module
from config import FINAL_PROMPT_TEMPLATE, FINAL_SYSTEM_PROMPT
from core.enums import ActionStatus
from core.models import CustomBaseModel
from engine.base_moderator import BaseModerator
from engine.discord.actions import (
    BanAction,
    DiscordAction,
    DiscordActionType,
    MuteAction,
)
from engine.base_action import BaseActionDefinition
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
        self, deployment_id: UUID, moderator_id: UUID, token: str, config: DiscordConfig
    ) -> None:
        super().__init__(
            deployment_id,
            moderator_id,
            logging.getLogger(f"discord-moderator-{moderator_id}"),
        )
        self._token = token
        self._config = config
        self._client: discord.Client | None = None
        self._stream: DiscordStream | None = None
        self._action_handler: DiscordActionHandler | None = None
        self._allowed_action_formats: list[dict] | None = None

    async def moderate(self) -> None:
        self._logger.info("Launching moderation...")

        self._task_pool = TaskPool(size=20)
        self._stream = DiscordStream(
            self._config.guild_id, self._config.allowed_channels
        )

        async with self._task_pool:
            async for ctx in self._stream:
                if self._client is None:
                    self._client = self._stream.client
                    self._action_handler = DiscordActionHandler(
                        self._client, self._logger
                    )
                await self._task_pool.submit(self._handle_context(ctx))

    async def _handle_context(self, ctx: DiscordMessageContext) -> None:
        evaluation = await self._evaluate(ctx)
        if not evaluation:
            return

        await self._save_evaluation(evaluation, ctx)

        if evaluation.action:
            action = evaluation.action
            self._logger.info(f"Performing action '{action.type}'")
            log_id = await self._log_action(action)

            if action.requires_approval:
                await self._update_action_status(log_id, ActionStatus.AWAITING_APPROVAL)
            else:
                success = await self._action_handler.handle(action, ctx)
                if success:
                    await self._update_action_status(log_id, ActionStatus.SUCCESS)

    async def _evaluate(
        self, ctx: DiscordMessageContext, max_attempts: int = 3
    ) -> MessageEvaluation | None:
        self._logger.info("Validating prompt")
        mal_state = await PromptValidator.validate_prompt(ctx.content)
        if mal_state == MaliciousState.MALICIOUS:
            self._logger.critical(f'Malicious content "{ctx.content}"')
            return

        self._logger.info("Checking guidelines.")
        if not self._guidelines:
            self._guidelines, self._topics = await self._fetch_guidelines()

        self._logger.info("Building actions list.")

        if self._allowed_action_formats is None:
            self._allowed_action_formats = self._build_action_formats(
                self._config.allowed_actions
            )

        self._logger.info("Fetching eval.")
        attempt = 0
        while attempt < max_attempts:
            try:
                similars = await self._fetch_similar(ctx.content)
                if similars:
                    topic_scores = await self._handle_similars(ctx, similars)
                else:
                    topic_scores = await self._fetch_topic_scores(ctx, self._topics)

                # Final Output
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
                    ]
                )
                data = parse_to_json(content["choices"][0]["message"]["content"])

                action_data = data.get("action")
                if action_data:
                    action_data["requires_approval"] = False
                    action = self._build_action(action_data)
                else:
                    action = None

                evaluation = MessageEvaluation(
                    evaluation_score=data["evaluation_score"],
                    action=action,
                    topic_evaluations=[
                        TopicEvaluation(topic=key, topic_score=val)
                        for key, val in topic_scores.items()
                    ],
                )

                return evaluation
            except (
                ClientError,
                asyncio.TimeoutError,
                json.JSONDecodeError,
                ValueError,
            ) as e:
                self._logger.info(
                    f"Attempt {attempt + 1} failed. Error -> {type(e)} - {str(e)}"
                )
                import traceback

                traceback.print_exc()
            finally:
                attempt += 1

    def _build_action(self, data: dict[str, Any]) -> DiscordAction:
        typ = data.get("type")

        if typ == DiscordActionType.BAN:
            return BanAction(**data)
        if typ == DiscordActionType.MUTE:
            return MuteAction(**data)

        raise NotImplemented(f"Action type '{typ}' not implemented.")

    def _build_action_formats(
        self, action_defs: list[BaseActionDefinition | Literal["*"]]
    ) -> list[dict]:
        formats: list[dict] = []
        mod_dict = actions_module.__dict__

        if action_defs[0] == "*":
            keys = [*mod_dict.keys()]
            for key in keys:
                if key.endswith("Definition"):
                    _cls: CustomBaseModel = mod_dict.get(key)
                    if _cls:
                        formats.append(_cls.model_json_schema())
        else:
            for ac_def in action_defs:
                key = ac_def.__class__.__name__.replace("Definition", "")
                ac: CustomBaseModel = actions_module.__dict__.get(key)
                if ac:
                    formats.append(ac.model_json_schema())

        return formats

    async def __aexit__(self, exc_type, exc_value, tcb):
        self._client = None
        self._stream = None
        await super().__aexit__(exc_type, exc_value, tcb)
