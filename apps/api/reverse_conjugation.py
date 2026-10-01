from dataclasses import dataclass
from functools import lru_cache

from adjective_conjugation import conjugate_adjective
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

    verb_patterns = [
        ("v1", "る"),
        ("v1-s", "くれる"),
        ("v1-s", "呉れる"),
        ("vz", "ずる"),
        ("v5aru", "る"),
        ("v5r-i", "ある"),
        ("v5r-i", "有る"),
        ("v5r-i", "在る"),
        *((verb_class, endings[0]) for verb_class, endings in GODAN_ENDINGS.items()),
        ("vs-i", "する"),
        ("vs-s", "する"),
        ("vs-s-aisu", "愛する"),
        ("vs-s-aisu", "あいする"),
        ("vk", "くる"),
        ("vk", "来る"),
    ]

    rules = []

    for verb_class, dictionary_ending in verb_patterns:
        template = marker + dictionary_ending
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

    for rule in (*_reverse_rules(), *_adjective_reverse_rules()):
        if not cleaned.endswith(rule.surface_ending):
            continue

        stem = cleaned[: -len(rule.surface_ending)]

        # These classes have rules covering the complete standalone word.
        if not stem and rule.verb_class not in {
            "vs-i",
            "vk",
            "adj-ix",
            "v1-s",
            "v5r-i",
            "vs-s-aisu",
        }:
            continue

        candidate = ReverseCandidate(
            dictionary_form=stem + rule.dictionary_ending,
            verb_class=rule.verb_class,
            group=rule.group,
            form=rule.form,
        )
        candidates[candidate] = None

    return tuple(candidates)


@lru_cache(maxsize=1)
def _reverse_prefix_index() -> dict[str, tuple[tuple[int, ReverseRule], ...]]:
    rules_by_prefix: dict[str, list[tuple[int, ReverseRule]]] = {}

    for order, rule in enumerate((*_reverse_rules(), *_adjective_reverse_rules())):
        # Include an empty ending for bare stems, but leave at least
        # one character of the generated ending untyped.
        for typed_length in range(len(rule.surface_ending)):
            prefix = rule.surface_ending[:typed_length]
            rules_by_prefix.setdefault(prefix, []).append((order, rule))

    return {prefix: tuple(rules) for prefix, rules in rules_by_prefix.items()}


def reverse_conjugate_prefix(text: str) -> tuple[ReverseCandidate, ...]:
    cleaned = normalize_written_form(text.strip())

    if (
        not cleaned
        or len(cleaned) > 1000
        or any(character.isspace() for character in cleaned)
    ):
        return ()

    candidates: dict[ReverseCandidate, None] = {}

    # Copulas have complete surface forms rather than reusable stems.
    for surface, surface_candidates in _copula_reverse_index().items():
        if surface != cleaned and surface.startswith(cleaned):
            for candidate in surface_candidates:
                candidates[candidate] = None

    index = _reverse_prefix_index()
    matching_rules = []

    for typed_length in range(len(cleaned) + 1):
        typed_ending = cleaned[-typed_length:] if typed_length else ""
        matching_rules.extend(
            (order, typed_length, rule) for order, rule in index.get(typed_ending, ())
        )

    # Restore rule order, then typed length, to preserve candidate ordering.
    for _, typed_length, rule in sorted(matching_rules):
        stem = cleaned[:-typed_length] if typed_length else cleaned

        if not stem and rule.verb_class not in {
            "vs-i",
            "vk",
            "adj-ix",
            "v1-s",
            "v5r-i",
            "vs-s-aisu",
        }:
            continue

        candidate = ReverseCandidate(
            dictionary_form=stem + rule.dictionary_ending,
            verb_class=rule.verb_class,
            group=rule.group,
            form=rule.form,
        )
        candidates[candidate] = None

    return tuple(candidates)


@lru_cache(maxsize=1)
def _adjective_reverse_rules() -> tuple[ReverseRule, ...]:
    marker = "仮"

    adjective_patterns = (
        ("adj-i", "い", "い"),
        ("adj-ix", "いい", "いい"),
        ("adj-ix", "よい", "よい"),
        ("adj-ix", "い", "よい"),
        ("adj-na", "", ""),
    )

    rules: dict[ReverseRule, None] = {}

    for adjective_class, written_ending, reading_ending in adjective_patterns:
        template = marker + written_ending
        generated = conjugate_adjective(
            template,
            marker + reading_ending,
            adjective_class,
        )

        for item in generated:
            if item.written == template:
                continue

            if not item.written.startswith(marker):
                raise ValueError("Adjective rule changed the template stem")

            surface_ending = normalize_written_form(item.written[len(marker) :])

            if not surface_ending:
                raise ValueError("Adjective rule produced an empty ending")

            rule = ReverseRule(
                surface_ending=surface_ending,
                dictionary_ending=written_ending,
                verb_class=adjective_class,
                group=item.group,
                form=item.form,
            )
            rules[rule] = None

    return tuple(rules)
