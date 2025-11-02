import json
import logging
from typing import Type
from uuid import UUID

from kafka import KafkaConsumer, KafkaProducer
from sqlalchemy import select


from config import (
    KAFKA_BOOTSTRAP_SERVER,
    KAFKA_MODERATOR_EVENTS_TOPIC,
    PRICING_TIER_LIMITS,
    REDIS_CLIENT_SYNC,
    REDIS_USER_MODERATOR_MESSAGES_PREFIX,
)
from core.enums import ModeratorEventType, ModeratorStatus, PricingTierType
from core.events import (
    DeadModeratorEvent,
    EvaluationCreatedModeratorEvent,
    CoreEvent,
    ActionPerformedModeratorEvent,
    KillModeratorEvent,
    ModeratorEvent,
    StartModeratorEvent,
)
from db_models import Moderators
from engine.discord.actions import DiscActionUnion
from engine.discord.context import DiscordMessageContext
from engine.moderator_event_logger import ModeratorEventLogger
from utils.kafka import dump_model
from utils.db import get_db_sess_sync, smaker_sync
from .base_runner import BaseRunner


class EventLoggerRunner(BaseRunner):
    def __init__(self):
        super().__init__("Event Logger")
        self.logger = logging.getLogger("event_logger")
        self._message_counts: dict[UUID, int] = {}
        self._moderator_users: dict[UUID, (UUID, PricingTierType)] = {}
        self._event_class_map: dict[ModeratorEventType, Type[ModeratorEvent]] = {
            ModeratorEventType.START: StartModeratorEvent,
            ModeratorEventType.ALIVE: ModeratorEvent,
            ModeratorEventType.KILL: KillModeratorEvent,
            ModeratorEventType.DEAD: DeadModeratorEvent,
            ModeratorEventType.ACTION_PERFORMED: ActionPerformedModeratorEvent[
                DiscActionUnion, DiscordMessageContext
            ],
            ModeratorEventType.EVALUATION_CREATED: EvaluationCreatedModeratorEvent[
                DiscActionUnion, DiscordMessageContext
            ],
        }
        self._kafka_producer: KafkaProducer | None = None

    def run(self) -> None:
        db = smaker_sync()
        event_logger = ModeratorEventLogger(db)
        consumer = KafkaConsumer(
            KAFKA_MODERATOR_EVENTS_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVER
        )
        self._kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)

        self.logger.info("Event logger consumer started.")
        for msg in consumer:
            try:
                data = json.loads(msg.value.decode())
                ev = CoreEvent(**data)
                ev_type = ev.data.get("type")

                self.logger.info(f"Received event '{ev_type}'")
                event_cls = self._event_class_map.get(ev_type)

                if event_cls:
                    parsed_ev = event_cls(**ev.data)
                    event_logger.log_event(parsed_ev)

                    if ev_type == ModeratorEventType.EVALUATION_CREATED:
                        self._handle_evaluation_created(parsed_ev)

                else:
                    self.logger.warning(f"Unhandled event type: {ev_type}")

            except Exception as e:
                self.logger.exception(f"Error processing event: {e}")

    def _handle_evaluation_created(
        self, event: EvaluationCreatedModeratorEvent
    ) -> None:
        """
        Sends kill event to all moderators when a user has gone over their
        pricing tier's message limit
        """
        moderator_id = event.moderator_id
        if moderator_id in self._moderator_users:
            user_id, pricing_tier = self._moderator_users[moderator_id]
        else:
            data = self._fetch_user(event.moderator_id)
            if user_id is None:
                return
            user_id, pricing_tier = data

        key = f"{REDIS_USER_MODERATOR_MESSAGES_PREFIX}{user_id}"
        REDIS_CLIENT_SYNC.incrby(key, 1)
        count = REDIS_CLIENT_SYNC.get(key)

        if count >= PRICING_TIER_LIMITS[pricing_tier]["max_messages"]:
            mids = self._fetch_moderator_ids(user_id, ModeratorStatus.ONLINE)
            for mid in mids:
                kill_event = KillModeratorEvent(
                    moderator_id=mid, reason="Limit reached"
                )
                self._kafka_producer.send(
                    KAFKA_MODERATOR_EVENTS_TOPIC, dump_model(kill_event)
                )

    @staticmethod
    def _fetch_moderator_ids(user_id: UUID, status: ModeratorStatus) -> list[UUID]:
        with get_db_sess_sync() as db_sess:
            res = db_sess.scalars(
                select(Moderators.moderator_id).where(
                    Moderators.user_id == user_id, Moderators.status == status.value
                )
            )
            return res.all()

    @staticmethod
    def _fetch_user(moderator_id: UUID) -> tuple[UUID, PricingTierType] | None:
        with get_db_sess_sync() as db_sess:
            return db_sess.scalar(
                select(Moderators.user_id).where(
                    Moderators.moderator_id == moderator_id
                )
            )
