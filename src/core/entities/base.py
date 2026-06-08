from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    Mapped,
    mapped_column,
    validates,
)
from typing import Optional, TypedDict, TYPE_CHECKING
from datetime import datetime
from core.utils.timezoneHandler import TimezoneHandler

Base = declarative_base()
