from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PartialUpdate
from app.schemas.types import (
    Address,
    Cnpj,
    EstablishmentName,
    HexColor,
    Phone,
    Price,
    PriceValue,
    Slug,
)


class EstablishmentCreate(BaseModel):
    name: EstablishmentName
    address: Address
    phone: Phone
    cnpj: Cnpj | None = None
    slug: Slug | None = None


class EstablishmentUpdate(PartialUpdate):
    nullable_fields = frozenset({"cnpj", "min_order", "logo_key"})

    name: EstablishmentName | None = None
    address: Address | None = None
    phone: Phone | None = None
    cnpj: Cnpj | None = None
    slug: Slug | None = None
    primary_color: HexColor | None = None
    accent_color: HexColor | None = None
    auto_accept: bool | None = None
    delivery_fee_enabled: bool | None = None
    delivery_fee: Price | None = None
    min_order: Price | None = None
    online_payments_enabled: bool | None = None
    logo_key: str | None = None


class EstablishmentPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    address: str
    phone: str
    primary_color: str
    accent_color: str
    delivery_fee_enabled: bool
    delivery_fee: PriceValue
    min_order: PriceValue | None
    online_payments_enabled: bool
    logo_url: str | None = None
    is_open: bool = False
    absence_reason: str | None = None
    absence_ends_at: datetime | None = None


class EstablishmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    address: str
    phone: str
    cnpj: str | None
    primary_color: str
    accent_color: str
    auto_accept: bool
    delivery_fee_enabled: bool
    delivery_fee: PriceValue
    min_order: PriceValue | None
    online_payments_enabled: bool
    logo_key: str | None
    logo_url: str | None = None
    created_at: datetime
    updated_at: datetime
