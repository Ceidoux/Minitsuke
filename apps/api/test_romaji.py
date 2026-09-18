import pytest

from romaji import interpret_romaji


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("tabe", "たべ"),
        ("TABE", "たべ"),
        ("ｔａｂｅ", "たべ"),
        ("  tabe  ", "たべ"),
        ("gakkou", "がっこう"),
        ("shi", "し"),
        ("si", "し"),
        ("kyo", "きょ"),
        ("kan'i", "かんい"),
        ("dabe", "だべ"),
    ],
)
def test_interprets_complete_romaji(query: str, expected: str):
    result = interpret_romaji(query)

    assert result.complete_reading == expected
    assert result.completion_prefixes == ()


def test_unfinished_syllable_keeps_its_consonant():
    result = interpret_romaji("tab")

    assert result.complete_reading is None
    assert {"たば", "たび", "たぶ", "たべ", "たぼ"}.issubset(result.completion_prefixes)
    assert "た" not in result.completion_prefixes
    assert "たか" not in result.completion_prefixes


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("sh", "し"),
        ("ch", "ち"),
        ("ky", "きょ"),
    ],
)
def test_completes_multi_letter_consonants(query: str, expected: str):
    result = interpret_romaji(query)

    assert result.complete_reading is None
    assert expected in result.completion_prefixes


def test_final_n_retains_both_interpretations():
    result = interpret_romaji("kan")

    assert result.complete_reading == "かん"
    assert "かな" in result.completion_prefixes
    assert "かに" in result.completion_prefixes


@pytest.mark.parametrize(
    "query",
    ["school", "scho", "école", "two words", "学校", "たべ", "", "%"],
)
def test_input_without_valid_romaji_has_no_reading_candidates(query: str):
    result = interpret_romaji(query)

    assert result.complete_reading is None
    assert result.completion_prefixes == ()
