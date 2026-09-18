import pytest

from japanese_text import normalize_reading, normalize_written_form


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("たべ", "たべ"),
        ("タベ", "たべ"),
        ("ﾀﾍﾞ", "たべ"),
        ("がっこう", "がっこう"),
        ("カ\u3099ッコウ", "がっこう"),
        ("ｶﾞｯｺｳ", "がっこう"),
        ("データベース", "でーたべーす"),
        ("スーパー", "すーぱー"),
        ("ヴァイオリン", "ゔぁいおりん"),
        ("バナヽ", "ばなゝ"),
        ("", ""),
    ],
)
def test_normalizes_reading(text: str, expected: str):
    assert normalize_reading(text) == expected


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("びょういん", "びよういん"),
        ("は", "ば"),
        ("スーパー", "スパ"),
    ],
)
def test_normalization_preserves_meaningful_differences(
    first: str,
    second: str,
):
    assert normalize_reading(first) != normalize_reading(second)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tシャツ", "tしゃつ"),
        ("Ｔシャツ", "tしゃつ"),
        ("tシャツ", "tしゃつ"),
        ("Tしゃつ", "tしゃつ"),
        ("Ｔｼｬﾂ", "tしゃつ"),
        ("食べ物", "食べ物"),
        ("学校", "学校"),
        ("", ""),
    ],
)
def test_normalizes_written_form(text: str, expected: str):
    assert normalize_written_form(text) == expected


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Tシャツ", "ティーシャツ"),
        ("学校", "學校"),
        ("食べ物", "食物"),
    ],
)
def test_written_normalization_preserves_distinct_spellings(
    first: str,
    second: str,
):
    assert normalize_written_form(first) != normalize_written_form(second)
