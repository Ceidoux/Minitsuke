from dataclasses import dataclass
from unicodedata import normalize

from sqlalchemy.orm import Session

from jmdict_exact_repository import ExactCandidate, find_exact_candidates
from sentence_analysis import SentenceAnalyzer, SentenceToken
from sentence_candidate_repository import (
    load_candidate_labels,
    load_candidate_spellings,
)
from sentence_ranking import rank_sentence_candidates


@dataclass(frozen=True)
class ResolvedToken:
    token: SentenceToken
    lookup_forms: tuple[str, ...]
    candidates: tuple[ExactCandidate, ...]


def token_lookup_forms(token: SentenceToken) -> tuple[str, ...]:
    if not token.surface.strip():
        return ()

    if token.part_of_speech and token.part_of_speech[0] in {
        "補助記号",
        "記号",
        "空白",
    }:
        return ()

    return tuple(
        dict.fromkeys(
            form.strip()
            for form in (
                token.dictionary_form,
                token.normalized_form,
            )
            if form.strip()
        )
    )


def resolve_sentence(
    session: Session,
    text: str,
    *,
    analyzer: SentenceAnalyzer,
) -> tuple[ResolvedToken, ...]:
    tokens = analyzer.analyze(text)
    forms_by_token = tuple(token_lookup_forms(token) for token in tokens)

    all_forms = tuple(dict.fromkeys(form for forms in forms_by_token for form in forms))

    matches = find_exact_candidates(session, all_forms) if all_forms else {}

    entry_ids = tuple(
        dict.fromkeys(
            candidate.entry_id
            for candidates in matches.values()
            for candidate in candidates
        )
    )
    labels_by_entry = load_candidate_labels(session, entry_ids)
    spellings_by_entry = load_candidate_spellings(session, entry_ids)

    resolved = []

    for token, forms in zip(tokens, forms_by_token, strict=True):
        unique_candidates: dict[int, ExactCandidate] = {}

        for form in forms:
            for candidate in matches.get(form, ()):
                previous = unique_candidates.get(candidate.entry_id)

                if previous is None or candidate.match_tier < previous.match_tier:
                    unique_candidates[candidate.entry_id] = candidate

        normalized_written_ids = {
            candidate.entry_id
            for candidate in matches.get(token.normalized_form.strip(), ())
            if candidate.match_tier == 0
        }
        dictionary_form_ids = {
            candidate.entry_id
            for candidate in matches.get(token.dictionary_form.strip(), ())
        }
        original_form = normalize("NFKC", token.surface)
        original_form_ids = {
            entry_id
            for entry_id in unique_candidates
            if original_form in spellings_by_entry.get(entry_id, frozenset())
        }
        ranked = rank_sentence_candidates(
            token,
            tuple(unique_candidates.values()),
            labels_by_entry=labels_by_entry,
            normalized_written_ids=normalized_written_ids,
            dictionary_form_ids=dictionary_form_ids,
            original_form_ids=original_form_ids,
        )

        resolved.append(
            ResolvedToken(
                token=token,
                lookup_forms=forms,
                candidates=ranked,
            )
        )

    return tuple(resolved)
