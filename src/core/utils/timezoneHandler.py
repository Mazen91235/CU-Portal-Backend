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
    def _clean_datetime(cls, iso_datetime: str | datetime) -> str:
        if isinstance(iso_datetime, datetime):
            iso_datetime = iso_datetime.astimezone(cls.UTC_TZ).isoformat()
        if "T" in iso_datetime:
            return iso_datetime
        if " " in iso_datetime:
            return iso_datetime.replace(" ", "T")

        cairo_offset = datetime.now(cls.CAIRO_TZ).strftime("%z")
        formatted_offset = f"{cairo_offset[:3]}:{cairo_offset[3:]}"

        return iso_datetime + f"T00:00:00.000{formatted_offset}"

    @classmethod
    def to_isoformat(cls, dt: datetime, timezone: str = "UTC") -> str:
        if timezone.lower() == "cairo":
            return dt.astimezone(cls.CAIRO_TZ).isoformat()
        else:
            return dt.astimezone(cls.UTC_TZ).isoformat()

    @classmethod
    def now(cls, timezone: str = "UTC") -> datetime:
        if timezone.lower() == "cairo":
            return datetime.now(cls.CAIRO_TZ)
        else:
            return datetime.now(cls.UTC_TZ)

    @classmethod
    def from_isoformat(
        cls, iso_string: str | datetime, timezone: str = "UTC"
    ) -> datetime:
        dt = datetime.fromisoformat(cls._clean_datetime(iso_string))
        if timezone.lower() == "cairo":
            return dt.astimezone(cls.CAIRO_TZ)
        else:
            return dt.astimezone(cls.UTC_TZ)

    @classmethod
    def to_date(cls, dt: datetime) -> datetime:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

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
        return abs(int((dt1 - dt2).total_seconds() // 86400))

    @classmethod
    def get_abs_diff_in_hours(cls, dt1: datetime, dt2: datetime | None = None) -> int:
        if not dt2:
            dt2 = cls.now("UTC")
        return abs(int((dt1 - dt2).total_seconds() // 3600))

    @classmethod
    def get_due_as_str(cls, dt: datetime, timezone: str = "UTC") -> str | None:
        now = cls.now(timezone)
        if dt <= now:
            return None
        diff_hours = cls.get_abs_diff_in_hours(dt, now)
        if diff_hours < 1:
            return None
        if diff_hours < 24:
            return f"{diff_hours} hour{'s' if diff_hours > 1 else ''}"
        diff_days = diff_hours // 24
        return f"{diff_days} day{'s' if diff_days > 1 else ''}"
