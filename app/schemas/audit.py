from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.history import HistoryOperation


class AuditEntry(BaseModel):
    history_id: UUID
    entity: str
    entity_id: UUID
    operation: HistoryOperation
    valid_from: datetime
    changed_by: str | None
    snapshot: dict[str, Any]
