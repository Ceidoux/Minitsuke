import pytest

from copula_conjugation import conjugate_copula


@pytest.mark.parametrize(
    ("written", "reading", "form", "expected", "expected_reading"),
    [
        ("だ", "だ", "past", "だった", "だった"),
        ("だ", "だ", "negative", "ではない", "ではない"),
        ("だ", "だ", "negative_colloquial", "じゃない", "じゃない"),
        ("だ", "だ", "conditional_nara", "なら", "なら"),
        ("だ", "だ", "presumptive", "だろう", "だろう"),
        ("です", "です", "nonpast", "だ", "だ"),
        ("です", "です", "polite", "です", "です"),
        ("です", "です", "polite_past", "でした", "でした"),
        (
            "です",
            "です",
            "polite_negative_alternative",
            "ではないです",
            "ではないです",
        ),
        (
            "です",
            "です",
            "polite_negative_past",
            "ではありませんでした",
            "ではありませんでした",
        ),
        ("である", "である", "past", "であった", "であった"),
        ("である", "である", "conditional_ba", "であれば", "であれば"),
        ("である", "である", "polite", "であります", "であります"),
        (
            "でございます",
            "でございます",
            "negative",
            "ではございません",
            "ではございません",
        ),
        (
            "で御座います",
            "でございます",
            "past",
            "で御座いました",
            "でございました",
        ),
        (
            "で御座います",
            "でございます",
            "negative",
            "では御座いません",
            "ではございません",
        ),
    ],
)
def test_generates_copula_forms(
    written: str,
    reading: str,
    form: str,
    expected: str,
    expected_reading: str,
):
    forms = conjugate_copula(written, reading)
    result = next(item for item in forms if item.form == form)

    assert result.written == expected
    assert result.reading == expected_reading


@pytest.mark.parametrize("reading", ["だ", "です", "である", "でございます"])
def test_copulas_have_unique_basic_forms(reading: str):
    forms = conjugate_copula(reading, reading)

    assert {item.group for item in forms} == {"basic"}
    keys = [(item.group, item.form) for item in forms]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("written", "reading"),
    [
        ("ある", "ある"),
        ("食べる", "たべる"),
        ("出す", "です"),
        ("", ""),
    ],
)
def test_rejects_unsupported_copulas(written: str, reading: str):
    with pytest.raises(ValueError):
        conjugate_copula(written, reading)


@pytest.mark.parametrize(
    ("reading", "expected"),
    [
        ("でわありませんでした", "ではありませんでした"),
        ("でわございません", "ではございません"),
        ("ではありません", None),
        ("でわ", None),
        ("わたし", None),
        ("これはでわありません", None),
    ],
)
def test_resolves_only_complete_copula_pronunciation_aliases(
    reading: str,
    expected: str | None,
):
    from copula_conjugation import resolve_copula_pronunciation

    assert resolve_copula_pronunciation(reading) == expected
