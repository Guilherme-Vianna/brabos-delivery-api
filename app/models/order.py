from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    PRICE,
    Base,
    TimestampMixin,
    UUIDv7PrimaryKeyMixin,
    enum_check,
    string_enum,
)
from app.models.history import versioned


class OrderStatus(StrEnum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"
    PIX = "pix"
    CARD = "card"
    ONLINE = "online"


class PaymentStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


class OrderActor(StrEnum):
    OWNER = "owner"
    CUSTOMER = "customer"
    COURIER = "courier"
    SYSTEM = "system"


class Doneness(StrEnum):
    RARE = "rare"
    MEDIUM_RARE = "medium_rare"
    MEDIUM = "medium"
    MEDIUM_WELL = "medium_well"
    WELL_DONE = "well_done"


@versioned
class Order(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("establishment_id", "number"),
        enum_check("status", OrderStatus),
        enum_check("payment_method", PaymentMethod),
        enum_check("payment_status", PaymentStatus),
        enum_check("cancelled_by", OrderActor),
        CheckConstraint("total >= 0", name="total"),
        Index("ix_orders_establishment_id_created_at", "establishment_id", "created_at"),
    )

    establishment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("establishments.id"))
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[OrderStatus] = mapped_column(string_enum(OrderStatus, 9))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(String(300))
    reference_point: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(500))
    payment_method: Mapped[PaymentMethod] = mapped_column(string_enum(PaymentMethod, 6))
    payment_status: Mapped[PaymentStatus] = mapped_column(string_enum(PaymentStatus, 12))
    payment_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    change_for: Mapped[Decimal | None] = mapped_column(PRICE)
    subtotal: Mapped[Decimal] = mapped_column(PRICE)
    delivery_fee: Mapped[Decimal] = mapped_column(PRICE)
    total: Mapped[Decimal] = mapped_column(PRICE)
    customer_token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    customer_uid: Mapped[str | None] = mapped_column(String(128), index=True)
    courier_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("couriers.id"), index=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(200))
    cancelled_by: Mapped[OrderActor | None] = mapped_column(string_enum(OrderActor, 8))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[OrderItem]] = relationship(
        viewonly=True, lazy="raise", order_by="OrderItem.id"
    )


@versioned
class OrderItem(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        enum_check("doneness", Doneness),
        CheckConstraint("quantity BETWEEN 1 AND 99", name="quantity"),
        CheckConstraint("unit_price >= 0", name="unit_price"),
    )

    order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("orders.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True)
    half_product_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(100))
    half_product_name: Mapped[str | None] = mapped_column(String(100))
    unit_price: Mapped[Decimal] = mapped_column(PRICE)
    quantity: Mapped[int] = mapped_column(SmallInteger)
    doneness: Mapped[Doneness | None] = mapped_column(string_enum(Doneness, 11))
    notes: Mapped[str | None] = mapped_column(String(200))

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
