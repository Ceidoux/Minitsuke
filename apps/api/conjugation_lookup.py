from sqlalchemy.orm import Session

from conjugation_service import build_conjugation_tables
from copula_conjugation import resolve_copula_pronunciation
from japanese_text import normalize_written_form
from jmdict_entry_service import load_entries
from jmdict_exact_repository import ExactCandidate, find_exact_candidates
from reverse_conjugation import (
    ReverseCandidate,
    reverse_conjugate,
    reverse_conjugate_prefix,
)
from schemas import ConjugationCompletionResponse

GROUP_LABELS = {
    "potential": "potential",
    "passive": "passive",
    "causative": "causative",
    "causative_passive": "causative-passive",
    "te_iru": "ている construction",
    "potential_colloquial": "potential — colloquial",
    "te_iru_colloquial": "ている construction — colloquial",
    "te_oku": "ておく construction",
    "te_oku_colloquial": "ておく construction — colloquial",
    "te_shimau": "てしまう construction",
    "te_shimau_colloquial": "てしまう construction — colloquial",
}


def _lookup_forms(candidate: ReverseCandidate) -> tuple[str, ...]:
    base = candidate.dictionary_form

    if candidate.verb_class == "vs-i" and base.endswith("する"):
        noun = base[:-2]
        if noun:
            return (base, noun)

    return (base,)


def _description(candidate: ReverseCandidate) -> str:
    form = (
        "polite non-past"
        if candidate.form == "polite"
        else candidate.form.replace("_", " ")
    )

    if candidate.group == "basic":
        return form

    group = " → ".join(GROUP_LABELS[part] for part in candidate.group.split("+"))

    return group if candidate.form == "nonpast" else f"{group}, {form}"


def find_generated_inflections(
    session: Session,
    text: str,
    *,
    allow_copula_pronunciation: bool = False,
) -> tuple[tuple[ExactCandidate, ...], dict[int, list[str]]]:
    query = normalize_written_form(text.strip())
    copula_query = (
        resolve_copula_pronunciation(query) if allow_copula_pronunciation else None
    )

    candidates = reverse_conjugate(query)

    if copula_query is not None:
        alias_candidates = (
            candidate
            for candidate in reverse_conjugate(copula_query)
            if candidate.verb_class == "cop"
        )
        candidates = tuple(dict.fromkeys((*candidates, *alias_candidates)))

    if not candidates:
        return (), {}
    forms = tuple(
        dict.fromkeys(
            form for candidate in candidates for form in _lookup_forms(candidate)
        )
    )
    matches_by_form = find_exact_candidates(session, forms)
    entry_ids = tuple(
        dict.fromkeys(
            match.entry_id for matches in matches_by_form.values() for match in matches
        )
    )

    if not entry_ids:
        return (), {}

    tables_by_source = {
        entry.source_id: build_conjugation_tables(entry)[0]
        for entry in load_entries(session, entry_ids)
    }

    accepted: dict[int, ExactCandidate] = {}
    descriptions: dict[int, list[str]] = {}

    for candidate in candidates:
        base = normalize_written_form(candidate.dictionary_form)

        for lookup_form in _lookup_forms(candidate):
            for match in matches_by_form.get(lookup_form, ()):
                confirmed = False

                for table in tables_by_source.get(match.source_id, []):
                    if table.verb_class != candidate.verb_class:
                        continue

                    if base not in {
                        normalize_written_form(table.written),
                        normalize_written_form(table.reading),
                    }:
                        continue

                    accepted_queries = {query}
                    if candidate.verb_class == "cop" and copula_query is not None:
                        accepted_queries.add(copula_query)

                    confirmed = any(
                        item.group == candidate.group
                        and item.form == candidate.form
                        and bool(
                            accepted_queries
                            & {
                                normalize_written_form(item.written),
                                normalize_written_form(item.reading),
                            }
                        )
                        for item in table.forms
                    )

                    if confirmed:
                        break

                if not confirmed:
                    continue

                previous = accepted.get(match.entry_id)
                if previous is None or match.match_tier < previous.match_tier:
                    accepted[match.entry_id] = match

                explanation = _description(candidate)
                entry_descriptions = descriptions.setdefault(match.source_id, [])
                if explanation not in entry_descriptions:
                    entry_descriptions.append(explanation)

    ranked = tuple(
        sorted(
            accepted.values(),
            key=lambda match: (
                match.match_tier,
                not match.is_common,
                match.frequency_band is None,
                match.frequency_band or 0,
                match.source_id,
            ),
        )
    )

    return ranked, descriptions


