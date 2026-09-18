import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from japanese_text import normalize_reading
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictWrittenFormRecord,
)


def test_entry_stores_multiple_written_forms(db_session: Session):
    entry = JmdictEntryRecord(source_id=1206730)
    db_session.add(entry)
    db_session.flush()

    db_session.add_all(
        [
            JmdictWrittenFormRecord(
                entry_id=entry.id,
                text="學校",
                position=2,
            ),
            JmdictWrittenFormRecord(
                entry_id=entry.id,
                text="学校",
                position=1,
            ),
        ]
    )
    db_session.flush()

    statement = (
        select(
            JmdictWrittenFormRecord.text,
            JmdictWrittenFormRecord.position,
        )
        .where(JmdictWrittenFormRecord.entry_id == entry.id)
        .order_by(JmdictWrittenFormRecord.position)
    )

    rows = db_session.execute(statement).all()

    assert [tuple(row) for row in rows] == [
        ("学校", 1),
        ("學校", 2),
    ]


def test_duplicate_source_id_is_rejected(db_session: Session):
    db_session.add(JmdictEntryRecord(source_id=1206730))
    db_session.flush()

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(JmdictEntryRecord(source_id=1206730))
        db_session.flush()

    assert error.value.orig.diag.constraint_name == "uq_jmdict_entries_source_id"


@pytest.mark.parametrize(
    ("text", "position", "constraint_name"),
    [
        ("学校", 2, "uq_jmdict_written_forms_entry_text"),
        ("學校", 1, "uq_jmdict_written_forms_entry_position"),
        ("學校", 0, "ck_jmdict_written_forms_positive_position"),
    ],
)
def test_invalid_written_form_is_rejected(
    db_session: Session,
    text: str,
    position: int,
    constraint_name: str,
):
    entry = JmdictEntryRecord(source_id=1206730)
    db_session.add(entry)
    db_session.flush()

    db_session.add(
        JmdictWrittenFormRecord(
            entry_id=entry.id,
            text="学校",
            position=1,
        )
    )
    db_session.flush()

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            JmdictWrittenFormRecord(
                entry_id=entry.id,
                text=text,
                position=position,
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == constraint_name


def test_deleting_entry_removes_only_its_forms(db_session: Session):
    first = JmdictEntryRecord(source_id=1206730)
    second = JmdictEntryRecord(source_id=1358280)
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add_all(
        [
            JmdictWrittenFormRecord(
                entry_id=first.id,
                text="学校",
                position=1,
            ),
            JmdictWrittenFormRecord(
                entry_id=second.id,
                text="食べる",
                position=1,
            ),
        ]
    )
    db_session.flush()

    db_session.execute(
        delete(JmdictEntryRecord).where(
            JmdictEntryRecord.id == first.id,
        )
    )

    remaining = db_session.scalars(select(JmdictWrittenFormRecord.text)).all()

    assert remaining == ["食べる"]


def test_entry_stores_multiple_readings(db_session: Session):
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    db_session.add_all(
        [
            JmdictReadingRecord(
                entry_id=entry.id,
                text="なまもの",
                search_text="なまもの",
                position=2,
                no_kanji=False,
            ),
            JmdictReadingRecord(
                entry_id=entry.id,
                text="せいぶつ",
                search_text="せいぶつ",
                position=1,
                no_kanji=False,
            ),
        ]
    )
    db_session.flush()

    statement = (
        select(
            JmdictReadingRecord.text,
            JmdictReadingRecord.position,
            JmdictReadingRecord.no_kanji,
        )
        .where(JmdictReadingRecord.entry_id == entry.id)
        .order_by(JmdictReadingRecord.position)
    )

    rows = db_session.execute(statement).all()

    assert [tuple(row) for row in rows] == [
        ("せいぶつ", 1, False),
        ("なまもの", 2, False),
    ]


@pytest.mark.parametrize("no_kanji", [False, True])
def test_reading_without_written_forms_preserves_flag(
    db_session: Session,
    no_kanji: bool,
):
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    db_session.add(
        JmdictReadingRecord(
            entry_id=entry.id,
            text="こんにちは",
            search_text="こんにちは",
            position=1,
            no_kanji=no_kanji,
        )
    )
    db_session.flush()

    stored_flag = db_session.scalar(
        select(JmdictReadingRecord.no_kanji).where(
            JmdictReadingRecord.entry_id == entry.id,
        )
    )

    assert stored_flag is no_kanji


@pytest.mark.parametrize(
    ("text", "position", "constraint_name"),
    [
        ("せいぶつ", 2, "uq_jmdict_readings_entry_text"),
        ("なまもの", 1, "uq_jmdict_readings_entry_position"),
        ("なまもの", 0, "ck_jmdict_readings_positive_position"),
    ],
)
def test_invalid_reading_is_rejected(
    db_session: Session,
    text: str,
    position: int,
    constraint_name: str,
):
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    db_session.add(
        JmdictReadingRecord(
            entry_id=entry.id,
            text="せいぶつ",
            search_text="せいぶつ",
            position=1,
            no_kanji=False,
        )
    )
    db_session.flush()

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            JmdictReadingRecord(
                entry_id=entry.id,
                text=text,
                search_text=normalize_reading(text),
                position=position,
                no_kanji=False,
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == constraint_name


def test_deleting_entry_removes_only_its_readings(db_session: Session):
    first = JmdictEntryRecord(source_id=1000001)
    second = JmdictEntryRecord(source_id=1000002)
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add_all(
        [
            JmdictReadingRecord(
                entry_id=first.id,
                text="がっこう",
                search_text="がっこう",
                position=1,
                no_kanji=False,
            ),
            JmdictReadingRecord(
                entry_id=second.id,
                text="がっこう",
                search_text="がっこう",
                position=1,
                no_kanji=False,
            ),
        ]
    )
    db_session.flush()

    db_session.execute(
        delete(JmdictEntryRecord).where(
            JmdictEntryRecord.id == first.id,
        )
    )

    remaining_entry_ids = db_session.scalars(select(JmdictReadingRecord.entry_id)).all()

    assert remaining_entry_ids == [second.id]


@pytest.mark.parametrize("is_common", [False, True])
def test_entry_preserves_commonness(
    db_session: Session,
    is_common: bool,
):
    entry = JmdictEntryRecord(
        source_id=1000001,
        is_common=is_common,
    )
    db_session.add(entry)
    db_session.flush()

    stored = db_session.scalar(
        select(JmdictEntryRecord.is_common).where(
            JmdictEntryRecord.id == entry.id,
        )
    )

    assert stored is is_common


def test_entry_commonness_defaults_to_false(db_session: Session):
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    stored = db_session.scalar(
        select(JmdictEntryRecord.is_common).where(
            JmdictEntryRecord.id == entry.id,
        )
    )

    assert stored is False
