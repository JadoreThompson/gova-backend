from typing import Any, Type

from .base_runner import BaseRunner


class RunnerConfig:
    def __init__(
        self,
        cls: Type[BaseRunner],
        name: str | None = None,
        args: tuple[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ):
        self.cls = cls
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.name = name or cls.__name__
