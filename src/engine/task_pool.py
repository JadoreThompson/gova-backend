import asyncio
from types import CoroutineType
from typing import Any


class TaskPool:
    def __init__(self, size: int | None = None):
        self._size = size
        self._tasks: list[asyncio.Task] | None = None
        self._slot_idxs: asyncio.Queue | None = None
        self._lock: asyncio.Lock | None = None
        self._closing = False
        self._alive = False
        self._join_fut: asyncio.Future | None = None

    @property
    def size(self) -> int | None:
        return self._size

    def start(self):
        self._tasks = [None]
        self._slot_idxs = asyncio.Queue()
        self._lock = asyncio.Lock()

        if self._size is not None:
            for i in range(self._size):
                self._tasks.append(None)
                self._slot_idxs.put_nowait(i)

        self._alive = True
        self._closing = False
        self._join_fut = None

    async def stop(self) -> None:
        async with self._lock:
            if self._closing or not self._alive:
                return

            self._closing = True
            self._alive = False
            ts = []
            for t in self._tasks:
                if t is not None and not t.done():
                    t.cancel()
                    ts.append(t)

            await asyncio.gather(*ts, return_exceptions=True)

            self._tasks = None
            self._slot_idxs = None

            if self._join_fut:
                self._join_fut.set_result(True)

    async def __aenter__(self):
        self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, tcb):
        await self.stop()

    async def submit(self, coro: CoroutineType[Any, Any, Any]) -> None:
        async with self._lock:
            if self._closing or not self._alive:
                return

            try:
                idx = self._slot_idxs.get_nowait()
                self._tasks[idx] = asyncio.create_task(self._wrapper(coro, idx))
                self._slot_idxs.task_done()
                return
            except asyncio.QueueEmpty:
                if self._size is None:
                    idx = len(self._tasks)
                    self._tasks.append(asyncio.create_task(self._wrapper(coro, idx)))
                    return

            idx = await self._slot_idxs.get()
            self._tasks[idx] = asyncio.create_task(self._wrapper(coro, idx))

    async def join(self) -> None:
        if not self._join_fut:
            self._join_fut = asyncio.Future()

        await self._join_fut

    async def _wrapper(self, coro: CoroutineType[Any, Any, Any], ind: int) -> None:
        try:
            await coro
        finally:
            self._slot_idxs.put_nowait(ind)