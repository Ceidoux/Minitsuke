import pytest

from japanese_text import normalize_reading


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
