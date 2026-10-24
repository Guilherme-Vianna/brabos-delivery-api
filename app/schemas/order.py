from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.order import (
    Doneness,
    OrderActor,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.models.order_event import OrderEventKind
from app.schemas.types import Address, FullName, OptionalText200, Phone, Price, PriceValue

Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]


class OrderItemCreate(BaseModel):
    product_id: UUID
    half_product_id: UUID | None = None
    quantity: Annotated[int, Field(ge=1, le=99)] = 1
    doneness: Doneness | None = None
    notes: OptionalText200 | None = None

    @model_validator(mode="after")
    def check_half(self) -> Self:
        if self.half_product_id == self.product_id:
            raise ValueError("half_product_id must differ from product_id")
        return self


class OrderCreate(BaseModel):
    full_name: FullName
    phone: Phone
    address: Address
    reference_point: OptionalText200 | None = None
    notes: Notes | None = None
    payment_method: PaymentMethod
    change_for: Price | None = None
    items: Annotated[list[OrderItemCreate], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def check_change(self) -> Self:
        if self.change_for is not None and self.payment_method is not PaymentMethod.CASH:
            raise ValueError("change_for is only allowed for cash payments")
        return self


class OrderCancel(BaseModel):
    reason: Reason


class CustomerOrderCancel(BaseModel):
    reason: Reason | None = None


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    half_product_id: UUID | None
    product_name: str
    half_product_name: str | None
    unit_price: PriceValue
    quantity: int
    doneness: Doneness | None
    notes: str | None
    line_total: PriceValue


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    establishment_id: UUID
    number: int
    status: OrderStatus
    full_name: str
    phone: str
    address: str
    reference_point: str | None
    notes: str | None
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    change_for: PriceValue | None
    subtotal: PriceValue
    delivery_fee: PriceValue
    total: PriceValue
    courier_id: UUID | None
    cancel_reason: str | None
    cancelled_by: OrderActor | None
    accepted_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]


class OrderPlacedRead(OrderRead):
    checkout_url: str | None = None


class CustomerOrderRead(OrderRead):
    establishment_slug: str
    establishment_name: str


class OrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    order_number: int
    kind: OrderEventKind
    actor: OrderActor
    actor_uid: str | None
    detail: str | None
    created_at: datetime
