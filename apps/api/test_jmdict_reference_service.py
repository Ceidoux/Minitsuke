from dataclasses import replace

import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_reference_service import ReferenceTarget, resolve_references


def make_entry(source_id: int = 100) -> JmdictEntry:
    return JmdictEntry(
        source_id=source_id,
        written_forms=("丸",),
        readings=(JmdictReading(text="まる"),),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("circle", "eng"),),
            ),
            JmdictSense(
                glosses=(JmdictGloss("zero", "eng"),),
            ),
        ),
    )


@pytest.mark.parametrize(
    ("query", "sense_position"),
    [
        ("丸", None),
        ("まる", None),
        ("丸・まる", None),
        ("丸・1", 1),
        ("まる・2", 2),
        ("丸・まる・2", 2),
    ],
)
def test_resolves_forms_readings_and_senses(
    db_session: Session,
    query: str,
    sense_position: int | None,
):
    save_jmdict_entry(db_session, make_entry())

    assert resolve_references(db_session, (query,)) == {
        query: (ReferenceTarget(100, sense_position),),
    }


def test_rejects_missing_sense_and_wrong_reading(db_session: Session):
    save_jmdict_entry(db_session, make_entry())

    assert resolve_references(
        db_session,
        ("丸・3", "丸・ちがう・1", "存在しない語"),
    ) == {
        "丸・3": (),
        "丸・ちがう・1": (),
        "存在しない語": (),
    }


def test_preserves_ambiguous_targets(db_session: Session):
    save_jmdict_entry(db_session, make_entry(200))
    save_jmdict_entry(db_session, make_entry(100))

    assert resolve_references(db_session, ("まる",)) == {
        "まる": (
            ReferenceTarget(100),
            ReferenceTarget(200),
        ),
    }


def test_resolves_literal_middle_dots_and_numbered_sense(db_session: Session):
    entry = replace(
        make_entry(),
        written_forms=(),
        readings=(JmdictReading(text="リズム・アンド・ブルース"),),
    )
    save_jmdict_entry(db_session, entry)

    assert resolve_references(
        db_session,
        ("リズム・アンド・ブルース", "リズム・アンド・ブルース・1"),
    ) == {
        "リズム・アンド・ブルース": (ReferenceTarget(100),),
        "リズム・アンド・ブルース・1": (ReferenceTarget(100, 1),),
    }


def test_respects_reading_and_sense_restrictions(db_session: Session):
    entry = JmdictEntry(
        source_id=100,
        written_forms=("甲", "乙"),
        readings=(
            JmdictReading(text="こう", restricted_to=("甲",)),
            JmdictReading(text="おつ", restricted_to=("乙",)),
        ),
        senses=(
            JmdictSense(
                glosses=(JmdictGloss("first", "eng"),),
                restricted_to_written_forms=("甲",),
                restricted_to_readings=("こう",),
            ),
            JmdictSense(
                glosses=(JmdictGloss("second", "eng"),),
                restricted_to_written_forms=("乙",),
                restricted_to_readings=("おつ",),
            ),
        ),
    )
    save_jmdict_entry(db_session, entry)

    assert resolve_references(
        db_session,
        ("甲・こう・1", "甲・おつ", "乙・1", "おつ・1", "乙・おつ・2"),
    ) == {
        "甲・こう・1": (ReferenceTarget(100, 1),),
        "甲・おつ": (),
        "乙・1": (),
        "おつ・1": (),
        "乙・おつ・2": (ReferenceTarget(100, 2),),
    }


def test_no_kanji_reading_is_not_a_written_form_pair(db_session: Session):
    entry = replace(
        make_entry(),
        readings=(JmdictReading(text="まる", no_kanji=True),),
    )
    save_jmdict_entry(db_session, entry)

    assert resolve_references(db_session, ("まる", "丸・まる")) == {
        "まる": (ReferenceTarget(100),),
        "丸・まる": (),
    }


def test_keeps_literal_and_structured_interpretations(db_session: Session):
    save_jmdict_entry(db_session, make_entry(100))

    literal_entry = replace(
        make_entry(200),
        written_forms=("丸・1",),
        readings=(JmdictReading(text="てすと"),),
    )
    save_jmdict_entry(db_session, literal_entry)

    assert resolve_references(db_session, ("丸・1",)) == {
        "丸・1": (
            ReferenceTarget(100, 1),
            ReferenceTarget(200),
        ),
    }


def test_handles_empty_and_repeated_input(db_session: Session):
    save_jmdict_entry(db_session, make_entry())

    assert resolve_references(db_session, ()) == {}
    assert resolve_references(db_session, ("", "丸", "丸")) == {
        "": (),
        "丸": (ReferenceTarget(100),),
    }
