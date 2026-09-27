from dataclasses import dataclass

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from japanese_text import normalize_reading, normalize_written_form
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictWrittenFormRecord,
)


@dataclass(frozen=True)
class ExactCandidate:
    entry_id: int
    source_id: int
    match_tier: int
    is_common: bool
    frequency_band: int | None


def find_exact_candidates(
    session: Session,
    forms: tuple[str, ...],
) -> dict[str, tuple[ExactCandidate, ...]]:
    terms = tuple(dict.fromkeys(form.strip() for form in forms if form.strip()))

    if not terms:
        return {}

    written_keys = tuple(dict.fromkeys(normalize_written_form(term) for term in terms))
    reading_keys = tuple(dict.fromkeys(normalize_reading(term) for term in terms))

    written_matches = (
        select(
            JmdictWrittenFormRecord.search_text.label("matched_text"),
            JmdictEntryRecord.id.label("entry_id"),
            JmdictEntryRecord.source_id,
            literal(0).label("match_tier"),
            JmdictEntryRecord.is_common,
            JmdictEntryRecord.frequency_band,
        )
        .join(
            JmdictEntryRecord,
            JmdictEntryRecord.id == JmdictWrittenFormRecord.entry_id,
        )
        .where(JmdictWrittenFormRecord.search_text.in_(written_keys))
    )

    reading_matches = (
        select(
            JmdictReadingRecord.search_text.label("matched_text"),
            JmdictEntryRecord.id.label("entry_id"),
            JmdictEntryRecord.source_id,
            literal(1).label("match_tier"),
            JmdictEntryRecord.is_common,
            JmdictEntryRecord.frequency_band,
        )
        .join(
            JmdictEntryRecord,
            JmdictEntryRecord.id == JmdictReadingRecord.entry_id,
        )
        .where(JmdictReadingRecord.search_text.in_(reading_keys))
    )

    matches_by_key: dict[tuple[int, str], list[ExactCandidate]] = {}

    for row in session.execute(union_all(written_matches, reading_matches)):
        candidate = ExactCandidate(
            entry_id=row.entry_id,
            source_id=row.source_id,
            match_tier=row.match_tier,
            is_common=row.is_common,
            frequency_band=row.frequency_band,
        )
        key = (row.match_tier, row.matched_text)
        matches_by_key.setdefault(key, []).append(candidate)

    results = {}

    for term in terms:
        candidates = [
            *matches_by_key.get((0, normalize_written_form(term)), []),
            *matches_by_key.get((1, normalize_reading(term)), []),
        ]

        candidates.sort(
            key=lambda candidate: (
                candidate.match_tier,
                not candidate.is_common,
                candidate.frequency_band is None,
                candidate.frequency_band or 0,
                candidate.source_id,
            )
        )

        unique: dict[int, ExactCandidate] = {}

        for candidate in candidates:
            unique.setdefault(candidate.entry_id, candidate)

        results[term] = tuple(unique.values())

    return results
