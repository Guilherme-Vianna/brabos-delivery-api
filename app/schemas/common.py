from typing import ClassVar, Self

from pydantic import BaseModel, model_validator


class Page[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int


class PartialUpdate(BaseModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_nulls(self) -> Self:
        nulls = sorted(
            name
            for name in self.model_fields_set - self.nullable_fields
            if getattr(self, name) is None
        )
        if nulls:
            raise ValueError(f"Fields cannot be null: {', '.join(nulls)}")
        return self
