from json import dumps

from pydantic import BaseModel

from core.models import CustomBaseModel


def dump_model(value: CustomBaseModel | BaseModel) -> bytes:
    if isinstance(value, CustomBaseModel):
        return dumps(value.to_serialisable_dict()).encode()
    return value.model_dump_json().encode()