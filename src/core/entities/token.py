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
    expire_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    type: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # (0: Google Token, 1: Verification Token, 2: Stored Token)
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
        Index("idx_token_expire_at", "token", "expire_at"),
    )

    # Validation
    @validates("type")
    def validate_type(self, key, value) -> int:
        if value not in [v["value"] for v in self.TokenType.__dict__.values()]:
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
        REFRESH_TOKEN = {
            "name": "Refresh Token",
            "value": 2,
        }

    STANDARD_LENGTH = 32
    SHORT_LENGTH = 6

    # Methods
    def get_token_type(self):
        return next(
            (
                v["name"]
                for v in self.TokenType.__dict__.values()
                if v["value"] == self.type
            ),
            "Unknown",
        )
