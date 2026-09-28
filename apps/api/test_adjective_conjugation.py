import pytest

from adjective_conjugation import conjugate_adjective


@pytest.mark.parametrize(
    ("written", "reading", "adjective_class", "form", "expected", "kana"),
    [
        ("高い", "たかい", "adj-i", "past", "高かった", "たかかった"),
        ("高い", "たかい", "adj-i", "negative", "高くない", "たかくない"),
        (
            "高い",
            "たかい",
            "adj-i",
            "polite_past",
            "高かったです",
            "たかかったです",
        ),
        (
            "高い",
            "たかい",
            "adj-i",
            "polite_negative_past_alternative",
            "高くありませんでした",
            "たかくありませんでした",
        ),
        (
            "高い",
            "たかい",
            "adj-i",
            "conditional_ba",
            "高ければ",
            "たかければ",
        ),
        ("高い", "たかい", "adj-i", "te", "高くて", "たかくて"),
        ("高い", "たかい", "adj-i", "adverbial", "高く", "たかく"),
        ("いい", "いい", "adj-ix", "past", "よかった", "よかった"),
        ("いい", "いい", "adj-ix", "negative", "よくない", "よくない"),
        ("いい", "いい", "adj-ix", "polite", "いいです", "いいです"),
        ("良い", "よい", "adj-i", "past", "良かった", "よかった"),
        (
            "格好いい",
            "かっこいい",
            "adj-ix",
            "past",
            "格好よかった",
            "かっこよかった",
        ),
        (
            "格好良い",
            "かっこいい",
            "adj-ix",
            "negative",
            "格好良くない",
            "かっこよくない",
        ),
        (
            "かわいい",
            "かわいい",
            "adj-i",
            "past",
            "かわいかった",
            "かわいかった",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "past",
            "静かだった",
            "しずかだった",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "negative",
            "静かではない",
            "しずかではない",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "polite_past",
            "静かでした",
            "しずかでした",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "conditional_ba",
            "静かであれば",
            "しずかであれば",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "attributive",
            "静かな",
            "しずかな",
        ),
        (
            "静か",
            "しずか",
            "adj-na",
            "adverbial",
            "静かに",
            "しずかに",
        ),
        (
            "綺麗",
            "きれい",
            "adj-na",
            "past",
            "綺麗だった",
            "きれいだった",
        ),
        (
            "きれい",
            "きれい",
            "adj-na",
            "negative_colloquial",
            "きれいじゃない",
            "きれいじゃない",
        ),
    ],
)
def test_generates_adjective_forms(
    written: str,
    reading: str,
    adjective_class: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_adjective(written, reading, adjective_class)
    result = next(item for item in forms if item.form == form)

    assert result.written == expected
    assert result.reading == kana


@pytest.mark.parametrize(
    ("written", "reading", "adjective_class"),
    [
        ("高い", "たかい", "adj-i"),
        ("いい", "いい", "adj-ix"),
        ("静か", "しずか", "adj-na"),
    ],
)
def test_adjective_forms_have_unique_keys(
    written: str,
    reading: str,
    adjective_class: str,
):
    forms = conjugate_adjective(written, reading, adjective_class)
    keys = [(item.group, item.form) for item in forms]

    assert len(keys) == len(set(keys))
    assert {item.group for item in forms} == {"basic"}


@pytest.mark.parametrize(
    ("written", "reading", "adjective_class"),
    [
        ("", "たかい", "adj-i"),
        ("高い", "", "adj-i"),
        ("静か", "しずか", "adj-i"),
        ("高い", "たかい", "adj-ix"),
        ("高い", "たかい", "unsupported"),
    ],
)
def test_rejects_unsupported_adjective_inputs(
    written: str,
    reading: str,
    adjective_class: str,
):
    with pytest.raises(ValueError):
        conjugate_adjective(written, reading, adjective_class)
