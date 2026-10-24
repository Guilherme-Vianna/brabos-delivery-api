from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, or_, select

from app.models.push_device import PushDevice, PushRole
from app.repositories.base import BaseRepository


class PushDeviceRepository(BaseRepository[PushDevice]):
    model = PushDevice

    async def get_by_token(self, fcm_token: str) -> PushDevice | None:
        return await self.get_by(fcm_token=fcm_token)

    async def tokens_for(
        self,
        role: PushRole,
        *,
        uids: Iterable[str | None] = (),
        token_hash: str | None = None,
    ) -> list[str]:
        owners: list[ColumnElement[bool]] = []
        uid_list = [uid for uid in uids if uid]
        if uid_list:
            owners.append(PushDevice.firebase_uid.in_(uid_list))
        if token_hash is not None:
            owners.append(PushDevice.customer_token_hash == token_hash)
        if not owners:
            return []
        stmt = select(PushDevice.fcm_token).where(PushDevice.role == role, or_(*owners))
        return list((await self.session.scalars(stmt)).all())

    async def find_tokens(self, tokens: Iterable[str]) -> Sequence[PushDevice]:
        stmt = select(PushDevice).where(PushDevice.fcm_token.in_(list(tokens)))
        return (await self.session.scalars(stmt)).all()
