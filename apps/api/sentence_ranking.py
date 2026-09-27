from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet

from jmdict_exact_repository import ExactCandidate
from sentence_analysis import SentenceToken

# Start with categories confirmed by our current sentence examples.
# Unmapped categories receive no grammatical preference.
COMPATIBLE_LABELS: dict[str, frozenset[str]] = {
    "連体詞": frozenset(
        {
            "pre-noun adjectival (rentaishi)",
        }
    ),
    "助詞": frozenset(
        {
            "particle",
        }
    ),
    "助動詞": frozenset(
        {
            "auxiliary verb",
            "auxiliary adjective",
        }
    ),
    "動詞": frozenset(
        {
            "transitive verb",
            "intransitive verb",
            "auxiliary verb",
            "suru verb - included",
        }
    ),
}


def rank_sentence_candidates(
    token: SentenceToken,
    candidates: Sequence[ExactCandidate],
    *,
    labels_by_entry: Mapping[int, AbstractSet[str]],
    normalized_written_ids: AbstractSet[int],
    dictionary_form_ids: AbstractSet[int] = frozenset(),
    original_form_ids: AbstractSet[int] = frozenset(),
) -> tuple[ExactCandidate, ...]:
    category = token.part_of_speech[0] if token.part_of_speech else ""
    compatible_labels = COMPATIBLE_LABELS.get(category, frozenset())

    def ranking_key(
        candidate: ExactCandidate,
    ) -> tuple[bool, bool, bool, bool, int, bool, bool, int, int]:
        labels = labels_by_entry.get(candidate.entry_id, frozenset())

        grammatical_mismatch = bool(compatible_labels) and not (
            compatible_labels.intersection(labels)
        )

        return (
            grammatical_mismatch,
            candidate.entry_id not in original_form_ids,
            candidate.entry_id not in dictionary_form_ids,
            candidate.entry_id not in normalized_written_ids,
            candidate.match_tier,
            not candidate.is_common,
            candidate.frequency_band is None,
            candidate.frequency_band or 0,
            candidate.source_id,
        )

    return tuple(sorted(candidates, key=ranking_key))
