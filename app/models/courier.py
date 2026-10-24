from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.history import versioned


@versioned
class Courier(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "couriers"
    __table_args__ = (UniqueConstraint("establishment_id", "firebase_uid"),)

    establishment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("establishments.id"))
    firebase_uid: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


@versioned
class CourierInvite(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courier_invites"

    establishment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("establishments.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    courier_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("couriers.id"))
