from typing import Any

from pydantic import Field

from core.models import CustomBaseModel


# TODO: Fix type errors

class BaseAction(CustomBaseModel):
    type: Any # Enum
    requires_approval: bool
    reason: str = Field(description="Filled by the system and not the agent.")


class BaseActionDefinition(CustomBaseModel):
    """
    The client facing model(s) which allow prefilling
    parameters. Used in the platforms config for defining
    the allowed actions.
    """
    type: Any # Enum
    requires_approval: bool
