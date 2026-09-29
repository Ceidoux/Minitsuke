import pytest

from conjugation import conjugate_verb


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "group", "form", "expected", "kana"),
    [
        (
            "食べる",
            "たべる",
            "v1",
            "te_iru_colloquial",
            "nonpast",
            "食べてる",
            "たべてる",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_iru_colloquial",
            "negative",
            "食べてない",
            "たべてない",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "te_iru_colloquial",
            "polite",
            "読んでます",
            "よんでます",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_oku",
            "past",
            "食べておいた",
            "たべておいた",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_oku_colloquial",
            "past",
            "食べといた",
            "たべといた",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_oku_colloquial",
            "conditional_ba",
            "食べとけば",
            "たべとけば",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "te_oku_colloquial",
            "nonpast",
            "読んどく",
            "よんどく",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "te_oku_colloquial",
            "negative",
            "読んどかない",
            "よんどかない",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_shimau",
            "polite_past",
            "食べてしまいました",
            "たべてしまいました",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_shimau_colloquial",
            "past",
            "食べちゃった",
            "たべちゃった",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "te_shimau_colloquial",
            "past",
            "読んじゃった",
            "よんじゃった",
        ),
        (
            "する",
            "する",
            "vs-i",
            "te_shimau_colloquial",
            "past",
            "しちゃった",
            "しちゃった",
        ),
        (
            "来る",
            "くる",
            "vk",
            "te_shimau_colloquial",
            "past",
            "来ちゃった",
            "きちゃった",
        ),
        (
            "行く",
            "いく",
            "v5k-s",
            "te_shimau_colloquial",
            "past",
            "行っちゃった",
            "いっちゃった",
        ),
    ],
)
def test_generates_auxiliary_forms(
    written: str,
    reading: str,
    verb_class: str,
    group: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb(written, reading, verb_class)
    result = next(item for item in forms if item.group == group and item.form == form)

    assert result.written == expected
    assert result.reading == kana


def test_auxiliary_forms_keep_unique_keys():
    forms = conjugate_verb("読む", "よむ", "v5m")
    keys = [(item.group, item.form) for item in forms]

    assert len(keys) == len(set(keys))


def test_voiced_te_form_uses_voiced_contractions():
    forms = conjugate_verb("読む", "よむ", "v5m")
    surfaces = {item.written for item in forms}

    assert "読んじゃった" in surfaces
    assert "読んどく" in surfaces
    assert "読んちゃった" not in surfaces
    assert "読んとく" not in surfaces
