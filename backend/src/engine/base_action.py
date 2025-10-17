from __future__ import annotations
from enum import Enum

from core.models import CustomBaseModel


class BaseAction(CustomBaseModel):
    type: Enum
    requires_approval: bool
    reason: str


class BaseActionDefinition(CustomBaseModel):
    """
    The client facing model(s) which allow prefilling
    parameters. Used in the platforms config for defining
    the allowed actions.
    """
    type: Enum
    requires_approval: bool
