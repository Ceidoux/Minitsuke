from dataclasses import dataclass


@dataclass(frozen=True)
class ConjugatedForm:
    group: str
    form: str
    written: str
    reading: str


# Negative, polite, conditional, volitional, te-form, past endings.
GODAN_ENDINGS = {
    "v5u": ("う", "わ", "い", "え", "お", "って", "った"),
    "v5k": ("く", "か", "き", "け", "こ", "いて", "いた"),
    "v5g": ("ぐ", "が", "ぎ", "げ", "ご", "いで", "いだ"),
    "v5s": ("す", "さ", "し", "せ", "そ", "して", "した"),
    "v5t": ("つ", "た", "ち", "て", "と", "って", "った"),
    "v5n": ("ぬ", "な", "に", "ね", "の", "んで", "んだ"),
    "v5b": ("ぶ", "ば", "び", "べ", "ぼ", "んで", "んだ"),
    "v5m": ("む", "ま", "み", "め", "も", "んで", "んだ"),
    "v5r": ("る", "ら", "り", "れ", "ろ", "って", "った"),
    "v5k-s": ("く", "か", "き", "け", "こ", "って", "った"),
}


def _require_ending(word: str, ending: str) -> str:
    if not word.endswith(ending):
        raise ValueError(f"{word!r} must end with {ending!r}")

    return word[: -len(ending)]


def _finite_forms(
    dictionary: str,
    polite_stem: str,
    negative: str,
    past: str,
) -> dict[str, str]:
    negative_stem = _require_ending(negative, "い")

    return {
        "nonpast": dictionary,
        "negative": negative,
        "past": past,
        "negative_past": negative_stem + "かった",
        "polite": polite_stem + "ます",
        "polite_negative": polite_stem + "ません",
        "polite_past": polite_stem + "ました",
        "polite_negative_past": polite_stem + "ませんでした",
    }


def _ichidan_finite_forms(word: str) -> dict[str, str]:
    stem = _require_ending(word, "る")
    return _finite_forms(word, stem, stem + "ない", stem + "た")


def _generate_surface_forms(
    word: str,
    verb_class: str,
) -> dict[tuple[str, str], str]:
    if not word:
        raise ValueError("Dictionary form must not be empty")

    if verb_class == "v1":
        stem = _require_ending(word, "る")
        polite_stem = stem
        negative = stem + "ない"
        te = stem + "て"
        past = stem + "た"
        conditional = stem + "れば"
        volitional = stem + "よう"
        imperatives = (stem + "ろ", stem + "よ")
        potential = stem + "られる"
        passive = stem + "られる"
        causative = stem + "させる"

    elif verb_class in GODAN_ENDINGS:
        ending, a, i, e, o, te_ending, past_ending = GODAN_ENDINGS[verb_class]
        stem = _require_ending(word, ending)
        polite_stem = stem + i
        negative = stem + a + "ない"
        te = stem + te_ending
        past = stem + past_ending
        conditional = stem + e + "ば"
        volitional = stem + o + "う"
        imperatives = (stem + e,)
        potential = stem + e + "る"
        passive = stem + a + "れる"
        causative = stem + a + "せる"

    elif verb_class == "vs-i":
        stem = _require_ending(word, "する")
        polite_stem = stem + "し"
        negative = stem + "しない"
        te = stem + "して"
        past = stem + "した"
        conditional = stem + "すれば"
        volitional = stem + "しよう"
        imperatives = (stem + "しろ", stem + "せよ")
        potential = stem + "できる"
        passive = stem + "される"
        causative = stem + "させる"

    elif verb_class == "vk":
        if word.endswith("くる"):
            stem = _require_ending(word, "くる")
            ki = stem + "き"
            ko = stem + "こ"
            kure = stem + "くれ"
        elif word.endswith("来る"):
            stem = _require_ending(word, "来る")
            ki = stem + "来"
            ko = stem + "来"
            kure = stem + "来れ"
        else:
            raise ValueError("Kuru verbs must end with くる or 来る")

        polite_stem = ki
        negative = ko + "ない"
        te = ki + "て"
        past = ki + "た"
        conditional = kure + "ば"
        volitional = ko + "よう"
        imperatives = (ko + "い",)
        potential = ko + "られる"
        passive = ko + "られる"
        causative = ko + "させる"

    else:
        raise ValueError(f"Unsupported verb class: {verb_class}")

    basic = _finite_forms(word, polite_stem, negative, past)
    negative_stem = _require_ending(negative, "い")

    basic.update(
        {
            "te": te,
            "negative_te": negative_stem + "くて",
            "without_doing": negative + "で",
            "conditional_ba": conditional,
            "negative_conditional_ba": negative_stem + "ければ",
            "conditional_tara": past + "ら",
            "negative_conditional_tara": negative_stem + "かったら",
            "volitional": volitional,
            "polite_volitional": polite_stem + "ましょう",
            "imperative": imperatives[0],
            "prohibitive": word + "な",
        }
    )

    if len(imperatives) > 1:
        basic["imperative_alternative"] = imperatives[1]

    results = {("basic", form): surface for form, surface in basic.items()}

    derived = {
        "potential": potential,
        "passive": passive,
        "causative": causative,
        "causative_passive": _require_ending(causative, "る") + "られる",
        "te_iru": te + "いる",
    }

    for group, dictionary in derived.items():
        for form, surface in _ichidan_finite_forms(dictionary).items():
            results[(group, form)] = surface

    return results


def conjugate_verb(
    written: str,
    reading: str,
    verb_class: str,
) -> tuple[ConjugatedForm, ...]:
    written_forms = _generate_surface_forms(written, verb_class)
    reading_forms = _generate_surface_forms(reading, verb_class)

    return tuple(
        ConjugatedForm(
            group=group,
            form=form,
            written=surface,
            reading=reading_forms[(group, form)],
        )
        for (group, form), surface in written_forms.items()
    )
