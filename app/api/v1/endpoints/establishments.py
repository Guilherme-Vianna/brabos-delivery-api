from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUserDep,
    CustomerOrderServiceDep,
    CustomerTokenDep,
    EstablishmentServiceDep,
    OptionalUserDep,
    PublicCatalogServiceDep,
    PublicEstablishmentServiceDep,
    PublicOpeningHoursServiceDep,
    StorageDep,
)
from app.api.media import present, present_all
from app.api.pagination import PaginationDep
from app.schemas.common import Page
from app.schemas.establishment import (
    EstablishmentCreate,
    EstablishmentPublicRead,
    EstablishmentRead,
    EstablishmentUpdate,
)
from app.schemas.opening_hours import OpeningHoursRead
from app.schemas.order import CustomerOrderCancel, OrderCreate, OrderPlacedRead, OrderRead
from app.schemas.product import ProductPublicRead

router = APIRouter(prefix="/establishments", tags=["establishments"])


@router.post("", response_model=EstablishmentRead, status_code=status.HTTP_201_CREATED)
async def register_establishment(
    data: EstablishmentCreate,
    user: CurrentUserDep,
    service: EstablishmentServiceDep,
    storage: StorageDep,
) -> EstablishmentRead:
    return await present(EstablishmentRead, await service.register(user, data), storage)


@router.get("/me", response_model=EstablishmentRead)
async def get_my_establishment(
    user: CurrentUserDep, service: EstablishmentServiceDep, storage: StorageDep
) -> EstablishmentRead:
    return await present(EstablishmentRead, await service.get_for_user(user), storage)


@router.patch("/me", response_model=EstablishmentRead)
async def update_my_establishment(
    data: EstablishmentUpdate,
    user: CurrentUserDep,
    service: EstablishmentServiceDep,
    storage: StorageDep,
) -> EstablishmentRead:
    return await present(EstablishmentRead, await service.update(user, data), storage)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_establishment(user: CurrentUserDep, service: EstablishmentServiceDep) -> None:
    await service.unregister(user)


@router.get("/{slug}", response_model=EstablishmentPublicRead)
async def get_establishment(
    slug: str, service: PublicEstablishmentServiceDep, storage: StorageDep
) -> EstablishmentPublicRead:
    establishment, open_status = await service.get_public(slug)
    absence = open_status.absence
    return await present(
        EstablishmentPublicRead,
        establishment,
        storage,
        is_open=open_status.is_open,
        absence_reason=absence.reason if absence else None,
        absence_ends_at=absence.ends_at if absence else None,
    )


@router.get("/{slug}/products", response_model=Page[ProductPublicRead])
async def list_establishment_products(
    slug: str,
    service: PublicCatalogServiceDep,
    storage: StorageDep,
    pagination: PaginationDep,
) -> Page[ProductPublicRead]:
    items, total = await service.list_public(slug, offset=pagination.offset, limit=pagination.limit)
    return Page[ProductPublicRead](
        items=await present_all(ProductPublicRead, items, storage),
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.get("/{slug}/opening-hours", response_model=OpeningHoursRead)
async def get_establishment_opening_hours(
    slug: str, service: PublicOpeningHoursServiceDep
) -> OpeningHoursRead:
    return await service.get_public(slug)


@router.post("/{slug}/orders", response_model=OrderPlacedRead, status_code=status.HTTP_201_CREATED)
async def place_order(
    slug: str,
    data: OrderCreate,
    customer_token: CustomerTokenDep,
    user: OptionalUserDep,
    service: CustomerOrderServiceDep,
) -> OrderPlacedRead:
    order, checkout_url = await service.place(slug, data, customer_token, user)
    return OrderPlacedRead.model_validate(order).model_copy(update={"checkout_url": checkout_url})


@router.get("/{slug}/my-orders", response_model=Page[OrderRead])
async def list_my_orders(
    slug: str,
    customer_token: CustomerTokenDep,
    user: OptionalUserDep,
    service: CustomerOrderServiceDep,
    pagination: PaginationDep,
) -> Page[OrderRead]:
    items, total = await service.list_mine(
        slug, customer_token, user, offset=pagination.offset, limit=pagination.limit
    )
    return Page[OrderRead](
        items=[OrderRead.model_validate(item) for item in items],
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.get("/{slug}/my-orders/{order_id}", response_model=OrderRead)
async def get_my_order(
    slug: str,
    order_id: UUID,
    customer_token: CustomerTokenDep,
    user: OptionalUserDep,
    service: CustomerOrderServiceDep,
) -> OrderRead:
    return OrderRead.model_validate(await service.get_mine(slug, order_id, customer_token, user))


@router.post("/{slug}/my-orders/{order_id}/cancel", response_model=OrderRead)
async def cancel_my_order(
    slug: str,
    order_id: UUID,
    data: CustomerOrderCancel,
    customer_token: CustomerTokenDep,
    user: OptionalUserDep,
    service: CustomerOrderServiceDep,
) -> OrderRead:
    order = await service.cancel_mine(slug, order_id, customer_token, user, data.reason)
    return OrderRead.model_validate(order)
