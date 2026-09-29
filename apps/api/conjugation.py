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


def _ichidan_derived_forms(word: str) -> dict[str, str]:
    stem = _require_ending(word, "る")
    forms = _finite_forms(word, stem, stem + "ない", stem + "た")

    forms.update(
        {
            "te": stem + "て",
            "negative_te": stem + "なくて",
            "without_doing": stem + "ないで",
            "conditional_ba": stem + "れば",
            "negative_conditional_ba": stem + "なければ",
            "conditional_tara": stem + "たら",
            "negative_conditional_tara": stem + "なかったら",
        }
    )

    return forms


def _kureru_forms(word: str) -> dict[tuple[str, str], str]:
    stem = _require_ending(word, "る")
    forms = _generate_surface_forms(word, "v1")

    forms[("basic", "imperative")] = stem
    forms.pop(("basic", "imperative_alternative"), None)

    return forms


def _honorific_aru_forms(word: str) -> dict[tuple[str, str], str]:
    stem = _require_ending(word, "る")
    forms = _generate_surface_forms(word, "v5r")
    polite_stem = stem + "い"

    polite_endings = {
        "polite": "ます",
        "polite_negative": "ません",
        "polite_past": "ました",
        "polite_negative_past": "ませんでした",
        "polite_volitional": "ましょう",
    }

    for form, ending in polite_endings.items():
        forms[("basic", form)] = polite_stem + ending

    forms[("basic", "imperative")] = polite_stem

    return forms


def _aru_forms(word: str) -> dict[tuple[str, str], str]:
    ending = next(
        (
            candidate
            for candidate in ("ある", "有る", "在る")
            if word.endswith(candidate)
        ),
        None,
    )

    if ending is None:
        raise ValueError("Aru verbs must end with ある, 有る, or 在る")

    prefix = _require_ending(word, ending)

    # Reuse the regular affirmative forms, but do not automatically
    # generate the ordinary verb's voice and progressive groups.
    forms = {
        key: surface
        for key, surface in _generate_surface_forms(word, "v5r").items()
        if key[0] == "basic"
    }

    negative_forms = {
        "negative": "ない",
        "negative_past": "なかった",
        "negative_te": "なくて",
        "without_doing": "ないで",
        "negative_conditional_ba": "なければ",
        "negative_conditional_tara": "なかったら",
    }

    for form, ending in negative_forms.items():
        forms[("basic", form)] = prefix + ending

    return forms


def _zuru_forms(word: str) -> dict[tuple[str, str], str]:
    stem = _require_ending(word, "ずる")
    forms = _generate_surface_forms(stem + "じる", "v1")

    forms[("basic", "nonpast")] = word
    forms[("basic", "conditional_ba")] = stem + "ずれば"
    forms[("basic", "conditional_ba_alternative")] = stem + "じれば"
    forms[("basic", "imperative_alternative")] = stem + "ぜよ"
    forms[("basic", "prohibitive")] = word + "な"

    return forms


def _special_suru_forms(word: str) -> dict[tuple[str, str], str]:
    stem = _require_ending(word, "する")
    regular = _generate_surface_forms(word, "vs-i")

    shared_forms = {
        "nonpast",
        "past",
        "polite",
        "polite_negative",
        "polite_past",
        "polite_negative_past",
        "te",
        "conditional_ba",
        "conditional_tara",
        "polite_volitional",
        "prohibitive",
    }

    forms = {
        key: surface
        for key, surface in regular.items()
        if key[0] == "basic" and key[1] in shared_forms
    }

    forms[("basic", "imperative_formal")] = stem + "せよ"

    return forms


