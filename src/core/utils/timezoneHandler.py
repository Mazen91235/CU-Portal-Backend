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
    def now(cls, timezone: str = "UTC") -> datetime:
        if timezone.lower() == "cairo":
            return datetime.now(cls.CAIRO_TZ)
        else:
            return datetime.now(cls.UTC_TZ)

    @classmethod
    def from_isoformat(cls, iso_string: str, timezone: str = "UTC") -> datetime:
        dt = datetime.fromisoformat(iso_string)
        if timezone.lower() == "cairo":
            return dt.astimezone(cls.CAIRO_TZ)
        else:
            return dt.astimezone(cls.UTC_TZ)

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

    @classmethod
    def add_minutes(cls, minutes: int, dt: datetime | None = None) -> datetime:
        if not dt:
            dt = cls.now("UTC")
        return dt + timedelta(minutes=minutes)

    @classmethod
    def get_abs_diff_in_days(cls, dt1: datetime, dt2: datetime | None = None) -> int:
        if not dt2:
            dt2 = cls.now("UTC")
        return abs((dt1 - dt2).days)

    @classmethod
    def get_abs_diff_in_hours(cls, dt1: datetime, dt2: datetime | None = None) -> int:
        if not dt2:
            dt2 = cls.now("UTC")
        return abs((dt1 - dt2).seconds // 3600)
