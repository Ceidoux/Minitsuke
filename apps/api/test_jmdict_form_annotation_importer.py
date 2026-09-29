from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry, validate_entry_for_import
from models import (
    JmdictReadingInfoRecord,
    JmdictReadingRecord,
    JmdictWrittenFormInfoRecord,
    JmdictWrittenFormRecord,
)


@pytest.fixture
def annotated_entry() -> JmdictEntry:
    return JmdictEntry(
        source_id=1000001,
        written_forms=("学校", "學校"),
        written_form_info={
            "學校": (
                "out-dated kanji or kanji usage",
                "rarely used kanji form",
            ),
        },
        readings=(
            JmdictReading(text="がっこう"),
            JmdictReading(
                text="ガッコウ",
                restricted_to=("學校",),
                info=("rarely used kana form",),
            ),
        ),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("school", "eng"),),
            ),
        ),
    )


def annotation_snapshot(session: Session) -> dict:
    written = session.execute(
        select(
            JmdictWrittenFormRecord.text,
            JmdictWrittenFormInfoRecord.position,
            JmdictWrittenFormInfoRecord.label,
        )
        .join(
            JmdictWrittenFormInfoRecord,
            JmdictWrittenFormInfoRecord.written_form_id == JmdictWrittenFormRecord.id,
        )
        .order_by(
            JmdictWrittenFormRecord.position,
            JmdictWrittenFormInfoRecord.position,
        )
    ).all()

    readings = session.execute(
        select(
            JmdictReadingRecord.text,
            JmdictReadingInfoRecord.position,
            JmdictReadingInfoRecord.label,
        )
        .join(
            JmdictReadingInfoRecord,
            JmdictReadingInfoRecord.reading_id == JmdictReadingRecord.id,
        )
        .order_by(
            JmdictReadingRecord.position,
            JmdictReadingInfoRecord.position,
        )
    ).all()

    return {
        "written": [tuple(row) for row in written],
        "readings": [tuple(row) for row in readings],
    }


@pytest.mark.parametrize("repeat", [False, True])
def test_import_preserves_annotation_targets_and_order(
    db_session: Session,
    annotated_entry: JmdictEntry,
    repeat: bool,
):
    entry_id = save_jmdict_entry(db_session, annotated_entry)

    if repeat:
        assert save_jmdict_entry(db_session, annotated_entry) == entry_id

    assert annotation_snapshot(db_session) == {
        "written": [
            ("學校", 1, "out-dated kanji or kanji usage"),
            ("學校", 2, "rarely used kanji form"),
        ],
        "readings": [
            ("ガッコウ", 1, "rarely used kana form"),
        ],
    }


def test_reimport_removes_obsolete_form_annotations(
    db_session: Session,
    annotated_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, annotated_entry)

    replacement = replace(
        annotated_entry,
        written_form_info={},
        readings=tuple(
            replace(reading, info=()) for reading in annotated_entry.readings
        ),
    )

    assert save_jmdict_entry(db_session, replacement) == entry_id
    assert annotation_snapshot(db_session) == {
        "written": [],
        "readings": [],
    }


def test_form_annotation_replacement_can_be_rolled_back(
    db_session: Session,
    annotated_entry: JmdictEntry,
):
    save_jmdict_entry(db_session, annotated_entry)
    before = annotation_snapshot(db_session)

    replacement = replace(
        annotated_entry,
        written_form_info={},
        readings=(JmdictReading(text="がっこう"),),
    )

    with (
        pytest.raises(RuntimeError, match="Cancel replacement"),
        db_session.begin_nested(),
    ):
        save_jmdict_entry(db_session, replacement)
        raise RuntimeError("Cancel replacement")

    assert annotation_snapshot(db_session) == before


def test_rejects_annotations_for_unknown_written_forms(
    annotated_entry: JmdictEntry,
):
    invalid = replace(
        annotated_entry,
        written_form_info={"存在しない表記": ("test annotation",)},
    )

    with pytest.raises(
        ValueError,
        match="Written-form annotation references an unknown written form",
    ):
        validate_entry_for_import(invalid)
