from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from models import (
    JmdictDialectRecord,
    JmdictFieldRecord,
    JmdictSenseNoteRecord,
    JmdictSenseRecord,
)


@pytest.fixture
def metadata_entry() -> JmdictEntry:
    return JmdictEntry(
        source_id=1000001,
        written_forms=(),
        readings=(JmdictReading(text="てすと"),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("first meaning", "eng"),),
                fields=("computing", "telecommunications"),
                dialects=("Kansai-ben", "Kyoto-ben"),
                notes=("First note.", "Second note."),
            ),
            JmdictSense(
                glosses=(JmdictGloss("second meaning", "eng"),),
                fields=("music",),
                dialects=("Tosa-ben",),
                notes=("Another sense.",),
            ),
        ),
    )


def metadata_snapshot(session: Session, entry_id: int) -> dict:
    result = {}

    for model, value_column in (
        (JmdictFieldRecord, JmdictFieldRecord.label),
        (JmdictDialectRecord, JmdictDialectRecord.label),
        (JmdictSenseNoteRecord, JmdictSenseNoteRecord.text),
    ):
        statement = (
            select(
                JmdictSenseRecord.position,
                model.position,
                value_column,
            )
            .join(
                JmdictSenseRecord,
                model.sense_id == JmdictSenseRecord.id,
            )
            .where(JmdictSenseRecord.entry_id == entry_id)
            .order_by(JmdictSenseRecord.position, model.position)
        )
        result[model.__tablename__] = [tuple(row) for row in session.execute(statement)]

    return result


@pytest.mark.parametrize("repeat", [False, True])
def test_import_preserves_metadata_order_and_sense(
    db_session: Session,
    metadata_entry: JmdictEntry,
    repeat: bool,
):
    entry_id = save_jmdict_entry(db_session, metadata_entry)

    if repeat:
        assert save_jmdict_entry(db_session, metadata_entry) == entry_id

    assert metadata_snapshot(db_session, entry_id) == {
        "jmdict_fields": [
            (1, 1, "computing"),
            (1, 2, "telecommunications"),
            (2, 1, "music"),
        ],
        "jmdict_dialects": [
            (1, 1, "Kansai-ben"),
            (1, 2, "Kyoto-ben"),
            (2, 1, "Tosa-ben"),
        ],
        "jmdict_sense_notes": [
            (1, 1, "First note."),
            (1, 2, "Second note."),
            (2, 1, "Another sense."),
        ],
    }


def test_reimport_replaces_metadata_and_removes_old_rows(
    db_session: Session,
    metadata_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, metadata_entry)

    old_sense_ids = tuple(
        db_session.scalars(
            select(JmdictSenseRecord.id).where(
                JmdictSenseRecord.entry_id == entry_id,
            )
        )
    )

    replacement = replace(
        metadata_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
                fields=("medicine",),
            ),
        ),
    )

    assert save_jmdict_entry(db_session, replacement) == entry_id

    assert metadata_snapshot(db_session, entry_id) == {
        "jmdict_fields": [(1, 1, "medicine")],
        "jmdict_dialects": [],
        "jmdict_sense_notes": [],
    }

    for model in (
        JmdictFieldRecord,
        JmdictDialectRecord,
        JmdictSenseNoteRecord,
    ):
        assert (
            db_session.scalars(
                select(model.id).where(model.sense_id.in_(old_sense_ids))
            ).all()
            == []
        )


def test_metadata_replacement_can_be_rolled_back(
    db_session: Session,
    metadata_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, metadata_entry)
    before = metadata_snapshot(db_session, entry_id)

    replacement = replace(
        metadata_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
                notes=("Temporary replacement.",),
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
