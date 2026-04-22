import uuid

from sqlalchemy import UUID, DateTime, text
from sqlalchemy.orm import mapped_column

from utils import get_datetime


def get_uuid():
    return uuid.uuid4()


def uuid_pk(**kw):
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )


def datetime_tz():
    return mapped_column(DateTime(timezone=True), nullable=False, default=get_datetime)