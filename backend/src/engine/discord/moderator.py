import asyncio
import json
import logging
from uuid import UUID

import discord
from aiohttp import ClientError

import engine.discord.actions as actions_module
from core.enums import ActionStatus
from config import FINAL_PROMPT
from engine.base_moderator import BaseModerator
from engine.discord.action_handler import DiscordActionHandler
from engine.discord.context import DiscordMessageContext
from engine.enums import MaliciousState
from engine.models import TopicEvaluation, MessageEvaluation
from engine.prompt_validator import PromptValidator
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
        self._action_handlers = {}
        self._client: discord.Client | None = None
        self._stream: DiscordStream | None = None
        self._client_task: asyncio.Task | None = None
        self._action_handler: DiscordActionHandler | None = None

    def _initialise_discord(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        self._client = discord.Client(intents=intents)
        self._stream = DiscordStream(
            self._client, self._config.guild_id, self._config.allowed_channels
        )
        self._action_handler = DiscordActionHandler(self._client, self._logger)

        self._stream.append_events()

        self._client_task = asyncio.create_task(self._client.start(self._token))

    async def moderate(self) -> None:
        # TODO: Improve for throughput & latency
        self._logger.info("Launching moderation...")
        self._initialise_discord()
        self._load_embedding_model()

        async for ctx in self._stream:
            evaluation = await self._evaluate(ctx)
            if not evaluation:
                continue

            if evaluation.action:
                action = evaluation.action
                log_id = await self._log_action()

                if action.requires_approval:
                    await self._update_action_status(
                        log_id, ActionStatus.AWAITING_APPROVAL
                    )
                else:
                    await self._action_handler.handle(action, ctx)
                    await self._update_action_status(log_id, ActionStatus.SUCCESS)

            await self._save_evaluation(evaluation, ctx)

    async def _evaluate(
        self, ctx: DiscordMessageContext, max_attempts: int = 3
    ) -> MessageEvaluation:
        self._logger.info("Validating prompt")
        mal_state = await PromptValidator.validate_prompt(ctx.content)
        if mal_state == MaliciousState.MALICIOUS:
            self._logger.critical(f'Malicious content "{ctx.content}"')
            return
        
        self._logger.info("Checking guidelines.")
        if not self._guidelines:
            self._guidelines, self._topics = await self._fetch_guidelines()

        self._logger.info("Building actions list.")
        allowed_actions = [a.type.value for a in self._config.allowed_actions]
        action_formats = []
        for a in allowed_actions:
            ac = actions_module.__dict__.get(a)
            if ac:
                action_formats.append(ac.model_json_schema())

        self._logger.info("Fetching eval.")
        attempt = 0
        while attempt < max_attempts:
            msgs = []
            try:
                similars = await self._fetch_similar(ctx.content)
                if similars:
                    topic_scores = await self._handle_similars(ctx, similars)
                else:
                    topic_scores = await self._fetch_topic_scores(ctx, self._topics)

                msgs.append(topic_scores)

                # Final Output
                prompt = FINAL_PROMPT.format(
                    guidelines=self._guidelines,
                    topics=self._topics,
                    topic_scores=topic_scores,
                    actions=allowed_actions,
                    message=ctx.content,
                    action_formats=action_formats,
                    context=ctx.to_serialisable_dict(),
                )
                data = await self._fetch_llm_response(
                    [{"role": "user", "content": prompt}]
                )

                evaluation = MessageEvaluation(
                    **data,
                    topic_evaluations=[
                        TopicEvaluation(topic=key, topic_score=val)
                        for key, val in topic_scores.items()
                    ],
                )
                msgs.append(data)

                return evaluation
            except (
                ClientError,
                asyncio.TimeoutError,
                json.JSONDecodeError,
                ValueError,
            ) as e:
                import traceback; traceback.print_exc()
                self._logger.info(
                    f"Attempt {attempt + 1} failed. Error -> {type(e)} - {str(e)}"
                )
            finally:
                attempt += 1

    def __del__(self):
        if self._client_task:
            self._client_task.cancel()
            self._client_task = None
            self._client = None
            self._stream = None
