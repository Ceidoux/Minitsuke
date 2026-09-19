"""add JMdict search indexes

Revision ID: 1d35359fc290
Revises: fb50f8c58ecf
Create Date: 2026-09-19 13:44:12.011574

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1d35359fc290"
down_revision: str | Sequence[str] | None = "fb50f8c58ecf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable trigram support and create search indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_jmdict_glosses_lower_text",
        "jmdict_glosses",
        [sa.text("lower(text)")],
        unique=False,
    )
    op.create_index(
        "ix_jmdict_glosses_text_trgm",
        "jmdict_glosses",
        ["text"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"text": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_jmdict_readings_search_text_trgm",
        "jmdict_readings",
        ["search_text"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_jmdict_written_forms_search_text_trgm",
        "jmdict_written_forms",
        ["search_text"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Remove search indexes while retaining shared trigram support."""
    op.drop_index(
        "ix_jmdict_written_forms_search_text_trgm",
        table_name="jmdict_written_forms",
    )
    op.drop_index(
        "ix_jmdict_readings_search_text_trgm",
        table_name="jmdict_readings",
    )
    op.drop_index(
        "ix_jmdict_glosses_text_trgm",
        table_name="jmdict_glosses",
    )
    op.drop_index(
        "ix_jmdict_glosses_lower_text",
        table_name="jmdict_glosses",
    )

    # pg_trgm may predate this migration or support other database objects.
