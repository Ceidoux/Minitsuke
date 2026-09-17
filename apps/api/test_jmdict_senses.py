import pytest
from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictSenseRecord,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def sense_parents(db_session: Session) -> tuple[int, int, int]:
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    first = JmdictSenseRecord(entry_id=entry.id, position=1)
    second = JmdictSenseRecord(entry_id=entry.id, position=2)
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add_all(
        [
            JmdictGlossRecord(
                sense_id=first.id,
                text="to eat",
                language="eng",
                position=1,
            ),
            JmdictGlossRecord(
                sense_id=second.id,
                text="to live on",
                language="eng",
                position=1,
            ),
        ]
    )
    db_session.flush()

    return entry.id, first.id, second.id


def test_glosses_preserve_grouping_language_and_duplicates(
    db_session: Session,
    sense_parents: tuple[int, int, int],
):
    entry_id, first_id, second_id = sense_parents

    db_session.add_all(
        [
            JmdictGlossRecord(
                sense_id=first_id,
                text="manger",
                language="fre",
                position=2,
            ),
            JmdictGlossRecord(
                sense_id=second_id,
                text="to live on",
                language="eng",
                position=2,
            ),
        ]
    )
    db_session.flush()

    statement = (
        select(
            JmdictSenseRecord.position,
            JmdictGlossRecord.position,
            JmdictGlossRecord.text,
            JmdictGlossRecord.language,
        )
        .join(
            JmdictGlossRecord,
            JmdictGlossRecord.sense_id == JmdictSenseRecord.id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictGlossRecord.position,
        )
    )

    rows = db_session.execute(statement).all()

    assert [tuple(row) for row in rows] == [
        (1, 1, "to eat", "eng"),
        (1, 2, "manger", "fre"),
        (2, 1, "to live on", "eng"),
        (2, 2, "to live on", "eng"),
    ]


@pytest.mark.parametrize(
    ("record_type", "position", "constraint_name"),
    [
        ("sense", 0, "ck_jmdict_senses_positive_position"),
        ("sense", 1, "uq_jmdict_senses_entry_position"),
        ("gloss", 0, "ck_jmdict_glosses_positive_position"),
        ("gloss", 1, "uq_jmdict_glosses_sense_position"),
    ],
)
def test_invalid_sense_or_gloss_position_is_rejected(
    db_session: Session,
    sense_parents: tuple[int, int, int],
    record_type: str,
    position: int,
    constraint_name: str,
):
    entry_id, first_id, _ = sense_parents

    if record_type == "sense":
        record = JmdictSenseRecord(
            entry_id=entry_id,
            position=position,
        )
    else:
        record = JmdictGlossRecord(
            sense_id=first_id,
            text="another gloss",
            language="eng",
            position=position,
        )

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(record)
        db_session.flush()

    assert error.value.orig.diag.constraint_name == constraint_name


def test_deleting_sense_preserves_other_sense_and_glosses(
    db_session: Session,
    sense_parents: tuple[int, int, int],
):
    entry_id, first_id, second_id = sense_parents

    db_session.execute(
        delete(JmdictSenseRecord).where(
            JmdictSenseRecord.id == first_id,
        )
    )

    remaining_sense_ids = db_session.scalars(
        select(JmdictSenseRecord.id).where(
            JmdictSenseRecord.entry_id == entry_id,
        )
    ).all()
    remaining_glosses = db_session.scalars(select(JmdictGlossRecord.text)).all()

    assert remaining_sense_ids == [second_id]
    assert remaining_glosses == ["to live on"]
    assert db_session.get(JmdictEntryRecord, entry_id) is not None


def test_deleting_entry_removes_senses_and_glosses(
    db_session: Session,
    sense_parents: tuple[int, int, int],
):
    entry_id, _, _ = sense_parents

    db_session.execute(
        delete(JmdictEntryRecord).where(
            JmdictEntryRecord.id == entry_id,
        )
    )

    assert db_session.scalars(select(JmdictSenseRecord.id)).all() == []
    assert db_session.scalars(select(JmdictGlossRecord.id)).all() == []
