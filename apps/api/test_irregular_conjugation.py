import pytest

from conjugation import conjugate_verb


@pytest.mark.parametrize(
    ("written", "reading", "verb_class", "form", "expected", "kana"),
    [
        ("くれる", "くれる", "v1-s", "imperative", "くれ", "くれ"),
        ("呉れる", "くれる", "v1-s", "imperative", "呉れ", "くれ"),
        ("呉れる", "くれる", "v1-s", "polite", "呉れます", "くれます"),
        (
            "下さる",
            "くださる",
            "v5aru",
            "polite",
            "下さいます",
            "くださいます",
        ),
        (
            "下さる",
            "くださる",
            "v5aru",
            "imperative",
            "下さい",
            "ください",
        ),
        (
            "なさる",
            "なさる",
            "v5aru",
            "polite_negative_past",
            "なさいませんでした",
            "なさいませんでした",
        ),
        (
            "なさる",
            "なさる",
            "v5aru",
            "imperative",
            "なさい",
            "なさい",
        ),
        (
            "いらっしゃる",
            "いらっしゃる",
            "v5aru",
            "polite",
            "いらっしゃいます",
            "いらっしゃいます",
        ),
        (
            "おっしゃる",
            "おっしゃる",
            "v5aru",
            "past",
            "おっしゃった",
            "おっしゃった",
        ),
        (
            "御座る",
            "ござる",
            "v5aru",
            "polite",
            "御座います",
            "ございます",
        ),
        ("ある", "ある", "v5r-i", "negative", "ない", "ない"),
        ("有る", "ある", "v5r-i", "negative", "ない", "ない"),
        ("在る", "ある", "v5r-i", "negative_past", "なかった", "なかった"),
        ("有る", "ある", "v5r-i", "past", "有った", "あった"),
        ("有る", "ある", "v5r-i", "polite", "有ります", "あります"),
        (
            "有る",
            "ある",
            "v5r-i",
            "polite_negative",
            "有りません",
            "ありません",
        ),
        (
            "ある",
            "ある",
            "v5r-i",
            "negative_conditional_ba",
            "なければ",
            "なければ",
        ),
    ],
)
def test_generates_irregular_basic_forms(
    written: str,
    reading: str,
    verb_class: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb(written, reading, verb_class)
    result = next(item for item in forms if item.group == "basic" and item.form == form)

    assert result.written == expected
    assert result.reading == kana


def test_kureru_does_not_use_regular_ichidan_imperative():
    forms = conjugate_verb("くれる", "くれる", "v1-s")
    imperatives = {
        item.written
        for item in forms
        if item.group == "basic"
        and item.form in {"imperative", "imperative_alternative"}
    }

    assert imperatives == {"くれ"}


def test_regular_ichidan_homophone_keeps_its_own_imperative():
    forms = conjugate_verb("暮れる", "くれる", "v1")
    imperative = next(
        item for item in forms if item.group == "basic" and item.form == "imperative"
    )

    assert imperative.written == "暮れろ"


def test_aru_does_not_generate_ordinary_voice_groups():
    forms = conjugate_verb("ある", "ある", "v5r-i")

    assert {item.group for item in forms} == {"basic"}
    assert not any(item.reading == "あらない" for item in forms)


@pytest.mark.parametrize(
    ("group", "form", "expected", "kana"),
    [
        ("basic", "nonpast", "信ずる", "しんずる"),
        ("basic", "polite", "信じます", "しんじます"),
        ("basic", "negative", "信じない", "しんじない"),
        ("basic", "past", "信じた", "しんじた"),
        ("basic", "te", "信じて", "しんじて"),
        ("basic", "conditional_ba", "信ずれば", "しんずれば"),
        (
            "basic",
            "conditional_ba_alternative",
            "信じれば",
            "しんじれば",
        ),
        ("basic", "imperative", "信じろ", "しんじろ"),
        ("basic", "imperative_alternative", "信ぜよ", "しんぜよ"),
        ("basic", "prohibitive", "信ずるな", "しんずるな"),
        ("potential", "nonpast", "信じられる", "しんじられる"),
        ("passive", "nonpast", "信じられる", "しんじられる"),
        ("causative", "nonpast", "信じさせる", "しんじさせる"),
    ],
)
def test_generates_zuru_forms(
    group: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb("信ずる", "しんずる", "vz")
    result = next(item for item in forms if item.group == group and item.form == form)

    assert result.written == expected
    assert result.reading == kana


def test_zuru_rejects_incompatible_dictionary_form():
    with pytest.raises(ValueError):
        conjugate_verb("食べる", "たべる", "vz")


@pytest.mark.parametrize(
    ("written", "reading", "form", "expected", "kana"),
    [
        ("達する", "たっする", "polite", "達します", "たっします"),
        ("達する", "たっする", "past", "達した", "たっした"),
        ("関する", "かんする", "te", "関して", "かんして"),
        (
            "達する",
            "たっする",
            "polite_negative",
            "達しません",
            "たっしません",
        ),
        (
            "達する",
            "たっする",
            "conditional_ba",
            "達すれば",
            "たっすれば",
        ),
        (
            "課する",
            "かする",
            "imperative_formal",
            "課せよ",
            "かせよ",
        ),
        (
            "不問に付する",
            "ふもんにふする",
            "past",
            "不問に付した",
            "ふもんにふした",
        ),
    ],
)
def test_generates_shared_special_suru_forms(
    written: str,
    reading: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb(written, reading, "vs-s")
    result = next(item for item in forms if item.group == "basic" and item.form == form)

    assert result.written == expected
    assert result.reading == kana


def test_shared_special_suru_does_not_guess_potential():
    forms = conjugate_verb("達する", "たっする", "vs-s")

    assert not any(item.group == "potential" for item in forms)
    assert not any(item.written == "達できる" for item in forms)


@pytest.mark.parametrize(
    ("group", "form", "expected", "kana"),
    [
        ("basic", "nonpast", "愛する", "あいする"),
        ("basic", "negative", "愛さない", "あいさない"),
        ("basic", "negative_past", "愛さなかった", "あいさなかった"),
        ("basic", "polite", "愛します", "あいします"),
        ("basic", "past", "愛した", "あいした"),
        ("basic", "volitional", "愛そう", "あいそう"),
        ("basic", "imperative", "愛せ", "あいせ"),
        ("basic", "imperative_formal", "愛せよ", "あいせよ"),
        ("basic", "conditional_ba", "愛すれば", "あいすれば"),
        (
            "basic",
            "conditional_ba_alternative",
            "愛せば",
            "あいせば",
        ),
        ("potential", "nonpast", "愛せる", "あいせる"),
        ("potential", "negative", "愛せない", "あいせない"),
        ("passive", "nonpast", "愛される", "あいされる"),
        ("causative", "nonpast", "愛させる", "あいさせる"),
    ],
)
def test_generates_aisuru_forms(
    group: str,
    form: str,
    expected: str,
    kana: str,
):
    forms = conjugate_verb("愛する", "あいする", "vs-s-aisu")
    result = next(item for item in forms if item.group == group and item.form == form)

    assert result.written == expected
    assert result.reading == kana


def test_aisuru_preserves_expression_prefix():
    forms = conjugate_verb(
        "こよなく愛する",
        "こよなくあいする",
        "vs-s-aisu",
    )
    negative = next(
        item for item in forms if item.group == "basic" and item.form == "negative"
    )

    assert negative.written == "こよなく愛さない"
    assert negative.reading == "こよなくあいさない"


def test_aisuru_profile_rejects_other_special_suru_verbs():
    with pytest.raises(ValueError):
        conjugate_verb("達する", "たっする", "vs-s-aisu")
