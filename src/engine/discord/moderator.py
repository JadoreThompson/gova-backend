import asyncio
import json
from typing import Any
from uuid import UUID

from aiohttp import ClientError
from aiokafka import AIOKafkaProducer

import engine.discord.actions as actions_module
from config import FINAL_PROMPT_TEMPLATE, FINAL_SYSTEM_PROMPT
from models import CustomBaseModel
from engine.base.base_moderator import BaseModerator
from engine.base.base_action import BaseActionDefinition
from engine.discord.actions import (
    BanAction,
    DiscActionDefinitionUnion,
    DiscActionUnion,
    DiscordAction,
    DiscordAction,
    KickAction,
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


class DiscordModerator(BaseModerator):
    _action_type_map = {
        DiscordAction.MUTE: MuteAction,
        DiscordAction.KICK: KickAction,
        DiscordAction.BAN: BanAction,
    }

    def __init__(
        self,
        moderator_id: UUID,
        config: DiscordConfig,
        action_handler: DiscordActionHandler,
        kafka_producer: AIOKafkaProducer,
        task_pool: TaskPool | None = None,
        max_retries: int = 3,
    ):
        super().__init__(
            moderator_id, config, action_handler, kafka_producer, task_pool, max_retries
        )
        self._allowed_action_formats: list[dict] | None = None
        self._allowed_action_types: set[DiscordAction] | None = None
        self._allowed_action_definitions: dict[
            DiscordAction, DiscActionDefinitionUnion
        ] = None

    async def start(self):
        await super().start()

        self._logger.info("Checking guidelines.")
        if not self._guidelines:
            self._guidelines, self._topics = await self._fetch_guidelines()

        self._logger.info("Building actions formats.")
        self._allowed_action_formats = []
        self._allowed_action_types = set()
        self._allowed_action_definitions = {}

        for action in self._config.allowed_actions:
            action_format = self._get_action_format(action)
            action_type = action.type
            self._allowed_action_types.add(action_type)
            self._allowed_action_formats.append(action_format)
            self._allowed_action_definitions[action_type] = action

    # async def _fetch_evaluation(self, ctx: DiscordMessageContext, topic_scores: dict[str, float], max_attempts: int):
    async def evaluate(
        self, ctx: DiscordMessageContext, max_attempts: int = 3
    ) -> MessageEvaluation | None:
        self._logger.info("Validating prompt")
        if ctx.metadata.channel_id not in self._config.allowed_channels:
            return

        mal_state = await PromptValidator.validate_prompt(ctx.content)
        if mal_state == MaliciousState.MALICIOUS:
            self._logger.critical(f'Malicious content "{ctx.content}"')
            return

        self._logger.info("Fetching evaluation.")

        similars = await self._fetch_similar(ctx.content)
        topic_scores = (
            await self._handle_similars(ctx, similars)
            if similars
            else await self._fetch_topic_scores(ctx, self._topics)
        )

        attempt = 0
        while attempt < max_attempts:
            try:
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
                    temperature=0.1,
                )
                data = parse_to_json(content["choices"][0]["message"]["content"])

                # Building action
                action_data = data.get("action")
                action = None
                if action_data and self._allowed_action_definitions.get(
                    action_data.get("type")
                ):
                    action_type = action_data["type"]
                    for k, v in (
                        self._allowed_action_definitions[action_type]
                        .model_dump()
                        .items()
                    ):
                        if v is not None:
                            action_data[k] = v
                    cls = self._action_type_map.get(action_type)
                    if cls:
                        action = cls(**action_data)

                return MessageEvaluation[DiscActionUnion](
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
                Exception,
            ) as e:
                self._logger.warning(
                    f"Attempt {attempt + 1} failed. Error: {type(e).__name__} - {str(e)}"
                )

                import traceback

                traceback.print_exc()
            finally:
                attempt += 1

    @staticmethod
    def _build_action(data: dict[str, Any]) -> DiscordAction:
        """Instantiate the correct DiscordAction subclass based on type."""
        typ = data.get("type")

        if typ == DiscordAction.BAN:
            return BanAction(**data)
        if typ == DiscordAction.MUTE:
            return MuteAction(**data)
        if typ == DiscordAction.KICK:
            return KickAction(**data)

        raise NotImplementedError(f"Action type '{typ}' not implemented.")

    @staticmethod
    def _get_action_format(action_def: BaseActionDefinition) -> list[dict]:
        """Generate JSON schemas for allowed Discord actions."""
        mod_dict = actions_module.__dict__

        key = action_def.__class__.__name__.replace("Definition", "")
        action_cls: CustomBaseModel = mod_dict.get(key)

        if action_cls:
            return action_cls.model_json_schema()
