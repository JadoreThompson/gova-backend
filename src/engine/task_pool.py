import asyncio
from types import CoroutineType
from typing import Any


class TaskPool:
    def __init__(self, size: int | None = None):
        self._size = size
        self._tasks: list[asyncio.Task | None] | None = None
        self._available_slots: set[int] | None = None
        self._lock: asyncio.Lock | None = None
        self._slot_available: asyncio.Event | None = None
        self._closing = False
        self._alive = False

    @property
    def size(self) -> int | None:
        return self._size

    def start(self):
        self._lock = asyncio.Lock()
        self._slot_available = asyncio.Event()
        
        if self._size is not None:
            self._tasks = [None] * self._size
            self._available_slots = set(range(self._size))
            self._slot_available.set()
        else:
            self._tasks = []
            self._available_slots = set()

        self._alive = True
        self._closing = False

    async def stop(self) -> None:
        async with self._lock:
            if self._closing or not self._alive:
                return

            self._closing = True
            self._alive = False
            ts = [t for t in self._tasks if t is not None and not t.done()]

        for t in ts:
            t.cancel()
        
        if ts:
            await asyncio.gather(*ts, return_exceptions=True)

        self._tasks = None
        self._available_slots = None

    async def __aenter__(self):
        self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, tcb):
        await self.stop()

    async def submit(self, coro: CoroutineType[Any, Any, Any]) -> None:
        while True:
            async with self._lock:
                if self._closing or not self._alive:
                    return

                if self._available_slots:
                    idx = self._available_slots.pop()
                    if not self._available_slots:
                        self._slot_available.clear()
                    self._tasks[idx] = asyncio.create_task(self._wrapper(coro, idx))
                    return
                
                if self._size is None:
                    idx = len(self._tasks)
                    self._tasks.append(asyncio.create_task(self._wrapper(coro, idx)))
                    return

            await self._slot_available.wait()

    async def _wrapper(self, coro: CoroutineType[Any, Any, Any], ind: int) -> None:
        try:
            await coro
        finally:
            async with self._lock:
                if self._alive and not self._closing:
                    self._available_slots.add(ind)
                    self._slot_available.set()