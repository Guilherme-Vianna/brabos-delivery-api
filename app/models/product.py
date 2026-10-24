from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    false,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PRICE, Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.history import versioned


@versioned
class Product(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("establishment_id", "name"),
        CheckConstraint("price >= 0", name="price"),
    )

    establishment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="", server_default="")
    ingredients: Mapped[str] = mapped_column(String(500), default="", server_default="")
    category: Mapped[str] = mapped_column(String(60), default="", server_default="")
    price: Mapped[Decimal] = mapped_column(PRICE)
    allows_half: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    asks_doneness: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    position: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    image_key: Mapped[str | None] = mapped_column(String(300))
