from datetime import time
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Weekday = Annotated[int, Field(ge=0, le=6)]


class OpeningDay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekday: Weekday
    opens_at: time
    closes_at: time

    @model_validator(mode="after")
    def check_period(self) -> Self:
        if self.closes_at == self.opens_at:
            raise ValueError("closes_at must differ from opens_at")
        return self


class OpeningHoursUpdate(BaseModel):
    days: Annotated[list[OpeningDay], Field(max_length=7)]

    @model_validator(mode="after")
    def check_days(self) -> Self:
        weekdays = [day.weekday for day in self.days]
        if len(set(weekdays)) != len(weekdays):
            raise ValueError("weekdays must not repeat")
        return self


class OpeningHoursRead(BaseModel):
    days: list[OpeningDay]
