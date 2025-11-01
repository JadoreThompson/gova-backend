from aiokafka import AIOKafkaProducer

from config import KAFKA_HOST, KAFKA_PORT


class KafkaManager:
    _producer: AIOKafkaProducer | None = None

    @classmethod
    async def start(cls) -> None:
        if not cls._producer:
            cls._producer = AIOKafkaProducer(
                bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}"
            )
            await cls._producer.start()
            await cls._producer.send("tmp", b"hello world")

    @classmethod
    async def stop(cls) -> None:
        if cls._producer:
            await cls._producer.stop()

    @classmethod
    def get_producer(cls) -> AIOKafkaProducer | None:
        return cls._producer
