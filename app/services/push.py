from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.push_device import PushDevice, PushRole
from app.repositories.courier import CourierRepository
from app.repositories.establishment import EstablishmentRepository
from app.repositories.push_device import PushDeviceRepository
from app.schemas.push import PushDeviceRegister
from app.services.common import hash_token


class PushDeviceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.devices = PushDeviceRepository(session)

    async def register(
        self,
        data: PushDeviceRegister,
        user: AuthenticatedUser | None,
        customer_token: str | None,
    ) -> None:
        fields = await self._owner_fields(data.role, user, customer_token)
        device = await self.devices.get_by_token(data.fcm_token)
        if device is None:
            await self.devices.add(PushDevice(fcm_token=data.fcm_token, role=data.role, **fields))
        else:
            device.role = data.role
            for name, value in fields.items():
                setattr(device, name, value)
            await self.devices.save(device)
        await self.session.commit()

    async def unregister(self, fcm_token: str) -> None:
        device = await self.devices.get_by_token(fcm_token)
        if device is not None:
            await self.devices.delete(device)
            await self.session.commit()

    async def _owner_fields(
        self, role: PushRole, user: AuthenticatedUser | None, customer_token: str | None
    ) -> dict[str, object]:
        if role is PushRole.CUSTOMER:
            if customer_token is None and user is None:
                raise UnauthorizedError("Customer token or sign-in required")
            return {
                "firebase_uid": user.uid if user else None,
                "customer_token_hash": hash_token(customer_token) if customer_token else None,
                "establishment_id": None,
            }
        if user is None:
            raise UnauthorizedError("Missing bearer token")
        if role is PushRole.OWNER:
            establishment = await EstablishmentRepository(self.session).get_by_firebase_uid(
                user.uid
            )
            if establishment is None:
                raise ForbiddenError("Register an establishment before performing this action")
            establishment_id = establishment.id
        else:
            if not await CourierRepository(self.session).active_for_uid(user.uid):
                raise ForbiddenError("User is not an active courier")
            establishment_id = None
        return {
            "firebase_uid": user.uid,
            "customer_token_hash": None,
            "establishment_id": establishment_id,
        }
