from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

IMAGE_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
UPLOAD_EXPIRES_SECONDS = 600
VIEW_URL_WINDOW_SECONDS = 3600


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime


class ObjectStorage(Protocol):
    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...

    async def presign_view(self, key: str) -> str: ...

    async def delete(self, key: str) -> None: ...


def view_expires_at(now: datetime) -> datetime:
    window = VIEW_URL_WINDOW_SECONDS
    return datetime.fromtimestamp((int(now.timestamp()) // window + 2) * window, tz=UTC)


def establishment_prefix(establishment_id: object) -> str:
    return f"establishments/{establishment_id}/"
