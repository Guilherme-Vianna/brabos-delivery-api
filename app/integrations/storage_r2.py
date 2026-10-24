import asyncio
from datetime import timedelta

import boto3
from botocore.config import Config

from app.core.storage import UPLOAD_EXPIRES_SECONDS, PresignedUpload
from app.models.base import utc_now


class R2ObjectStorage:
    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        public_base_url: str,
    ) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")

    async def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=UPLOAD_EXPIRES_SECONDS,
        )
        return PresignedUpload(
            url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            expires_at=utc_now() + timedelta(seconds=UPLOAD_EXPIRES_SECONDS),
        )

    def public_url(self, key: str) -> str:
        return f"{self._public_base_url}/{key}"

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
