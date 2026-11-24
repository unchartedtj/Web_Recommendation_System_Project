"""remove the SUS questionnaire and last-login tracking

Revision ID: f2c9d4e7a1b3
Revises: e4b7c2a9d815
"""
import sqlalchemy as sa
from alembic import op

revision = "f2c9d4e7a1b3"
down_revision = "e4b7c2a9d815"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM activity_logs WHERE action LIKE 'sus.%'")
    op.drop_table("sus_responses")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_login_at")


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.create_table(
        "sus_responses",
        sa.Column("response_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False),
        *[sa.Column(f"q{i}", sa.SmallInteger(), nullable=False) for i in range(1, 11)],
        sa.Column("sus_score", sa.Float(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
