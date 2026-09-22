from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictPartOfSpeechRecord,
    JmdictReadingRecord,
    JmdictReadingRestrictionRecord,
    JmdictSenseReadingRestrictionRecord,
    JmdictSenseRecord,
    JmdictSenseWrittenFormRestrictionRecord,
    JmdictWrittenFormRecord,
)


@dataclass(frozen=True)
class EntryBasics:
    entries: tuple[JmdictEntryRecord, ...]
    written_forms: tuple[JmdictWrittenFormRecord, ...]
    readings: tuple[JmdictReadingRecord, ...]


def load_entry_basics(
    session: Session,
    entry_ids: tuple[int, ...],
) -> EntryBasics:
    """Load entry basics, preserving the requested entry order."""
    ordered_ids = tuple(dict.fromkeys(entry_ids))

    if not ordered_ids:
        return EntryBasics(entries=(), written_forms=(), readings=())

    entries = session.scalars(
        select(JmdictEntryRecord).where(
            JmdictEntryRecord.id.in_(ordered_ids),
        )
    ).all()

    entries_by_id = {entry.id: entry for entry in entries}

    written_forms = session.scalars(
        select(JmdictWrittenFormRecord)
        .where(JmdictWrittenFormRecord.entry_id.in_(ordered_ids))
        .order_by(
            JmdictWrittenFormRecord.entry_id,
            JmdictWrittenFormRecord.position,
        )
    ).all()

    readings = session.scalars(
        select(JmdictReadingRecord)
        .where(JmdictReadingRecord.entry_id.in_(ordered_ids))
        .order_by(
            JmdictReadingRecord.entry_id,
            JmdictReadingRecord.position,
        )
    ).all()

    return EntryBasics(
        entries=tuple(
            entries_by_id[entry_id]
            for entry_id in ordered_ids
            if entry_id in entries_by_id
        ),
        written_forms=tuple(written_forms),
        readings=tuple(readings),
    )


@dataclass(frozen=True)
class SenseDetails:
    senses: tuple[JmdictSenseRecord, ...]
    glosses: tuple[JmdictGlossRecord, ...]
    parts_of_speech: tuple[JmdictPartOfSpeechRecord, ...]


def load_sense_details(
    session: Session,
    entry_ids: tuple[int, ...],
) -> SenseDetails:
    """Load senses and their children for the requested entries."""
    if not entry_ids:
        return SenseDetails(senses=(), glosses=(), parts_of_speech=())

    senses = session.scalars(
        select(JmdictSenseRecord)
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
        )
    ).all()

    glosses = session.scalars(
        select(JmdictGlossRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictGlossRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictGlossRecord.position,
        )
    ).all()

    parts_of_speech = session.scalars(
        select(JmdictPartOfSpeechRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictPartOfSpeechRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictPartOfSpeechRecord.position,
        )
    ).all()

    return SenseDetails(
        senses=tuple(senses),
        glosses=tuple(glosses),
        parts_of_speech=tuple(parts_of_speech),
    )


@dataclass(frozen=True)
class EntryRestrictions:
    reading_restrictions: tuple[JmdictReadingRestrictionRecord, ...]
    sense_written_restrictions: tuple[JmdictSenseWrittenFormRestrictionRecord, ...]
    sense_reading_restrictions: tuple[JmdictSenseReadingRestrictionRecord, ...]


def load_entry_restrictions(
    session: Session,
    entry_ids: tuple[int, ...],
) -> EntryRestrictions:
    """Load restriction links for the requested entries."""
    if not entry_ids:
        return EntryRestrictions(
            reading_restrictions=(),
            sense_written_restrictions=(),
            sense_reading_restrictions=(),
        )

    reading_restrictions = session.scalars(
        select(JmdictReadingRestrictionRecord).where(
            JmdictReadingRestrictionRecord.entry_id.in_(entry_ids),
        )
    ).all()

    sense_written_restrictions = session.scalars(
        select(JmdictSenseWrittenFormRestrictionRecord).where(
            JmdictSenseWrittenFormRestrictionRecord.entry_id.in_(entry_ids),
        )
    ).all()

    sense_reading_restrictions = session.scalars(
        select(JmdictSenseReadingRestrictionRecord).where(
            JmdictSenseReadingRestrictionRecord.entry_id.in_(entry_ids),
        )
    ).all()

    return EntryRestrictions(
        reading_restrictions=tuple(reading_restrictions),
        sense_written_restrictions=tuple(sense_written_restrictions),
        sense_reading_restrictions=tuple(sense_reading_restrictions),
    )


def find_entry_id_by_source_id(
    session: Session,
    source_id: int,
) -> int | None:
    return session.scalar(
        select(JmdictEntryRecord.id).where(
            JmdictEntryRecord.source_id == source_id,
        )
    )
