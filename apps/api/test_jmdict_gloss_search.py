import pytest
from sqlalchemy.orm import Session

from jmdict_search_repository import find_gloss_matches
from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictSenseRecord,
)


def add_gloss_entry(
    session: Session,
    source_id: int,
    glosses: tuple[tuple[str, str], ...],
    *,
    is_common: bool = False,
) -> None:
    entry = JmdictEntryRecord(
        source_id=source_id,
        is_common=is_common,
    )
    session.add(entry)
    session.flush()

    sense = JmdictSenseRecord(entry_id=entry.id, position=1)
    session.add(sense)
    session.flush()

    session.add_all(
        [
            JmdictGlossRecord(
                sense_id=sense.id,
                text=text,
                language=language,
                position=position,
            )
            for position, (text, language) in enumerate(glosses, start=1)
        ]
    )
    session.flush()


def test_ranks_exact_then_whole_word_then_prefix(db_session: Session):
    add_gloss_entry(db_session, 400, (("school", "eng"),))
    add_gloss_entry(db_session, 300, (("secondary school", "eng"),), is_common=True)
    add_gloss_entry(db_session, 200, (("primary school", "eng"),), is_common=True)
    add_gloss_entry(db_session, 100, (("a school", "eng"),))
    add_gloss_entry(db_session, 50, (("schoolhouse", "eng"),), is_common=True)
    add_gloss_entry(db_session, 25, (("preschool", "eng"),))

    page = find_gloss_matches(db_session, "school")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (400, 0),
        (200, 1),
        (300, 1),
        (100, 1),
        (50, 3),
    ]


def test_tab_is_not_a_whole_word_match_for_table(db_session: Session):
    add_gloss_entry(db_session, 300, (("tab", "eng"),))
    add_gloss_entry(db_session, 200, (("a tab", "eng"),))
    add_gloss_entry(db_session, 100, (("table", "eng"),))
    add_gloss_entry(db_session, 50, (("stable", "eng"),))

    page = find_gloss_matches(db_session, "tab")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (300, 0),
        (200, 1),
        (100, 3),
    ]


def test_partial_query_finds_school(db_session: Session):
    add_gloss_entry(db_session, 100, (("school", "eng"),))

    page = find_gloss_matches(db_session, "scho")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 3),
    ]


def test_matching_ignores_case_and_outer_whitespace(db_session: Session):
    add_gloss_entry(db_session, 100, (("School", "eng"),))

    page = find_gloss_matches(db_session, "  SCHOOL  ")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 0),
    ]


def test_searches_only_enabled_languages(db_session: Session):
    add_gloss_entry(db_session, 100, (("chat", "eng"),))
    add_gloss_entry(db_session, 200, (("chat", "fre"),))

    english = find_gloss_matches(db_session, "chat")
    both = find_gloss_matches(db_session, "chat", languages=("eng", "fre"))
    neither = find_gloss_matches(db_session, "chat", languages=())

    assert [match.source_id for match in english.matches] == [100]
    assert [match.source_id for match in both.matches] == [100, 200]
    assert neither.matches == ()


def test_phrase_matches_require_word_boundaries(db_session: Session):
    add_gloss_entry(db_session, 100, (("high school", "eng"),))
    add_gloss_entry(db_session, 200, (("a high school student", "eng"),))
    add_gloss_entry(db_session, 300, (("high schoolhouse", "eng"),))
    add_gloss_entry(db_session, 400, (("high schooling", "eng"),))

    page = find_gloss_matches(db_session, "high school")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 0),
        (200, 1),
        (400, 3),
        (300, 3),
    ]


@pytest.mark.parametrize("query", [".", "(", "%", "_"])
def test_search_punctuation_is_literal(
    db_session: Session,
    query: str,
):
    add_gloss_entry(db_session, 100, ((query, "eng"),))
    add_gloss_entry(db_session, 200, (("school", "eng"),))

    page = find_gloss_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [100]


def test_keeps_best_match_before_pagination(db_session: Session):
    add_gloss_entry(
        db_session,
        100,
        (
            ("schoolhouse", "eng"),
            ("a school", "eng"),
            ("school", "eng"),
            ("school", "eng"),
        ),
    )
    add_gloss_entry(db_session, 200, (("secondary school", "eng"),))

    first = find_gloss_matches(db_session, "school", limit=1)
    second = find_gloss_matches(db_session, "school", limit=1, offset=1)

    assert [(match.source_id, match.tier) for match in first.matches] == [
        (100, 0),
    ]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [200]
    assert second.has_more is False


def test_rejects_blank_query(db_session: Session):
    with pytest.raises(ValueError, match="Search query must not be empty"):
        find_gloss_matches(db_session, "   ")


def test_gloss_prefix_prefers_direct_definition(db_session: Session):
    add_gloss_entry(db_session, 500, (("school", "eng"),))
    add_gloss_entry(db_session, 400, (("school building", "eng"),), is_common=True)
    add_gloss_entry(db_session, 300, (("primary school", "eng"),), is_common=True)
    add_gloss_entry(
        db_session,
        100,
        (("cheering (esp. for a school sports team)", "eng"),),
        is_common=True,
    )

    page = find_gloss_matches(db_session, "scho")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (400, 3),
        (500, 3),
        (300, 4),
        (100, 5),
    ]


def test_earlier_gloss_takes_priority_over_shorter_later_gloss(db_session: Session):
    add_gloss_entry(
        db_session,
        200,
        (
            ("school building", "eng"),
            ("school", "eng"),
            ("a", "eng"),
        ),
    )
    add_gloss_entry(
        db_session,
        100,
        (("schoolhouse", "eng"),),
        is_common=True,
    )

    page = find_gloss_matches(db_session, "scho")

    assert [match.source_id for match in page.matches] == [100, 200]


def test_equal_gloss_lengths_use_commonness_then_source_id(db_session: Session):
    add_gloss_entry(db_session, 100, (("school", "eng"),))
    add_gloss_entry(db_session, 300, (("school", "eng"),), is_common=True)
    add_gloss_entry(db_session, 200, (("school", "eng"),), is_common=True)

    page = find_gloss_matches(db_session, "scho")

    assert [match.source_id for match in page.matches] == [200, 300, 100]