def _aisuru_forms(word: str) -> dict[tuple[str, str], str]:
    if not word.endswith(("愛する", "あいする")):
        raise ValueError("Aisuru forms require 愛する or あいする")

    stem = _require_ending(word, "する")

    # 愛す supplies 愛さない, 愛そう, 愛せ, and 愛せる.
    forms = _generate_surface_forms(stem + "す", "v5s")

    forms[("basic", "nonpast")] = word
    forms[("basic", "conditional_ba")] = stem + "すれば"
    forms[("basic", "conditional_ba_alternative")] = stem + "せば"
    forms[("basic", "imperative_formal")] = stem + "せよ"
    forms[("basic", "prohibitive")] = word + "な"

    return forms


def _godan_derived_forms(
    word: str,
    verb_class: str,
) -> dict[str, str]:
    ending, a, i, e, _, te_ending, past_ending = GODAN_ENDINGS[verb_class]
    stem = _require_ending(word, ending)
    negative = stem + a + "ない"
    past = stem + past_ending

    forms = _finite_forms(word, stem + i, negative, past)
    negative_stem = _require_ending(negative, "い")

    forms.update(
        {
            "te": stem + te_ending,
            "negative_te": negative_stem + "くて",
            "without_doing": negative + "で",
            "conditional_ba": stem + e + "ば",
            "negative_conditional_ba": negative_stem + "ければ",
            "conditional_tara": past + "ら",
            "negative_conditional_tara": negative_stem + "かったら",
        }
    )

    return forms


def _te_auxiliary_forms(te: str) -> dict[tuple[str, str], str]:
    if te.endswith("て"):
        contracted_oku = te[:-1] + "とく"
        contracted_shimau = te[:-1] + "ちゃう"
    elif te.endswith("で"):
        contracted_oku = te[:-1] + "どく"
        contracted_shimau = te[:-1] + "じゃう"
    else:
        raise ValueError("Te-form must end with て or で")

    constructions = (
        ("te_iru_colloquial", te + "る", "v1"),
        ("te_oku", te + "おく", "v5k"),
        ("te_oku_colloquial", contracted_oku, "v5k"),
        ("te_shimau", te + "しまう", "v5u"),
        ("te_shimau_colloquial", contracted_shimau, "v5u"),
    )

    results = {}

    for group, dictionary, verb_class in constructions:
        forms = (
            _ichidan_derived_forms(dictionary)
            if verb_class == "v1"
            else _godan_derived_forms(dictionary, verb_class)
        )

        for form, surface in forms.items():
            results[(group, form)] = surface

    return results


def _generate_surface_forms(
    word: str,
    verb_class: str,
) -> dict[tuple[str, str], str]:
    if not word:
        raise ValueError("Dictionary form must not be empty")

    if verb_class == "v1-s":
        return _kureru_forms(word)

    if verb_class == "v5aru":
        return _honorific_aru_forms(word)

    if verb_class == "v5r-i":
        return _aru_forms(word)

    if verb_class == "vz":
        return _zuru_forms(word)

    if verb_class == "vs-s":
        return _special_suru_forms(word)

    if verb_class == "vs-s-aisu":
        return _aisuru_forms(word)

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
    if verb_class == "v1":
        derived["potential_colloquial"] = _require_ending(word, "る") + "れる"
    elif verb_class == "vk":
        derived["potential_colloquial"] = ko + "れる"
    for group, dictionary in derived.items():
        for form, surface in _ichidan_derived_forms(dictionary).items():
            results[(group, form)] = surface

    results.update(_te_auxiliary_forms(te))

    voice_groups = (
        "potential",
        "passive",
        "causative",
        "causative_passive",
        "potential_colloquial",
    )

    for voice_group in voice_groups:
        dictionary = derived.get(voice_group)
        if dictionary is None:
            continue

        derived_te = _require_ending(dictionary, "る") + "て"

        for form, surface in _ichidan_derived_forms(derived_te + "いる").items():
            results[(f"{voice_group}+te_iru", form)] = surface

        for (auxiliary_group, form), surface in _te_auxiliary_forms(derived_te).items():
            combined_group = f"{voice_group}+{auxiliary_group}"
            results[(combined_group, form)] = surface

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
