import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search import search_jmdict


def add_school(session: Session, source_id: int = 100) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            is_common=True,
            written_forms=("学校", "學校"),
            readings=(JmdictReading(text="がっこう"),),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss(text="school", language="eng"),
                        JmdictGloss(text="école", language="fre"),
                    ),
                    parts_of_speech=("noun",),
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    "query",
    ["学校", "がっこう", "ガッコウ", "ｶﾞｯｺｳ", "gakkou", "school", "scho"],
)
def test_routes_queries_and_returns_complete_entry(
    db_session: Session,
    query: str,
):
    add_school(db_session)

    response = search_jmdict(db_session, query)

    assert response.query == query
    assert response.limit == 30
    assert response.offset == 0
    assert response.has_more is False
    assert len(response.results) == 1

    entry = response.results[0]
    assert entry.source_id == 100
    assert entry.is_common is True
    assert entry.written_forms == ["学校", "學校"]
    assert entry.readings[0].text == "がっこう"
    assert entry.senses[0].parts_of_speech == ["noun"]
    assert [(gloss.text, gloss.language) for gloss in entry.senses[0].glosses] == [
        ("school", "eng")
    ]


def test_routes_mixed_spelling_to_written_form_matching(db_session: Session):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=100,
            written_forms=("Ｔシャツ",),
            readings=(JmdictReading(text="ティーシャツ"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="T-shirt", language="eng"),),
                ),
            ),
        ),
    )

    response = search_jmdict(db_session, "tしゃつ")

    assert [entry.source_id for entry in response.results] == [100]
    assert response.results[0].written_forms == ["Ｔシャツ"]


def test_enabled_languages_control_gloss_matching_and_display(
    db_session: Session,
):
    add_school(db_session)

    english = search_jmdict(db_session, "école")
    french = search_jmdict(
        db_session,
        "école",
        languages=("fre",),
    )
    both = search_jmdict(
        db_session,
        "学校",
        languages=("eng", "fre"),
    )

    assert english.results == []
    assert [entry.source_id for entry in french.results] == [100]
    assert [
        (gloss.text, gloss.language) for gloss in french.results[0].senses[0].glosses
    ] == [("école", "fre")]
    assert [gloss.language for gloss in both.results[0].senses[0].glosses] == [
        "eng",
        "fre",
    ]


def test_keeps_japanese_match_when_enabled_gloss_language_is_missing(
    db_session: Session,
):
    add_school(db_session)

    response = search_jmdict(
        db_session,
        "学校",
        languages=("ger",),
    )

    assert [entry.source_id for entry in response.results] == [100]
    sense = response.results[0].senses[0]
    assert sense.glosses == []
    assert sense.parts_of_speech == ["noun"]


def test_preserves_pagination_and_ranked_entry_order(db_session: Session):
    for source_id in reversed(range(100, 131)):
        add_school(db_session, source_id)

    first = search_jmdict(db_session, "school")
    second = search_jmdict(db_session, "school", offset=30)

    assert [entry.source_id for entry in first.results] == list(range(100, 130))
    assert first.has_more is True
    assert [entry.source_id for entry in second.results] == [130]
    assert second.offset == 30
    assert second.has_more is False


def test_trims_query_and_handles_no_results(db_session: Session):
    response = search_jmdict(db_session, "  nonexistent  ")

    assert response.query == "nonexistent"
    assert response.results == []
    assert response.has_more is False


@pytest.mark.parametrize(
    ("query", "limit", "offset", "message"),
    [
        ("   ", 30, 0, "Search query must not be empty"),
        ("学校", 0, 0, "Limit must be between"),
        ("がっこう", 101, 0, "Limit must be between"),
        ("school", 30, -1, "Offset must not be negative"),
    ],
)
def test_rejects_invalid_arguments(
    db_session: Session,
    query: str,
    limit: int,
    offset: int,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        search_jmdict(
            db_session,
            query,
            limit=limit,
            offset=offset,
        )
