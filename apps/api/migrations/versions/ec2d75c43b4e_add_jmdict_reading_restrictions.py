"""add jmdict reading restrictions

Revision ID: ec2d75c43b4e
Revises: 68190d6898f2
Create Date: 2026-09-17 14:06:18.540144

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec2d75c43b4e"
down_revision: str | Sequence[str] | None = "68190d6898f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_jmdict_readings_entry_id",
        "jmdict_readings",
        ["entry_id", "id"],
    )
    op.create_unique_constraint(
        "uq_jmdict_written_forms_entry_id",
        "jmdict_written_forms",
        ["entry_id", "id"],
    )

    op.create_table(
        "jmdict_reading_restrictions",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("written_form_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id", "reading_id"],
            ["jmdict_readings.entry_id", "jmdict_readings.id"],
            name="fk_jmdict_reading_restrictions_reading",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id", "written_form_id"],
            ["jmdict_written_forms.entry_id", "jmdict_written_forms.id"],
            name="fk_jmdict_reading_restrictions_written_form",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("reading_id", "written_form_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("jmdict_reading_restrictions")

    op.drop_constraint(
        "uq_jmdict_written_forms_entry_id",
        "jmdict_written_forms",
        type_="unique",
    )
    op.drop_constraint(
        "uq_jmdict_readings_entry_id",
        "jmdict_readings",
        type_="unique",
    )
