import asyncio
import json
from uuid import UUID

from aiohttp import ClientError

from config import FINAL_PROMPT, SCORE_SYSTEM_PROMPT
from engine.base_moderator import BaseChatModerator
from engine.discord.actions import BanAction, DiscordActionType, MuteAction
from engine.enums import MaliciousState
from engine.models import MessageBreach, MessageContext, MessageEvaluation
from engine.prompt_validator import PromptValidator
from .stream import DiscordStream


class DiscordModerator(BaseChatModerator):

    def __init__(self, moderator_id: UUID, stream: DiscordStream):
        super().__init__(moderator_id)
        self._stream = stream

    async def moderate(self) -> None:
        self._load_embedding_model()

        async for ctx in self._stream:
            eval = await self._evaluate(ctx)
            print("Eval", eval)
            if not eval:
                continue

            await self._save_evaluation(eval, ctx)

    async def _evaluate(
        self, ctx: MessageContext, max_attempts: int = 3
    ) -> MessageEvaluation:
        mstate = await PromptValidator.validate_prompt(ctx.content)
        if mstate == MaliciousState.MALICIOUS:
            print("It's malicious", mstate)
            return

        if not self._guidelines:
            data = await self._fetch_guidelines()
            if not data:
                print("No guidelines")
                return
            self._guidelines, self._breach_types = data

        attempt = 0
        while attempt < max_attempts:
            msgs = []
            try:
                similars = await self._fetch_similar(ctx.content)
                if similars:
                    topic_scores = await self._handle_similars(ctx, similars)
                else:
                    # Fetching topic scores
                    topic_scores = await self._fetch_topic_scores(
                        ctx, self._breach_types
                    )

                msgs.append(topic_scores)

                # Final Output
                prompt = FINAL_PROMPT.format(
                    guidelines=self._guidelines,
                    topics=self._breach_types,
                    topic_scores=topic_scores,
                    actions=DiscordActionType._value2member_map_.keys(),
                    message=ctx.content,
                    action_formats=[
                        BanAction.model_json_schema(),
                        MuteAction.model_json_schema(),
                    ],
                    context=ctx.to_serialisable_dict(),
                )
                data = await self._fetch_llm_response(
                    [{"role": "user", "content": prompt}]
                )

                eval = MessageEvaluation(
                    **data,
                    breaches=[
                        MessageBreach(breach_type=key, breach_score=val)
                        for key, val in topic_scores.items()
                    ]
                )
                msgs.append(data)

                return eval
            except (
                ClientError,
                asyncio.TimeoutError,
                json.JSONDecodeError,
                ValueError,
            ) as e:
                print(type(e), str(e))
            finally:
                attempt += 1

    async def _fetch_topic_scores(self, ctx: MessageContext, topics: list[str]):
        sys_prompt = SCORE_SYSTEM_PROMPT.format(
            guidelines=self._guidelines, topics=self._breach_types
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

        remaining = set(self._breach_types).difference(set(topic_scores.keys()))
        if remaining:
            rem_scores = await self._fetch_topic_scores(ctx, list(remaining))
            for k, v in rem_scores:
                topic_scores[k] = v

        return topic_scores
