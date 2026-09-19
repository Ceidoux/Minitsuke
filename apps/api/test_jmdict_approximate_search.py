from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_latin_matches, find_reading_matches


def add_entry(
    session: Session,
    source_id: int,
    readings: tuple[str, ...],
    *,
    is_common: bool = False,
    band: int | None = None,
    gloss: str = "test",
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=(),
            readings=tuple(JmdictReading(text=text) for text in readings),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text=gloss, language="eng"),),
                ),
            ),
            is_common=is_common,
            frequency_band=band,
        ),
    )


def test_genuine_matches_outrank_all_voicing_suggestions(db_session: Session):
    add_entry(db_session, 500, ("だべ",))
    add_entry(db_session, 400, ("だべる",))
    add_entry(db_session, 300, ("あだべ",))
    add_entry(db_session, 200, ("たべ",), is_common=True, band=1)
    add_entry(db_session, 100, ("たべる",), is_common=True, band=1)

    page = find_reading_matches(db_session, "だべ")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (500, 0),
        (400, 1),
        (300, 2),
        (200, 3),
        (100, 4),
    ]


def test_suggestions_require_one_change_at_the_reading_start(db_session: Session):
    add_entry(db_session, 100, ("たべる",))
    add_entry(db_session, 200, ("たへる",))
    add_entry(db_session, 300, ("あたべる",))

    page = find_reading_matches(db_session, "だべ")

    assert [match.source_id for match in page.matches] == [100]


def test_single_kana_does_not_enable_suggestions(db_session: Session):
    add_entry(db_session, 100, ("たべる",))
    add_entry(db_session, 200, ("だべる",))

    page = find_reading_matches(db_session, "だ")

    assert [match.source_id for match in page.matches] == [200]


def test_keeps_best_entry_match_before_paginating(db_session: Session):
    add_entry(db_session, 100, ("だべる", "たべる"))
    add_entry(db_session, 200, ("たべもの",))

    first = find_reading_matches(db_session, "だべ", limit=1)
    second = find_reading_matches(db_session, "だべ", limit=1, offset=1)
    exhausted = find_reading_matches(db_session, "だべ", limit=1, offset=2)

    assert [(match.source_id, match.tier) for match in first.matches] == [
        (100, 1),
    ]
    assert first.has_more is True

    assert [(match.source_id, match.tier) for match in second.matches] == [
        (200, 4),
    ]
    assert second.has_more is False
    assert exhausted.matches == ()


def test_suggestions_use_commonness_and_frequency_within_tier(
    db_session: Session,
):
    add_entry(db_session, 100, ("たべる",), band=1)
    add_entry(db_session, 200, ("たべもの",), is_common=True)
    add_entry(db_session, 300, ("たべかた",), is_common=True, band=3)
    add_entry(db_session, 400, ("たべすぎ",), is_common=True, band=1)

    page = find_reading_matches(db_session, "だべ")

    assert [match.source_id for match in page.matches] == [
        400,
        300,
        200,
        100,
    ]
    assert all(match.tier == 4 for match in page.matches)


def test_romaji_genuine_matches_outrank_suggestions(db_session: Session):
    add_entry(db_session, 600, ("だべ",))
    add_entry(db_session, 500, ("あ",), gloss="dabe")
    add_entry(db_session, 400, ("だべる",))
    add_entry(db_session, 300, ("あだべ",))
    add_entry(db_session, 200, ("たべ",), is_common=True, band=1)
    add_entry(db_session, 100, ("たべる",), is_common=True, band=1)

    page = find_latin_matches(db_session, "dabe")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (600, 0),
        (500, 0),
        (400, 2),
        (300, 6),
        (200, 7),
        (100, 8),
    ]


def test_romaji_gloss_prefix_outranks_suggestion(db_session: Session):
    add_entry(db_session, 200, ("あ",), gloss="dabelike")
    add_entry(db_session, 100, ("たべる",), is_common=True, band=1)

    page = find_latin_matches(db_session, "dabe")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (200, 3),
        (100, 8),
    ]


def test_unfinished_romaji_does_not_add_voicing_suggestions(db_session: Session):
    add_entry(db_session, 100, ("だべる",))
    add_entry(db_session, 200, ("たべる",))

    page = find_latin_matches(db_session, "dab")

    assert [match.source_id for match in page.matches] == [100]


def test_romaji_suggestions_are_deduplicated_before_pagination(
    db_session: Session,
):
    add_entry(db_session, 100, ("だべる", "たべる"))
    add_entry(db_session, 200, ("たべもの",))

    first = find_latin_matches(db_session, "dabe", limit=1)
    second = find_latin_matches(db_session, "dabe", limit=1, offset=1)

    assert [(match.source_id, match.tier) for match in first.matches] == [
        (100, 2),
    ]
    assert first.has_more is True
    assert [(match.source_id, match.tier) for match in second.matches] == [
        (200, 8),
    ]
    assert second.has_more is False


def test_romaji_suggestion_requires_two_kana(db_session: Session):
    add_entry(db_session, 100, ("だ",))
    add_entry(db_session, 200, ("た",))

    page = find_latin_matches(db_session, "da")

    assert [match.source_id for match in page.matches] == [100]
