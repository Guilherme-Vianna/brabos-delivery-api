import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.auth import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.core.storage import ObjectStorage, establishment_prefix
from app.models.absence import Absence
from app.models.establishment import Establishment
from app.models.opening_hours import OpeningHours
from app.repositories.establishment import EstablishmentRepository

logger = logging.getLogger(__name__)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def local_zone() -> ZoneInfo:
    return ZoneInfo(settings.time_zone)


async def require_establishment(
    establishments: EstablishmentRepository, user: AuthenticatedUser
) -> Establishment:
    establishment = await establishments.get_by_firebase_uid(user.uid)
    if establishment is None:
        raise ForbiddenError("Register an establishment before performing this action")
    return establishment


async def existing_establishment(
    establishments: EstablishmentRepository, slug: str
) -> Establishment:
    establishment = await establishments.get_by_slug(slug.lower())
    if establishment is None:
        raise NotFoundError(f"Establishment {slug} not found")
    return establishment


def _minutes(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def is_within_hours(hours: Sequence[OpeningHours], moment: datetime) -> bool:
    local = moment.astimezone(local_zone())
    minute = _minutes(local)
    by_day = {item.weekday: item for item in hours}
    today = by_day.get(local.weekday())
    if today is not None:
        opens, closes = _minutes(today.opens_at), _minutes(today.closes_at)
        if opens < closes and opens <= minute < closes:
            return True
        if closes < opens and minute >= opens:
            return True
    yesterday = by_day.get((local.weekday() - 1) % 7)
    if yesterday is not None:
        opens, closes = _minutes(yesterday.opens_at), _minutes(yesterday.closes_at)
        if closes < opens and minute < closes:
            return True
    return False


@dataclass(frozen=True, slots=True)
class OpenStatus:
    is_open: bool
    absence: Absence | None


OPEN_STATUS_TTL = timedelta(minutes=1)


def ensure_media_key(
    storage: ObjectStorage | None, establishment: Establishment, key: str | None
) -> None:
    if key is None:
        return
    if storage is None:
        raise UnprocessableError("Image storage is not configured")
    if not key.startswith(establishment_prefix(establishment.id)) or ".." in key:
        raise UnprocessableError("Image key does not belong to this establishment")


async def discard_media(storage: ObjectStorage | None, key: str | None) -> None:
    if storage is None or key is None:
        return
    try:
        await storage.delete(key)
    except Exception:
        logger.exception("Could not delete stored object %s", key)
