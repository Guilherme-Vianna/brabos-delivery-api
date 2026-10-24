import secrets
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.base import utc_now
from app.models.courier import Courier, CourierInvite
from app.models.establishment import Establishment
from app.repositories.courier import CourierInviteRepository, CourierRepository
from app.repositories.establishment import EstablishmentRepository
from app.schemas.courier import (
    CourierInvitePublicRead,
    CourierInviteRead,
    CourierJoin,
    CourierMembershipRead,
    CourierUpdate,
)
from app.services.common import hash_token, require_establishment

INVITE_LIFETIME = timedelta(days=7)


class CourierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.establishments = EstablishmentRepository(session)
        self.couriers = CourierRepository(session)
        self.invites = CourierInviteRepository(session)

    async def invite(self, user: AuthenticatedUser) -> CourierInviteRead:
        establishment = await require_establishment(self.establishments, user)
        token = secrets.token_urlsafe(32)
        invite = await self.invites.add(
            CourierInvite(
                establishment_id=establishment.id,
                token_hash=hash_token(token),
                expires_at=utc_now() + INVITE_LIFETIME,
            )
        )
        await self.session.commit()
        url = f"{settings.public_app_url.rstrip('/')}/entregador/convite/{token}"
        return CourierInviteRead(token=token, url=url, expires_at=invite.expires_at)

    async def describe_invite(self, token: str) -> CourierInvitePublicRead:
        invite, establishment = await self._valid_invite(token)
        return CourierInvitePublicRead(
            establishment_name=establishment.name, expires_at=invite.expires_at
        )

    async def join(
        self, user: AuthenticatedUser, token: str, data: CourierJoin
    ) -> CourierMembershipRead:
        invite, establishment = await self._valid_invite(token)
        if establishment.firebase_uid == user.uid:
            raise ConflictError("Owners cannot join their own establishment as couriers")
        courier = await self.couriers.get_by(
            establishment_id=establishment.id, firebase_uid=user.uid
        )
        if courier is None:
            courier = await self.couriers.add(
                Courier(
                    establishment_id=establishment.id, firebase_uid=user.uid, **data.model_dump()
                )
            )
        else:
            courier.name, courier.phone, courier.active = data.name, data.phone, True
            await self.couriers.save(courier)
        invite.used_at = utc_now()
        invite.courier_id = courier.id
        await self.invites.save(invite)
        await self.session.commit()
        return self._membership(courier, establishment)

    async def memberships(self, user: AuthenticatedUser) -> list[CourierMembershipRead]:
        result = []
        for courier in await self.couriers.active_for_uid(user.uid):
            establishment = await self.establishments.get(courier.establishment_id)
            if establishment is not None:
                result.append(self._membership(courier, establishment))
        return result

    async def list(
        self, user: AuthenticatedUser, *, offset: int, limit: int
    ) -> tuple[Sequence[Courier], int]:
        establishment = await require_establishment(self.establishments, user)
        return await self.couriers.list_for_establishment(
            establishment.id, offset=offset, limit=limit
        )

    async def update(
        self, user: AuthenticatedUser, courier_id: UUID, data: CourierUpdate
    ) -> Courier:
        courier = await self._owned(user, courier_id)
        courier.active = data.active
        await self.couriers.save(courier)
        await self.session.commit()
        return courier

    async def delete(self, user: AuthenticatedUser, courier_id: UUID) -> None:
        courier = await self._owned(user, courier_id)
        if await self.couriers.has_orders(courier.id):
            raise ConflictError("Courier has deliveries; deactivate them instead")
        for invite in await self.invites.find_by(courier_id=courier.id):
            invite.courier_id = None
            await self.invites.save(invite)
        await self.couriers.delete(courier)
        await self.session.commit()

    async def _owned(self, user: AuthenticatedUser, courier_id: UUID) -> Courier:
        establishment = await require_establishment(self.establishments, user)
        courier = await self.couriers.get_by(id=courier_id, establishment_id=establishment.id)
        if courier is None:
            raise NotFoundError(f"Courier {courier_id} not found")
        return courier

    async def _valid_invite(self, token: str) -> tuple[CourierInvite, Establishment]:
        invite = await self.invites.get_by_hash(hash_token(token))
        if invite is None or invite.used_at is not None or invite.expires_at <= utc_now():
            raise NotFoundError("Invite is invalid or has expired")
        establishment = await self.establishments.get(invite.establishment_id)
        assert establishment is not None
        return invite, establishment

    @staticmethod
    def _membership(courier: Courier, establishment: Establishment) -> CourierMembershipRead:
        return CourierMembershipRead(
            courier_id=courier.id,
            establishment_id=establishment.id,
            establishment_name=establishment.name,
            establishment_slug=establishment.slug,
        )
