from functools import lru_cache

from app.core.config import settings
from app.core.storage import ObjectStorage


@lru_cache
def get_object_storage() -> ObjectStorage | None:
    match settings.storage_provider:
        case "gcs" if settings.gcs_bucket:
            from app.integrations.storage_gcs import GcsObjectStorage

            return GcsObjectStorage(settings.gcs_bucket)
        case "r2" if (
            settings.r2_account_id
            and settings.r2_access_key_id
            and settings.r2_secret_access_key
            and settings.r2_bucket
        ):
            from app.integrations.storage_r2 import R2ObjectStorage

            return R2ObjectStorage(
                settings.r2_account_id,
                settings.r2_access_key_id,
                settings.r2_secret_access_key,
                settings.r2_bucket,
            )
    return None
