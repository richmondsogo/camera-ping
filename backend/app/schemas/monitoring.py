from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MonitoringStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    running: bool
    interval_seconds: int
    last_cycle_started_at: datetime | None
    last_cycle_finished_at: datetime | None
    next_check_at: datetime | None
    total: int
    online: int
    offline: int
    unknown: int
