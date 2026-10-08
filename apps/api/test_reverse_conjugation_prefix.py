import pytest

from japanese_text import normalize_written_form
from reverse_conjugation import (
    ReverseCandidate,
    _adjective_reverse_rules,
    _copula_reverse_index,
    _reverse_rules,
    reverse_conjugate_prefix,
)
from romaji import interpret_romaji


@pytest.mark.parametrize(
    ("query", "dictionary_form", "verb_class", "group", "form"),
    [
        ("たかくな", "たかい", "adj-i", "basic", "negative"),
        ("高くな", "高い", "adj-i", "basic", "negative"),
        ("タカクナ", "たかい", "adj-i", "basic", "negative"),
        ("よかっ", "いい", "adj-ix", "basic", "past"),
        ("かっこよかっ", "かっこいい", "adj-ix", "basic", "past"),
        ("静かじゃな", "静か", "adj-na", "basic", "negative_colloquial"),
        ("食べ", "食べる", "v1", "basic", "polite"),
        ("食べま", "食べる", "v1", "basic", "polite"),
        (
            "食べませんで",
            "食べる",
            "v1",
            "basic",
            "polite_negative_past",
        ),
        ("書けま", "書く", "v5k", "potential", "polite"),
        (
            "食べさせられま",
            "食べる",
            "v1",
            "causative_passive",
            "polite",
        ),
        (
            "ではありませ",
            "です",
            "cop",
            "basic",
            "polite_negative",
        ),
    ],
)
def test_finds_possible_conjugation_completions(
    query: str,
    dictionary_form: str,
    verb_class: str,
    group: str,
    form: str,
):
    candidates = reverse_conjugate_prefix(query)

    assert (
        ReverseCandidate(
            dictionary_form=dictionary_form,
            verb_class=verb_class,
            group=group,
            form=form,
        )
        in candidates
    )


def test_keeps_multiple_possible_completions():
    candidates = reverse_conjugate_prefix("たかくな")

    matching_forms = {
        candidate.form
        for candidate in candidates
        if candidate.dictionary_form == "たかい"
        and candidate.verb_class == "adj-i"
        and candidate.group == "basic"
    }

    assert {"negative", "negative_past"} <= matching_forms


def test_complete_form_is_not_its_own_prefix_match():
    candidates = reverse_conjugate_prefix("たかくない")

    assert (
        ReverseCandidate(
            dictionary_form="たかい",
            verb_class="adj-i",
            group="basic",
            form="negative",
        )
        not in candidates
    )

    # It can still be the beginning of a longer form.
    assert (
        ReverseCandidate(
            dictionary_form="たかい",
            verb_class="adj-i",
            group="basic",
            form="polite_negative",
        )
        in candidates
    )


def test_prefix_candidates_are_unique():
    candidates = reverse_conjugate_prefix("食べま")

    assert len(candidates) == len(set(candidates))


@pytest.mark.parametrize(
    "query",
    ["", "   ", "食べ ま", "食べ\nま", "あ" * 1001],
)
def test_rejects_invalid_prefix_input(query: str):
    assert reverse_conjugate_prefix(query) == ()


def _scan_prefix_candidates(text: str) -> tuple[ReverseCandidate, ...]:
    """Keep the original rule scan as an independent regression oracle."""
    cleaned = normalize_written_form(text.strip())
    candidates: dict[ReverseCandidate, None] = {}

    for surface, surface_candidates in _copula_reverse_index().items():
        if surface != cleaned and surface.startswith(cleaned):
            candidates.update(dict.fromkeys(surface_candidates))

    for rule in (*_reverse_rules(), *_adjective_reverse_rules()):
        maximum_typed_length = min(len(cleaned), len(rule.surface_ending) - 1)

        for typed_length in range(maximum_typed_length + 1):
            if typed_length and not cleaned.endswith(
                rule.surface_ending[:typed_length]
            ):
                continue

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

            candidates[
                ReverseCandidate(
                    dictionary_form=stem + rule.dictionary_ending,
                    verb_class=rule.verb_class,
                    group=rule.group,
                    form=rule.form,
                )
            ] = None

    return tuple(candidates)


@pytest.mark.parametrize(
    "query",
    tuple(
        dict.fromkeys(
            (
                "食べ",
                "食べま",
                " 食べま ",
                "タベマ",
                "ﾀﾍﾞﾏ",
                "高くな",
                "たかくない",
                "よかっ",
                "かっこよかっ",
                "静かじゃな",
                "書けま",
                "行かなかっ",
                "来られま",
                "くれ",
                "ございま",
                "ありませ",
                "愛しま",
                "あいさな",
                "論じま",
                "食べさせられま",
                "食べられちゃっ",
                "食べさせておきま",
                "ではありませ",
                "だ",
                "で",
                "し",
                "く",
                "よ",
                "ま",
                "ます",
                "ぬ",
                "あ" * 1000,
                *(
                    prefix
                    for romaji in ("tabemas", "takakun", "shizukajan")
                    for prefix in interpret_romaji(romaji).completion_prefixes
                ),
            )
        )
    ),
)
def test_index_preserves_all_candidates_and_their_order(query: str):
    assert reverse_conjugate_prefix(query) == _scan_prefix_candidates(query)


def test_index_matches_scan_at_each_partial_ending_length():
    representative_rules = (
        ("v1", "basic", "polite_negative_past"),
        ("v5k", "potential", "polite"),
        ("vs-s-aisu", "basic", "negative"),
        ("vk", "basic", "polite"),
        ("adj-ix", "basic", "past"),
        ("adj-na", "basic", "negative_colloquial"),
    )
    rules = (*_reverse_rules(), *_adjective_reverse_rules())

    for verb_class, group, form in representative_rules:
        rule = next(
            rule
            for rule in rules
            if (rule.verb_class, rule.group, rule.form) == (verb_class, group, form)
        )
        for typed_length in range(len(rule.surface_ending) + 1):
            # Check both an ordinary stem and an empty standalone stem.
            for stem in ("仮", ""):
                query = stem + rule.surface_ending[:typed_length]
                if query:
                    assert reverse_conjugate_prefix(query) == _scan_prefix_candidates(
                        query
                    )
