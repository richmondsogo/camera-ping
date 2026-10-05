from typing import Self

from pydantic import BaseModel, ConfigDict, StrictInt, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.config import MAX_INTERVAL_SECONDS, MIN_INTERVAL_SECONDS


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_interval_seconds: int


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_interval_seconds: StrictInt | None = None

    @field_validator("check_interval_seconds")
    @classmethod
    def validate_interval(cls, v: int | None) -> int:
        if v is None:
            raise PydanticCustomError("null_value", "Field cannot be null.")
        if v < MIN_INTERVAL_SECONDS or v > MAX_INTERVAL_SECONDS:
            raise PydanticCustomError(
                "interval_bounds",
                "Choose an interval between 10 seconds and 365 days.",
            )
        return v

    @model_validator(mode="after")
    def validate_not_empty_body(self) -> Self:
        if "check_interval_seconds" not in self.model_fields_set:
            raise PydanticCustomError(
                "empty_body",
                "At least one field must be provided for update.",
            )
        return self
