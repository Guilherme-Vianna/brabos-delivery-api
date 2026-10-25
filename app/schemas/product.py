from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.common import PartialUpdate
from app.schemas.types import Price, PriceValue

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
Position = Annotated[int, Field(ge=0, le=10_000)]
MAX_PRODUCT_IMAGES = 5
ImageKeys = Annotated[
    list[Annotated[str, StringConstraints(min_length=1, max_length=300)]],
    Field(max_length=MAX_PRODUCT_IMAGES),
]


def _reject_duplicate_keys(keys: list[str] | None) -> list[str] | None:
    if keys is not None and len(set(keys)) != len(keys):
        raise ValueError("Image keys must be unique")
    return keys


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
    featured: bool = False
    image_keys: ImageKeys = []

    _unique_keys = field_validator("image_keys")(_reject_duplicate_keys)


class ProductUpdate(PartialUpdate):
    name: ProductName | None = None
    price: Price | None = None
    description: LongText | None = None
    ingredients: LongText | None = None
    category: Category | None = None
    allows_half: bool | None = None
    asks_doneness: bool | None = None
    active: bool | None = None
    position: Position | None = None
    featured: bool | None = None
    image_keys: ImageKeys | None = None

    _unique_keys = field_validator("image_keys")(_reject_duplicate_keys)


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
    featured: bool
    image_url: str | None = None
    image_urls: list[str] = []


class ProductRead(ProductPublicRead):
    active: bool
    image_keys: list[str]
    created_at: datetime
    updated_at: datetime
