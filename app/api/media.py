import asyncio
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

from app.core.storage import ObjectStorage


async def sign_views(storage: ObjectStorage | None, keys: Iterable[str]) -> list[str]:
    if storage is None:
        return []
    return list(await asyncio.gather(*(storage.presign_view(key) for key in keys)))


async def present[SchemaT: BaseModel](
    schema: type[SchemaT], entity: Any, storage: ObjectStorage | None, **extra: Any
) -> SchemaT:
    urls: dict[str, Any] = {}
    for field in schema.model_fields:
        if field.endswith("_urls"):
            keys = getattr(entity, field.removesuffix("_urls") + "_keys", None) or []
            urls[field] = await sign_views(storage, keys)
        elif field.endswith("_url"):
            base = field.removesuffix("_url")
            key = getattr(entity, base + "_key", None)
            if key is None:
                key = next(iter(getattr(entity, base + "_keys", None) or []), None)
            urls[field] = (await sign_views(storage, [key]))[0] if storage and key else None
    return schema.model_validate(entity).model_copy(update={**urls, **extra})


async def present_all[SchemaT: BaseModel](
    schema: type[SchemaT], entities: Iterable[Any], storage: ObjectStorage | None
) -> list[SchemaT]:
    return list(await asyncio.gather(*(present(schema, entity, storage) for entity in entities)))
