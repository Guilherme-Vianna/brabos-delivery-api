from typing import Any

from pydantic import BaseModel

from app.core.storage import ObjectStorage


def present[SchemaT: BaseModel](
    schema: type[SchemaT], entity: Any, storage: ObjectStorage | None, **extra: Any
) -> SchemaT:
    urls = {}
    for field in schema.model_fields:
        if field.endswith("_url"):
            key = getattr(entity, field.removesuffix("_url") + "_key", None)
            urls[field] = storage.public_url(key) if storage is not None and key else None
    return schema.model_validate(entity).model_copy(update={**urls, **extra})
