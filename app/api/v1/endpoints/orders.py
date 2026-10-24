from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, OrderServiceDep
from app.api.filters import PeriodDep
from app.api.pagination import PaginationDep, to_page
from app.models.order import OrderStatus
from app.schemas.common import Page
from app.schemas.order import OrderCancel, OrderEventRead, OrderRead

router = APIRouter(tags=["orders"])


@router.get("/orders", response_model=Page[OrderRead])
async def list_orders(
    user: CurrentUserDep,
    service: OrderServiceDep,
    pagination: PaginationDep,
    period: PeriodDep,
    order_status: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
) -> Page[OrderRead]:
    result = await service.list(
        user,
        offset=pagination.offset,
        limit=pagination.limit,
        statuses=order_status,
        created_from=period.starts_from,
        created_until=period.starts_until,
    )
    return to_page(OrderRead, result, pagination)


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(order_id: UUID, user: CurrentUserDep, service: OrderServiceDep) -> OrderRead:
    return OrderRead.model_validate(await service.get(user, order_id))


@router.post("/orders/{order_id}/accept", response_model=OrderRead)
async def accept_order(order_id: UUID, user: CurrentUserDep, service: OrderServiceDep) -> OrderRead:
    return OrderRead.model_validate(await service.accept(user, order_id))


@router.post("/orders/{order_id}/deliver", response_model=OrderRead)
async def deliver_order(
    order_id: UUID, user: CurrentUserDep, service: OrderServiceDep
) -> OrderRead:
    return OrderRead.model_validate(await service.deliver(user, order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: UUID, data: OrderCancel, user: CurrentUserDep, service: OrderServiceDep
) -> OrderRead:
    return OrderRead.model_validate(await service.cancel(user, order_id, data.reason))


@router.get("/order-events", response_model=Page[OrderEventRead])
async def list_order_events(
    user: CurrentUserDep,
    service: OrderServiceDep,
    pagination: PaginationDep,
    period: PeriodDep,
    order_id: UUID | None = None,
) -> Page[OrderEventRead]:
    result = await service.list_events(
        user,
        offset=pagination.offset,
        limit=pagination.limit,
        order_id=order_id,
        created_from=period.starts_from,
        created_until=period.starts_until,
    )
    return to_page(OrderEventRead, result, pagination)
