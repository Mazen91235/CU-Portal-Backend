from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimezoneHandler:
    try:
        UTC_TZ = ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        UTC_TZ = timezone.utc

    try:
        CAIRO_TZ = ZoneInfo("Africa/Cairo")
    except ZoneInfoNotFoundError:
        CAIRO_TZ = timezone.utc

    @classmethod
    def now(cls, timezone: str) -> datetime:
        if timezone.lower() == "cairo":
            return datetime.now(cls.CAIRO_TZ)
        else:
            return datetime.now(cls.UTC_TZ)

    @classmethod
    def add_days(cls, days: int, dt: datetime | None = None) -> datetime:
        if not dt:
            dt = cls.now("UTC")
        return dt + timedelta(days=days)

    @classmethod
    def add_hours(cls, hours: int, dt: datetime | None = None) -> datetime:
        if not dt:
            dt = cls.now("UTC")
        return dt + timedelta(hours=hours)
