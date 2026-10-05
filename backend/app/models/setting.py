from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.config import MAX_INTERVAL_SECONDS, MIN_INTERVAL_SECONDS
from app.database import Base


class AppSettings(Base):
    """Application-level persistent configuration.

    Guaranteed single row with id = 1. check_interval_seconds stores the
    persisted monitoring check interval, or NULL to indicate fallback to
    the MONITOR_INTERVAL_SECONDS environment variable.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("id = 1", name="id"),
        primary_key=True,
    )
    check_interval_seconds: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint(
            f"check_interval_seconds IS NULL OR "
            f"(check_interval_seconds >= {MIN_INTERVAL_SECONDS} AND "
            f"check_interval_seconds <= {MAX_INTERVAL_SECONDS})",
            name="check_interval_seconds",
        ),
        nullable=True,
    )
