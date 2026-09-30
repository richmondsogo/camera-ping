from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware datetime in UTC."""
    return datetime.now(UTC)
