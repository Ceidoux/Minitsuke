from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry
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


def validate_entry_for_import(entry: JmdictEntry) -> None:
    if not entry.readings:
        raise ValueError("Entry must contain at least one reading")

    if not entry.senses:
        raise ValueError("Entry must contain at least one sense")

    written_forms = set(entry.written_forms)
    reading_texts = {reading.text for reading in entry.readings}

    if len(written_forms) != len(entry.written_forms):
        raise ValueError("Entry contains duplicate written forms")

    if len(reading_texts) != len(entry.readings):
        raise ValueError("Entry contains duplicate readings")

    for reading in entry.readings:
        if reading.no_kanji and reading.restricted_to:
            raise ValueError("A no_kanji reading cannot have written-form restrictions")

        if set(reading.restricted_to) - written_forms:
            raise ValueError("Reading restriction references an unknown written form")

    for sense in entry.senses:
        if set(sense.restricted_to_written_forms) - written_forms:
            raise ValueError("Sense restriction references an unknown written form")

        if set(sense.restricted_to_readings) - reading_texts:
            raise ValueError("Sense restriction references an unknown reading")


def save_jmdict_entry(session: Session, entry: JmdictEntry) -> int:
    """Insert or replace one entry; the caller owns the transaction."""
    validate_entry_for_import(entry)

    record = session.scalar(
        select(JmdictEntryRecord).where(
            JmdictEntryRecord.source_id == entry.source_id,
        )
    )

    if record is None:
        record = JmdictEntryRecord(source_id=entry.source_id)
        session.add(record)
        session.flush()
    else:
        session.execute(
            delete(JmdictSenseRecord).where(
                JmdictSenseRecord.entry_id == record.id,
            )
        )
        session.execute(
            delete(JmdictReadingRecord).where(
                JmdictReadingRecord.entry_id == record.id,
            )
        )
        session.execute(
            delete(JmdictWrittenFormRecord).where(
                JmdictWrittenFormRecord.entry_id == record.id,
            )
        )

    forms = {
        text: JmdictWrittenFormRecord(
            entry_id=record.id,
            text=text,
            position=position,
        )
        for position, text in enumerate(entry.written_forms, start=1)
    }
    session.add_all(forms.values())
    session.flush()

    readings = {
        reading.text: JmdictReadingRecord(
            entry_id=record.id,
            text=reading.text,
            position=position,
            no_kanji=reading.no_kanji,
        )
        for position, reading in enumerate(entry.readings, start=1)
    }
    session.add_all(readings.values())
    session.flush()

    for reading in entry.readings:
        for text in dict.fromkeys(reading.restricted_to):
            session.add(
                JmdictReadingRestrictionRecord(
                    entry_id=record.id,
                    reading_id=readings[reading.text].id,
                    written_form_id=forms[text].id,
                )
            )

    for position, sense in enumerate(entry.senses, start=1):
        sense_record = JmdictSenseRecord(
            entry_id=record.id,
            position=position,
        )
        session.add(sense_record)
        session.flush()

        for gloss_position, gloss in enumerate(sense.glosses, start=1):
            session.add(
                JmdictGlossRecord(
                    sense_id=sense_record.id,
                    text=gloss.text,
                    language=gloss.language,
                    position=gloss_position,
                )
            )

        for label_position, label in enumerate(
            sense.parts_of_speech,
            start=1,
        ):
            session.add(
                JmdictPartOfSpeechRecord(
                    sense_id=sense_record.id,
                    label=label,
                    position=label_position,
                )
            )

        for text in dict.fromkeys(sense.restricted_to_written_forms):
            session.add(
                JmdictSenseWrittenFormRestrictionRecord(
                    entry_id=record.id,
                    sense_id=sense_record.id,
                    written_form_id=forms[text].id,
                )
            )

        for text in dict.fromkeys(sense.restricted_to_readings):
            session.add(
                JmdictSenseReadingRestrictionRecord(
                    entry_id=record.id,
                    sense_id=sense_record.id,
                    reading_id=readings[text].id,
                )
            )

    session.flush()
    return record.id
