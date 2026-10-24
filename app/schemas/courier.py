from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.types import FullName, Phone


class CourierInviteRead(BaseModel):
    token: str
    url: str
    expires_at: datetime


class CourierInvitePublicRead(BaseModel):
    establishment_name: str
    expires_at: datetime


class CourierJoin(BaseModel):
    name: FullName
    phone: Phone | None = None


class CourierUpdate(BaseModel):
    active: bool


class CourierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    establishment_id: UUID
    name: str
    phone: str | None
    active: bool
    created_at: datetime


class CourierMembershipRead(BaseModel):
    courier_id: UUID
    establishment_id: UUID
    establishment_name: str
    establishment_slug: str
