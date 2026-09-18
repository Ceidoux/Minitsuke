import pytest
from sqlalchemy.orm import Session

from japanese_text import normalize_reading
from jmdict_search_repository import (
    find_reading_matches,
    find_written_form_matches,
)
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictWrittenFormRecord,
)


def add_entry(
    session: Session,
    source_id: int,
    readings: tuple[str, ...],
    *,
    is_common: bool = False,
) -> None:
    entry = JmdictEntryRecord(
        source_id=source_id,
        is_common=is_common,
    )
    session.add(entry)
    session.flush()

    session.add_all(
        [
            JmdictReadingRecord(
                entry_id=entry.id,
                text=text,
                search_text=normalize_reading(text),
                position=position,
                no_kanji=False,
            )
            for position, text in enumerate(readings, start=1)
        ]
    )
    session.flush()


def test_ranks_by_tier_then_commonness_then_source_id(db_session: Session):
    add_entry(db_session, 100, ("たべもの",))
    add_entry(db_session, 300, ("たべる",), is_common=True)
    add_entry(db_session, 200, ("たべかた",), is_common=True)
    add_entry(db_session, 400, ("たべ",))
    add_entry(db_session, 50, ("データベース",), is_common=True)

    page = find_reading_matches(db_session, "たべ")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (400, 0),
        (200, 1),
        (300, 1),
        (100, 1),
        (50, 2),
    ]
    assert page.has_more is False


def test_entry_appears_once_with_its_best_reading_match(db_session: Session):
    add_entry(
        db_session,
        100,
        ("データベース", "たべる", "たべ", "タベ"),
    )

    page = find_reading_matches(db_session, "たべ")

    assert len(page.matches) == 1
    assert page.matches[0].source_id == 100
    assert page.matches[0].tier == 0


@pytest.mark.parametrize("query", ["たべ", "タベ", "ﾀﾍﾞ", "  タベ  "])
def test_equivalent_kana_queries_find_same_entry(
    db_session: Session,
    query: str,
):
    add_entry(db_session, 100, ("タベル",))

    page = find_reading_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [100]
    assert page.matches[0].tier == 1


def test_default_page_returns_30_distinct_entries(db_session: Session):
    for source_id in reversed(range(100, 131)):
        add_entry(db_session, source_id, ("たべる", "タベル"))

    first = find_reading_matches(db_session, "たべ")
    second = find_reading_matches(db_session, "たべ", offset=30)
    exhausted = find_reading_matches(db_session, "たべ", offset=31)

    assert [match.source_id for match in first.matches] == list(range(100, 130))
    assert first.has_more is True

    assert [match.source_id for match in second.matches] == [130]
    assert second.has_more is False

    assert exhausted.matches == ()
    assert exhausted.has_more is False


def test_returns_empty_page_for_no_match(db_session: Session):
    add_entry(db_session, 100, ("がっこう",))

    page = find_reading_matches(db_session, "たべ")

    assert page.matches == ()
    assert page.has_more is False


@pytest.mark.parametrize("query", ["%", "_"])
def test_sql_wildcards_are_treated_as_literal_text(
    db_session: Session,
    query: str,
):
    add_entry(db_session, 100, ("たべる",))

    assert find_reading_matches(db_session, query).matches == ()


@pytest.mark.parametrize(
    ("query", "limit", "offset", "message"),
    [
        ("   ", 30, 0, "Search query must not be empty"),
        ("たべ", 0, 0, "Limit must be between"),
        ("たべ", 101, 0, "Limit must be between"),
        ("たべ", 30, -1, "Offset must not be negative"),
    ],
)
def test_rejects_invalid_search_arguments(
    db_session: Session,
    query: str,
    limit: int,
    offset: int,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        find_reading_matches(
            db_session,
            query,
            limit=limit,
            offset=offset,
        )


def add_written_entry(
    session: Session,
    source_id: int,
    forms: tuple[str, ...],
    *,
    is_common: bool = False,
) -> None:
    entry = JmdictEntryRecord(
        source_id=source_id,
        is_common=is_common,
    )
    session.add(entry)
    session.flush()

    session.add_all(
        [
            JmdictWrittenFormRecord(
                entry_id=entry.id,
                text=text,
                position=position,
            )
            for position, text in enumerate(forms, start=1)
        ]
    )
    session.flush()


def test_written_forms_rank_exact_before_common_substrings(db_session: Session):
    add_written_entry(db_session, 400, ("食",))
    add_written_entry(db_session, 200, ("夕食",), is_common=True)
    add_written_entry(db_session, 300, ("食べ物",), is_common=True)
    add_written_entry(db_session, 100, ("食材",))

    page = find_written_form_matches(db_session, "食")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (400, 0),
        (200, 1),
        (300, 1),
        (100, 1),
    ]


def test_written_form_sequence_must_be_consecutive(db_session: Session):
    add_written_entry(db_session, 100, ("学校",))
    add_written_entry(db_session, 200, ("小学校",))
    add_written_entry(db_session, 300, ("学校生活",))
    add_written_entry(db_session, 400, ("学習校",))

    page = find_written_form_matches(db_session, "学校")

    assert [match.source_id for match in page.matches] == [100, 200, 300]


def test_mixed_kanji_kana_query_matches_anywhere(db_session: Session):
    add_written_entry(db_session, 100, ("食べる",))
    add_written_entry(db_session, 200, ("立ち食べ",))
    add_written_entry(db_session, 300, ("食事",))

    page = find_written_form_matches(db_session, "食べ")

    assert [match.source_id for match in page.matches] == [100, 200]


def test_written_variants_return_one_entry_with_best_tier(db_session: Session):
    add_written_entry(db_session, 100, ("学校生活", "学校"))

    page = find_written_form_matches(db_session, "学校")

    assert len(page.matches) == 1
    assert page.matches[0].tier == 0


def test_written_form_pagination_uses_distinct_entries(db_session: Session):
    add_written_entry(db_session, 100, ("学校", "小学校"))
    add_written_entry(db_session, 200, ("学校生活",))

    first = find_written_form_matches(db_session, "学校", limit=1)
    second = find_written_form_matches(db_session, "学校", limit=1, offset=1)

    assert [match.source_id for match in first.matches] == [100]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [200]
    assert second.has_more is False
