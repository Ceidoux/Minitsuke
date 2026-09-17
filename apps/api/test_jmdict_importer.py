from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry, validate_entry_for_import
from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictPartOfSpeechRecord,
    JmdictReadingRecord,
    JmdictReadingRestrictionRecord,
    JmdictSenseReadingRestrictionRecord,
    JmdictSenseRecord,
    JmdictSenseWrittenFormRestrictionRecord,
    JmdictWrittenFormRecord,
)


@pytest.fixture
def parsed_entry() -> JmdictEntry:
    return JmdictEntry(
        source_id=1000001,
        written_forms=("学校", "學校"),
        readings=(
            JmdictReading(
                text="がっこう",
                restricted_to=("学校", "學校"),
            ),
        ),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss(text="school", language="eng"),),
                restricted_to_written_forms=("学校",),
                restricted_to_readings=("がっこう",),
                parts_of_speech=("noun (common) (futsuumeishi)",),
            ),
        ),
    )


def test_accepts_valid_restrictions(parsed_entry: JmdictEntry):
    validate_entry_for_import(parsed_entry)


def test_accepts_kana_only_entry():
    entry = JmdictEntry(
        source_id=1000002,
        written_forms=(),
        readings=(JmdictReading(text="こんにちは", no_kanji=True),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss(text="hello", language="eng"),),
            ),
        ),
    )

    validate_entry_for_import(entry)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"readings": ()},
            "Entry must contain at least one reading",
        ),
        (
            {"senses": ()},
            "Entry must contain at least one sense",
        ),
        (
            {"written_forms": ("学校", "学校")},
            "Entry contains duplicate written forms",
        ),
        (
            {
                "readings": (
                    JmdictReading(text="がっこう"),
                    JmdictReading(text="がっこう"),
                ),
            },
            "Entry contains duplicate readings",
        ),
        (
            {
                "readings": (
                    JmdictReading(
                        text="がっこう",
                        restricted_to=("存在しない表記",),
                    ),
                ),
            },
            "Reading restriction references an unknown written form",
        ),
        (
            {
                "readings": (
                    JmdictReading(
                        text="がっこう",
                        restricted_to=("学校",),
                        no_kanji=True,
                    ),
                ),
            },
            "A no_kanji reading cannot have written-form restrictions",
        ),
        (
            {
                "senses": (
                    JmdictSense(
                        glosses=(JmdictGloss("school", "eng"),),
                        restricted_to_written_forms=("存在しない表記",),
                    ),
                ),
            },
            "Sense restriction references an unknown written form",
        ),
        (
            {
                "senses": (
                    JmdictSense(
                        glosses=(JmdictGloss("school", "eng"),),
                        restricted_to_readings=("そんざいしないよみ",),
                    ),
                ),
            },
            "Sense restriction references an unknown reading",
        ),
    ],
)
def test_rejects_inconsistent_entry(
    parsed_entry: JmdictEntry,
    changes: dict,
    message: str,
):
    entry = replace(parsed_entry, **changes)

    with pytest.raises(ValueError) as error:
        validate_entry_for_import(entry)

    assert str(error.value) == message


JMDICT_MODELS = (
    JmdictEntryRecord,
    JmdictWrittenFormRecord,
    JmdictReadingRecord,
    JmdictSenseRecord,
    JmdictGlossRecord,
    JmdictPartOfSpeechRecord,
    JmdictReadingRestrictionRecord,
    JmdictSenseWrittenFormRestrictionRecord,
    JmdictSenseReadingRestrictionRecord,
)


def stored_rows(session: Session, *columns) -> set[tuple]:
    return {tuple(row) for row in session.execute(select(*columns)).all()}


def database_snapshot(session: Session) -> dict[str, list[tuple]]:
    snapshot = {}

    for model in JMDICT_MODELS:
        table = model.__table__
        statement = select(table).order_by(*table.primary_key.columns)
        snapshot[table.name] = [tuple(row) for row in session.execute(statement).all()]

    return snapshot


