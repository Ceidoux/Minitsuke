from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_entry_service import load_entries
from jmdict_importer import save_jmdict_entry


def add_kana_entry(session: Session, source_id: int) -> int:
    return save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=(),
            readings=(JmdictReading(text="ありがとう", no_kanji=True),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="thank you", language="eng"),),
                ),
            ),
        ),
    )


def test_assembles_complete_entry_with_ordered_restrictions(db_session: Session):
    entry_id = save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=100,
            is_common=True,
            written_forms=("学校", "學校"),
            readings=(
                JmdictReading(
                    text="がっこう",
                    restricted_to=("學校", "学校"),
                ),
                JmdictReading(text="ガッコウ"),
            ),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss(text="school", language="eng"),
                        JmdictGloss(text="école", language="fre"),
                        JmdictGloss(text="school", language="eng"),
                    ),
                    parts_of_speech=("noun", "expression"),
                    restricted_to_written_forms=("學校", "学校"),
                    restricted_to_readings=("ガッコウ", "がっこう"),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="academy", language="eng"),),
                    parts_of_speech=("noun",),
                ),
            ),
        ),
    )
    add_kana_entry(db_session, 200)

    results = load_entries(db_session, (entry_id,))

    assert len(results) == 1
    assert results[0].model_dump() == {
        "source_id": 100,
        "is_common": True,
        "written_forms": ["学校", "學校"],
        "readings": [
            {
                "text": "がっこう",
                "no_kanji": False,
                "restricted_to": ["学校", "學校"],
            },
            {
                "text": "ガッコウ",
                "no_kanji": False,
                "restricted_to": [],
            },
        ],
        "senses": [
            {
                "glosses": [
                    {"text": "school", "language": "eng"},
                    {"text": "école", "language": "fre"},
                    {"text": "school", "language": "eng"},
                ],
                "parts_of_speech": ["noun", "expression"],
                "restricted_to_written_forms": ["学校", "學校"],
                "restricted_to_readings": ["がっこう", "ガッコウ"],
            },
            {
                "glosses": [
                    {"text": "academy", "language": "eng"},
                ],
                "parts_of_speech": ["noun"],
                "restricted_to_written_forms": [],
                "restricted_to_readings": [],
            },
        ],
    }


def test_assembles_kana_only_entry(db_session: Session):
    entry_id = add_kana_entry(db_session, 100)

    results = load_entries(db_session, (entry_id,))

    assert len(results) == 1
    assert results[0].model_dump() == {
        "source_id": 100,
        "is_common": False,
        "written_forms": [],
        "readings": [
            {
                "text": "ありがとう",
                "no_kanji": True,
                "restricted_to": [],
            },
        ],
        "senses": [
            {
                "glosses": [
                    {"text": "thank you", "language": "eng"},
                ],
                "parts_of_speech": [],
                "restricted_to_written_forms": [],
                "restricted_to_readings": [],
            },
        ],
    }


def test_preserves_ranked_order_without_duplicate_entries(db_session: Session):
    first = add_kana_entry(db_session, 100)
    second = add_kana_entry(db_session, 200)

    results = load_entries(db_session, (second, first, second))

    assert [entry.source_id for entry in results] == [200, 100]


def test_empty_or_missing_ids_return_no_entries(db_session: Session):
    add_kana_entry(db_session, 100)

    assert load_entries(db_session, ()) == []
    assert load_entries(db_session, (-1,)) == []
