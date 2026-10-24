from datetime import time
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Time, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.history import versioned


@versioned
class OpeningHours(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opening_hours"
    __table_args__ = (
        UniqueConstraint("establishment_id", "weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        CheckConstraint("closes_at <> opens_at", name="period"),
    )

    establishment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("establishments.id"))
    weekday: Mapped[int] = mapped_column(SmallInteger)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
