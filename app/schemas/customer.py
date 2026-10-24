from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.types import Address, FullName, OptionalText200, Phone


class CustomerUpsert(BaseModel):
    full_name: FullName
    phone: Phone
    address: Address | None = None
    reference_point: OptionalText200 | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    phone: str
    address: str | None
    reference_point: str | None
    created_at: datetime
    updated_at: datetime
