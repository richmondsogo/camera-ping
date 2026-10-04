from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, UTCDateTime


class MonitoringState(Base):
    __tablename__ = "monitoring_state"

    id: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("id = 1", name="id"),
        primary_key=True,
    )
    running: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("0"),
        nullable=False,
    )
    last_cycle_started_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )
    last_cycle_finished_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )
