from aiokafka import AIOKafkaProducer

from config import KAFKA_HOST, KAFKA_PORT


class KafkaProducerManager:
    _producer: AIOKafkaProducer | None = None
    _alive = False

    @classmethod
    async def start(cls) -> None:
        if cls._producer is None:
            cls._alive = True
            cls._producer = AIOKafkaProducer(
                bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}"
            )
            await cls._producer.start()
            await cls._producer.send("tmp", b"hello world")

    @classmethod
    async def stop(cls) -> None:
        if not cls._alive:
            return

        cls._alive = False
        if cls._producer:
            await cls._producer.stop()
            cls._producer = None

    @classmethod
    def get_producer(cls) -> AIOKafkaProducer:
        if not cls._alive:
            raise RuntimeError(
                "KafkaManager must be alive first. Call the start method."
            )
        return cls._producer
