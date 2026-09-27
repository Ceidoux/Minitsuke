import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_reading_matches


def add_entry(
    session: Session,
    source_id: int,
    readings: tuple[str, ...],
    *,
    forms: tuple[str, ...] = (),
    common: bool = False,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=forms,
            readings=tuple(JmdictReading(text=text) for text in readings),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="example", language="eng"),),
                ),
            ),
            is_common=common,
            frequency_band=1 if common else None,
        ),
    )


@pytest.mark.parametrize("query", ["ジム", "ｼﾞﾑ"])
def test_katakana_matches_precede_common_hiragana_exact_match(
    db_session: Session,
    query: str,
):
    add_entry(db_session, 100, ("じむ",), forms=("事務",), common=True)
    add_entry(db_session, 200, ("ジム",))
    add_entry(db_session, 300, ("ジムがよい",))
    add_entry(db_session, 400, ("スポーツジム",))

    first = find_reading_matches(db_session, query, limit=3)
    second = find_reading_matches(db_session, query, limit=3, offset=3)

    assert [match.source_id for match in first.matches] == [200, 300, 400]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [100]
    assert second.has_more is False


def test_katakana_written_form_qualifies_with_hiragana_reading(
    db_session: Session,
):
    add_entry(db_session, 100, ("じむ",), forms=("事務",), common=True)
    add_entry(db_session, 200, ("じむがよい",), forms=("ジム通い",))

    page = find_reading_matches(db_session, "ジム")

    assert [match.source_id for match in page.matches] == [200, 100]


def test_hiragana_input_prefers_hiragana_matches(db_session: Session):
    add_entry(db_session, 100, ("ジム",), common=True)
    add_entry(db_session, 200, ("じむ",), forms=("事務",))

    page = find_reading_matches(db_session, "じむ")

    assert [match.source_id for match in page.matches] == [200, 100]


def test_best_reading_is_selected_using_script_group_first(
    db_session: Session,
):
    add_entry(db_session, 100, ("じむ",), common=True)
    add_entry(db_session, 200, ("じむ", "スポーツジム"))

    page = find_reading_matches(db_session, "ジム")

    assert [match.source_id for match in page.matches] == [200, 100]
    assert page.matches[0].tier == 2
