import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.base_moderator import BaseModerator
from engine.models import BaseMessageContext
from engine.task_pool import TaskPool


logger = logging.getLogger("background_executor")


class BackgroundExecutor:
    def __init__(
        self, moderator: "BaseModerator", size: int | None = None, max_retries: int = 3
    ):
        self._moderator = moderator
        self._task_pool = TaskPool(size)
        self._max_retries = max_retries

    async def __aenter__(self):
        await self._task_pool.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._task_pool.__aexit__(exc_type, exc_value, traceback)

    async def submit(self, ctx: BaseMessageContext) -> None:
        await self._task_pool.submit(self._retry_wrapper(ctx))

    async def _retry_wrapper(self, ctx: BaseMessageContext) -> None:
        backoff = 1

        for attempt in range(1, self._max_retries + 1):
            try:
                evaluation = await self._moderator._evaluate(ctx, max_attempts=1)
                if evaluation:
                    await self._moderator._handle_evaluation(evaluation, ctx)
                    return

                logger.warning(
                    f"Empty evaluation on attempt {attempt}/{self._max_retries} for {ctx}"
                )
            except Exception as e:
                logger.error(f"Retry {attempt} failed: {type(e).__name__} - {e}")

            await asyncio.sleep(backoff)
            backoff *= 2

        logger.error(f"Max retries reached for {ctx}")
