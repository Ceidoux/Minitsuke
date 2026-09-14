import pytest

from search import normalize_query


def test_keeps_correct_strings():
    assert normalize_query("食べる") == "食べる"


def test_removes_surrounding_whitespace():
    assert normalize_query("  食べる  ") == "食べる"


def test_preserves_query_without_surrounding_whitespace():
    assert normalize_query("I'm     eating here !") == "I'm     eating here !"


def test_rejects_whitespace_only_query():
    with pytest.raises(ValueError, match="Search query must not be empty"):
        normalize_query("   ")


def test_rejects_empty_query():
    with pytest.raises(ValueError, match="Search query must not be empty"):
        normalize_query("")


def test_removes_tabs_and_newlines():
    assert normalize_query("\t食べる\n") == "食べる"
