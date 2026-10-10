"""skills, sectors and student profile

Adds the preset skills/sectors lists, the link tables, the student profile timestamp and
the recommendation score-breakdown columns. Converts internship_opportunities.sector
(free text) into sector_id (a foreign key to the new sectors table), keeping the data.

Revision ID: a3c9d2f1b7e4
Revises: 8f5aad39e1e3
Create Date: 2026-10-10 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3c9d2f1b7e4'
down_revision = '8f5aad39e1e3'
branch_labels = None
depends_on = None

# The preset sectors (also the career-interest options). Inserted here so every existing
# opportunity can be given a sector_id before the column becomes NOT NULL.
PRESET_SECTORS = [
    "Software Development",
    "Web & Mobile Development",
    "Data Analytics & AI",
    "Networking & Cybersecurity",
    "IT Support & Infrastructure",
    "Business Analysis & IT Consulting",
    "UI/UX & Digital Media",
]

# Free-text sector values written by the earlier demo seed → the new preset names.
LEGACY_SECTOR_MAP = {
    "software engineering": "Software Development",
    "web & mobile": "Web & Mobile Development",
    "data & ai": "Data Analytics & AI",
    "infrastructure": "Networking & Cybersecurity",
    "business it": "Business Analysis & IT Consulting",
}


def upgrade():
    # ---- 1. New preset lists -----------------------------------------------------------
    op.create_table(
        'skills',
        sa.Column('skill_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint('name', name='uq_skills_name'),
    )
    sectors = op.create_table(
        'sectors',
        sa.Column('sector_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint('name', name='uq_sectors_name'),
    )

    # ---- 2. Link tables (composite primary keys) -----------------------------------------
    op.create_table(
        'opportunity_skills',
        sa.Column('opportunity_id', sa.Integer(),
                  sa.ForeignKey('internship_opportunities.opportunity_id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('skill_id', sa.Integer(),
                  sa.ForeignKey('skills.skill_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('importance', sa.Enum('essential', 'desirable', name='skill_importance'),
                  nullable=False, server_default='essential'),
    )
    op.create_index('ix_opportunity_skills_skill_id', 'opportunity_skills', ['skill_id'])

    op.create_table(
        'student_skills',
        sa.Column('student_id', sa.Integer(),
                  sa.ForeignKey('students.student_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('skill_id', sa.Integer(),
                  sa.ForeignKey('skills.skill_id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_index('ix_student_skills_skill_id', 'student_skills', ['skill_id'])

    op.create_table(
        'student_interests',
        sa.Column('student_id', sa.Integer(),
                  sa.ForeignKey('students.student_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('sector_id', sa.Integer(),
                  sa.ForeignKey('sectors.sector_id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_index('ix_student_interests_sector_id', 'student_interests', ['sector_id'])

    op.add_column('students', sa.Column('profile_updated_at', sa.DateTime(), nullable=True))

    # ---- 3. DATA MIGRATION: internship_opportunities.sector (text) → sector_id ----------
    op.bulk_insert(sectors, [{"name": n, "is_active": True} for n in PRESET_SECTORS])
    op.add_column('internship_opportunities', sa.Column('sector_id', sa.Integer(), nullable=True))

    conn = op.get_bind()
    sector_ids = {name: sid for sid, name in
                  conn.execute(sa.text("SELECT sector_id, name FROM sectors"))}
    presets_lower = {n.lower(): n for n in PRESET_SECTORS}

    rows = conn.execute(sa.text(
        "SELECT opportunity_id, sector FROM internship_opportunities")).fetchall()
    for opp_id, text in rows:
        key = (text or "").strip()
        # Rule 1: exact (case-insensitive) preset name. Rule 2: known legacy demo value.
        name = presets_lower.get(key.lower()) or LEGACY_SECTOR_MAP.get(key.lower())
        if name is None:
            # Rule 3: unknown free text a partner typed. Keep it as an INACTIVE sector, so
            # no data is lost and it doesn't appear in the pick-lists.
            name = key or "Unspecified"
            if name not in sector_ids:
                result = conn.execute(
                    sa.text("INSERT INTO sectors (name, is_active) VALUES (:n, 0)"), {"n": name})
                sector_ids[name] = result.lastrowid
        conn.execute(
            sa.text("UPDATE internship_opportunities SET sector_id = :sid WHERE opportunity_id = :oid"),
            {"sid": sector_ids[name], "oid": opp_id})

    # Every row now has a sector_id, so it can be made required.
    op.alter_column('internship_opportunities', 'sector_id',
                    existing_type=sa.Integer(), nullable=False)
    op.create_index('ix_internship_opportunities_sector_id', 'internship_opportunities',
                    ['sector_id'])
    op.create_foreign_key('fk_opportunities_sector', 'internship_opportunities', 'sectors',
                          ['sector_id'], ['sector_id'])
    op.drop_column('internship_opportunities', 'sector')

    # ---- 4. Recommendation score breakdown (snapshot at generation time) -----------------
    op.add_column('recommendations', sa.Column('grade_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('skill_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('interest_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('interest_match', sa.Boolean(), nullable=True))
    op.add_column('recommendations', sa.Column('missing_skills', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('recommendations', 'missing_skills')
    op.drop_column('recommendations', 'interest_match')
    op.drop_column('recommendations', 'interest_score')
    op.drop_column('recommendations', 'skill_score')
    op.drop_column('recommendations', 'grade_score')

    # sector_id → free text again, copying each opportunity's sector name.
    op.add_column('internship_opportunities', sa.Column('sector', sa.String(100), nullable=True))
    op.execute("UPDATE internship_opportunities o JOIN sectors s ON s.sector_id = o.sector_id "
               "SET o.sector = s.name")
    op.drop_constraint('fk_opportunities_sector', 'internship_opportunities', type_='foreignkey')
    op.drop_index('ix_internship_opportunities_sector_id', table_name='internship_opportunities')
    op.drop_column('internship_opportunities', 'sector_id')

    op.drop_column('students', 'profile_updated_at')
    op.drop_table('student_interests')
    op.drop_table('student_skills')
    op.drop_table('opportunity_skills')
    op.drop_table('sectors')
    op.drop_table('skills')
