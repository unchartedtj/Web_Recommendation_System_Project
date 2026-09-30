"""units identified by name

Units are now identified by their (unique) name; unit codes become optional.
year_level (added in the previous revision) is removed, since the catalog has no year levels.

Revision ID: 8f5aad39e1e3
Revises: 1c2e064aa78d
Create Date: 2026-09-30 13:33:54.595819

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8f5aad39e1e3'
down_revision = '1c2e064aa78d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('academic_units', 'unit_code',
                    existing_type=mysql.VARCHAR(length=20), nullable=True)
    op.create_unique_constraint('uq_academic_units_unit_name', 'academic_units', ['unit_name'])
    # Drop the CHECK first: MariaDB refuses to drop a column a CHECK constraint uses.
    op.drop_constraint('ck_academic_units_year_level', 'academic_units', type_='check')
    op.drop_column('academic_units', 'year_level')


def downgrade():
    op.add_column('academic_units', sa.Column('year_level', sa.SmallInteger(),
                                              server_default='1', nullable=False))
    op.create_check_constraint('ck_academic_units_year_level', 'academic_units',
                               'year_level BETWEEN 1 AND 4')
    op.drop_constraint('uq_academic_units_unit_name', 'academic_units', type_='unique')
    # Making unit_code NOT NULL again fails if any unit has no code. Assign codes first.
    op.alter_column('academic_units', 'unit_code',
                    existing_type=mysql.VARCHAR(length=20), nullable=False)
