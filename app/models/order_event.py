from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin, enum_check, string_enum
from app.models.history import versioned
from app.models.order import OrderActor


class OrderEventKind(StrEnum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    PAID = "paid"
    REFUNDED = "refunded"


@versioned
class OrderEvent(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_events"
    __table_args__ = (
        enum_check("kind", OrderEventKind),
        enum_check("actor", OrderActor),
        Index("ix_order_events_establishment_id_created_at", "establishment_id", "created_at"),
    )

    establishment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("establishments.id"))
    order_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    order_number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[OrderEventKind] = mapped_column(string_enum(OrderEventKind, 9))
    actor: Mapped[OrderActor] = mapped_column(string_enum(OrderActor, 8))
    actor_uid: Mapped[str | None] = mapped_column(String(128))
    detail: Mapped[str | None] = mapped_column(String(300))
