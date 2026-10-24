from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from app.schemas.types import OptionalText200


class AbsenceCreate(BaseModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reason: OptionalText200 | None = None

    @model_validator(mode="after")
    def check_period(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class AbsenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    created_at: datetime
