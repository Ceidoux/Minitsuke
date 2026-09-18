import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_entry_repository import (
    EntryBasics,
    EntryRestrictions,
    SenseDetails,
    load_entry_basics,
    load_entry_restrictions,
    load_sense_details,
)
from jmdict_importer import save_jmdict_entry


def add_entry(
    session: Session,
    source_id: int,
    *,
    forms: tuple[str, ...] = ("学校", "學校"),
    readings: tuple[str, ...] = ("がっこう", "ガッコウ"),
    no_kanji: bool = False,
) -> int:
    return save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=forms,
            readings=tuple(
                JmdictReading(text=text, no_kanji=no_kanji) for text in readings
            ),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="test", language="eng"),),
                ),
            ),
            is_common=True,
        ),
    )


def test_loads_only_requested_entry_with_original_text(db_session: Session):
    wanted = add_entry(db_session, 100)
    add_entry(db_session, 200)

    data = load_entry_basics(db_session, (wanted,))

    assert [entry.source_id for entry in data.entries] == [100]
    assert data.entries[0].is_common is True

    assert [
        (form.entry_id, form.text, form.position) for form in data.written_forms
    ] == [
        (wanted, "学校", 1),
        (wanted, "學校", 2),
    ]

    assert [
        (reading.entry_id, reading.text, reading.position, reading.no_kanji)
        for reading in data.readings
    ] == [
        (wanted, "がっこう", 1, False),
        (wanted, "ガッコウ", 2, False),
    ]


def test_preserves_requested_order_and_removes_duplicate_ids(db_session: Session):
    first = add_entry(db_session, 100)
    second = add_entry(db_session, 200)

    data = load_entry_basics(db_session, (second, first, second, -1))

    assert [entry.source_id for entry in data.entries] == [200, 100]
    assert len(data.written_forms) == 4
    assert len(data.readings) == 4


def test_loads_kana_only_entry(db_session: Session):
    entry_id = add_entry(
        db_session,
        100,
        forms=(),
        readings=("ありがとう",),
        no_kanji=True,
    )

    data = load_entry_basics(db_session, (entry_id,))

    assert len(data.entries) == 1
    assert data.written_forms == ()
    assert [reading.text for reading in data.readings] == ["ありがとう"]
    assert data.readings[0].no_kanji is True


def test_query_count_does_not_grow_with_page_size(db_session: Session):
    entry_ids = tuple(add_entry(db_session, source_id) for source_id in range(100, 130))

    connection = db_session.connection()
    statements = []

    def record_statement(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", record_statement)

    try:
        empty = load_entry_basics(db_session, ())
        assert empty == EntryBasics(entries=(), written_forms=(), readings=())
        assert statements == []

        load_entry_basics(db_session, entry_ids[:1])
        single_count = len(statements)

        statements.clear()

        data = load_entry_basics(db_session, entry_ids)
        page_count = len(statements)
    finally:
        event.remove(connection, "before_cursor_execute", record_statement)

    assert len(data.entries) == 30
    assert single_count == page_count == 3


def test_loads_sense_children_with_grouping_and_order(db_session: Session):
    entry_id = save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=100,
            written_forms=("学校",),
            readings=(JmdictReading(text="がっこう"),),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss(text="school", language="eng"),
                        JmdictGloss(text="école", language="fre"),
                        JmdictGloss(text="school", language="eng"),
                    ),
                    parts_of_speech=("noun", "expression"),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="academy", language="eng"),),
                    parts_of_speech=("noun",),
                ),
            ),
        ),
    )
    add_entry(db_session, 200)

    data = load_sense_details(db_session, (entry_id,))

    assert [(sense.entry_id, sense.position) for sense in data.senses] == [
        (entry_id, 1),
        (entry_id, 2),
    ]

    first_sense, second_sense = data.senses

    assert [
        (gloss.sense_id, gloss.text, gloss.language, gloss.position)
        for gloss in data.glosses
    ] == [
        (first_sense.id, "school", "eng", 1),
        (first_sense.id, "école", "fre", 2),
        (first_sense.id, "school", "eng", 3),
        (second_sense.id, "academy", "eng", 1),
    ]

    assert [
        (part.sense_id, part.label, part.position) for part in data.parts_of_speech
    ] == [
        (first_sense.id, "noun", 1),
        (first_sense.id, "expression", 2),
        (second_sense.id, "noun", 1),
    ]


