from typing import Any, Type

from engine.actions.base import BaseAction, BasePerformedAction
from engine.agents.review import ReviewAgentAction
from engine.actions.discord import (
    DiscordActionType,
    DiscordPerformedActionReply,
    DiscordPerformedActionTimeout,
    DiscordPerformedActionKick,
)
from enums import ActionStatus, MessagePlatform


class PerformedActionRegistry:
    _registry: dict[tuple[MessagePlatform, Any], Type[BasePerformedAction]] = {}
    _registered_platforms: set[MessagePlatform] = set()

    @classmethod
    def register_discord(cls) -> None:
        if MessagePlatform.DISCORD in cls._registered_platforms:
            return

        cls.register(
            platform=MessagePlatform.DISCORD,
            action_type=DiscordActionType.REPLY,
            performed_cls=DiscordPerformedActionReply,
        )

        cls.register(
            platform=MessagePlatform.DISCORD,
            action_type=DiscordActionType.TIMEOUT,
            performed_cls=DiscordPerformedActionTimeout,
        )

        cls.register(
            platform=MessagePlatform.DISCORD,
            action_type=DiscordActionType.KICK,
            performed_cls=DiscordPerformedActionKick,
        )

        cls._registered_platforms.add(MessagePlatform.DISCORD)

    @classmethod
    def register_all(cls) -> None:
        cls.register_discord()

    @classmethod
    def register(
        cls,
        *,
        platform: MessagePlatform,
        action_type: Any,
        performed_cls: Type[BasePerformedAction],
    ) -> None:
        key = (platform, action_type)
        if key in cls._registry:
            raise RuntimeError(f"Performed action already registered for {key}")
        cls._registry[key] = performed_cls

    @classmethod
    def build(
        cls,
        *,
        planned_action: ReviewAgentAction,
        defined_action: BaseAction,
        reason: str,
        status: ActionStatus,
    ) -> BasePerformedAction:
        key = (defined_action.platform, planned_action.type)

        try:
            performed_cls = cls._registry[key]
        except KeyError:
            raise RuntimeError(f"No performed action registered for {key}")

        return performed_cls(
            **defined_action.model_dump(exclude={"default_params"}),
            params=planned_action.params,
            reason=reason,
            status=status,
        )
