from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.core.storage import MAX_IMAGE_BYTES


class UploadKind(StrEnum):
    PRODUCT = "product"
    LOGO = "logo"


class UploadRequest(BaseModel):
    kind: UploadKind
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size: Annotated[int, Field(gt=0, le=MAX_IMAGE_BYTES)]


class UploadRead(BaseModel):
    key: str
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime
    view_url: str
