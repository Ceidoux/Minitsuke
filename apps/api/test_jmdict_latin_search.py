from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_latin_matches


def add_entry(
    session: Session,
    source_id: int,
    *,
    reading: str,
    gloss: str,
    forms: tuple[str, ...] = (),
    language: str = "eng",
    is_common: bool = False,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=forms,
            readings=(JmdictReading(text=reading),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text=gloss, language=language),),
                ),
            ),
            is_common=is_common,
        ),
    )


def test_combines_all_latin_match_tiers(db_session: Session):
    add_entry(db_session, 600, reading="たべ", gloss="unrelated")
    add_entry(db_session, 500, reading="あ", gloss="tabe")
    add_entry(db_session, 400, reading="い", gloss="a tabe example")
    add_entry(db_session, 300, reading="たべる", gloss="to eat")
    add_entry(db_session, 200, reading="う", gloss="tabelike")
    add_entry(
        db_session,
        100,
        reading="データベース",
        gloss="database",
        is_common=True,
    )

    page = find_latin_matches(db_session, "tabe")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (600, 0),
        (500, 0),
        (400, 1),
        (300, 2),
        (200, 3),
        (100, 6),
    ]


def test_tab_keeps_translation_and_unfinished_romaji(db_session: Session):
    add_entry(db_session, 100, reading="タブ", gloss="tab")
    add_entry(db_session, 200, reading="たべる", gloss="to eat")
    add_entry(db_session, 300, reading="つくえ", gloss="table")
    add_entry(db_session, 400, reading="たこ", gloss="octopus")

    page = find_latin_matches(db_session, "tab")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 0),
        (200, 2),
        (300, 3),
    ]


def test_scho_finds_school_without_valid_romaji(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("学校",),
        reading="がっこう",
        gloss="school",
    )

    page = find_latin_matches(db_session, "scho")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 3),
    ]


def test_latin_letter_finds_mixed_written_form(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("Ｔシャツ",),
        reading="ティーシャツ",
        gloss="shirt",
    )

    page = find_latin_matches(db_session, "Ｔ")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 2),
    ]


def test_language_filter_does_not_disable_reading_matches(db_session: Session):
    add_entry(db_session, 100, reading="たべる", gloss="manger", language="fre")
    add_entry(db_session, 200, reading="あ", gloss="tabe", language="fre")

    english = find_latin_matches(db_session, "tabe")
    french = find_latin_matches(db_session, "tabe", languages=("fre",))

    assert [match.source_id for match in english.matches] == [100]
    assert [(match.source_id, match.tier) for match in french.matches] == [
        (200, 0),
        (100, 2),
    ]


def test_combines_and_deduplicates_before_pagination(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("ＴＡＢＥ",),
        reading="たべ",
        gloss="tabe",
    )
    add_entry(db_session, 200, reading="たべる", gloss="to eat")
    add_entry(db_session, 300, reading="あ", gloss="tabelike")

    first = find_latin_matches(db_session, "tabe", limit=2)
    second = find_latin_matches(db_session, "tabe", limit=2, offset=2)

    assert [match.source_id for match in first.matches] == [100, 200]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [300]
    assert second.has_more is False


def test_gloss_query_preserves_non_english_letters(db_session: Session):
    add_entry(
        db_session,
        100,
        reading="みち",
        gloss="Straße",
        language="ger",
    )

    page = find_latin_matches(
        db_session,
        "Straße",
        languages=("ger",),
    )

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (100, 0),
    ]


def test_combined_search_prefers_direct_gloss_prefix(db_session: Session):
    add_entry(
        db_session,
        300,
        reading="がっこう",
        gloss="school",
    )
    add_entry(
        db_session,
        200,
        reading="こうしゃ",
        gloss="school building",
        is_common=True,
    )
    add_entry(
        db_session,
        100,
        reading="おうえん",
        gloss="cheering (esp. for a school sports team)",
        is_common=True,
    )

    page = find_latin_matches(db_session, "scho")

    assert [(match.source_id, match.tier) for match in page.matches] == [
        (200, 3),
        (300, 3),
        (100, 5),
    ]
