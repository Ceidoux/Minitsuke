from dataclasses import dataclass

from sqlalchemy import select, union
from sqlalchemy.orm import Session

from jmdict_entry_service import load_entries
from jmdict_reference import ReferenceCandidate, parse_reference_candidates
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictReferenceRecord,
    JmdictSenseRecord,
    JmdictWrittenFormRecord,
)
from schemas import (
    JmdictEntryResponse,
    JmdictReferenceResponse,
    JmdictReferenceTargetResponse,
    JmdictSenseResponse,
)


@dataclass(frozen=True)
class ReferenceTarget:
    source_id: int
    sense_position: int | None = None


def _matches_sense(
    entry: JmdictEntryResponse,
    sense: JmdictSenseResponse,
    candidate: ReferenceCandidate,
) -> bool:
    for reading in entry.readings:
        if (
            sense.restricted_to_readings
            and reading.text not in sense.restricted_to_readings
        ):
            continue

        if reading.no_kanji or not entry.written_forms:
            if sense.restricted_to_written_forms:
                continue

            if candidate.reading is None and candidate.form == reading.text:
                return True

            continue

        for written in entry.written_forms:
            if reading.restricted_to and written not in reading.restricted_to:
                continue

            if (
                sense.restricted_to_written_forms
                and written not in sense.restricted_to_written_forms
            ):
                continue

            if candidate.reading is not None:
                if written == candidate.form and reading.text == candidate.reading:
                    return True
            elif candidate.form in (written, reading.text):
                return True

    return False


def _matches_candidate(
    entry: JmdictEntryResponse,
    candidate: ReferenceCandidate,
) -> bool:
    if candidate.sense_position is not None:
        if candidate.sense_position > len(entry.senses):
            return False

        sense = entry.senses[candidate.sense_position - 1]
        return _matches_sense(entry, sense, candidate)

    return any(_matches_sense(entry, sense, candidate) for sense in entry.senses)


def resolve_references(
    session: Session,
    texts: tuple[str, ...],
) -> dict[str, tuple[ReferenceTarget, ...]]:
    """Resolve a batch of raw references without choosing among ambiguities."""
    candidates_by_text = {
        text: parse_reference_candidates(text) for text in dict.fromkeys(texts)
    }
    results: dict[str, set[ReferenceTarget]] = {
        text: set() for text in candidates_by_text
    }

    all_candidates = {
        candidate
        for candidates in candidates_by_text.values()
        for candidate in candidates
    }

    if not all_candidates:
        return {text: () for text in results}

    written_texts = sorted({candidate.form for candidate in all_candidates})
    reading_texts = sorted(
        {candidate.form for candidate in all_candidates if candidate.reading is None}
    )

    statement = union(
        select(JmdictWrittenFormRecord.entry_id).where(
            JmdictWrittenFormRecord.text.in_(written_texts),
        ),
        select(JmdictReadingRecord.entry_id).where(
            JmdictReadingRecord.text.in_(reading_texts),
        ),
    )

    entry_ids = tuple(sorted(session.scalars(statement).all()))

    if not entry_ids:
        return {text: () for text in results}

    entries = load_entries(session, entry_ids)

    entries_by_form: dict[str, list[JmdictEntryResponse]] = {}

    for entry in entries:
        forms = {
            *entry.written_forms,
            *(reading.text for reading in entry.readings),
        }

        for form in forms:
            entries_by_form.setdefault(form, []).append(entry)

    for text, candidates in candidates_by_text.items():
        for candidate in candidates:
            for entry in entries_by_form.get(candidate.form, ()):
                if _matches_candidate(entry, candidate):
                    results[text].add(
                        ReferenceTarget(
                            source_id=entry.source_id,
                            sense_position=candidate.sense_position,
                        )
                    )

    return {
        text: tuple(
            sorted(
                targets,
                key=lambda target: (
                    target.source_id,
                    target.sense_position or 0,
                ),
            )
        )
        for text, targets in results.items()
    }


def attach_references(
    session: Session,
    entries: list[JmdictEntryResponse],
) -> None:
    """Attach references to returned entries without recursively loading links."""
    if not entries:
        return

    entries_by_source_id = {entry.source_id: entry for entry in entries}

    for entry in entries:
        for sense in entry.senses:
            sense.cross_references = []
            sense.antonyms = []

    rows = session.execute(
        select(
            JmdictEntryRecord.source_id,
            JmdictSenseRecord.position,
            JmdictReferenceRecord.kind,
            JmdictReferenceRecord.text,
        )
        .select_from(JmdictReferenceRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictReferenceRecord.sense_id,
        )
        .join(
            JmdictEntryRecord,
            JmdictEntryRecord.id == JmdictSenseRecord.entry_id,
        )
        .where(JmdictEntryRecord.source_id.in_(entries_by_source_id))
        .order_by(
            JmdictEntryRecord.source_id,
            JmdictSenseRecord.position,
            JmdictReferenceRecord.kind,
            JmdictReferenceRecord.position,
        )
    ).all()

    if not rows:
        return

    targets_by_text = resolve_references(
        session,
        tuple(dict.fromkeys(row.text for row in rows)),
    )

    for source_id, sense_position, kind, text in rows:
        entry = entries_by_source_id[source_id]
        sense = entry.senses[sense_position - 1]

        reference = JmdictReferenceResponse(
            text=text,
            targets=[
                JmdictReferenceTargetResponse(
                    source_id=target.source_id,
                    sense_position=target.sense_position,
                )
                for target in targets_by_text[text]
            ],
        )

        if kind == "xref":
            sense.cross_references.append(reference)
        else:
            sense.antonyms.append(reference)
