from sqlalchemy.orm import Session

from conjugation_service import build_conjugation_tables
from japanese_text import normalize_written_form
from jmdict_entry_service import load_entries
from jmdict_exact_repository import ExactCandidate, find_exact_candidates
from reverse_conjugation import ReverseCandidate, reverse_conjugate

GROUP_LABELS = {
    "potential": "potential",
    "passive": "passive",
    "causative": "causative",
    "causative_passive": "causative-passive",
    "te_iru": "ている construction",
    "potential_colloquial": "potential — colloquial",
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

    group = GROUP_LABELS[candidate.group]
    return group if candidate.form == "nonpast" else f"{group}, {form}"


def find_generated_inflections(
    session: Session,
    text: str,
) -> tuple[tuple[ExactCandidate, ...], dict[int, list[str]]]:
    candidates = reverse_conjugate(text)

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

    query = normalize_written_form(text.strip())
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

                    confirmed = any(
                        item.group == candidate.group
                        and item.form == candidate.form
                        and query
                        in {
                            normalize_written_form(item.written),
                            normalize_written_form(item.reading),
                        }
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
