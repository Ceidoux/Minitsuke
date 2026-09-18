import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from japanese_text import normalize_reading, normalize_written_form
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictSenseReadingRestrictionRecord,
    JmdictSenseRecord,
    JmdictSenseWrittenFormRestrictionRecord,
    JmdictWrittenFormRecord,
)


@pytest.fixture(
    params=[
        (
            JmdictSenseWrittenFormRestrictionRecord,
            JmdictWrittenFormRecord,
            "written_form_id",
        ),
        (
            JmdictSenseReadingRestrictionRecord,
            JmdictReadingRecord,
            "reading_id",
        ),
    ],
    ids=["written_form", "reading"],
)
def restriction_models(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture
def sense_restriction_parents(
    db_session: Session,
    restriction_models,
) -> list[tuple[int, int, int, int]]:
    _, target_model, target_field = restriction_models
    parents = []

    for source_id in (1000001, 1000002):
        entry = JmdictEntryRecord(source_id=source_id)
        db_session.add(entry)
        db_session.flush()

        sense = JmdictSenseRecord(
            entry_id=entry.id,
            position=1,
        )
        db_session.add(sense)

        if target_field == "reading_id":
            texts = ("がっこう", "ガッコウ")
            extra = {"no_kanji": False}
            normalize = normalize_reading
        else:
            texts = ("学校", "學校")
            extra = {}
            normalize = normalize_written_form

        targets = [
            target_model(
                entry_id=entry.id,
                text=text,
                search_text=normalize(text),
                position=position,
                **extra,
            )
            for position, text in enumerate(texts, start=1)
        ]
        db_session.add_all(targets)
        db_session.flush()

        parents.append((entry.id, sense.id, targets[0].id, targets[1].id))

    return parents


def test_sense_can_restrict_to_multiple_targets(
    db_session: Session,
    restriction_models,
    sense_restriction_parents,
):
    restriction_model, _, target_field = restriction_models
    entry_id, sense_id, first_id, second_id = sense_restriction_parents[0]

    for target_id in (first_id, second_id):
        db_session.add(
            restriction_model(
                entry_id=entry_id,
                sense_id=sense_id,
                **{target_field: target_id},
            )
        )
    db_session.flush()

    target_column = getattr(restriction_model, target_field)
    stored_ids = db_session.scalars(
        select(target_column).where(
            restriction_model.sense_id == sense_id,
        )
    ).all()

    assert len(stored_ids) == 2
    assert set(stored_ids) == {first_id, second_id}


@pytest.mark.parametrize("side", ["sense", "target"])
def test_sense_restriction_rejects_different_entry(
    db_session: Session,
    restriction_models,
    sense_restriction_parents,
    side: str,
):
    restriction_model, _, target_field = restriction_models
    entry_id, sense_id, target_id, _ = sense_restriction_parents[0]
    _, other_sense_id, other_target_id, _ = sense_restriction_parents[1]

    if side == "sense":
        sense_id = other_sense_id
    else:
        target_id = other_target_id

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            restriction_model(
                entry_id=entry_id,
                sense_id=sense_id,
                **{target_field: target_id},
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == (
        f"fk_{restriction_model.__tablename__}_{side}"
    )


def test_duplicate_sense_restriction_is_rejected(
    db_session: Session,
    restriction_models,
    sense_restriction_parents,
):
    restriction_model, _, target_field = restriction_models
    entry_id, sense_id, target_id, _ = sense_restriction_parents[0]
    values = {
        "entry_id": entry_id,
        "sense_id": sense_id,
        target_field: target_id,
    }

    table = restriction_model.__table__
    db_session.execute(table.insert().values(**values))

    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.execute(table.insert().values(**values))

    assert error.value.orig.diag.constraint_name == (
        f"{restriction_model.__tablename__}_pkey"
    )


@pytest.mark.parametrize("parent", ["entry", "sense", "target"])
def test_deleting_parent_removes_only_its_sense_restrictions(
    db_session: Session,
    restriction_models,
    sense_restriction_parents,
    parent: str,
):
    restriction_model, target_model, target_field = restriction_models

    for entry_id, sense_id, target_id, _ in sense_restriction_parents:
        db_session.add(
            restriction_model(
                entry_id=entry_id,
                sense_id=sense_id,
                **{target_field: target_id},
            )
        )
    db_session.flush()

    entry_id, sense_id, target_id, _ = sense_restriction_parents[0]

    if parent == "entry":
        statement = delete(JmdictEntryRecord).where(
            JmdictEntryRecord.id == entry_id,
        )
    elif parent == "sense":
        statement = delete(JmdictSenseRecord).where(
            JmdictSenseRecord.id == sense_id,
        )
    else:
        statement = delete(target_model).where(
            target_model.id == target_id,
        )

    db_session.execute(statement)

    remaining_entry_ids = db_session.scalars(select(restriction_model.entry_id)).all()

    assert remaining_entry_ids == [sense_restriction_parents[1][0]]

    if parent == "sense":
        assert db_session.get(target_model, target_id) is not None
    elif parent == "target":
        assert db_session.get(JmdictSenseRecord, sense_id) is not None
