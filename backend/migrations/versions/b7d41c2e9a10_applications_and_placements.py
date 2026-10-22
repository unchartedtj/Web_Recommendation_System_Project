"""applications and placement records

Adds the application snapshot, decision fields and status ENUM, plus created_at and a
status ENUM for placement records. One application per student per opportunity, and
at most one placement per application.

Revision ID: b7d41c2e9a10
Revises: a3c9d2f1b7e4
Create Date: 2026-10-20 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7d41c2e9a10'
down_revision = 'a3c9d2f1b7e4'
branch_labels = None
depends_on = None

APP_STATUSES = ("pending", "shortlisted", "accepted", "rejected", "withdrawn")
PLACEMENT_STATUSES = ("confirmed", "ongoing", "completed", "terminated")


def upgrade():
    # ---- applications ----
    with op.batch_alter_table("applications") as t:
        t.add_column(sa.Column("motivation_note", sa.Text(), nullable=True))
        t.add_column(sa.Column("profile_snapshot", sa.JSON(), nullable=True))
        t.add_column(sa.Column("match_score_at_apply", sa.Float(), nullable=True))
        t.add_column(sa.Column("meets_requirements_at_apply", sa.Boolean(), nullable=True))
        t.add_column(sa.Column("status_reason", sa.String(length=255), nullable=True))
        t.add_column(sa.Column("updated_at", sa.DateTime(), nullable=False,
                               server_default=sa.text("now()")))
        t.add_column(sa.Column("decided_at", sa.DateTime(), nullable=True))
    # Any old free-text status becomes 'pending' before the ENUM is applied.
    op.execute("UPDATE applications SET status='pending' WHERE status NOT IN "
               "('pending','shortlisted','accepted','rejected','withdrawn')")
    with op.batch_alter_table("applications") as t:
        t.alter_column("status", existing_type=sa.String(length=20),
                       type_=sa.Enum(*APP_STATUSES, name="application_status"),
                       existing_nullable=False, server_default="pending")
        t.create_unique_constraint("uq_applications_student_opportunity",
                                   ["student_id", "opportunity_id"])

    # ---- placement_records ----
    with op.batch_alter_table("placement_records") as t:
        t.add_column(sa.Column("created_at", sa.DateTime(), nullable=False,
                               server_default=sa.text("now()")))
    op.execute("UPDATE placement_records SET status='confirmed' WHERE status NOT IN "
               "('confirmed','ongoing','completed','terminated')")
    with op.batch_alter_table("placement_records") as t:
        t.alter_column("status", existing_type=sa.String(length=20),
                       type_=sa.Enum(*PLACEMENT_STATUSES, name="placement_status"),
                       existing_nullable=False, server_default="confirmed")
        t.create_unique_constraint("uq_placement_records_application", ["application_id"])


def downgrade():
    with op.batch_alter_table("placement_records") as t:
        t.drop_constraint("uq_placement_records_application", type_="unique")
        t.alter_column("status", existing_type=sa.Enum(*PLACEMENT_STATUSES, name="placement_status"),
                       type_=sa.String(length=20), existing_nullable=False,
                       server_default="ongoing")
        t.drop_column("created_at")

    with op.batch_alter_table("applications") as t:
        t.drop_constraint("uq_applications_student_opportunity", type_="unique")
        t.alter_column("status", existing_type=sa.Enum(*APP_STATUSES, name="application_status"),
                       type_=sa.String(length=20), existing_nullable=False,
                       server_default="pending")
        for column in ("decided_at", "updated_at", "status_reason", "meets_requirements_at_apply",
                       "match_score_at_apply", "profile_snapshot", "motivation_note"):
            t.drop_column(column)
