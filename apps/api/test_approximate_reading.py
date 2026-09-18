import pytest

from approximate_reading import reading_prefix_alternatives


def test_generates_exactly_one_voicing_change():
    alternatives = reading_prefix_alternatives("だべ")

    assert set(alternatives) == {"たべ", "だへ", "だぺ"}
    assert "だべ" not in alternatives
    assert "たへ" not in alternatives


@pytest.mark.parametrize("query", ["だべ", "ダベ", "ﾀﾞﾍﾞ", "  ダベ  "])
def test_normalizes_equivalent_kana_queries(query: str):
    assert reading_prefix_alternatives(query) == (reading_prefix_alternatives("だべ"))


@pytest.mark.parametrize("query", ["", " ", "た", "だ", "だー", "ー"])
def test_rejects_queries_with_fewer_than_two_kana(query: str):
    assert reading_prefix_alternatives(query) == ()


@pytest.mark.parametrize("query", ["dabe", "学校", "Tシャツ", "だ べ", "%_"])
def test_rejects_non_kana_queries(query: str):
    assert reading_prefix_alternatives(query) == ()


def test_preserves_small_kana():
    alternatives = reading_prefix_alternatives("びょう")

    assert "ひょう" in alternatives
    assert "ぴょう" in alternatives
    assert all(candidate[1] == "ょ" for candidate in alternatives)
    assert "びよう" not in alternatives


def test_preserves_long_vowel_mark():
    alternatives = reading_prefix_alternatives("スーパー")

    assert alternatives
    assert all(
        candidate[1] == "ー" and candidate[3] == "ー" for candidate in alternatives
    )


def test_returns_no_candidates_when_no_character_has_alternatives():
    assert reading_prefix_alternatives("ねこ") == ("ねご",)
    assert reading_prefix_alternatives("ねの") == ()


def test_candidates_are_unique_and_deterministic():
    alternatives = reading_prefix_alternatives("ばば")

    assert set(alternatives) == {"はば", "ぱば", "ばは", "ばぱ"}
    assert alternatives == tuple(sorted(set(alternatives)))
