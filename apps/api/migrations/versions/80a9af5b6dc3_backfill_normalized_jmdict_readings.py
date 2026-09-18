"""backfill normalized JMdict readings

Revision ID: 80a9af5b6dc3
Revises: c13c62d24d17
Create Date: 2026-09-18 11:36:21.079466

"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80a9af5b6dc3"
down_revision: str | Sequence[str] | None = "c13c62d24d17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate missing normalized reading text."""
    connection = op.get_bind()

    readings = sa.table(
        "jmdict_readings",
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
        sa.update(readings)
        .where(readings.c.id == sa.bindparam("reading_id"))
        .values(search_text=sa.bindparam("normalized_text"))
    )

    last_id = None

    while True:
        query = (
            sa.select(readings.c.id, readings.c.text)
            .where(readings.c.search_text.is_(None))
            .order_by(readings.c.id)
            .limit(1_000)
        )

        if last_id is not None:
            query = query.where(readings.c.id > last_id)

        rows = connection.execute(query).all()
        if not rows:
            break

        connection.execute(
            statement,
            [
                {
                    "reading_id": row.id,
                    "normalized_text": unicodedata.normalize(
                        "NFKC", row.text
                    ).translate(translation),
                }
                for row in rows
            ],
        )

        last_id = rows[-1].id


def downgrade() -> None:
    """Keep derived values; the preceding migration drops the column."""
