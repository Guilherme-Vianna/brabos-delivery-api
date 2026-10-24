from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import (
    AuditServiceDep,
    CurrentUserDep,
    GatewayDep,
    OptionalCustomerTokenDep,
    OptionalUserDep,
    PaymentOrderServiceDep,
    PushDeviceServiceDep,
    ReportServiceDep,
    UploadServiceDep,
)
from app.api.filters import PeriodDep
from app.api.pagination import PaginationDep
from app.core.exceptions import ServiceUnavailableError
from app.schemas.audit import AuditEntry
from app.schemas.common import Page
from app.schemas.push import PushDeviceRegister
from app.schemas.report import SalesReport
from app.schemas.upload import UploadRead, UploadRequest

router = APIRouter(tags=["platform"])


@router.get("/reports/sales", response_model=SalesReport)
async def sales_report(
    user: CurrentUserDep, service: ReportServiceDep, period: PeriodDep
) -> SalesReport:
    return await service.sales(user, period.starts_from, period.starts_until)


@router.get("/audit", response_model=Page[AuditEntry])
async def list_audit(
    user: CurrentUserDep,
    service: AuditServiceDep,
    pagination: PaginationDep,
    period: PeriodDep,
    entity: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[AuditEntry]:
    items, total = await service.list(
        user,
        offset=pagination.offset,
        limit=pagination.limit,
        entity=entity,
        created_from=period.starts_from,
        created_until=period.starts_until,
    )
    return Page[AuditEntry](
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.post("/uploads", response_model=UploadRead, status_code=status.HTTP_201_CREATED)
async def create_upload(
    data: UploadRequest, user: CurrentUserDep, service: UploadServiceDep
) -> UploadRead:
    return await service.create(user, data)


@router.post("/push-devices", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_device(
    data: PushDeviceRegister,
    user: OptionalUserDep,
    service: PushDeviceServiceDep,
    customer_token: OptionalCustomerTokenDep = None,
) -> None:
    await service.register(data, user, customer_token)


@router.delete("/push-devices/{fcm_token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_device(fcm_token: str, service: PushDeviceServiceDep) -> None:
    await service.unregister(fcm_token)


@router.post("/payments/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def payment_webhook(
    request: Request,
    gateway: GatewayDep,
    service: PaymentOrderServiceDep,
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")] = "",
) -> None:
    if gateway is None:
        raise ServiceUnavailableError("Online payments are not configured")
    event = gateway.parse_webhook(await request.body(), stripe_signature)
    await service.handle_payment(event)
