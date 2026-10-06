from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "processed_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("raw_event_id", sa.BigInteger(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fingerprint", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_processed_events_fingerprint"),
    )

    op.create_table(
        "event_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fingerprint", sa.CHAR(length=64), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_processed_events_client_timestamp",
        "processed_events",
        ["client_id", "event_timestamp"],
    )
    op.create_index(
        "idx_processed_events_processed_at",
        "processed_events",
        ["processed_at"],
    )
    op.create_index(
        "idx_event_attempts_created_at",
        "event_attempts",
        ["created_at"],
    )
    op.create_index(
        "idx_event_attempts_fingerprint",
        "event_attempts",
        ["fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("idx_event_attempts_fingerprint", table_name="event_attempts")
    op.drop_index("idx_event_attempts_created_at", table_name="event_attempts")
    op.drop_index(
        "idx_processed_events_processed_at",
        table_name="processed_events",
    )
    op.drop_index(
        "idx_processed_events_client_timestamp",
        table_name="processed_events",
    )
    op.drop_table("event_attempts")
    op.drop_table("processed_events")
    op.drop_table("raw_events")