def test_missing_entry_has_no_sense_details(db_session: Session):
    add_entry(db_session, 100)

    data = load_sense_details(db_session, (-1,))

    assert data == SenseDetails(
        senses=(),
        glosses=(),
        parts_of_speech=(),
    )


@pytest.mark.parametrize("entry_count", [1, 30])
def test_sense_query_count_is_constant(
    db_session: Session,
    entry_count: int,
):
    entry_ids = tuple(
        add_entry(db_session, source_id) for source_id in range(100, 100 + entry_count)
    )

    connection = db_session.connection()
    statements = []

    def record_statement(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", record_statement)

    try:
        empty = load_sense_details(db_session, ())
        assert empty == SenseDetails(
            senses=(),
            glosses=(),
            parts_of_speech=(),
        )
        assert statements == []

        data = load_sense_details(db_session, entry_ids)
    finally:
        event.remove(connection, "before_cursor_execute", record_statement)

    assert len(data.senses) == entry_count
    assert len(data.glosses) == entry_count
    assert data.parts_of_speech == ()
    assert len(statements) == 3


def add_restricted_entry(session: Session, source_id: int) -> int:
    return save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=("学校", "學校"),
            readings=(
                JmdictReading(
                    text="がっこう",
                    restricted_to=("学校", "學校"),
                ),
                JmdictReading(text="ガッコウ"),
            ),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="school", language="eng"),),
                    restricted_to_written_forms=("学校", "學校"),
                    restricted_to_readings=("がっこう", "ガッコウ"),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="academy", language="eng"),),
                ),
            ),
        ),
    )


def test_loads_only_requested_restriction_links(db_session: Session):
    entry_id = add_restricted_entry(db_session, 100)
    add_restricted_entry(db_session, 200)

    basics = load_entry_basics(db_session, (entry_id,))
    details = load_sense_details(db_session, (entry_id,))
    links = load_entry_restrictions(db_session, (entry_id,))

    first_reading, second_reading = basics.readings
    first_sense, _ = details.senses
    first_form, second_form = basics.written_forms

    assert {
        (link.entry_id, link.reading_id, link.written_form_id)
        for link in links.reading_restrictions
    } == {
        (entry_id, first_reading.id, first_form.id),
        (entry_id, first_reading.id, second_form.id),
    }

    assert {
        (link.entry_id, link.sense_id, link.written_form_id)
        for link in links.sense_written_restrictions
    } == {
        (entry_id, first_sense.id, first_form.id),
        (entry_id, first_sense.id, second_form.id),
    }

    assert {
        (link.entry_id, link.sense_id, link.reading_id)
        for link in links.sense_reading_restrictions
    } == {
        (entry_id, first_sense.id, first_reading.id),
        (entry_id, first_sense.id, second_reading.id),
    }


def test_unrestricted_entry_has_no_links(db_session: Session):
    entry_id = add_entry(db_session, 100)
    add_restricted_entry(db_session, 200)

    links = load_entry_restrictions(db_session, (entry_id,))

    assert links == EntryRestrictions(
        reading_restrictions=(),
        sense_written_restrictions=(),
        sense_reading_restrictions=(),
    )


@pytest.mark.parametrize("entry_count", [1, 30])
def test_restriction_query_count_is_constant(
    db_session: Session,
    entry_count: int,
):
    entry_ids = tuple(
        add_restricted_entry(db_session, source_id)
        for source_id in range(100, 100 + entry_count)
    )

    connection = db_session.connection()
    statements = []

    def record_statement(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", record_statement)

    try:
        empty = load_entry_restrictions(db_session, ())
        assert empty == EntryRestrictions(
            reading_restrictions=(),
            sense_written_restrictions=(),
            sense_reading_restrictions=(),
        )
        assert statements == []

        links = load_entry_restrictions(db_session, entry_ids)
    finally:
        event.remove(connection, "before_cursor_execute", record_statement)

    assert len(links.reading_restrictions) == 2 * entry_count
    assert len(links.sense_written_restrictions) == 2 * entry_count
    assert len(links.sense_reading_restrictions) == 2 * entry_count
    assert len(statements) == 3
