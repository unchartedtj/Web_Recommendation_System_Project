"""admin dashboard: account security, placement status reason, activity log, SUS

Adds users.is_active / must_change_password / last_login_at, placement_records
.status_reason / updated_at, and two new tables: activity_logs and sus_responses.

Revision ID: c5e8a1d4f203
Revises: b7d41c2e9a10
Create Date: 2026-10-26 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c5e8a1d4f203'
down_revision = 'b7d41c2e9a10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as t:
        t.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        t.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=False,
                               server_default=sa.false()))
        t.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("placement_records") as t:
        t.add_column(sa.Column("status_reason", sa.String(length=255), nullable=True))
        t.add_column(sa.Column("updated_at", sa.DateTime(), nullable=False,
                               server_default=sa.text("now()")))

    op.create_table(
        "activity_logs",
        sa.Column("log_id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(),
                  sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])

    op.create_table(
        "sus_responses",
        sa.Column("response_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        *[sa.Column(f"q{i}", sa.SmallInteger(), nullable=False) for i in range(1, 11)],
        sa.Column("sus_score", sa.Float(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        *[sa.CheckConstraint(f"q{i} BETWEEN 1 AND 5", name=f"ck_sus_q{i}") for i in range(1, 11)],
    )


def downgrade():
    op.drop_table("sus_responses")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_table("activity_logs")
    with op.batch_alter_table("placement_records") as t:
        t.drop_column("updated_at")
        t.drop_column("status_reason")
    with op.batch_alter_table("users") as t:
        t.drop_column("last_login_at")
        t.drop_column("must_change_password")
        t.drop_column("is_active")
