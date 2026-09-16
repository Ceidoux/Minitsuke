import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Meaning, Word
from schemas import WordEntry
from search import find_words, normalize_query

# NORMALIZE_QUERY TESTS


def test_keeps_correct_strings() -> None:
    assert normalize_query("食べる") == "食べる"


def test_removes_surrounding_whitespace() -> None:
    assert normalize_query("  食べる  ") == "食べる"


def test_preserves_internal_whitespace() -> None:
    assert normalize_query("I'm     eating here !") == "I'm     eating here !"


def test_rejects_whitespace_only_query() -> None:
    with pytest.raises(ValueError, match="Search query must not be empty"):
        normalize_query("   ")


def test_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="Search query must not be empty"):
        normalize_query("")


def test_removes_tabs_and_newlines() -> None:
    assert normalize_query("\t食べる\n") == "食べる"


# FIND_WORDS TESTS


def test_finds_entry_with_written_form(db_session: Session) -> None:
    assert find_words(db_session, "食べる") == [
        WordEntry(
            written_form="食べる",
            reading="たべる",
            meanings=["to eat"],
        )
    ]


def test_finds_entry_with_reading(db_session: Session) -> None:
    assert find_words(db_session, "たべる") == [
        WordEntry(
            written_form="食べる",
            reading="たべる",
            meanings=["to eat"],
        )
    ]


def test_rejects_partial_matching(db_session: Session) -> None:
    assert find_words(db_session, "食") == []


def test_groups_meanings_under_one_word(db_session: Session) -> None:
    word = db_session.scalars(select(Word).where(Word.written_form == "食べる")).one()

    db_session.add(Meaning(word_id=word.id, meaning="to live on"))
    db_session.flush()

    assert find_words(db_session, "食べる") == [
        WordEntry(
            written_form="食べる",
            reading="たべる",
            meanings=["to eat", "to live on"],
        )
    ]


def test_returns_word_without_meanings(db_session: Session) -> None:
    db_session.add(Word(written_form="猫", reading="ねこ"))
    db_session.flush()

    assert find_words(db_session, "猫") == [
        WordEntry(
            written_form="猫",
            reading="ねこ",
            meanings=[],
        )
    ]
