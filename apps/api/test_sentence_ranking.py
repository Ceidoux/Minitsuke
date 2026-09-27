import pytest

from jmdict_exact_repository import ExactCandidate
from sentence_analysis import SentenceToken
from sentence_ranking import rank_sentence_candidates


def make_token(category: str) -> SentenceToken:
    return SentenceToken(
        surface="test",
        start=0,
        end=4,
        dictionary_form="test",
        normalized_form="test",
        reading="",
        part_of_speech=(category, "*", "*", "*", "*", "*"),
        is_unknown=False,
    )


def make_candidate(
    entry_id: int,
    *,
    is_common: bool = False,
    frequency_band: int | None = None,
    match_tier: int = 1,
) -> ExactCandidate:
    return ExactCandidate(
        entry_id=entry_id,
        source_id=entry_id + 1_000_000,
        match_tier=match_tier,
        is_common=is_common,
        frequency_band=frequency_band,
    )


@pytest.mark.parametrize(
    ("category", "compatible_label", "other_label"),
    [
        ("連体詞", "pre-noun adjectival (rentaishi)", "numeric"),
        ("助詞", "particle", "numeric"),
        ("助詞", "particle", "noun (common) (futsuumeishi)"),
        ("助動詞", "auxiliary verb", "noun (common) (futsuumeishi)"),
        ("助動詞", "auxiliary adjective", "suffix"),
        ("動詞", "transitive verb", "noun (common) (futsuumeishi)"),
    ],
)
def test_grammar_outweighs_commonness(
    category,
    compatible_label,
    other_label,
):
    common_mismatch = make_candidate(
        1,
        is_common=True,
        frequency_band=1,
    )
    grammatical_match = make_candidate(2)

    ranked = rank_sentence_candidates(
        make_token(category),
        (common_mismatch, grammatical_match),
        labels_by_entry={
            1: {other_label},
            2: {compatible_label},
        },
        normalized_written_ids=set(),
    )

    assert ranked == (grammatical_match, common_mismatch)


def test_normalized_written_form_breaks_grammatical_tie():
    other_verb = make_candidate(
        1,
        is_common=True,
        frequency_band=1,
    )
    normalized_verb = make_candidate(2)

    ranked = rank_sentence_candidates(
        make_token("動詞"),
        (other_verb, normalized_verb),
        labels_by_entry={
            1: {"transitive verb"},
            2: {"suru verb - included", "transitive verb"},
        },
        normalized_written_ids={2},
    )

    assert ranked == (normalized_verb, other_verb)


def test_grammar_precedes_normalized_written_form():
    normalized_noun = make_candidate(1)
    particle = make_candidate(2)

    ranked = rank_sentence_candidates(
        make_token("助詞"),
        (normalized_noun, particle),
        labels_by_entry={
            1: {"noun (common) (futsuumeishi)"},
            2: {"particle"},
        },
        normalized_written_ids={1},
    )

    assert ranked == (particle, normalized_noun)


def test_unmapped_category_preserves_commonness_and_frequency_ranking():
    uncommon = make_candidate(1, frequency_band=1)
    common_without_band = make_candidate(2, is_common=True)
    common_band_three = make_candidate(
        3,
        is_common=True,
        frequency_band=3,
    )
    common_band_two = make_candidate(
        4,
        is_common=True,
        frequency_band=2,
    )

    ranked = rank_sentence_candidates(
        make_token("未対応"),
        (
            uncommon,
            common_without_band,
            common_band_three,
            common_band_two,
        ),
        labels_by_entry={},
        normalized_written_ids=set(),
    )

    assert ranked == (
        common_band_two,
        common_band_three,
        common_without_band,
        uncommon,
    )


def test_written_match_precedes_reading_match_when_other_evidence_ties():
    reading_match = make_candidate(1, is_common=True)
    written_match = make_candidate(2, match_tier=0)

    ranked = rank_sentence_candidates(
        make_token("未対応"),
        (reading_match, written_match),
        labels_by_entry={},
        normalized_written_ids=set(),
    )

    assert ranked == (written_match, reading_match)


def test_missing_labels_keeps_candidate_as_an_alternative():
    unknown_grammar = make_candidate(1)
    particle = make_candidate(2)

    ranked = rank_sentence_candidates(
        make_token("助詞"),
        (unknown_grammar, particle),
        labels_by_entry={2: {"particle"}},
        normalized_written_ids=set(),
    )

    assert ranked == (particle, unknown_grammar)
