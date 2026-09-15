import pytest

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


def test_finds_entry_with_written_form() -> None:
    assert find_words("食べる") == [
        WordEntry(
            written_form="食べる",
            reading="たべる",
            meanings=["to eat"],
        )
    ]


def test_finds_entry_with_reading() -> None:
    assert find_words("たべる") == [
        WordEntry(
            written_form="食べる",
            reading="たべる",
            meanings=["to eat"],
        )
    ]


def test_rejects_partial_matching() -> None:
    assert find_words("食") == []
