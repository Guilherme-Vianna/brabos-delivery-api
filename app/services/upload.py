from uuid import uuid7

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import ServiceUnavailableError
from app.core.storage import IMAGE_CONTENT_TYPES, ObjectStorage, establishment_prefix
from app.repositories.establishment import EstablishmentRepository
from app.schemas.upload import UploadRead, UploadRequest
from app.services.common import require_establishment


class UploadService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None) -> None:
        self.storage = storage
        self.establishments = EstablishmentRepository(session)

    async def create(self, user: AuthenticatedUser, data: UploadRequest) -> UploadRead:
        establishment = await require_establishment(self.establishments, user)
        if self.storage is None:
            raise ServiceUnavailableError("Image storage is not configured")
        extension = IMAGE_CONTENT_TYPES[data.content_type]
        key = f"{establishment_prefix(establishment.id)}{data.kind.value}s/{uuid7()}.{extension}"
        upload = await self.storage.presign_upload(key, data.content_type)
        return UploadRead(
            key=key,
            upload_url=upload.url,
            method=upload.method,
            headers=upload.headers,
            expires_at=upload.expires_at,
            public_url=self.storage.public_url(key),
        )
