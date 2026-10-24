from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin, enum_check, string_enum
from app.models.history import versioned


class PushRole(StrEnum):
    OWNER = "owner"
    COURIER = "courier"
    CUSTOMER = "customer"


@versioned
class PushDevice(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "push_devices"
    __table_args__ = (enum_check("role", PushRole),)

    fcm_token: Mapped[str] = mapped_column(String(512), unique=True)
    role: Mapped[PushRole] = mapped_column(string_enum(PushRole, 8))
    firebase_uid: Mapped[str | None] = mapped_column(String(128), index=True)
    customer_token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    establishment_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("establishments.id"), index=True
    )
