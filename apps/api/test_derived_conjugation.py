import pytest

from conjugation import conjugate_verb


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "group", "form", "expected", "kana"),
    [
        (
            "食べる",
            "たべる",
            "v1",
            "potential",
            "te",
            "食べられて",
            "たべられて",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "potential",
            "negative_conditional_ba",
            "食べられなければ",
            "たべられなければ",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "passive",
            "conditional_tara",
            "食べられたら",
            "たべられたら",
        ),
        (
            "書く",
            "かく",
            "v5k",
            "potential",
            "conditional_ba",
            "書ければ",
            "かければ",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative",
            "negative_te",
            "食べさせなくて",
            "たべさせなくて",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative_passive",
            "without_doing",
            "食べさせられないで",
            "たべさせられないで",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_iru",
            "conditional_ba",
            "食べていれば",
            "たべていれば",
        ),
        (
            "出る",
            "でる",
            "v1",
            "potential_colloquial",
            "negative_conditional_tara",
            "出れなかったら",
            "でれなかったら",
        ),
        (
            "来る",
            "くる",
            "vk",
            "potential",
            "conditional_ba",
            "来られれば",
            "こられれば",
        ),
        (
            "する",
            "する",
            "vs-i",
            "passive",
            "te",
            "されて",
            "されて",
        ),
        (
            "愛する",
            "あいする",
            "vs-s-aisu",
            "potential",
            "conditional_ba",
            "愛せれば",
            "あいせれば",
        ),
    ],
)
def test_generates_extended_derived_forms(
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


def test_extended_forms_preserve_potential_and_passive_ambiguity():
    forms = conjugate_verb("食べる", "たべる", "v1")

    groups = {
        item.group
        for item in forms
        if item.form == "conditional_tara" and item.written == "食べられたら"
    }

    assert groups == {"potential", "passive"}


def test_extended_generation_keeps_unique_form_keys():
    forms = conjugate_verb("食べる", "たべる", "v1")
    keys = [(item.group, item.form) for item in forms]

    assert len(keys) == len(set(keys))
