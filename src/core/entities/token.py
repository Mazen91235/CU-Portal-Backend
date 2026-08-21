from __future__ import annotations
from .base import (
    Base,
    Integer,
    String,
    Boolean,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
    Index,
    Mapped,
    Optional,
    TimezoneHandler,
    TypedDict,
    mapped_column,
    validates,
)


class Token(Base):
    # Tablename
    __tablename__ = "tokens"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    token_type: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # (0: Email Verification, 1: Google Token)
    details: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        nullable=True,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        onupdate=lambda: TimezoneHandler.now("UTC"),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("idx_token", "token", unique=True),
        # Composite Indexes
        Index("idx_token_expires_at", "token", "expires_at"),
    )

    # Validation
    @validates("token_type")
    def validate_token_type(self, key, value) -> int:
        if value not in [
            v["value"]
            for k, v in self.TokenType.__dict__.items()
            if not k.startswith("__") and isinstance(v, dict)
        ]:
            raise ValueError("Invalid token type")
        return value

    # Attributes
    class TokenType:
        EMAIL_VERIFICATION = {
            "name": "Email Verification",
            "value": 0,
        }
        GOOGLE_TOKEN = {
            "name": "Google Token",
            "value": 1,
        }

    STANDARD_LENGTH = 32
    SHORT_LENGTH = 6
    EXPIRE_HOURS = 1

    # Methods
    def get_token_type(self):
        return next(
            (
                v["name"]
                for v in self.TokenType.__dict__.values()
                if v["value"] == self.token_type
            ),
            "Unknown",
        )
