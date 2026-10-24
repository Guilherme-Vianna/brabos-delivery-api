from fastapi import APIRouter

from app.api.deps import CurrentUserDep, CustomerServiceDep
from app.api.pagination import PaginationDep
from app.schemas.common import Page
from app.schemas.customer import CustomerRead, CustomerUpsert
from app.schemas.order import CustomerOrderRead

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/me", response_model=CustomerRead)
async def get_my_profile(user: CurrentUserDep, service: CustomerServiceDep) -> CustomerRead:
    return CustomerRead.model_validate(await service.get(user))


@router.put("/me", response_model=CustomerRead)
async def save_my_profile(
    data: CustomerUpsert, user: CurrentUserDep, service: CustomerServiceDep
) -> CustomerRead:
    return CustomerRead.model_validate(await service.upsert(user, data))


@router.get("/me/orders", response_model=Page[CustomerOrderRead])
async def list_my_customer_orders(
    user: CurrentUserDep, service: CustomerServiceDep, pagination: PaginationDep
) -> Page[CustomerOrderRead]:
    items, total = await service.orders_of(user, offset=pagination.offset, limit=pagination.limit)
    return Page[CustomerOrderRead](
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )
