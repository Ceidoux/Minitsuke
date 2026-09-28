import pytest

from conjugation import conjugate_verb


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "group", "form", "expected", "kana"),
    [
        (
            "食べる",
            "たべる",
            "v1",
            "basic",
            "polite_negative",
            "食べません",
            "たべません",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "basic",
            "polite_negative_past",
            "食べませんでした",
            "たべませんでした",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "potential",
            "polite_negative",
            "食べられません",
            "たべられません",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "causative_passive",
            "polite_past",
            "食べさせられました",
            "たべさせられました",
        ),
        (
            "書く",
            "かく",
            "v5k",
            "potential",
            "negative",
            "書けない",
            "かけない",
        ),
        (
            "泳ぐ",
            "およぐ",
            "v5g",
            "basic",
            "te",
            "泳いで",
            "およいで",
        ),
        (
            "話す",
            "はなす",
            "v5s",
            "basic",
            "past",
            "話した",
            "はなした",
        ),
        (
            "待つ",
            "まつ",
            "v5t",
            "basic",
            "volitional",
            "待とう",
            "まとう",
        ),
        (
            "死ぬ",
            "しぬ",
            "v5n",
            "basic",
            "past",
            "死んだ",
            "しんだ",
        ),
        (
            "遊ぶ",
            "あそぶ",
            "v5b",
            "basic",
            "te",
            "遊んで",
            "あそんで",
        ),
        (
            "読む",
            "よむ",
            "v5m",
            "basic",
            "conditional_ba",
            "読めば",
            "よめば",
        ),
        (
            "帰る",
            "かえる",
            "v5r",
            "basic",
            "negative",
            "帰らない",
            "かえらない",
        ),
        (
            "買う",
            "かう",
            "v5u",
            "basic",
            "negative",
            "買わない",
            "かわない",
        ),
        (
            "行く",
            "いく",
            "v5k-s",
            "basic",
            "te",
            "行って",
            "いって",
        ),
        (
            "行く",
            "いく",
            "v5k-s",
            "basic",
            "past",
            "行った",
            "いった",
        ),
        (
            "する",
            "する",
            "vs-i",
            "potential",
            "nonpast",
            "できる",
            "できる",
        ),
        (
            "確認する",
            "かくにんする",
            "vs-i",
            "passive",
            "polite_past",
            "確認されました",
            "かくにんされました",
        ),
        (
            "来る",
            "くる",
            "vk",
            "basic",
            "negative",
            "来ない",
            "こない",
        ),
        (
            "来る",
            "くる",
            "vk",
            "basic",
            "polite",
            "来ます",
            "きます",
        ),
        (
            "来る",
            "くる",
            "vk",
            "basic",
            "conditional_ba",
            "来れば",
            "くれば",
        ),
        (
            "来る",
            "くる",
            "vk",
            "basic",
            "imperative",
            "来い",
            "こい",
        ),
        (
            "来る",
            "くる",
            "vk",
            "potential",
            "polite",
            "来られます",
            "こられます",
        ),
        (
            "食べる",
            "たべる",
            "v1",
            "te_iru",
            "polite_negative_past",
            "食べていませんでした",
            "たべていませんでした",
        ),
    ],
)
def test_generates_spelling_and_reading(
    written: str,
    reading: str,
    verb_class: str,
    group: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = {
        (item.group, item.form): item
        for item in conjugate_verb(written, reading, verb_class)
    }

    result = forms[(group, form)]
    assert result.written == expected
    assert result.reading == kana


def test_preserves_potential_and_passive_interpretations():
    forms = conjugate_verb("食べる", "たべる", "v1")

    matching = {
        item.group
        for item in forms
        if item.form == "nonpast" and item.written == "食べられる"
    }

    assert matching == {"potential", "passive"}


@pytest.mark.parametrize(
    ("written", "reading", "verb_class"),
    [
        ("書く", "かく", "v1"),
        ("食べる", "たべる", "v5k"),
        ("学校", "がっこう", "vs-i"),
        ("学校", "がっこう", "v5r-i"),
    ],
)
def test_rejects_mismatched_or_unsupported_classes(
    written: str,
    reading: str,
    verb_class: str,
):
    with pytest.raises(ValueError):
        conjugate_verb(written, reading, verb_class)


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "form", "expected", "kana"),
    [
        ("出る", "でる", "v1", "nonpast", "出れる", "でれる"),
        ("食べる", "たべる", "v1", "negative", "食べれない", "たべれない"),
        ("見る", "みる", "v1", "polite", "見れます", "みれます"),
        ("来る", "くる", "vk", "nonpast", "来れる", "これる"),
        (
            "出る",
            "でる",
            "v1",
            "polite_negative_past",
            "出れませんでした",
            "でれませんでした",
        ),
    ],
)
def test_generates_colloquial_potential(
    written: str,
    reading: str,
    verb_class: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb(written, reading, verb_class)
    result = next(
        item
        for item in forms
        if item.group == "potential_colloquial" and item.form == form
    )

    assert result.written == expected
    assert result.reading == kana


def test_colloquial_potential_does_not_replace_standard_or_passive():
    forms = conjugate_verb("出る", "でる", "v1")
    nonpast = {item.group: item.written for item in forms if item.form == "nonpast"}

    assert nonpast["potential"] == "出られる"
    assert nonpast["passive"] == "出られる"
    assert nonpast["potential_colloquial"] == "出れる"
