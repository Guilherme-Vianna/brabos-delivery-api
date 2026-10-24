from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.history import versioned


@versioned
class Customer(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(300))
    reference_point: Mapped[str | None] = mapped_column(String(200))
