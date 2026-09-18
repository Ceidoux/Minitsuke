from sqlalchemy.orm import Session

from jmdict_entry_repository import (
    load_entry_basics,
    load_entry_restrictions,
    load_sense_details,
)
from schemas import (
    JmdictEntryResponse,
    JmdictGlossResponse,
    JmdictReadingResponse,
    JmdictSenseResponse,
)


def load_entries(
    session: Session,
    entry_ids: tuple[int, ...],
) -> list[JmdictEntryResponse]:
    basics = load_entry_basics(session, entry_ids)

    if not basics.entries:
        return []

    existing_ids = tuple(entry.id for entry in basics.entries)
    details = load_sense_details(session, existing_ids)
    restrictions = load_entry_restrictions(session, existing_ids)

    forms_by_entry = {entry.id: [] for entry in basics.entries}
    readings_by_entry = {entry.id: [] for entry in basics.entries}
    senses_by_entry = {entry.id: [] for entry in basics.entries}

    for form in basics.written_forms:
        forms_by_entry[form.entry_id].append(form)

    for reading in basics.readings:
        readings_by_entry[reading.entry_id].append(reading)

    for sense in details.senses:
        senses_by_entry[sense.entry_id].append(sense)

    glosses_by_sense = {sense.id: [] for sense in details.senses}
    parts_by_sense = {sense.id: [] for sense in details.senses}

    for gloss in details.glosses:
        glosses_by_sense[gloss.sense_id].append(
            JmdictGlossResponse(
                text=gloss.text,
                language=gloss.language,
            )
        )

    for part in details.parts_of_speech:
        parts_by_sense[part.sense_id].append(part.label)

    forms_by_reading = {reading.id: set() for reading in basics.readings}
    forms_by_sense = {sense.id: set() for sense in details.senses}
    readings_by_sense = {sense.id: set() for sense in details.senses}

    for link in restrictions.reading_restrictions:
        forms_by_reading[link.reading_id].add(link.written_form_id)

    for link in restrictions.sense_written_restrictions:
        forms_by_sense[link.sense_id].add(link.written_form_id)

    for link in restrictions.sense_reading_restrictions:
        readings_by_sense[link.sense_id].add(link.reading_id)

    results = []

    for entry in basics.entries:
        forms = forms_by_entry[entry.id]
        readings = readings_by_entry[entry.id]

        reading_responses = [
            JmdictReadingResponse(
                text=reading.text,
                no_kanji=reading.no_kanji,
                restricted_to=[
                    form.text
                    for form in forms
                    if form.id in forms_by_reading[reading.id]
                ],
            )
            for reading in readings
        ]

        sense_responses = [
            JmdictSenseResponse(
                glosses=glosses_by_sense[sense.id],
                parts_of_speech=parts_by_sense[sense.id],
                restricted_to_written_forms=[
                    form.text for form in forms if form.id in forms_by_sense[sense.id]
                ],
                restricted_to_readings=[
                    reading.text
                    for reading in readings
                    if reading.id in readings_by_sense[sense.id]
                ],
            )
            for sense in senses_by_entry[entry.id]
        ]

        results.append(
            JmdictEntryResponse(
                source_id=entry.source_id,
                is_common=entry.is_common,
                written_forms=[form.text for form in forms],
                readings=reading_responses,
                senses=sense_responses,
            )
        )

    return results
