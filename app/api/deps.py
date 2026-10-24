from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, IdentityProvider
from app.core.database import get_session
from app.core.exceptions import UnauthorizedError
from app.core.payments import PaymentGateway
from app.core.push import PushNotifier
from app.core.storage import ObjectStorage
from app.integrations.fcm import get_push_notifier
from app.integrations.firebase import get_identity_provider
from app.integrations.storage import get_object_storage
from app.integrations.stripe import get_payment_gateway
from app.models.history import ACTOR_KEY
from app.services.absence import AbsenceService
from app.services.audit import AuditService
from app.services.catalog import CatalogService
from app.services.courier import CourierService
from app.services.customer import CustomerService
from app.services.establishment import EstablishmentService
from app.services.notifications import Notifier
from app.services.opening_hours import OpeningHoursService
from app.services.order import OrderService
from app.services.push import PushDeviceService
from app.services.report import ReportService
from app.services.upload import UploadService

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
IdentityDep = Annotated[IdentityProvider, Depends(get_identity_provider)]
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
StorageDep = Annotated[ObjectStorage | None, Depends(get_object_storage)]
GatewayDep = Annotated[PaymentGateway | None, Depends(get_payment_gateway)]
PushDep = Annotated[PushNotifier | None, Depends(get_push_notifier)]


async def get_current_user(credentials: CredentialsDep, identity: IdentityDep) -> AuthenticatedUser:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")
    return await identity.verify_token(credentials.credentials)


async def get_optional_user(
    credentials: CredentialsDep, identity: IdentityDep
) -> AuthenticatedUser | None:
    if credentials is None:
        return None
    return await identity.verify_token(credentials.credentials)


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUserDep = Annotated[AuthenticatedUser | None, Depends(get_optional_user)]

CUSTOMER_TOKEN_PATTERN = r"^[A-Za-z0-9_-]{32,128}$"

CustomerTokenDep = Annotated[str, Header(alias="X-Customer-Token", pattern=CUSTOMER_TOKEN_PATTERN)]
OptionalCustomerTokenDep = Annotated[
    str | None, Header(alias="X-Customer-Token", pattern=CUSTOMER_TOKEN_PATTERN)
]


def get_audited_session(session: SessionDep, user: CurrentUserDep) -> AsyncSession:
    session.info[ACTOR_KEY] = user.uid
    return session


def get_customer_session(session: SessionDep, user: OptionalUserDep) -> AsyncSession:
    if user is not None:
        session.info[ACTOR_KEY] = user.uid
    return session


AuditedSessionDep = Annotated[AsyncSession, Depends(get_audited_session)]
CustomerSessionDep = Annotated[AsyncSession, Depends(get_customer_session)]


def get_public_establishment_service(
    session: SessionDep, storage: StorageDep
) -> EstablishmentService:
    return EstablishmentService(session, storage)


PublicEstablishmentServiceDep = Annotated[
    EstablishmentService, Depends(get_public_establishment_service)
]


def get_establishment_service(
    session: AuditedSessionDep, storage: StorageDep, gateway: GatewayDep
) -> EstablishmentService:
    return EstablishmentService(session, storage, gateway)


EstablishmentServiceDep = Annotated[EstablishmentService, Depends(get_establishment_service)]


def get_public_catalog_service(session: SessionDep, storage: StorageDep) -> CatalogService:
    return CatalogService(session, storage)


PublicCatalogServiceDep = Annotated[CatalogService, Depends(get_public_catalog_service)]


def get_catalog_service(session: AuditedSessionDep, storage: StorageDep) -> CatalogService:
    return CatalogService(session, storage)


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


def get_public_opening_hours_service(session: SessionDep) -> OpeningHoursService:
    return OpeningHoursService(session)


PublicOpeningHoursServiceDep = Annotated[
    OpeningHoursService, Depends(get_public_opening_hours_service)
]


def get_opening_hours_service(session: AuditedSessionDep) -> OpeningHoursService:
    return OpeningHoursService(session)


OpeningHoursServiceDep = Annotated[OpeningHoursService, Depends(get_opening_hours_service)]


def get_absence_service(session: AuditedSessionDep) -> AbsenceService:
    return AbsenceService(session)


AbsenceServiceDep = Annotated[AbsenceService, Depends(get_absence_service)]


def get_customer_order_service(
    session: CustomerSessionDep, push: PushDep, gateway: GatewayDep
) -> OrderService:
    return OrderService(session, Notifier(session, push), gateway)


CustomerOrderServiceDep = Annotated[OrderService, Depends(get_customer_order_service)]


def get_order_service(
    session: AuditedSessionDep, push: PushDep, gateway: GatewayDep
) -> OrderService:
    return OrderService(session, Notifier(session, push), gateway)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


def get_payment_order_service(
    session: SessionDep, push: PushDep, gateway: GatewayDep
) -> OrderService:
    return OrderService(session, Notifier(session, push), gateway)


PaymentOrderServiceDep = Annotated[OrderService, Depends(get_payment_order_service)]


def get_public_courier_service(session: SessionDep) -> CourierService:
    return CourierService(session)


PublicCourierServiceDep = Annotated[CourierService, Depends(get_public_courier_service)]


def get_courier_service(session: AuditedSessionDep) -> CourierService:
    return CourierService(session)


CourierServiceDep = Annotated[CourierService, Depends(get_courier_service)]


def get_customer_service(session: AuditedSessionDep) -> CustomerService:
    return CustomerService(session)


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]


def get_push_device_service(session: CustomerSessionDep) -> PushDeviceService:
    return PushDeviceService(session)


PushDeviceServiceDep = Annotated[PushDeviceService, Depends(get_push_device_service)]


def get_report_service(session: AuditedSessionDep) -> ReportService:
    return ReportService(session)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


def get_audit_service(session: AuditedSessionDep) -> AuditService:
    return AuditService(session)


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


def get_upload_service(session: AuditedSessionDep, storage: StorageDep) -> UploadService:
    return UploadService(session, storage)


UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
