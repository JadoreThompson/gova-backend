from __future__ import annotations
from enum import Enum
from typing import Any

from pydantic import Field

from core.models import CustomBaseModel


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
