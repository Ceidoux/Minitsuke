import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import JmdictEntryRecord, JmdictWrittenFormRecord


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
