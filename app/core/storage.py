from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

IMAGE_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
UPLOAD_EXPIRES_SECONDS = 600


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime


class ObjectStorage(Protocol):
    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...

    def public_url(self, key: str) -> str: ...

    async def delete(self, key: str) -> None: ...


def establishment_prefix(establishment_id: object) -> str:
    return f"establishments/{establishment_id}/"
