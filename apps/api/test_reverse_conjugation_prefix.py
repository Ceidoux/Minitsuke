import pytest

from reverse_conjugation import (
    ReverseCandidate,
    reverse_conjugate_prefix,
)


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
