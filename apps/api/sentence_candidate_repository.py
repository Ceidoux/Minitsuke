from unicodedata import normalize

from sqlalchemy import select, union_all
from sqlalchemy.orm import Session

from models import (
    JmdictPartOfSpeechRecord,
    JmdictReadingRecord,
    JmdictSenseRecord,
    JmdictWrittenFormRecord,
)


def load_candidate_labels(
    session: Session,
    entry_ids: tuple[int, ...],
) -> dict[int, frozenset[str]]:
    if not entry_ids:
        return {}

    statement = (
        select(
            JmdictSenseRecord.entry_id,
            JmdictPartOfSpeechRecord.label,
        )
        .join(
            JmdictPartOfSpeechRecord,
            JmdictPartOfSpeechRecord.sense_id == JmdictSenseRecord.id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .distinct()
    )

    labels: dict[int, set[str]] = {}

    for entry_id, label in session.execute(statement):
        labels.setdefault(entry_id, set()).add(label)

    return {
        entry_id: frozenset(entry_labels) for entry_id, entry_labels in labels.items()
    }


def load_candidate_spellings(
    session: Session,
    entry_ids: tuple[int, ...],
) -> dict[int, frozenset[str]]:
    if not entry_ids:
        return {}

    statement = union_all(
        select(
            JmdictWrittenFormRecord.entry_id,
            JmdictWrittenFormRecord.text,
        ).where(JmdictWrittenFormRecord.entry_id.in_(entry_ids)),
        select(
            JmdictReadingRecord.entry_id,
            JmdictReadingRecord.text,
        ).where(JmdictReadingRecord.entry_id.in_(entry_ids)),
    )

    spellings: dict[int, set[str]] = {}

    for entry_id, text in session.execute(statement):
        spellings.setdefault(entry_id, set()).add(normalize("NFKC", text))

    return {entry_id: frozenset(forms) for entry_id, forms in spellings.items()}
