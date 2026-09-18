from dataclasses import replace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from models import JmdictEntryRecord


@pytest.mark.parametrize("band", [None, 1, 48])
def test_entry_stores_optional_frequency_band(
    db_session: Session,
    band: int | None,
):
    record = JmdictEntryRecord(
        source_id=1000001,
        frequency_band=band,
    )
    db_session.add(record)
    db_session.flush()
    db_session.refresh(record)

    assert record.frequency_band == band


@pytest.mark.parametrize("band", [0, -1])
def test_rejects_nonpositive_frequency_band(
    db_session: Session,
    band: int,
):
    with pytest.raises(IntegrityError) as error, db_session.begin_nested():
        db_session.add(
            JmdictEntryRecord(
                source_id=1000001,
                frequency_band=band,
            )
        )
        db_session.flush()

    assert error.value.orig.diag.constraint_name == (
        "ck_jmdict_entries_positive_frequency_band"
    )


def test_import_updates_and_clears_frequency_band(db_session: Session):
    entry = JmdictEntry(
        source_id=1000001,
        written_forms=("学校",),
        readings=(JmdictReading(text="がっこう"),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss(text="school", language="eng"),),
            ),
        ),
        is_common=True,
        frequency_band=3,
    )

    entry_id = save_jmdict_entry(db_session, entry)
    record = db_session.get(JmdictEntryRecord, entry_id)
    assert record is not None
    db_session.refresh(record)
    assert record.frequency_band == 3

    assert (
        save_jmdict_entry(
            db_session,
            replace(entry, frequency_band=1),
        )
        == entry_id
    )
    db_session.refresh(record)
    assert record.frequency_band == 1

    assert (
        save_jmdict_entry(
            db_session,
            replace(entry, frequency_band=None),
        )
        == entry_id
    )
    db_session.refresh(record)
    assert record.frequency_band is None
    assert record.is_common is True
