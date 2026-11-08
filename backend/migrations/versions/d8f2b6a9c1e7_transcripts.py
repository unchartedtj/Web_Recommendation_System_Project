"""transcripts: uploaded PDF + marks verification status

One row per student: the stored PDF's name, when it was uploaded, and whether the WBL office
accepted or rejected the typed marks against it.

Revision ID: d8f2b6a9c1e7
Revises: c5e8a1d4f203
Create Date: 2026-11-02 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8f2b6a9c1e7'
down_revision = 'c5e8a1d4f203'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transcripts",
        sa.Column("transcript_id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"),
                  nullable=False, unique=True),
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


def downgrade():
    op.drop_table("transcripts")
