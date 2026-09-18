import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictReadingRestrictionRecord,
    JmdictWrittenFormRecord,
)


@pytest.fixture
def restriction_parents(db_session: Session) -> list[tuple[int, int, int]]:
    parents = []

    for source_id in (1000001, 1000002):
        entry = JmdictEntryRecord(source_id=source_id)
        db_session.add(entry)
        db_session.flush()

        reading = JmdictReadingRecord(
            entry_id=entry.id,
            text="がっこう",
            search_text="がっこう",
            position=1,
            no_kanji=False,
        )
        form = JmdictWrittenFormRecord(
            entry_id=entry.id,
            text="学校",
            position=1,
        )
        db_session.add_all([reading, form])
        db_session.flush()

        parents.append((entry.id, reading.id, form.id))

    return parents


def test_reading_can_restrict_to_multiple_forms(
    db_session: Session,
    restriction_parents: list[tuple[int, int, int]],
):
    entry_id, reading_id, form_id = restriction_parents[0]

    second_form = JmdictWrittenFormRecord(
        entry_id=entry_id,
        text="學校",
        position=2,
    )
    db_session.add(second_form)
    db_session.flush()

    db_session.add_all(
        [
            JmdictReadingRestrictionRecord(
                entry_id=entry_id,
                reading_id=reading_id,
                written_form_id=form_id,
            ),
            JmdictReadingRestrictionRecord(
                entry_id=entry_id,
                reading_id=reading_id,
                written_form_id=second_form.id,
            ),
        ]
    )
    db_session.flush()

    statement = (
        select(JmdictWrittenFormRecord.text)
        .join(
            JmdictReadingRestrictionRecord,
            JmdictReadingRestrictionRecord.written_form_id
            == JmdictWrittenFormRecord.id,
        )
        .where(JmdictReadingRestrictionRecord.reading_id == reading_id)
        .order_by(JmdictWrittenFormRecord.position)
    )

    assert db_session.scalars(statement).all() == ["学校", "學校"]


@pytest.mark.parametrize(
    ("side", "constraint_name"),
    [
        ("reading", "fk_jmdict_reading_restrictions_reading"),
        ("written_form", "fk_jmdict_reading_restrictions_written_form"),
    ],
)
def test_restriction_rejects_different_entry(
    db_session: Session,
    restriction_parents: list[tuple[int, int, int]],
    side: str,
    constraint_name: str,
):
    entry_id, reading_id, form_id = restriction_parents[0]
    _, other_reading_id, other_form_id = restriction_parents[1]

    if side == "reading":
        reading_id = other_reading_id
    else:
        form_id = other_form_id

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            JmdictReadingRestrictionRecord(
                entry_id=entry_id,
                reading_id=reading_id,
                written_form_id=form_id,
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == constraint_name


def test_duplicate_restriction_is_rejected(
    db_session: Session,
    restriction_parents: list[tuple[int, int, int]],
):
    entry_id, reading_id, form_id = restriction_parents[0]
    values = {
        "entry_id": entry_id,
        "reading_id": reading_id,
        "written_form_id": form_id,
    }

    table = JmdictReadingRestrictionRecord.__table__
    db_session.execute(table.insert().values(**values))

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.execute(table.insert().values(**values))

    assert error.value.orig.diag.constraint_name == ("jmdict_reading_restrictions_pkey")


@pytest.mark.parametrize("parent", ["entry", "reading", "written_form"])
def test_deleting_parent_removes_only_its_restrictions(
    db_session: Session,
    restriction_parents: list[tuple[int, int, int]],
    parent: str,
):
    for entry_id, reading_id, form_id in restriction_parents:
        db_session.add(
            JmdictReadingRestrictionRecord(
                entry_id=entry_id,
                reading_id=reading_id,
                written_form_id=form_id,
            )
        )
    db_session.flush()

    entry_id, reading_id, form_id = restriction_parents[0]

    if parent == "entry":
        statement = delete(JmdictEntryRecord).where(JmdictEntryRecord.id == entry_id)
    elif parent == "reading":
        statement = delete(JmdictReadingRecord).where(
            JmdictReadingRecord.id == reading_id
        )
    else:
        statement = delete(JmdictWrittenFormRecord).where(
            JmdictWrittenFormRecord.id == form_id
        )

    db_session.execute(statement)

    remaining_entry_ids = db_session.scalars(
        select(JmdictReadingRestrictionRecord.entry_id)
    ).all()

    assert remaining_entry_ids == [restriction_parents[1][0]]

    if parent == "reading":
        assert db_session.get(JmdictWrittenFormRecord, form_id) is not None
    elif parent == "written_form":
        assert db_session.get(JmdictReadingRecord, reading_id) is not None
