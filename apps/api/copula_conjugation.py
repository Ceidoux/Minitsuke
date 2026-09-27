from functools import lru_cache

from conjugation import ConjugatedForm

_PLAIN_FORMS = {
    "nonpast": "だ",
    "negative": "ではない",
    "negative_colloquial": "じゃない",
    "past": "だった",
    "negative_past": "ではなかった",
    "negative_past_colloquial": "じゃなかった",
    "polite": "です",
    "polite_negative": "ではありません",
    "polite_negative_colloquial": "じゃありません",
    "polite_negative_alternative": "ではないです",
    "polite_negative_colloquial_alternative": "じゃないです",
    "polite_past": "でした",
    "polite_negative_past": "ではありませんでした",
    "polite_negative_past_colloquial": "じゃありませんでした",
    "polite_negative_past_alternative": "ではなかったです",
    "polite_negative_past_colloquial_alternative": "じゃなかったです",
    "te": "で",
    "negative_te": "ではなくて",
    "negative_te_colloquial": "じゃなくて",
    "conditional_nara": "なら",
    "conditional_tara": "だったら",
    "negative_conditional_ba": "ではなければ",
    "negative_conditional_tara": "ではなかったら",
    "presumptive": "だろう",
    "polite_presumptive": "でしょう",
}

_FORMAL_FORMS = {
    "nonpast": "である",
    "negative": "ではない",
    "past": "であった",
    "negative_past": "ではなかった",
    "polite": "であります",
    "polite_negative": "ではありません",
    "polite_past": "でありました",
    "polite_negative_past": "ではありませんでした",
    "te": "であって",
    "negative_te": "ではなくて",
    "conditional_ba": "であれば",
    "conditional_tara": "であったら",
    "negative_conditional_ba": "ではなければ",
    "negative_conditional_tara": "ではなかったら",
    "presumptive": "であろう",
    "polite_presumptive": "でありましょう",
}

_GOZAIMASU_FORMS = {
    "nonpast": "でございます",
    "negative": "ではございません",
    "past": "でございました",
    "negative_past": "ではございませんでした",
    "conditional_tara": "でございましたら",
    "presumptive": "でございましょう",
}

_FORMS_BY_READING = {
    "だ": _PLAIN_FORMS,
    "です": _PLAIN_FORMS,
    "である": _FORMAL_FORMS,
    "でございます": _GOZAIMASU_FORMS,
}

_ALLOWED_WRITTEN_FORMS = {
    "だ": {"だ"},
    "です": {"です"},
    "である": {"である"},
    "でございます": {"でございます", "で御座います"},
}


def conjugate_copula(
    written: str,
    reading: str,
) -> tuple[ConjugatedForm, ...]:
    forms = _FORMS_BY_READING.get(reading)

    if forms is None:
        raise ValueError(f"Unsupported copula reading: {reading!r}")

    if written not in _ALLOWED_WRITTEN_FORMS[reading]:
        raise ValueError(f"Unsupported copula spelling: {written!r} for {reading!r}")

    use_kanji = written == "で御座います"

    return tuple(
        ConjugatedForm(
            group="basic",
            form=form,
            written=(surface.replace("ござい", "御座い") if use_kanji else surface),
            reading=surface,
        )
        for form, surface in forms.items()
    )


@lru_cache(maxsize=1)
def _pronunciation_aliases() -> dict[str, str]:
    aliases = {}

    for reading in _FORMS_BY_READING:
        for item in conjugate_copula(reading, reading):
            if item.reading.startswith("では"):
                alias = "でわ" + item.reading[2:]
                aliases[alias] = item.reading

    return aliases


def resolve_copula_pronunciation(reading: str) -> str | None:
    return _pronunciation_aliases().get(reading)