@pytest.mark.parametrize("repeat", [False, True])
def test_saves_complete_entry(
    db_session: Session,
    parsed_entry: JmdictEntry,
    repeat: bool,
):
    first_sense = replace(
        parsed_entry.senses[0],
        glosses=(
            JmdictGloss("school", "eng"),
            JmdictGloss("école", "fre"),
            JmdictGloss("school", "eng"),
        ),
        parts_of_speech=("noun",),
    )
    entry = replace(
        parsed_entry,
        senses=(
            first_sense,
            JmdictSense(
                glosses=(JmdictGloss("academy", "eng"),),
                parts_of_speech=("noun",),
            ),
        ),
    )

    entry_id = save_jmdict_entry(db_session, entry)

    if repeat:
        assert save_jmdict_entry(db_session, entry) == entry_id

    forms = {
        form.text: form.id
        for form in db_session.scalars(select(JmdictWrittenFormRecord))
    }
    reading_id = db_session.scalars(select(JmdictReadingRecord.id)).one()
    sense_ids = db_session.scalars(
        select(JmdictSenseRecord.id).order_by(JmdictSenseRecord.position)
    ).all()

    assert len(sense_ids) == 2
    first_id, second_id = sense_ids

    assert stored_rows(
        db_session,
        JmdictEntryRecord.id,
        JmdictEntryRecord.source_id,
    ) == {(entry_id, 1000001)}

    assert stored_rows(
        db_session,
        JmdictWrittenFormRecord.entry_id,
        JmdictWrittenFormRecord.text,
        JmdictWrittenFormRecord.position,
    ) == {
        (entry_id, "学校", 1),
        (entry_id, "學校", 2),
    }

    assert stored_rows(
        db_session,
        JmdictReadingRecord.entry_id,
        JmdictReadingRecord.text,
        JmdictReadingRecord.position,
        JmdictReadingRecord.no_kanji,
    ) == {(entry_id, "がっこう", 1, False)}

    assert stored_rows(
        db_session,
        JmdictSenseRecord.entry_id,
        JmdictSenseRecord.position,
    ) == {(entry_id, 1), (entry_id, 2)}

    assert stored_rows(
        db_session,
        JmdictGlossRecord.sense_id,
        JmdictGlossRecord.position,
        JmdictGlossRecord.text,
        JmdictGlossRecord.language,
    ) == {
        (first_id, 1, "school", "eng"),
        (first_id, 2, "école", "fre"),
        (first_id, 3, "school", "eng"),
        (second_id, 1, "academy", "eng"),
    }

    assert stored_rows(
        db_session,
        JmdictPartOfSpeechRecord.sense_id,
        JmdictPartOfSpeechRecord.position,
        JmdictPartOfSpeechRecord.label,
    ) == {
        (first_id, 1, "noun"),
        (second_id, 1, "noun"),
    }

    assert stored_rows(
        db_session,
        JmdictReadingRestrictionRecord.entry_id,
        JmdictReadingRestrictionRecord.reading_id,
        JmdictReadingRestrictionRecord.written_form_id,
    ) == {
        (entry_id, reading_id, forms["学校"]),
        (entry_id, reading_id, forms["學校"]),
    }

    assert stored_rows(
        db_session,
        JmdictSenseWrittenFormRestrictionRecord.entry_id,
        JmdictSenseWrittenFormRestrictionRecord.sense_id,
        JmdictSenseWrittenFormRestrictionRecord.written_form_id,
    ) == {(entry_id, first_id, forms["学校"])}

    assert stored_rows(
        db_session,
        JmdictSenseReadingRestrictionRecord.entry_id,
        JmdictSenseReadingRestrictionRecord.sense_id,
        JmdictSenseReadingRestrictionRecord.reading_id,
    ) == {(entry_id, first_id, reading_id)}


def test_update_replaces_old_contents(
    db_session: Session,
    parsed_entry: JmdictEntry,
):
    entry_id = save_jmdict_entry(db_session, parsed_entry)

    replacement = JmdictEntry(
        source_id=parsed_entry.source_id,
        written_forms=(),
        readings=(JmdictReading("こんにちは", no_kanji=True),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("hello", "eng"),),
            ),
        ),
    )

    assert save_jmdict_entry(db_session, replacement) == entry_id

    assert stored_rows(
        db_session,
        JmdictEntryRecord.id,
        JmdictEntryRecord.source_id,
    ) == {(entry_id, 1000001)}

    assert stored_rows(db_session, JmdictWrittenFormRecord.id) == set()
    assert stored_rows(
        db_session,
        JmdictReadingRecord.text,
        JmdictReadingRecord.no_kanji,
    ) == {("こんにちは", True)}
    assert stored_rows(
        db_session,
        JmdictSenseRecord.entry_id,
        JmdictSenseRecord.position,
    ) == {(entry_id, 1)}
    assert stored_rows(
        db_session,
        JmdictGlossRecord.text,
        JmdictGlossRecord.language,
    ) == {("hello", "eng")}

    for model in (
        JmdictPartOfSpeechRecord,
        JmdictReadingRestrictionRecord,
        JmdictSenseWrittenFormRestrictionRecord,
        JmdictSenseReadingRestrictionRecord,
    ):
        assert db_session.execute(select(model)).all() == []


def test_caller_can_roll_back_replacement(
    db_session: Session,
    parsed_entry: JmdictEntry,
):
    save_jmdict_entry(db_session, parsed_entry)
    before = database_snapshot(db_session)

    replacement = replace(
        parsed_entry,
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("replacement", "eng"),),
            ),
        ),
    )

    with (
        pytest.raises(RuntimeError, match="Cancel transaction"),
        db_session.begin_nested(),
    ):
        save_jmdict_entry(db_session, replacement)
        raise RuntimeError("Cancel transaction")

    assert database_snapshot(db_session) == before


def test_invalid_update_leaves_existing_entry_untouched(
    db_session: Session,
    parsed_entry: JmdictEntry,
):
    save_jmdict_entry(db_session, parsed_entry)
    before = database_snapshot(db_session)

    invalid = replace(
        parsed_entry,
        readings=(
            JmdictReading(
                text="がっこう",
                restricted_to=("存在しない表記",),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Reading restriction references an unknown written form",
    ):
        save_jmdict_entry(db_session, invalid)

    assert database_snapshot(db_session) == before
