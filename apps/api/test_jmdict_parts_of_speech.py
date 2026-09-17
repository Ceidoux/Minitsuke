import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    JmdictEntryRecord,
    JmdictPartOfSpeechRecord,
    JmdictSenseRecord,
)


@pytest.fixture
def labeled_senses(db_session: Session) -> tuple[int, int, int]:
    entry = JmdictEntryRecord(source_id=1000001)
    db_session.add(entry)
    db_session.flush()

    first = JmdictSenseRecord(entry_id=entry.id, position=1)
    second = JmdictSenseRecord(entry_id=entry.id, position=2)
    db_session.add_all([first, second])
    db_session.flush()

    for sense in (first, second):
        db_session.add_all(
            [
                JmdictPartOfSpeechRecord(
                    sense_id=sense.id,
                    label="transitive verb",
                    position=2,
                ),
                JmdictPartOfSpeechRecord(
                    sense_id=sense.id,
                    label="Ichidan verb",
                    position=1,
                ),
            ]
        )
    db_session.flush()

    return entry.id, first.id, second.id


def test_labels_are_stored_and_ordered_per_sense(
    db_session: Session,
    labeled_senses: tuple[int, int, int],
):
    entry_id, _, _ = labeled_senses

    statement = (
        select(
            JmdictSenseRecord.position,
            JmdictPartOfSpeechRecord.position,
            JmdictPartOfSpeechRecord.label,
        )
        .join(
            JmdictPartOfSpeechRecord,
            JmdictPartOfSpeechRecord.sense_id == JmdictSenseRecord.id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictPartOfSpeechRecord.position,
        )
    )

    rows = db_session.execute(statement).all()

    assert [tuple(row) for row in rows] == [
        (1, 1, "Ichidan verb"),
        (1, 2, "transitive verb"),
        (2, 1, "Ichidan verb"),
        (2, 2, "transitive verb"),
    ]


@pytest.mark.parametrize(
    ("position", "constraint_name"),
    [
        (0, "ck_jmdict_parts_of_speech_positive_position"),
        (1, "uq_jmdict_parts_of_speech_sense_position"),
    ],
)
def test_invalid_label_position_is_rejected(
    db_session: Session,
    labeled_senses: tuple[int, int, int],
    position: int,
    constraint_name: str,
):
    _, first_id, _ = labeled_senses

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            JmdictPartOfSpeechRecord(
                sense_id=first_id,
                label="another label",
                position=position,
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == constraint_name


@pytest.mark.parametrize("parent", ["sense", "entry"])
def test_labels_follow_parent_deletion(
    db_session: Session,
    labeled_senses: tuple[int, int, int],
    parent: str,
):
    entry_id, first_id, second_id = labeled_senses

    if parent == "sense":
        statement = delete(JmdictSenseRecord).where(
            JmdictSenseRecord.id == first_id,
        )
    else:
        statement = delete(JmdictEntryRecord).where(
            JmdictEntryRecord.id == entry_id,
        )

    db_session.execute(statement)

    remaining = db_session.scalars(
        select(JmdictPartOfSpeechRecord.sense_id).order_by(
            JmdictPartOfSpeechRecord.position,
        )
    ).all()

    if parent == "sense":
        assert remaining == [second_id, second_id]
        assert db_session.get(JmdictEntryRecord, entry_id) is not None
    else:
        assert remaining == []
