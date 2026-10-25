from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7d1e5c2a9b43"
down_revision: str | None = "4c4b7cbb09d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("products", "products_history")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.add_column(
            table,
            sa.Column(
                "image_keys",
                postgresql.ARRAY(sa.String(length=300)),
                server_default=sa.text("'{}'"),
                nullable=False,
            ),
        )
        op.execute(f"UPDATE {table} SET image_keys = ARRAY[image_key] WHERE image_key IS NOT NULL")
        op.drop_column(table, "image_key")
    op.alter_column("products_history", "featured", server_default=None)
    op.alter_column("products_history", "image_keys", server_default=None)


def downgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("image_key", sa.String(length=300), nullable=True))
        op.execute(f"UPDATE {table} SET image_key = image_keys[1]")
        op.drop_column(table, "image_keys")
        op.drop_column(table, "featured")
