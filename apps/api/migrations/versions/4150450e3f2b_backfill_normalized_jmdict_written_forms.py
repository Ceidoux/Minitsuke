"""backfill normalized JMdict written forms

Revision ID: 4150450e3f2b
Revises: 8c54599bbf70
Create Date: 2026-09-18 13:27:19.082554

"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4150450e3f2b"
down_revision: str | Sequence[str] | None = "8c54599bbf70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate missing normalized written-form text."""
    connection = op.get_bind()

    forms = sa.table(
        "jmdict_written_forms",
        sa.column("id", sa.Integer()),
        sa.column("text", sa.Text()),
        sa.column("search_text", sa.Text()),
    )

    translation = str.maketrans(
        {
            chr(codepoint): chr(codepoint - 0x60)
            for codepoint in range(ord("ァ"), ord("ヶ") + 1)
        }
        | {
            "ヽ": "ゝ",
            "ヾ": "ゞ",
        }
    )

    statement = (
        sa.update(forms)
        .where(forms.c.id == sa.bindparam("form_id"))
        .values(search_text=sa.bindparam("normalized_text"))
    )

    last_id = None

    while True:
        query = (
            sa.select(forms.c.id, forms.c.text)
            .where(forms.c.search_text.is_(None))
            .order_by(forms.c.id)
            .limit(1_000)
        )

        if last_id is not None:
            query = query.where(forms.c.id > last_id)

        rows = connection.execute(query).all()
        if not rows:
            break

        connection.execute(
            statement,
            [
                {
                    "form_id": row.id,
                    "normalized_text": (
                        unicodedata.normalize("NFKC", row.text)
                        .translate(translation)
                        .casefold()
                    ),
                }
                for row in rows
            ],
        )

        last_id = rows[-1].id


def downgrade() -> None:
    """Keep derived values; the preceding migration drops the column."""
