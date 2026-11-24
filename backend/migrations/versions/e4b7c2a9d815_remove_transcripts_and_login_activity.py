"""remove transcript verification; clear login activity

The transcript upload / marks verification feature was removed, so its table is dropped and
its activity-log entries deleted. Logins are no longer recorded in the activity log, so the
existing login entries are deleted too (users.last_login_at is kept).

Revision ID: e4b7c2a9d815
Revises: d8f2b6a9c1e7
Create Date: 2026-11-08 18:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4b7c2a9d815'
down_revision = 'd8f2b6a9c1e7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM activity_logs WHERE action = 'auth.login' OR action LIKE 'transcript.%'")
    op.drop_table("transcripts")


def downgrade():
    # Recreates the (empty) table; deleted activity entries can't be restored.
    op.create_table(
        "transcripts",
        sa.Column("transcript_id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.Enum("pending", "accepted", "rejected", name="transcript_status"),
                  nullable=False, server_default="pending"),
        sa.Column("review_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.Integer(),
                  sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