def find_conjugation_completions(
    session: Session,
    prefixes: dict[str, bool],
    *,
    exclude_source_ids: tuple[int, ...] = (),
) -> tuple[
    tuple[ExactCandidate, ...],
    dict[int, list[ConjugationCompletionResponse]],
]:
    # True permits an exact kana match when the kana was obtained
    # by completing an unfinished romaji syllable.
    candidate_prefixes: dict[
        ReverseCandidate,
        set[tuple[str, bool]],
    ] = {}

    for text, allow_equal in prefixes.items():
        prefix = normalize_written_form(text.strip())

        if (
            not prefix
            or len(prefix) > 1000
            or any(character.isspace() for character in prefix)
        ):
            continue

        candidates = reverse_conjugate_prefix(prefix)

        if allow_equal:
            candidates = (*candidates, *reverse_conjugate(prefix))

        for candidate in candidates:
            candidate_prefixes.setdefault(candidate, set()).add((prefix, allow_equal))

    if not candidate_prefixes:
        return (), {}

    lookup_forms = tuple(
        dict.fromkeys(
            form
            for candidate in candidate_prefixes
            for form in _lookup_forms(candidate)
        )
    )
    matches_by_form = find_exact_candidates(session, lookup_forms)
    excluded = set(exclude_source_ids)

    entry_ids = tuple(
        dict.fromkeys(
            match.entry_id
            for matches in matches_by_form.values()
            for match in matches
            if match.source_id not in excluded
        )
    )

    if not entry_ids:
        return (), {}

    tables_by_source = {
        entry.source_id: build_conjugation_tables(entry)[0]
        for entry in load_entries(session, entry_ids)
    }

    accepted: dict[int, ExactCandidate] = {}
    completions: dict[
        int,
        dict[tuple[str, str, str, str], ConjugationCompletionResponse],
    ] = {}

    for candidate, possible_prefixes in candidate_prefixes.items():
        base = normalize_written_form(candidate.dictionary_form)

        for lookup_form in _lookup_forms(candidate):
            for match in matches_by_form.get(lookup_form, ()):
                if match.source_id in excluded:
                    continue

                for table in tables_by_source.get(match.source_id, ()):
                    if table.verb_class != candidate.verb_class:
                        continue

                    if base not in {
                        normalize_written_form(table.written),
                        normalize_written_form(table.reading),
                    }:
                        continue

                    for item in table.forms:
                        if item.group != candidate.group or item.form != candidate.form:
                            continue

                        surfaces = {
                            normalize_written_form(item.written),
                            normalize_written_form(item.reading),
                        }

                        confirmed = any(
                            surface.startswith(prefix)
                            and (allow_equal or surface != prefix)
                            for surface in surfaces
                            for prefix, allow_equal in possible_prefixes
                        )

                        if not confirmed:
                            continue

                        previous = accepted.get(match.entry_id)
                        if previous is None or match.match_tier < previous.match_tier:
                            accepted[match.entry_id] = match

                        key = (
                            item.written,
                            item.reading,
                            item.group,
                            item.form,
                        )
                        completions.setdefault(match.source_id, {})[key] = (
                            ConjugationCompletionResponse(
                                written=item.written,
                                reading=item.reading,
                                group=item.group,
                                form=item.form,
                                description=_description(candidate),
                            )
                        )

    ranked = tuple(
        sorted(
            accepted.values(),
            key=lambda match: (
                match.match_tier,
                not match.is_common,
                match.frequency_band is None,
                match.frequency_band or 0,
                match.source_id,
            ),
        )
    )

    return ranked, {
        source_id: sorted(
            items.values(),
            key=lambda item: (
                len(item.reading),
                item.reading,
                item.written,
                item.group,
                item.form,
            ),
        )
        for source_id, items in completions.items()
    }
