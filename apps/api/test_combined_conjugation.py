import pytest

from conjugation import conjugate_verb


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "group", "form", "expected", "kana"),
    [
        (
            "食べる",
            "たべる",
            "v1",
            "potential+te_iru",
            "negative_past",
            "食べられていなかった",
            "たべられていなかった",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "passive+te_iru",
            "nonpast",
            "食べられている",
            "たべられている",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative_passive+te_iru",
            "polite",
            "食べさせられています",
            "たべさせられています",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative_passive+te_iru_colloquial",
            "nonpast",
            "食べさせられてる",
            "たべさせられてる",
        ),
        (
            "書く",
            "かく",
            "v5k",
            "potential+te_iru",
            "polite_negative",
            "書けていません",
            "かけていません",
        ),
        (
            "する",
            "する",
            "vs-i",
            "passive+te_iru",
            "past",
            "されていた",
            "されていた",
        ),
        (
            "来る",
            "くる",
            "vk",
            "causative+te_iru",
            "nonpast",
            "来させている",
            "こさせている",
        ),
        (
            "出る",
            "でる",
            "v1",
            "potential_colloquial+te_iru",
            "negative",
            "出れていない",
            "でれていない",
        ),
    ],
)
def test_generates_combined_conjugations(
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


def test_combined_forms_preserve_potential_and_passive_interpretations():
    forms = conjugate_verb("食べる", "たべる", "v1")

    groups = {
        item.group
        for item in forms
        if item.written == "食べられている" and item.form == "nonpast"
    }

    assert groups == {"potential+te_iru", "passive+te_iru"}


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "group", "form", "expected", "kana"),
    [
        (
            "食べる",
            "たべる",
            "v1",
            "passive+te_shimau",
            "past",
            "食べられてしまった",
            "たべられてしまった",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "passive+te_shimau_colloquial",
            "past",
            "食べられちゃった",
            "たべられちゃった",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative+te_oku",
            "nonpast",
            "食べさせておく",
            "たべさせておく",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative+te_oku_colloquial",
            "conditional_ba",
            "食べさせとけば",
            "たべさせとけば",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative_passive+te_shimau",
            "polite_past",
            "食べさせられてしまいました",
            "たべさせられてしまいました",
        ),
        (
            "書く",
            "かく",
            "v5k",
            "potential+te_shimau_colloquial",
            "past",
            "書けちゃった",
            "かけちゃった",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "passive+te_shimau_colloquial",
            "past",
            "読まれちゃった",
            "よまれちゃった",
        ),
        (
            "する",
            "する",
            "vs-i",
            "causative+te_oku_colloquial",
            "nonpast",
            "させとく",
            "させとく",
        ),
        (
            "来る",
            "くる",
            "vk",
            "causative+te_oku",
            "past",
            "来させておいた",
            "こさせておいた",
        ),
        (
            "出る",
            "でる",
            "v1",
            "potential_colloquial+te_shimau_colloquial",
            "past",
            "出れちゃった",
            "でれちゃった",
        ),
    ],
)
def test_generates_combined_auxiliaries(
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


def test_combined_auxiliaries_have_unique_group_and_form_keys():
    forms = conjugate_verb("食べる", "たべる", "v1")
    keys = [(item.group, item.form) for item in forms]

    assert len(keys) == len(set(keys))


def test_combined_auxiliaries_do_not_chain_recursively():
    forms = conjugate_verb("食べる", "たべる", "v1")

    assert all(item.group.count("+") <= 1 for item in forms)
