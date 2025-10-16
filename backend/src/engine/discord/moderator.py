import asyncio
import json
import logging
from uuid import UUID

from aiohttp import ClientError

import engine.discord.actions as actions_module
from config import FINAL_PROMPT, SCORE_SYSTEM_PROMPT
from engine.base_moderator import BaseModerator
from engine.models import TopicEvaluation, MessageContext, MessageEvaluation
from engine.enums import MaliciousState
from engine.prompt_validator import PromptValidator
from .config import DiscordConfig
from .stream import DiscordStream


class DiscordModerator(BaseModerator):

    def __init__(
        self, moderator_id: UUID, stream: DiscordStream, config: DiscordConfig
    ):
        super().__init__(
            moderator_id, logging.getLogger(f"discord-moderator-{moderator_id}")
        )
        self._config = config
        self._stream = stream

    async def moderate(self) -> None:
        self._logger.info("Launching moderation...")
        self._load_embedding_model()

        async for ctx in self._stream:
            evaluation = await self._evaluate(ctx)
            if not evaluation:
                continue

            await self._save_evaluation(evaluation, ctx)

    async def _evaluate(
        self, ctx: MessageContext, max_attempts: int = 3
    ) -> MessageEvaluation:
        mstate = await PromptValidator.validate_prompt(ctx.content)
        if mstate == MaliciousState.MALICIOUS:
            self._logger.critical(f'Malicious content "{ctx.content}"')
            return

        if not self._guidelines:
            self._guidelines, self._topics = await self._fetch_guidelines()

        allowed_actions = [a.type.value for a in self._config.allowed_actions]
        action_formats = []
        for a in allowed_actions:
            ac = actions_module.__dict__.get(a)
            if ac:
                action_formats.append(ac.model_json_schema())

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
                self._logger.info(f"Attempt {attempt + 1} failed. Error -> {type(e)} - {str(e)}")
            finally:
                attempt += 1

    async def _fetch_topic_scores(self, ctx: MessageContext, topics: list[str]):
        sys_prompt = SCORE_SYSTEM_PROMPT.format(
            guidelines=self._guidelines, topics=topics
        )
        topic_scores: dict[str, float] = await self._fetch_llm_response(
            [
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": json.dumps(ctx.to_serialisable_dict()),
                },
            ]
        )
        return topic_scores

    async def _handle_similars(
        self, ctx: MessageContext, similars: tuple[tuple[str, float], ...]
    ) -> dict[str, float]:
        topic_scores = {}

        # TODO: Optimise
        for topic, score in similars:
            if topic in topic_scores:
                score, count = topic_scores[topic]
                score += score
                count += 1
                topic_scores[topic] = (round(score / count, 2), count)
            else:
                topic_scores[topic] = (score, 1)

        items = topic_scores.items()
        for k, (score, _) in items:
            topic_scores[k] = score

        remaining = set(self._topics).difference(set(topic_scores.keys()))
        if remaining:
            rem_scores = await self._fetch_topic_scores(ctx, list(remaining))
            for k, v in rem_scores:
                topic_scores[k] = v

        return topic_scores
