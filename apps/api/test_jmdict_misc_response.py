from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_entry_service import load_entries, load_entry_by_source_id
from jmdict_importer import save_jmdict_entry

KANA_LABEL = "word usually written using kana alone"


def add_example(session: Session) -> int:
    return save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=100,
            written_forms=(),
            readings=(
                JmdictReading(text="あほんだら"),
                JmdictReading(text="あほだら"),
            ),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="fool", language="eng"),),
                    misc=(KANA_LABEL, "colloquial"),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="mock Buddhist sutra", language="eng"),),
                    restricted_to_readings=("あほだら",),
                    misc=("abbreviation",),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="imbécile", language="fre"),),
                ),
            ),
        ),
    )


def test_response_preserves_tag_order_scope_and_restrictions(
    db_session: Session,
):
    entry_id = add_example(db_session)

    entry = load_entries(db_session, (entry_id,))[0]
    payload = entry.model_dump()

    assert payload["senses"][0]["misc"] == [KANA_LABEL, "colloquial"]
    assert payload["senses"][1]["misc"] == ["abbreviation"]
    assert payload["senses"][1]["restricted_to_readings"] == ["あほだら"]
    assert payload["senses"][2]["misc"] == []


def test_language_filter_does_not_copy_or_remove_usage_annotations(
    db_session: Session,
):
    add_example(db_session)

    entry = load_entry_by_source_id(
        db_session,
        100,
        languages=("fre",),
    )

    assert entry is not None
    assert entry.senses[0].glosses == []
    assert entry.senses[0].misc == [KANA_LABEL, "colloquial"]
    assert entry.senses[1].misc == ["abbreviation"]
    assert entry.senses[2].misc == []
    assert entry.senses[2].glosses[0].text == "imbécile"
