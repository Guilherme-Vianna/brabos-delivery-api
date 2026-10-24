from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CourierServiceDep,
    CurrentUserDep,
    OrderServiceDep,
    PublicCourierServiceDep,
)
from app.api.pagination import PaginationDep, to_page
from app.schemas.common import Page
from app.schemas.courier import (
    CourierInvitePublicRead,
    CourierInviteRead,
    CourierJoin,
    CourierMembershipRead,
    CourierRead,
    CourierUpdate,
)
from app.schemas.order import OrderRead

router = APIRouter(tags=["couriers"])


@router.post(
    "/courier-invites", response_model=CourierInviteRead, status_code=status.HTTP_201_CREATED
)
async def create_courier_invite(
    user: CurrentUserDep, service: CourierServiceDep
) -> CourierInviteRead:
    return await service.invite(user)


@router.get("/courier-invites/{token}", response_model=CourierInvitePublicRead)
async def get_courier_invite(
    token: str, service: PublicCourierServiceDep
) -> CourierInvitePublicRead:
    return await service.describe_invite(token)


@router.post("/courier-invites/{token}/accept", response_model=CourierMembershipRead)
async def accept_courier_invite(
    token: str, data: CourierJoin, user: CurrentUserDep, service: CourierServiceDep
) -> CourierMembershipRead:
    return await service.join(user, token, data)


@router.get("/couriers", response_model=Page[CourierRead])
async def list_couriers(
    user: CurrentUserDep, service: CourierServiceDep, pagination: PaginationDep
) -> Page[CourierRead]:
    result = await service.list(user, offset=pagination.offset, limit=pagination.limit)
    return to_page(CourierRead, result, pagination)


@router.patch("/couriers/{courier_id}", response_model=CourierRead)
async def update_courier(
    courier_id: UUID, data: CourierUpdate, user: CurrentUserDep, service: CourierServiceDep
) -> CourierRead:
    return CourierRead.model_validate(await service.update(user, courier_id, data))


@router.delete("/couriers/{courier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courier(
    courier_id: UUID, user: CurrentUserDep, service: CourierServiceDep
) -> None:
    await service.delete(user, courier_id)


@router.get("/courier/me", response_model=list[CourierMembershipRead])
async def list_my_courier_memberships(
    user: CurrentUserDep, service: CourierServiceDep
) -> list[CourierMembershipRead]:
    return await service.memberships(user)


@router.get("/courier/orders", response_model=Page[OrderRead])
async def list_courier_orders(
    user: CurrentUserDep, service: OrderServiceDep, pagination: PaginationDep
) -> Page[OrderRead]:
    result = await service.list_for_courier(user, offset=pagination.offset, limit=pagination.limit)
    return to_page(OrderRead, result, pagination)


@router.post("/courier/orders/{order_id}/deliver", response_model=OrderRead)
async def deliver_as_courier(
    order_id: UUID, user: CurrentUserDep, service: OrderServiceDep
) -> OrderRead:
    return OrderRead.model_validate(await service.deliver_as_courier(user, order_id))
