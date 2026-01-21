import asyncio
import json
import statistics as stats
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime

from sqlalchemy import insert, select, update

from config import KAFKA_MODERATOR_EVENTS_TOPIC
from db_models import Moderators, ActionEvents, EvaluationEvents
from enums import ActionStatus, MessagePlatform, ModeratorStatus
from events.moderator import ModeratorEventType
from infra.db import get_db_sess
from infra.kafka import AsyncKafkaConsumer


class ModeratorEventHandler:
    def __init__(self, batch_size: int = 100):
        """
        Args:
            batch_size (int, optional): The quantity of messages to be taken into account
                when calculating the user's behaviour score. Defaults to 100.
        """
        if batch_size < 0:
            raise ValueError("batch_size must be >= 0")

        self._batch_size = batch_size

        self._task: asyncio.Task | None = None
        self._prev_scores: dict[tuple[str, MessagePlatform], deque[float]] = (
            defaultdict(lambda: deque(maxlen=batch_size))
        )

        self._stopped = False

    @property
    def stopped(self):
        return self._stopped

    def start(self) -> None:
        self._task = asyncio.create_task(self.run())

    async def run(self) -> None:
        consumer = AsyncKafkaConsumer(KAFKA_MODERATOR_EVENTS_TOPIC)

        try:
            await consumer.start()

            async for msg in consumer:
                try:
                    event_data = json.loads(msg.value.decode())
                    event_type = event_data["type"]

                    if event_type == ModeratorEventType.ALIVE:
                        await self._update_moderator(
                            event_data["moderator_id"], status=ModeratorStatus.ONLINE
                        )
                    elif event_type == ModeratorEventType.DEAD:
                        await self._update_moderator(
                            event_data["moderator_id"], status=ModeratorStatus.OFFLINE
                        )
                    elif event_type == ModeratorEventType.CONFIG_UPDATED:
                        await self._update_moderator(
                            event_data["moderator_id"], conf=event_data["config"]
                        )
                    elif event_type == ModeratorEventType.EVALUATION_CREATED:
                        await self._persist_evaluation(event_data)
                    elif event_type == ModeratorEventType.ACTION_PERFORMED:
                        await self._persist_action(event_data)

                except json.JSONDecodeError:
                    pass

        finally:
            await consumer.stop()

    async def _update_moderator(self, moderator_id: uuid.UUID, **kw) -> bool:
        async with get_db_sess() as db_sess:
            res = await db_sess.scalar(
                update(Moderators)
                .values(**kw)
                .where(Moderators.moderator_id == moderator_id)
                .returning(Moderators.moderator_id)
            )

            await db_sess.commit()
            return res is not None

    async def _persist_evaluation(self, event: dict) -> None:
        user_id = event["user_id"]
        if user_id is None:
            return

        user_id = str(user_id)
        moderator_id = event["moderator_id"]
        severity_score = event["severity_score"]

        async with get_db_sess() as db_sess:
            platform = await db_sess.scalar(
                select(Moderators.platform).where(
                    Moderators.moderator_id == moderator_id
                )
            )
            key = (user_id, platform)

            msgs = self._prev_scores[key]
            if not msgs:
                res = await db_sess.scalars(
                    select(EvaluationEvents.severity_score)
                    .where(
                        EvaluationEvents.moderator_id == moderator_id,
                        EvaluationEvents.moderator_id == moderator_id,
                    )
                    .order_by(EvaluationEvents.created_at.desc())
                    .limit(self._batch_size)
                )

                db_scores = res.all()
                msgs.extend(db_scores)

            msgs.append(severity_score)
            behaviour_score = round(stats.mean(msgs), 2)

            await db_sess.execute(
                insert(EvaluationEvents).values(
                    event_id=event["id"],
                    moderator_id=moderator_id,
                    platform_user_id=str(user_id),
                    severity_score=severity_score,
                    behaviour_score=behaviour_score,
                    context=event["ctx"],
                    created_at=datetime.fromtimestamp(event["timestamp"], UTC),
                )
            )

            await db_sess.commit()

    async def _persist_action(self, event: dict) -> None:
        action = event["action"]
        ctx = event["ctx"]

        async with get_db_sess() as db_sess:
            created_at = datetime.fromtimestamp(event["timestamp"], UTC)
            platform_user_id = action["params"].get("user_id")
            if platform_user_id:
                platform_user_id = str(platform_user_id)

            await db_sess.execute(
                insert(ActionEvents).values(
                    action_id=event["action_id"],
                    event_id=event["id"],
                    evaluation_id=event['evaluation_id'],
                    moderator_id=event["moderator_id"],
                    platform_user_id=platform_user_id,
                    action_type=action["type"],
                    action_params=action.get("params"),
                    context=ctx,
                    status=action["status"],
                    reason=action["reason"],
                    error_msg=action['error_msg'],
                    created_at=created_at,
                    executed_at=(
                        created_at
                        if action["status"] == ActionStatus.COMPLETED
                        else None
                    ),
                )
            )

            await db_sess.commit()

    async def stop(self) -> None:
        self._stopped = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
