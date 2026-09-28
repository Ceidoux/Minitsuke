from conjugation import ConjugatedForm
from copula_conjugation import conjugate_copula


def _i_adjective_stem(word: str, adjective_class: str) -> str:
    if adjective_class == "adj-ix":
        if word.endswith("いい"):
            return word[:-2] + "よ"
        if word.endswith("イイ"):
            return word[:-2] + "ヨ"

    if not word.endswith(("い", "イ")):
        raise ValueError(f"I-adjective must end with い or イ: {word!r}")

    return word[:-1]


def _i_adjective_forms(
    word: str,
    adjective_class: str,
) -> dict[str, str]:
    stem = _i_adjective_stem(word, adjective_class)
    negative = stem + "くない"
    past = stem + "かった"
    negative_past = stem + "くなかった"

    return {
        "nonpast": word,
        "negative": negative,
        "past": past,
        "negative_past": negative_past,
        "polite": word + "です",
        "polite_negative": negative + "です",
        "polite_negative_alternative": stem + "くありません",
        "polite_past": past + "です",
        "polite_negative_past": negative_past + "です",
        "polite_negative_past_alternative": stem + "くありませんでした",
        "te": stem + "くて",
        "negative_te": stem + "くなくて",
        "conditional_ba": stem + "ければ",
        "negative_conditional_ba": stem + "くなければ",
        "conditional_tara": past + "ら",
        "negative_conditional_tara": negative_past + "ら",
        "conditional_nara": word + "なら",
        "presumptive": word + "だろう",
        "polite_presumptive": word + "でしょう",
        "attributive": word,
        "adverbial": stem + "く",
    }


def conjugate_adjective(
    written: str,
    reading: str,
    adjective_class: str,
) -> tuple[ConjugatedForm, ...]:
    if not written or not reading:
        raise ValueError("Adjective spelling and reading must not be empty")

    if adjective_class == "adj-na":
        forms = [
            ConjugatedForm(
                group="basic",
                form=item.form,
                written=written + item.written,
                reading=reading + item.reading,
            )
            for item in conjugate_copula("だ", "だ")
        ]

        forms.extend(
            [
                ConjugatedForm(
                    group="basic",
                    form="conditional_ba",
                    written=written + "であれば",
                    reading=reading + "であれば",
                ),
                ConjugatedForm(
                    group="basic",
                    form="attributive",
                    written=written + "な",
                    reading=reading + "な",
                ),
                ConjugatedForm(
                    group="basic",
                    form="adverbial",
                    written=written + "に",
                    reading=reading + "に",
                ),
            ]
        )
        return tuple(forms)

    if adjective_class not in {"adj-i", "adj-ix"}:
        raise ValueError(f"Unsupported adjective class: {adjective_class}")

    if adjective_class == "adj-ix" and not reading.endswith(
        ("いい", "よい", "イイ", "ヨイ")
    ):
        raise ValueError(f"Unsupported ii/yoi reading: {reading!r}")

    written_forms = _i_adjective_forms(written, adjective_class)
    reading_forms = _i_adjective_forms(reading, adjective_class)

    return tuple(
        ConjugatedForm(
            group="basic",
            form=form,
            written=surface,
            reading=reading_forms[form],
        )
        for form, surface in written_forms.items()
    )
