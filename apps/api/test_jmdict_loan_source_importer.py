from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jmdict import (
    JmdictEntry,
    JmdictGloss,
    JmdictLoanSource,
    JmdictReading,
    JmdictSense,
)
from jmdict_importer import save_jmdict_entry
from models import (
    JmdictGlossRecord,
    JmdictLoanSourceRecord,
    JmdictSenseRecord,
)


@pytest.fixture
def loan_entry() -> JmdictEntry:
    return JmdictEntry(
        source_id=1000001,
        written_forms=(),
        readings=(JmdictReading(text="てすと"),),
        senses=(
            JmdictSense(
                glosses=(
                    JmdictGloss("literal meaning", "eng", gloss_type="lit"),
                    JmdictGloss("école", "fre", gender="f"),
                ),
                loan_sources=(
                    JmdictLoanSource(text="Arbeit", language="ger"),
                    JmdictLoanSource(
                        text="travail",
                        language="fre",
                        source_type="part",
                    ),
                    JmdictLoanSource(wasei=True),
                ),
            ),
            JmdictSense(
                glosses=(JmdictGloss("ordinary meaning", "eng"),),
            ),
        ),
    )


def metadata_snapshot(session: Session, entry_id: int) -> dict:
    sources = session.execute(
        select(
            JmdictSenseRecord.position,
            JmdictLoanSourceRecord.position,
            JmdictLoanSourceRecord.text,
            JmdictLoanSourceRecord.language,
            JmdictLoanSourceRecord.source_type,
            JmdictLoanSourceRecord.wasei,
        )
        .select_from(JmdictLoanSourceRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictLoanSourceRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictLoanSourceRecord.position,
        )
    ).all()

    glosses = session.execute(
        select(
            JmdictSenseRecord.position,
            JmdictGlossRecord.position,
            JmdictGlossRecord.text,
            JmdictGlossRecord.language,
            JmdictGlossRecord.gloss_type,
            JmdictGlossRecord.gender,
        )
        .select_from(JmdictGlossRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictGlossRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictGlossRecord.position,
        )
    ).all()

    return {
        "sources": [tuple(row) for row in sources],
        "glosses": [tuple(row) for row in glosses],
    }


@pytest.mark.parametrize("repeat", [False, True])
def test_preserves_loan_sources_and_gloss_qualifiers(
    db_session: Session,
    loan_entry: JmdictEntry,
    repeat: bool,
):
    entry_id = save_jmdict_entry(db_session, loan_entry)

    if repeat:
        assert save_jmdict_entry(db_session, loan_entry) == entry_id

    assert metadata_snapshot(db_session, entry_id) == {
        "sources": [
            (1, 1, "Arbeit", "ger", "full", False),
            (1, 2, "travail", "fre", "part", False),
            (1, 3, None, "eng", "full", True),
        ],
        "glosses": [
            (1, 1, "literal meaning", "eng", "lit", None),
            (1, 2, "école", "fre", None, "f"),
            (2, 1, "ordinary meaning", "eng", None, None),
        ],
    }


def test_reimport_removes_obsolete_sources_and_qualifiers(
    db_session: Session,
    loan_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, loan_entry)
    old_sense_ids = tuple(
        db_session.scalars(
            select(JmdictSenseRecord.id).where(
                JmdictSenseRecord.entry_id == entry_id,
            )
        )
    )

    replacement = replace(
        loan_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
            ),
        ),
    )

    assert save_jmdict_entry(db_session, replacement) == entry_id

    assert metadata_snapshot(db_session, entry_id) == {
        "sources": [],
        "glosses": [
            (1, 1, "replacement", "eng", None, None),
        ],
    }

    assert (
        db_session.scalars(
            select(JmdictLoanSourceRecord.id).where(
                JmdictLoanSourceRecord.sense_id.in_(old_sense_ids),
            )
        ).all()
        == []
    )


def test_loan_metadata_replacement_can_be_rolled_back(
    db_session: Session,
    loan_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, loan_entry)
    before = metadata_snapshot(db_session, entry_id)

    replacement = replace(
        loan_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
            ),
        ),
    )

    with (
        pytest.raises(RuntimeError, match="Cancel replacement"),
        db_session.begin_nested(),
    ):
        save_jmdict_entry(db_session, replacement)
        raise RuntimeError("Cancel replacement")

    assert metadata_snapshot(db_session, entry_id) == before
