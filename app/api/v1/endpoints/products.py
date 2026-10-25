from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CatalogServiceDep, CurrentUserDep, StorageDep
from app.api.media import present, present_all
from app.api.pagination import PaginationDep
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate, user: CurrentUserDep, service: CatalogServiceDep, storage: StorageDep
) -> ProductRead:
    return await present(ProductRead, await service.create(user, data), storage)


@router.get("", response_model=Page[ProductRead])
async def list_products(
    user: CurrentUserDep,
    service: CatalogServiceDep,
    storage: StorageDep,
    pagination: PaginationDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    active: bool | None = None,
) -> Page[ProductRead]:
    items, total = await service.list(
        user, offset=pagination.offset, limit=pagination.limit, search=search, active=active
    )
    return Page[ProductRead](
        items=await present_all(ProductRead, items, storage),
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID, user: CurrentUserDep, service: CatalogServiceDep, storage: StorageDep
) -> ProductRead:
    return await present(ProductRead, await service.get(user, product_id), storage)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    user: CurrentUserDep,
    service: CatalogServiceDep,
    storage: StorageDep,
) -> ProductRead:
    return await present(ProductRead, await service.update(user, product_id, data), storage)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID, user: CurrentUserDep, service: CatalogServiceDep
) -> None:
    await service.delete(user, product_id)
