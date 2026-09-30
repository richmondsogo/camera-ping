from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, UTCDateTime


class CameraStatus(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        CheckConstraint("status IN ('unknown', 'online', 'offline')", name="status"),
        server_default=text("'unknown'"),
        nullable=False,
    )
    last_checked: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_online: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("consecutive_failures >= 0", name="consecutive_failures"),
        server_default=text("0"),
        nullable=False,
    )
    alert_sent_for_current_outage: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("0"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
