from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Integer, String, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PRICE, Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.history import versioned

DEFAULT_PRIMARY_COLOR = "#D62828"
DEFAULT_ACCENT_COLOR = "#F77F00"


@versioned
class Establishment(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "establishments"
    __table_args__ = (
        CheckConstraint("delivery_fee >= 0", name="delivery_fee"),
        CheckConstraint("min_order >= 0", name="min_order"),
        CheckConstraint("next_order_number > 0", name="next_order_number"),
    )

    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(String(300))
    phone: Mapped[str] = mapped_column(String(20))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    primary_color: Mapped[str] = mapped_column(
        String(7), default=DEFAULT_PRIMARY_COLOR, server_default=DEFAULT_PRIMARY_COLOR
    )
    accent_color: Mapped[str] = mapped_column(
        String(7), default=DEFAULT_ACCENT_COLOR, server_default=DEFAULT_ACCENT_COLOR
    )
    auto_accept: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    delivery_fee_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    delivery_fee: Mapped[Decimal] = mapped_column(PRICE, default=Decimal(0), server_default="0")
    min_order: Mapped[Decimal | None] = mapped_column(PRICE)
    online_payments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    stripe_account_id: Mapped[str | None] = mapped_column(String(64))
    logo_key: Mapped[str | None] = mapped_column(String(300))
    next_order_number: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
