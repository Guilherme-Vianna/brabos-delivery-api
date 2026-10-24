from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import PartialUpdate
from app.schemas.types import Price, PriceValue

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
Position = Annotated[int, Field(ge=0, le=10_000)]


class ProductCreate(BaseModel):
    name: ProductName
    price: Price
    description: LongText = ""
    ingredients: LongText = ""
    category: Category = ""
    allows_half: bool = False
    asks_doneness: bool = False
    active: bool = True
    position: Position = 0
    image_key: str | None = None


class ProductUpdate(PartialUpdate):
    nullable_fields = frozenset({"image_key"})

    name: ProductName | None = None
    price: Price | None = None
    description: LongText | None = None
    ingredients: LongText | None = None
    category: Category | None = None
    allows_half: bool | None = None
    asks_doneness: bool | None = None
    active: bool | None = None
    position: Position | None = None
    image_key: str | None = None


class ProductPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    ingredients: str
    category: str
    price: PriceValue
    allows_half: bool
    asks_doneness: bool
    position: int
    image_url: str | None = None


class ProductRead(ProductPublicRead):
    active: bool
    image_key: str | None
    created_at: datetime
    updated_at: datetime
