import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaProducer
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, update

from config import (
    KAFKA_MODERATOR_EVENTS_TOPIC,
    SCORE_PROMPT_TEMPLATE,
    SCORE_SYSTEM_PROMPT,
)
from core.enums import ActionStatus, CoreEventType, ModeratorEventType, ModeratorStatus
from core.events import (
    ActionPerformedModeratorEvent,
    CoreEvent,
    DeadModeratorEvent,
    EvaluationCreatedModeratorEvent,
    ModeratorEvent,
)
from db_models import Guidelines, Moderators, MessagesEvaluations
from engine.base.base_action_handler import BaseActionHandler
from engine.models import BaseMessageContext, MessageEvaluation
from engine.task_pool import TaskPool
from utils.db import get_db_sess
from utils.kafka import dump_model
from utils.llm import fetch_response, parse_to_json


class BaseModerator(ABC):
    _embedding_model: SentenceTransformer | None = None

    def __init__(
        self,
        moderator_id: UUID,
        config: Any,
        action_handler: BaseActionHandler,
        kafka_producer: AIOKafkaProducer,
        task_pool: TaskPool | None = None,
        max_retries: int = 3,
    ) -> None:
        self._moderator_id = moderator_id
        self._config = config
        self._action_handler = action_handler
        self._kafka_producer = kafka_producer
        self._task_pool = task_pool
        self._max_retries = max_retries
        self._logger = logging.getLogger(f"moderator-{moderator_id}")
        self._topics: list[str] | None = None
        self._guidelines: str | None = None
        self._status = ModeratorStatus.OFFLINE
        self._count = 1
        self._count_lock = asyncio.Lock()

    @property
    def moderator_id(self):
        return self._moderator_id

    @property
    def status(self):
        return self._status

    async def start(self):
        if self._status == ModeratorStatus.OFFLINE:
            self._status = ModeratorStatus.ONLINE
            await self._update_status(ModeratorStatus.ONLINE)
            event = ModeratorEvent(
                type=ModeratorEventType.ALIVE, moderator_id=self._moderator_id
            )
            await self._kafka_producer.send(
                KAFKA_MODERATOR_EVENTS_TOPIC,
                dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
            )

    async def stop(self, reason: str | None = None) -> None:
        if self._status == ModeratorStatus.ONLINE:
            self._status = ModeratorStatus.PENDING
            await self._update_status(ModeratorStatus.PENDING)

            while True:
                async with self._count_lock:
                    if not self._count:
                        break
                await asyncio.sleep(0.5)

            self._status = ModeratorStatus.OFFLINE
            self._topics = None
            self._guidelines = None

            await self._update_status(ModeratorStatus.OFFLINE)
            event = DeadModeratorEvent(moderator_id=self._moderator_id, reason=reason)
            await self._kafka_producer.send(
                KAFKA_MODERATOR_EVENTS_TOPIC,
                dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
            )

    @abstractmethod
    async def evaluate(
        self, ctx: BaseMessageContext, max_attempts: int = 3
    ) -> MessageEvaluation | None:
        """
        Evaluates the given context
        """

    async def moderate(self, ctx: BaseMessageContext, max_attempts: int = 3) -> None:
        self._load_embedding_model()
        if self._status == ModeratorStatus.ONLINE:
            evaluation = await self.evaluate(ctx, max_attempts)
            if evaluation is None:
                await self._task_pool.submit(self._handle_retry(ctx))
                return

            await self._handle_evaluation(evaluation, ctx)
            return

    async def _handle_retry(self, ctx: BaseMessageContext) -> None:
        backoff = 1

        for attempt in range(self._max_retries):
            if self._status != ModeratorStatus.ONLINE:
                break

            try:
                evaluation = await self.evaluate(ctx, max_attempts=1)
                if evaluation is not None:
                    await self._handle_evaluation(evaluation, ctx)
                    return

                self._logger.warning(
                    f"Empty evaluation on attempt {attempt + 1}/{self._max_retries} for {ctx}"
                )
            except Exception as e:
                self._logger.error(
                    f"Retry {attempt + 1} failed: {type(e).__name__} - {e}"
                )

            await asyncio.sleep(backoff)
            backoff *= 2

        self._logger.error(f"Max retries reached for {ctx}")

    async def _handle_evaluation(
        self, evaluation: MessageEvaluation, ctx: BaseMessageContext
    ) -> None:
        eval_event = EvaluationCreatedModeratorEvent(
            moderator_id=self._moderator_id, evaluation=evaluation, context=ctx
        )
        await self._kafka_producer.send(
            KAFKA_MODERATOR_EVENTS_TOPIC,
            dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=eval_event)),
        )

        if evaluation.action:
            action = evaluation.action
            self._logger.info(f"Performing action '{action.type}'")
            action_params = action.to_serialisable_dict()
            action_type = action.type

            kw = {
                "moderator_id": self._moderator_id,
                "action_type": action_type,
                "params": action_params,
            }

            if action.requires_approval:
                event = ActionPerformedModeratorEvent(
                    **kw, status=ActionStatus.AWAITING_APPROVAL
                )
            else:
                success = await self._action_handler.handle(action, ctx)
                event = ActionPerformedModeratorEvent(
                    **kw,
                    status=ActionStatus.SUCCESS if success else ActionStatus.FAILED,
                )

            await self._kafka_producer.send(
                KAFKA_MODERATOR_EVENTS_TOPIC,
                dump_model(CoreEvent(type=CoreEventType.MODERATOR_EVENT, data=event)),
            )

    async def _handle_similars(
        self, ctx: BaseMessageContext, similars: tuple[tuple[str, float], ...]
    ) -> dict[str, float]:
        topic_scores = {}

        for topic, score in similars:
            if topic in topic_scores:
                score_sum, count = topic_scores[topic]
                score_sum += score
                count += 1
                topic_scores[topic] = (round(score_sum / count, 2), count)
            else:
                topic_scores[topic] = (score, 1)

        for k, (score, _) in topic_scores.items():
            topic_scores[k] = score

        remaining = set(self._topics).difference(set(topic_scores.keys()))
        if remaining:
            rem_scores = await self._fetch_topic_scores(ctx, list(remaining))
            for k, v in rem_scores.items():
                topic_scores[k] = v

        return topic_scores

    def _load_embedding_model(self) -> None:
        if self._embedding_model is not None:
            return
        self._embedding_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

    async def _update_status(self, status: ModeratorStatus) -> None:
        async with get_db_sess() as db_sess:
            await db_sess.execute(
                update(Moderators)
                .values(status=status.value)
                .where(Moderators.moderator_id == self._moderator_id)
            )
            await db_sess.commit()

    async def _fetch_guidelines(self) -> tuple[str, list[str]]:
        async with get_db_sess() as db_sess:
            res = await db_sess.execute(
                select(Guidelines.text, Guidelines.topics).where(
                    Guidelines.guideline_id
                    == select(Moderators.guideline_id).where(
                        Moderators.moderator_id == self._moderator_id
                    )
                )
            )
            return res.first()

    async def _fetch_topic_scores(
        self, ctx: BaseMessageContext, topics: list[str]
    ) -> dict[str, float]:
        prompt = SCORE_PROMPT_TEMPLATE.format(
            guidelines=self._guidelines,
            topics=topics,
            message=ctx.content,
            context=ctx.to_serialisable_dict(),
        )
        data: dict[str, float] = await fetch_response(
            [
                {"role": "system", "content": SCORE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return parse_to_json(data["choices"][0]["message"]["content"])

    async def _fetch_similar(
        self, text: str, distance: float = 0.5
    ) -> tuple[tuple[str, float], ...]:
        embedding = self._embedding_model.encode([text])[0]
        async with get_db_sess() as db_sess:
            res = await db_sess.scalars(
                select(MessagesEvaluations).where(
                    MessagesEvaluations.embedding.l2_distance(embedding) < distance,
                    MessagesEvaluations.topic.in_(self._topics),
                )
            )
            return tuple((r.topic, r.topic_score) for r in res.yield_per(1000))
