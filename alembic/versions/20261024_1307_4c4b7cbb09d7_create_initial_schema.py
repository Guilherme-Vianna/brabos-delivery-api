from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c4b7cbb09d7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "absences_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_absences_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_absences_history")),
    )
    op.create_index(
        "ix_absences_history_id_valid_from", "absences_history", ["id", "valid_from"], unique=False
    )
    op.create_table(
        "courier_invites_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("courier_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_courier_invites_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_courier_invites_history")),
    )
    op.create_index(
        "ix_courier_invites_history_id_valid_from",
        "courier_invites_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "couriers_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_couriers_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_couriers_history")),
    )
    op.create_index(
        "ix_couriers_history_id_valid_from", "couriers_history", ["id", "valid_from"], unique=False
    )
    op.create_table(
        "customers",
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("reference_point", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
    )
    op.create_index(op.f("ix_customers_firebase_uid"), "customers", ["firebase_uid"], unique=True)
    op.create_table(
        "customers_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("reference_point", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_customers_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_customers_history")),
    )
    op.create_index(
        "ix_customers_history_id_valid_from",
        "customers_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "establishments",
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("primary_color", sa.String(length=7), server_default="#D62828", nullable=False),
        sa.Column("accent_color", sa.String(length=7), server_default="#FFB703", nullable=False),
        sa.Column("auto_accept", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "delivery_fee_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "delivery_fee", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False
        ),
        sa.Column("min_order", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "online_payments_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("stripe_account_id", sa.String(length=64), nullable=True),
        sa.Column("logo_key", sa.String(length=300), nullable=True),
        sa.Column("next_order_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("delivery_fee >= 0", name=op.f("ck_establishments_delivery_fee")),
        sa.CheckConstraint("min_order >= 0", name=op.f("ck_establishments_min_order")),
        sa.CheckConstraint(
            "next_order_number > 0", name=op.f("ck_establishments_next_order_number")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_establishments")),
    )
    op.create_index(
        op.f("ix_establishments_firebase_uid"), "establishments", ["firebase_uid"], unique=True
    )
    op.create_index(op.f("ix_establishments_slug"), "establishments", ["slug"], unique=True)
    op.create_table(
        "establishments_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("primary_color", sa.String(length=7), nullable=False),
        sa.Column("accent_color", sa.String(length=7), nullable=False),
        sa.Column("auto_accept", sa.Boolean(), nullable=False),
        sa.Column("delivery_fee_enabled", sa.Boolean(), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("min_order", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("online_payments_enabled", sa.Boolean(), nullable=False),
        sa.Column("stripe_account_id", sa.String(length=64), nullable=True),
        sa.Column("logo_key", sa.String(length=300), nullable=True),
        sa.Column("next_order_number", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_establishments_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_establishments_history")),
    )
    op.create_index(
        "ix_establishments_history_id_valid_from",
        "establishments_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "opening_hours_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=False),
        sa.Column("closes_at", sa.Time(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_opening_hours_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_opening_hours_history")),
    )
    op.create_index(
        "ix_opening_hours_history_id_valid_from",
        "opening_hours_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "order_events_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "placed",
                "accepted",
                "delivered",
                "cancelled",
                "paid",
                "refunded",
                name="ordereventkind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "actor",
            sa.Enum("owner", "customer", "courier", "system", name="orderactor", native_enum=False),
            nullable=False,
        ),
        sa.Column("actor_uid", sa.String(length=128), nullable=True),
        sa.Column("detail", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_order_events_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_order_events_history")),
    )
    op.create_index(
        "ix_order_events_history_id_valid_from",
        "order_events_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "order_items_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("half_product_id", sa.Uuid(), nullable=True),
        sa.Column("product_name", sa.String(length=100), nullable=False),
        sa.Column("half_product_name", sa.String(length=100), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantity", sa.SmallInteger(), nullable=False),
        sa.Column(
            "doneness",
            sa.Enum(
                "rare",
                "medium_rare",
                "medium",
                "medium_well",
                "well_done",
                name="doneness",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("notes", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_order_items_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_order_items_history")),
    )
    op.create_index(
        "ix_order_items_history_id_valid_from",
        "order_items_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "orders_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "placed",
                "accepted",
                "delivered",
                "cancelled",
                name="orderstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("reference_point", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "payment_method",
            sa.Enum("cash", "pix", "card", "online", name="paymentmethod", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum(
                "not_required",
                "pending",
                "paid",
                "refunded",
                name="paymentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("payment_reference", sa.String(length=255), nullable=True),
        sa.Column("change_for", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("customer_token_hash", sa.String(length=64), nullable=True),
        sa.Column("customer_uid", sa.String(length=128), nullable=True),
        sa.Column("courier_id", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=200), nullable=True),
        sa.Column(
            "cancelled_by",
            sa.Enum("owner", "customer", "courier", "system", name="orderactor", native_enum=False),
            nullable=True,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')", name=op.f("ck_orders_history_operation")
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_orders_history")),
    )
    op.create_index(
        "ix_orders_history_id_valid_from", "orders_history", ["id", "valid_from"], unique=False
    )
    op.create_table(
        "products_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("ingredients", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("allows_half", sa.Boolean(), nullable=False),
        sa.Column("asks_doneness", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("image_key", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_products_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_products_history")),
    )
    op.create_index(
        "ix_products_history_id_valid_from", "products_history", ["id", "valid_from"], unique=False
    )
    op.create_table(
        "push_devices_history",
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.Column("fcm_token", sa.String(length=512), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "courier", "customer", name="pushrole", native_enum=False),
            nullable=False,
        ),
        sa.Column("firebase_uid", sa.String(length=128), nullable=True),
        sa.Column("customer_token_hash", sa.String(length=64), nullable=True),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operation",
            sa.Enum("insert", "update", "delete", name="historyoperation", native_enum=False),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "operation IN ('insert', 'update', 'delete')",
            name=op.f("ck_push_devices_history_operation"),
        ),
        sa.PrimaryKeyConstraint("history_id", name=op.f("pk_push_devices_history")),
    )
    op.create_index(
        "ix_push_devices_history_id_valid_from",
        "push_devices_history",
        ["id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "absences",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_absences_period")),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_absences_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_absences")),
    )
    op.create_index(
        op.f("ix_absences_establishment_id"), "absences", ["establishment_id"], unique=False
    )
    op.create_table(
        "couriers",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_couriers_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_couriers")),
        sa.UniqueConstraint(
            "establishment_id",
            "firebase_uid",
            name=op.f("uq_couriers_establishment_id_firebase_uid"),
        ),
    )
    op.create_index(op.f("ix_couriers_firebase_uid"), "couriers", ["firebase_uid"], unique=False)
    op.create_table(
        "opening_hours",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=False),
        sa.Column("closes_at", sa.Time(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("closes_at <> opens_at", name=op.f("ck_opening_hours_period")),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_opening_hours_weekday")),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_opening_hours_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opening_hours")),
        sa.UniqueConstraint(
            "establishment_id", "weekday", name=op.f("uq_opening_hours_establishment_id_weekday")
        ),
    )
    op.create_table(
        "order_events",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "placed",
                "accepted",
                "delivered",
                "cancelled",
                "paid",
                "refunded",
                name="ordereventkind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "actor",
            sa.Enum("owner", "customer", "courier", "system", name="orderactor", native_enum=False),
            nullable=False,
        ),
        sa.Column("actor_uid", sa.String(length=128), nullable=True),
        sa.Column("detail", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor IN ('owner', 'customer', 'courier', 'system')",
            name=op.f("ck_order_events_actor"),
        ),
        sa.CheckConstraint(
            "kind IN ('placed', 'accepted', 'delivered', 'cancelled', 'paid', 'refunded')",
            name=op.f("ck_order_events_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_order_events_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_events")),
    )
    op.create_index(
        "ix_order_events_establishment_id_created_at",
        "order_events",
        ["establishment_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_order_events_order_id"), "order_events", ["order_id"], unique=False)
    op.create_table(
        "products",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("ingredients", sa.String(length=500), server_default="", nullable=False),
        sa.Column("category", sa.String(length=60), server_default="", nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("allows_half", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("asks_doneness", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("position", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("image_key", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price >= 0", name=op.f("ck_products_price")),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_products_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint(
            "establishment_id", "name", name=op.f("uq_products_establishment_id_name")
        ),
    )
    op.create_table(
        "push_devices",
        sa.Column("fcm_token", sa.String(length=512), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "courier", "customer", name="pushrole", native_enum=False),
            nullable=False,
        ),
        sa.Column("firebase_uid", sa.String(length=128), nullable=True),
        sa.Column("customer_token_hash", sa.String(length=64), nullable=True),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'courier', 'customer')", name=op.f("ck_push_devices_role")
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_push_devices_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_push_devices")),
        sa.UniqueConstraint("fcm_token", name=op.f("uq_push_devices_fcm_token")),
    )
    op.create_index(
        op.f("ix_push_devices_customer_token_hash"),
        "push_devices",
        ["customer_token_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_devices_establishment_id"), "push_devices", ["establishment_id"], unique=False
    )
    op.create_index(
        op.f("ix_push_devices_firebase_uid"), "push_devices", ["firebase_uid"], unique=False
    )
    op.create_table(
        "courier_invites",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("courier_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["courier_id"], ["couriers.id"], name=op.f("fk_courier_invites_courier_id_couriers")
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_courier_invites_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courier_invites")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_courier_invites_token_hash")),
    )
    op.create_index(
        op.f("ix_courier_invites_establishment_id"),
        "courier_invites",
        ["establishment_id"],
        unique=False,
    )
    op.create_table(
        "orders",
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "placed",
                "accepted",
                "delivered",
                "cancelled",
                name="orderstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("reference_point", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "payment_method",
            sa.Enum("cash", "pix", "card", "online", name="paymentmethod", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum(
                "not_required",
                "pending",
                "paid",
                "refunded",
                name="paymentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("payment_reference", sa.String(length=255), nullable=True),
        sa.Column("change_for", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("customer_token_hash", sa.String(length=64), nullable=True),
        sa.Column("customer_uid", sa.String(length=128), nullable=True),
        sa.Column("courier_id", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=200), nullable=True),
        sa.Column(
            "cancelled_by",
            sa.Enum("owner", "customer", "courier", "system", name="orderactor", native_enum=False),
            nullable=True,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cancelled_by IN ('owner', 'customer', 'courier', 'system')",
            name=op.f("ck_orders_cancelled_by"),
        ),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'pix', 'card', 'online')",
            name=op.f("ck_orders_payment_method"),
        ),
        sa.CheckConstraint(
            "payment_status IN ('not_required', 'pending', 'paid', 'refunded')",
            name=op.f("ck_orders_payment_status"),
        ),
        sa.CheckConstraint(
            "status IN ('placed', 'accepted', 'delivered', 'cancelled')",
            name=op.f("ck_orders_status"),
        ),
        sa.CheckConstraint("total >= 0", name=op.f("ck_orders_total")),
        sa.ForeignKeyConstraint(
            ["courier_id"], ["couriers.id"], name=op.f("fk_orders_courier_id_couriers")
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id"],
            ["establishments.id"],
            name=op.f("fk_orders_establishment_id_establishments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint(
            "establishment_id", "number", name=op.f("uq_orders_establishment_id_number")
        ),
    )
    op.create_index(op.f("ix_orders_courier_id"), "orders", ["courier_id"], unique=False)
    op.create_index(
        op.f("ix_orders_customer_token_hash"), "orders", ["customer_token_hash"], unique=False
    )
    op.create_index(op.f("ix_orders_customer_uid"), "orders", ["customer_uid"], unique=False)
    op.create_index(
        "ix_orders_establishment_id_created_at",
        "orders",
        ["establishment_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_payment_reference"), "orders", ["payment_reference"], unique=False
    )
    op.create_table(
        "order_items",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("half_product_id", sa.Uuid(), nullable=True),
        sa.Column("product_name", sa.String(length=100), nullable=False),
        sa.Column("half_product_name", sa.String(length=100), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantity", sa.SmallInteger(), nullable=False),
        sa.Column(
            "doneness",
            sa.Enum(
                "rare",
                "medium_rare",
                "medium",
                "medium_well",
                "well_done",
                name="doneness",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("notes", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "doneness IN ('rare', 'medium_rare', 'medium', 'medium_well', 'well_done')",
            name=op.f("ck_order_items_doneness"),
        ),
        sa.CheckConstraint("quantity BETWEEN 1 AND 99", name=op.f("ck_order_items_quantity")),
        sa.CheckConstraint("unit_price >= 0", name=op.f("ck_order_items_unit_price")),
        sa.ForeignKeyConstraint(
            ["half_product_id"],
            ["products.id"],
            name=op.f("fk_order_items_half_product_id_products"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_order_items_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(
        op.f("ix_order_items_half_product_id"), "order_items", ["half_product_id"], unique=False
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_half_product_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_payment_reference"), table_name="orders")
    op.drop_index("ix_orders_establishment_id_created_at", table_name="orders")
    op.drop_index(op.f("ix_orders_customer_uid"), table_name="orders")
    op.drop_index(op.f("ix_orders_customer_token_hash"), table_name="orders")
    op.drop_index(op.f("ix_orders_courier_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_courier_invites_establishment_id"), table_name="courier_invites")
    op.drop_table("courier_invites")
    op.drop_index(op.f("ix_push_devices_firebase_uid"), table_name="push_devices")
    op.drop_index(op.f("ix_push_devices_establishment_id"), table_name="push_devices")
    op.drop_index(op.f("ix_push_devices_customer_token_hash"), table_name="push_devices")
    op.drop_table("push_devices")
    op.drop_table("products")
    op.drop_index(op.f("ix_order_events_order_id"), table_name="order_events")
    op.drop_index("ix_order_events_establishment_id_created_at", table_name="order_events")
    op.drop_table("order_events")
    op.drop_table("opening_hours")
    op.drop_index(op.f("ix_couriers_firebase_uid"), table_name="couriers")
    op.drop_table("couriers")
    op.drop_index(op.f("ix_absences_establishment_id"), table_name="absences")
    op.drop_table("absences")
    op.drop_index("ix_push_devices_history_id_valid_from", table_name="push_devices_history")
    op.drop_table("push_devices_history")
    op.drop_index("ix_products_history_id_valid_from", table_name="products_history")
    op.drop_table("products_history")
    op.drop_index("ix_orders_history_id_valid_from", table_name="orders_history")
    op.drop_table("orders_history")
    op.drop_index("ix_order_items_history_id_valid_from", table_name="order_items_history")
    op.drop_table("order_items_history")
    op.drop_index("ix_order_events_history_id_valid_from", table_name="order_events_history")
    op.drop_table("order_events_history")
    op.drop_index("ix_opening_hours_history_id_valid_from", table_name="opening_hours_history")
    op.drop_table("opening_hours_history")
    op.drop_index("ix_establishments_history_id_valid_from", table_name="establishments_history")
    op.drop_table("establishments_history")
    op.drop_index(op.f("ix_establishments_slug"), table_name="establishments")
    op.drop_index(op.f("ix_establishments_firebase_uid"), table_name="establishments")
    op.drop_table("establishments")
    op.drop_index("ix_customers_history_id_valid_from", table_name="customers_history")
    op.drop_table("customers_history")
    op.drop_index(op.f("ix_customers_firebase_uid"), table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_couriers_history_id_valid_from", table_name="couriers_history")
    op.drop_table("couriers_history")
    op.drop_index("ix_courier_invites_history_id_valid_from", table_name="courier_invites_history")
    op.drop_table("courier_invites_history")
    op.drop_index("ix_absences_history_id_valid_from", table_name="absences_history")
    op.drop_table("absences_history")
