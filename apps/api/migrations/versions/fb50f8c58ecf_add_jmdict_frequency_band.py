"""add JMdict frequency band

Revision ID: fb50f8c58ecf
Revises: 21bf67a5759e
Create Date: 2026-09-18 19:26:07.708052

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb50f8c58ecf"
down_revision: str | Sequence[str] | None = "21bf67a5759e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an optional, positive frequency band."""
    op.add_column(
        "jmdict_entries",
        sa.Column("frequency_band", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_jmdict_entries_positive_frequency_band",
        "jmdict_entries",
        "frequency_band > 0",
    )


def downgrade() -> None:
    """Remove the frequency band and its constraint."""
    op.drop_constraint(
        "ck_jmdict_entries_positive_frequency_band",
        "jmdict_entries",
        type_="check",
    )
    op.drop_column("jmdict_entries", "frequency_band")
