from datetime import datetime
from typing import Any

from sqlalchemy import Select, Table, func, literal, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.exceptions import UnprocessableError
from app.models import (
    Absence,
    Courier,
    CourierInvite,
    Establishment,
    OpeningHours,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    PushDevice,
)
from app.models.history import HISTORY_COLUMNS
from app.repositories.establishment import EstablishmentRepository
from app.schemas.audit import AuditEntry
from app.services.common import require_establishment

SCOPED_MODELS = (
    Absence,
    Courier,
    CourierInvite,
    OpeningHours,
    Order,
    OrderEvent,
    Product,
    PushDevice,
)
AUDITED_ENTITIES = {Establishment.__tablename__, OrderItem.__tablename__} | {
    model.__tablename__ for model in SCOPED_MODELS
}


def _history(model: type) -> Table:
    return model.__history_table__


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.establishments = EstablishmentRepository(session)

    async def list(
        self,
        user: AuthenticatedUser,
        *,
        offset: int,
        limit: int,
        entity: str | None,
        created_from: datetime | None,
        created_until: datetime | None,
    ) -> tuple[list[AuditEntry], int]:
        if entity is not None and entity not in AUDITED_ENTITIES:
            raise UnprocessableError(f"Unknown entity {entity}")
        establishment = await require_establishment(self.establishments, user)
        selects = [
            self._select(table, condition, created_from, created_until)
            for table, condition in self._scopes(establishment.id)
            if entity is None or table.name.removesuffix("_history") == entity
        ]
        combined = union_all(*selects).subquery()
        total = await self.session.scalar(select(func.count()).select_from(combined))
        rows = await self.session.execute(
            select(combined)
            .order_by(combined.c.valid_from.desc(), combined.c.history_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._entry(row) for row in rows.mappings()], total or 0

    @staticmethod
    def _scopes(establishment_id: Any) -> list[tuple[Table, Any]]:
        orders = _history(Order)
        scopes = [(_history(Establishment), _history(Establishment).c.id == establishment_id)]
        scopes += [
            (_history(model), _history(model).c.establishment_id == establishment_id)
            for model in SCOPED_MODELS
        ]
        order_ids = select(orders.c.id).where(orders.c.establishment_id == establishment_id)
        scopes.append((_history(OrderItem), _history(OrderItem).c.order_id.in_(order_ids)))
        return scopes

    @staticmethod
    def _select(
        table: Table,
        condition: Any,
        created_from: datetime | None,
        created_until: datetime | None,
    ) -> Select:
        stmt = select(
            literal(table.name.removesuffix("_history")).label("entity"),
            table.c.history_id,
            table.c.id.label("entity_id"),
            table.c.operation,
            table.c.valid_from,
            table.c.changed_by,
            func.to_jsonb(literal_column(table.name)).label("snapshot"),
        ).where(condition)
        if created_from is not None:
            stmt = stmt.where(table.c.valid_from >= created_from)
        if created_until is not None:
            stmt = stmt.where(table.c.valid_from < created_until)
        return stmt

    @staticmethod
    def _entry(row: Any) -> AuditEntry:
        snapshot = {
            key: value
            for key, value in row["snapshot"].items()
            if key not in HISTORY_COLUMNS and key not in {"customer_token_hash", "token_hash"}
        }
        return AuditEntry(
            history_id=row["history_id"],
            entity=row["entity"],
            entity_id=row["entity_id"],
            operation=row["operation"],
            valid_from=row["valid_from"],
            changed_by=row["changed_by"],
            snapshot=snapshot,
        )
