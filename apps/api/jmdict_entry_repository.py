from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    JmdictDialectRecord,
    JmdictEntryRecord,
    JmdictFieldRecord,
    JmdictGlossRecord,
    JmdictLoanSourceRecord,
    JmdictMiscRecord,
    JmdictPartOfSpeechRecord,
    JmdictReadingInfoRecord,
    JmdictReadingRecord,
    JmdictReadingRestrictionRecord,
    JmdictSenseNoteRecord,
    JmdictSenseReadingRestrictionRecord,
    JmdictSenseRecord,
    JmdictSenseWrittenFormRestrictionRecord,
    JmdictWrittenFormInfoRecord,
    JmdictWrittenFormRecord,
)


@dataclass(frozen=True)
class EntryBasics:
    entries: tuple[JmdictEntryRecord, ...]
    written_forms: tuple[JmdictWrittenFormRecord, ...]
    readings: tuple[JmdictReadingRecord, ...]
    written_form_info: tuple[JmdictWrittenFormInfoRecord, ...] = ()
    reading_info: tuple[JmdictReadingInfoRecord, ...] = ()


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
    written_form_info = session.scalars(
        select(JmdictWrittenFormInfoRecord)
        .join(
            JmdictWrittenFormRecord,
            JmdictWrittenFormRecord.id == JmdictWrittenFormInfoRecord.written_form_id,
        )
        .where(JmdictWrittenFormRecord.entry_id.in_(ordered_ids))
        .order_by(
            JmdictWrittenFormRecord.entry_id,
            JmdictWrittenFormRecord.position,
            JmdictWrittenFormInfoRecord.position,
        )
    ).all()

    reading_info = session.scalars(
        select(JmdictReadingInfoRecord)
        .join(
            JmdictReadingRecord,
            JmdictReadingRecord.id == JmdictReadingInfoRecord.reading_id,
        )
        .where(JmdictReadingRecord.entry_id.in_(ordered_ids))
        .order_by(
            JmdictReadingRecord.entry_id,
            JmdictReadingRecord.position,
            JmdictReadingInfoRecord.position,
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
        written_form_info=tuple(written_form_info),
        reading_info=tuple(reading_info),
    )


@dataclass(frozen=True)
class SenseDetails:
    senses: tuple[JmdictSenseRecord, ...]
    glosses: tuple[JmdictGlossRecord, ...]
    parts_of_speech: tuple[JmdictPartOfSpeechRecord, ...]
    misc: tuple[JmdictMiscRecord, ...] = ()
    fields: tuple[JmdictFieldRecord, ...] = ()
    dialects: tuple[JmdictDialectRecord, ...] = ()
    notes: tuple[JmdictSenseNoteRecord, ...] = ()
    loan_sources: tuple[JmdictLoanSourceRecord, ...] = ()


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
    misc = session.scalars(
        select(JmdictMiscRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictMiscRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictMiscRecord.position,
        )
    ).all()
    fields = session.scalars(
        select(JmdictFieldRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictFieldRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictFieldRecord.position,
        )
    ).all()

    dialects = session.scalars(
        select(JmdictDialectRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictDialectRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictDialectRecord.position,
        )
    ).all()

    notes = session.scalars(
        select(JmdictSenseNoteRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictSenseNoteRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictSenseNoteRecord.position,
        )
    ).all()
    loan_sources = session.scalars(
        select(JmdictLoanSourceRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictLoanSourceRecord.sense_id,
        )
        .where(JmdictSenseRecord.entry_id.in_(entry_ids))
        .order_by(
            JmdictSenseRecord.entry_id,
            JmdictSenseRecord.position,
            JmdictLoanSourceRecord.position,
        )
    ).all()
    return SenseDetails(
        senses=tuple(senses),
        glosses=tuple(glosses),
        parts_of_speech=tuple(parts_of_speech),
        misc=tuple(misc),
        fields=tuple(fields),
        dialects=tuple(dialects),
        notes=tuple(notes),
        loan_sources=tuple(loan_sources),
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
