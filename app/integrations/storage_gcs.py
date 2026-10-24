import asyncio
from datetime import timedelta

from google.cloud import storage

from app.core.storage import UPLOAD_EXPIRES_SECONDS, PresignedUpload
from app.models.base import utc_now


class GcsObjectStorage:
    def __init__(self, bucket: str, public_base_url: str | None = None) -> None:
        self._bucket = storage.Client().bucket(bucket)
        self._public_base_url = (
            public_base_url or f"https://storage.googleapis.com/{bucket}"
        ).rstrip("/")

    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        expires_in = timedelta(seconds=UPLOAD_EXPIRES_SECONDS)
        url = await asyncio.to_thread(
            self._bucket.blob(key).generate_signed_url,
            version="v4",
            expiration=expires_in,
            method="PUT",
            content_type=content_type,
        )
        return PresignedUpload(
            url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            expires_at=utc_now() + expires_in,
        )

    def public_url(self, key: str) -> str:
        return f"{self._public_base_url}/{key}"

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._bucket.blob(key).delete)
