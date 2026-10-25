import asyncio
from datetime import datetime, timedelta

from google.cloud import storage

from app.core.storage import UPLOAD_EXPIRES_SECONDS, PresignedUpload
from app.integrations.storage_views import ViewUrlCache
from app.models.base import utc_now


class GcsObjectStorage:
    def __init__(self, bucket: str) -> None:
        self._bucket = storage.Client().bucket(bucket)
        self._views = ViewUrlCache(self._sign_view)

    def _sign_view(self, key: str, expires_at: datetime) -> str:
        return self._bucket.blob(key).generate_signed_url(
            version="v4", expiration=expires_at, method="GET"
        )

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

    async def presign_view(self, key: str) -> str:
        return await self._views.get(key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._bucket.blob(key).delete)
