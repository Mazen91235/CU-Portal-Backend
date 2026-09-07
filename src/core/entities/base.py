from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList, MutableSet
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    Mapped,
    mapped_column,
    validates,
)
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from typing import Optional, TypedDict, Literal, TYPE_CHECKING
from datetime import datetime
from core.utils.timezoneHandler import TimezoneHandler

Base = declarative_base()
