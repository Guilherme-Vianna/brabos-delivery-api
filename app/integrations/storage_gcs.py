import asyncio
import threading
from datetime import datetime, timedelta

import google.auth
from google.auth.credentials import Signing
from google.auth.transport.requests import Request
from google.cloud import storage

from app.core.storage import UPLOAD_EXPIRES_SECONDS, PresignedUpload
from app.integrations.storage_views import ViewUrlCache
from app.models.base import utc_now

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GcsObjectStorage:
    def __init__(self, bucket: str) -> None:
        self._credentials, project = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
        self._bucket = storage.Client(project=project, credentials=self._credentials).bucket(bucket)
        self._refresh_lock = threading.Lock()
        self._views = ViewUrlCache(self._sign_view)

    def _signing_kwargs(self) -> dict[str, str]:
        if isinstance(self._credentials, Signing):
            return {}
        with self._refresh_lock:
            if not self._credentials.valid:
                self._credentials.refresh(Request())
            return {
                "service_account_email": self._credentials.service_account_email,
                "access_token": self._credentials.token,
            }

    def _sign_view(self, key: str, expires_at: datetime) -> str:
        return self._bucket.blob(key).generate_signed_url(
            version="v4", expiration=expires_at, method="GET", **self._signing_kwargs()
        )

    def _sign_upload(self, key: str, content_type: str, expires_in: timedelta) -> str:
        return self._bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=expires_in,
            method="PUT",
            content_type=content_type,
            **self._signing_kwargs(),
        )

    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        expires_in = timedelta(seconds=UPLOAD_EXPIRES_SECONDS)
        url = await asyncio.to_thread(self._sign_upload, key, content_type, expires_in)
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
