from dataclasses import dataclass
from functools import lru_cache

from conjugation import GODAN_ENDINGS, conjugate_verb
from copula_conjugation import conjugate_copula
from japanese_text import normalize_written_form


@dataclass(frozen=True)
class ReverseCandidate:
    dictionary_form: str
    verb_class: str
    group: str
    form: str


@dataclass(frozen=True)
class ReverseRule:
    surface_ending: str
    dictionary_ending: str
    verb_class: str
    group: str
    form: str


@lru_cache(maxsize=1)
def _reverse_rules() -> tuple[ReverseRule, ...]:
    # The marker stands for the unchanged beginning of a verb.
    marker = "仮"

    patterns = [
        ("v1", "る"),
        *((verb_class, endings[0]) for verb_class, endings in GODAN_ENDINGS.items()),
        ("vs-i", "する"),
        ("vk", "くる"),
        ("vk", "来る"),
    ]

    rules = []

    for verb_class, dictionary_ending in patterns:
        template = marker + dictionary_ending

        # We only use the written output here. Kana and kanji kuru
        # templates are handled separately.
        generated = conjugate_verb(template, template, verb_class)

        for item in generated:
            if item.group == "basic" and item.form == "nonpast":
                continue

            if not item.written.startswith(marker):
                raise ValueError("Conjugation rule changed the template stem")

            surface_ending = item.written[len(marker) :]

            if not surface_ending:
                raise ValueError("Conjugation rule produced an empty ending")

            rules.append(
                ReverseRule(
                    surface_ending=surface_ending,
                    dictionary_ending=dictionary_ending,
                    verb_class=verb_class,
                    group=item.group,
                    form=item.form,
                )
            )

    return tuple(
        sorted(
            rules,
            key=lambda rule: (
                -len(rule.surface_ending),
                rule.verb_class,
                rule.group,
                rule.form,
            ),
        )
    )


@lru_cache(maxsize=1)
def _copula_reverse_index() -> dict[str, tuple[ReverseCandidate, ...]]:
    candidates_by_surface: dict[str, dict[ReverseCandidate, None]] = {}

    pairs = (
        ("だ", "だ"),
        ("です", "です"),
        ("である", "である"),
        ("でございます", "でございます"),
        ("で御座います", "でございます"),
    )

    for written, reading in pairs:
        for item in conjugate_copula(written, reading):
            candidate = ReverseCandidate(
                dictionary_form=reading,
                verb_class="cop",
                group=item.group,
                form=item.form,
            )

            for surface in (item.written, item.reading):
                normalized = normalize_written_form(surface)

                # An unchanged dictionary form needs no inflection match.
                if normalized in {
                    normalize_written_form(written),
                    normalize_written_form(reading),
                }:
                    continue

                candidates_by_surface.setdefault(normalized, {})[candidate] = None

    return {
        surface: tuple(candidates)
        for surface, candidates in candidates_by_surface.items()
    }


def reverse_conjugate(text: str) -> tuple[ReverseCandidate, ...]:
    cleaned = normalize_written_form(text.strip())

    if not cleaned or any(character.isspace() for character in cleaned):
        return ()

    candidates: dict[ReverseCandidate, None] = dict.fromkeys(
        _copula_reverse_index().get(cleaned, ())
    )

    for rule in _reverse_rules():
        if not cleaned.endswith(rule.surface_ending):
            continue

        stem = cleaned[: -len(rule.surface_ending)]

        # Regular verbs need a stem. Standalone する and 来る do not.
        if not stem and rule.verb_class not in {"vs-i", "vk"}:
            continue

        candidate = ReverseCandidate(
            dictionary_form=stem + rule.dictionary_ending,
            verb_class=rule.verb_class,
            group=rule.group,
            form=rule.form,
        )
        candidates[candidate] = None

    return tuple(candidates)
