from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from models import JmdictReferenceRecord, JmdictSenseRecord


@pytest.fixture
def reference_entry() -> JmdictEntry:
    return JmdictEntry(
        source_id=1000001,
        written_forms=(),
        readings=(JmdictReading(text="てすと"),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("first meaning", "eng"),),
                cross_references=("同上", "丸・まる・1"),
                antonyms=("インナー・1",),
            ),
            JmdictSense(
                glosses=(JmdictGloss("second meaning", "eng"),),
                cross_references=("リズム・アンド・ブルース",),
                antonyms=("ルーラル",),
            ),
        ),
    )


def reference_snapshot(session: Session, entry_id: int) -> list[tuple]:
    statement = (
        select(
            JmdictSenseRecord.position,
            JmdictReferenceRecord.kind,
            JmdictReferenceRecord.position,
            JmdictReferenceRecord.text,
        )
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictReferenceRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictReferenceRecord.kind,
            JmdictReferenceRecord.position,
        )
    )

    return [tuple(row) for row in session.execute(statement)]


@pytest.mark.parametrize("repeat", [False, True])
def test_preserves_reference_kinds_order_and_source_senses(
    db_session: Session,
    reference_entry: JmdictEntry,
    repeat: bool,
):
    entry_id = save_jmdict_entry(db_session, reference_entry)

    if repeat:
        assert save_jmdict_entry(db_session, reference_entry) == entry_id

    assert reference_snapshot(db_session, entry_id) == [
        (1, "ant", 1, "インナー・1"),
        (1, "xref", 1, "同上"),
        (1, "xref", 2, "丸・まる・1"),
        (2, "ant", 1, "ルーラル"),
        (2, "xref", 1, "リズム・アンド・ブルース"),
    ]


def test_reimport_replaces_references_and_removes_old_rows(
    db_session: Session,
    reference_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, reference_entry)

    old_sense_ids = tuple(
        db_session.scalars(
            select(JmdictSenseRecord.id).where(
                JmdictSenseRecord.entry_id == entry_id,
            )
        )
    )

    replacement = replace(
        reference_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
                cross_references=("二重丸",),
            ),
        ),
    )

    assert save_jmdict_entry(db_session, replacement) == entry_id
    assert reference_snapshot(db_session, entry_id) == [
        (1, "xref", 1, "二重丸"),
    ]

    assert (
        db_session.scalars(
            select(JmdictReferenceRecord.id).where(
                JmdictReferenceRecord.sense_id.in_(old_sense_ids),
            )
        ).all()
        == []
    )


def test_reference_replacement_can_be_rolled_back(
    db_session: Session,
    reference_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, reference_entry)
    before = reference_snapshot(db_session, entry_id)

    replacement = replace(
        reference_entry,
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

    assert reference_snapshot(db_session, entry_id) == before
