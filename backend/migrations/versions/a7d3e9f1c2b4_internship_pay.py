"""internship pay: unpaid / paid / stipend, with an amount in KSh per month

Revision ID: a7d3e9f1c2b4
Revises: f2c9d4e7a1b3
"""
import sqlalchemy as sa
from alembic import op

revision = "a7d3e9f1c2b4"
down_revision = "f2c9d4e7a1b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("internship_opportunities") as batch_op:
        batch_op.add_column(sa.Column("compensation_type", sa.String(10), nullable=False,
                                      server_default="unpaid"))
        batch_op.add_column(sa.Column("compensation_amount", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_opportunities_compensation_type",
            "compensation_type IN ('unpaid','paid','stipend')")
        batch_op.create_check_constraint(
            "ck_opportunities_compensation_amount",
            "compensation_amount IS NULL OR compensation_amount > 0")


def downgrade():
    with op.batch_alter_table("internship_opportunities") as batch_op:
        batch_op.drop_constraint("ck_opportunities_compensation_amount", type_="check")
        batch_op.drop_constraint("ck_opportunities_compensation_type", type_="check")
        batch_op.drop_column("compensation_amount")
        batch_op.drop_column("compensation_type")
