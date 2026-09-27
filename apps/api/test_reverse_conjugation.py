import pytest

from reverse_conjugation import ReverseCandidate, reverse_conjugate


@pytest.mark.parametrize(
    ("query", "dictionary_form", "verb_class", "group", "form"),
    [
        (
            "でかけられる",
            "でかける",
            "v1",
            "potential",
            "nonpast",
        ),
        (
            "出かけられる",
            "出かける",
            "v1",
            "passive",
            "nonpast",
        ),
        (
            "食べません",
            "食べる",
            "v1",
            "basic",
            "polite_negative",
        ),
        (
            "食べませんでした",
            "食べる",
            "v1",
            "basic",
            "polite_negative_past",
        ),
        (
            "書ける",
            "書く",
            "v5k",
            "potential",
            "nonpast",
        ),
        (
            "書けません",
            "書く",
            "v5k",
            "potential",
            "polite_negative",
        ),
        (
            "行った",
            "行く",
            "v5k-s",
            "basic",
            "past",
        ),
        (
            "できる",
            "する",
            "vs-i",
            "potential",
            "nonpast",
        ),
        (
            "来ない",
            "来る",
            "vk",
            "basic",
            "negative",
        ),
        (
            "こられます",
            "くる",
            "vk",
            "potential",
            "polite",
        ),
        (
            "確認しました",
            "確認する",
            "vs-i",
            "basic",
            "polite_past",
        ),
        (
            "食べさせられました",
            "食べる",
            "v1",
            "causative_passive",
            "polite_past",
        ),
        (
            "食べていませんでした",
            "食べる",
            "v1",
            "te_iru",
            "polite_negative_past",
        ),
    ],
)
def test_proposes_expected_base_and_interpretation(
    query: str,
    dictionary_form: str,
    verb_class: str,
    group: str,
    form: str,
):
    expected = ReverseCandidate(
        dictionary_form=dictionary_form,
        verb_class=verb_class,
        group=group,
        form=form,
    )

    assert expected in reverse_conjugate(query)


def test_preserves_ambiguous_interpretations():
    candidates = reverse_conjugate("でかけられる")

    groups = {
        candidate.group
        for candidate in candidates
        if candidate.dictionary_form == "でかける"
        and candidate.verb_class == "v1"
        and candidate.form == "nonpast"
    }

    assert groups == {"potential", "passive"}


def test_normalizes_katakana():
    assert reverse_conjugate("デカケラレル") == reverse_conjugate("でかけられる")


@pytest.mark.parametrize("query", ["", "   ", "食べ ました", "学校"])
def test_rejects_empty_spaced_or_unmatched_input(query: str):
    assert reverse_conjugate(query) == ()


def test_reverses_colloquial_potential_without_passive_interpretation():
    candidates = reverse_conjugate("出れる")

    interpretations = {
        (candidate.group, candidate.form)
        for candidate in candidates
        if candidate.dictionary_form == "出る" and candidate.verb_class == "v1"
    }

    assert interpretations == {("potential_colloquial", "nonpast")}
