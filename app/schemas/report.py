from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.order import PaymentMethod
from app.schemas.types import PriceValue


class PaymentBreakdown(BaseModel):
    method: PaymentMethod
    orders: int
    revenue: PriceValue


class DailySales(BaseModel):
    day: date
    orders: int
    revenue: PriceValue


class ProductSales(BaseModel):
    product_id: UUID
    name: str
    quantity: float
    revenue: PriceValue


class SalesReport(BaseModel):
    starts_from: datetime
    starts_until: datetime
    orders: int
    revenue: PriceValue
    average_ticket: PriceValue
    delivery_fees: PriceValue
    cancelled_orders: int
    cancelled_value: PriceValue
    by_payment_method: list[PaymentBreakdown]
    by_day: list[DailySales]
    top_products: list[ProductSales]
