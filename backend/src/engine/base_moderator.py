import asyncio
import json
import logging
from abc import abstractmethod
from enum import Enum
from json import JSONDecodeError
from uuid import UUID

from aiohttp import ClientSession
from aiokafka import AIOKafkaConsumer
from sentence_transformers import SentenceTransformer
from sqlalchemy import insert, select, update

from config import (
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_DEPLOYMENT_EVENTS_TOPIC,
    LLM_API_KEY,
    LLM_BASE_URL,
    SCORE_PROMPT_TEMPLATE,
    SCORE_SYSTEM_PROMPT,
)
from core.enums import ActionStatus, ModeratorDeploymentStatus
from db_models import (
    Guidelines,
    Messages,
    MessagesEvaluations,
    ModeratorDeployments,
    ModeratorDeploymentLogs,
    Moderators,
)
from engine.base_action import BaseAction
from engine.models import MessageContext, MessageEvaluation
from engine.task_pool import TaskPool
from utils.db import get_db_sess
from utils.llm import fetch_response, parse_to_json


class BaseModerator:
    _embedding_model: SentenceTransformer | None = None

    def __init__(
        self,
        deployment_id: UUID,
        moderator_id: UUID,
        logger: logging.Logger | None = None,
    ) -> None:
        self._deployment_id = deployment_id
        self._moderator_id = moderator_id
        self._logger = logger
        self._http_sess: ClientSession | None = None
        self._topics: list[str] | None = None
        self._guidelines: str | None = None
        self._task_pool = TaskPool()
        self._moderate_task: asyncio.Task | None = None

    @abstractmethod
    async def moderate(self) -> None: ...

    async def run(self) -> None:
        if self._moderate_task:
            raise RuntimeError("Moderator is already running.")

        try:
            self._moderate_task = asyncio.create_task(self.moderate())
            await self._listen_to_events()
        except asyncio.CancelledError:
            pass

    async def _listen_to_events(self) -> None:
        self._consumer = AIOKafkaConsumer(
            KAFKA_DEPLOYMENT_EVENTS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
            auto_offset_reset="latest",
        )

        await self._consumer.start()

        try:
            async for m in self._consumer:
                try:
                    data = json.loads(m.value.decode())
                    
                    if (
                        data.get("type") == "stop"
                        and data.get("deployment_id") == str(self._deployment_id)
                    ):
                        self._moderate_task.cancel()
                        await self._moderate_task
                except JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            await self._consumer.stop()

    def _load_embedding_model(self) -> None:
        if self._embedding_model:
            return
        self._embedding_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

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

    async def _log_action(self, action: BaseAction) -> UUID:
        async with get_db_sess() as db_sess:
            res = await db_sess.scalar(
                insert(ModeratorDeploymentLogs)
                .values(
                    moderator_id=self._moderator_id,
                    deployment_id=self._deployment_id,
                    action_type=(
                        action.type.value
                        if isinstance(action.type, Enum)
                        else action.type
                    ),
                    action_params=action.to_serialisable_dict(),
                    status=(
                        ActionStatus.AWAITING_APPROVAL.value
                        if action.requires_approval
                        else ActionStatus.PENDING.value
                    ),
                )
                .returning(ModeratorDeploymentLogs.log_id)
            )

            await db_sess.commit()

        return res

    async def _update_action_status(self, log_id: UUID, status: ActionStatus) -> None:
        async with get_db_sess() as db_sess:
            await db_sess.execute(
                update(ModeratorDeploymentLogs)
                .values(status=status.value)
                .where(ModeratorDeploymentLogs.log_id == log_id)
            )
            await db_sess.commit()

    async def _save_evaluation(
        self, eval: MessageEvaluation, ctx: MessageContext
    ) -> None:
        """
        Stores the eval and generates embeddings for future
        similar retrieval.

        Args:
            eval (MessageEvaluation): Evaluation of the message.
            ctx (MessageContext): Context for the evaluation.
        """
        embedding = self._embedding_model.encode([ctx.content])[0]

        async with get_db_sess() as db_sess:
            message_id = await db_sess.scalar(
                insert(Messages)
                .values(
                    moderator_id=self._moderator_id,
                    deployment_id=self._deployment_id,
                    content=ctx.content,
                    platform=ctx.platform.value,
                )
                .returning(Messages.message_id)
            )

            records = [
                {
                    "message_id": message_id,
                    "embedding": embedding,
                    "topic": teval.topic,
                    "topic_score": teval.topic_score,
                }
                for teval in eval.topic_evaluations
            ]
            await db_sess.execute(insert(MessagesEvaluations), records)
            await db_sess.commit()

    async def _fetch_topic_scores(
        self, ctx: MessageContext, topics: list[str]
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

    async def _update_status(self, status: ModeratorDeploymentStatus) -> None:
        async with get_db_sess() as db_sess:
            await db_sess.execute(
                update(ModeratorDeployments)
                .values(state=status.value)
                .where(ModeratorDeployments.deployment_id == self._deployment_id)
            )
            await db_sess.commit()

    async def __aenter__(self):
        self._http_sess = ClientSession(
            base_url=LLM_BASE_URL, headers={"Authorization": f"Bearer {LLM_API_KEY}"}
        )
        self._load_embedding_model()
        await self._update_status(ModeratorDeploymentStatus.ONLINE)
        return self

    async def __aexit__(self, exc_type, exc_value, tcb) -> None:
        await self._http_sess.close()
        self._http_sess = None
        await self._update_status(ModeratorDeploymentStatus.OFFLINE)
