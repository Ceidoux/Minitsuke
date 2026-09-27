from conjugation import conjugate_verb
from japanese_text import normalize_reading
from schemas import (
    ConjugationTableResponse,
    JmdictEntryResponse,
    JmdictSenseResponse,
)

VERB_CLASSES = {
    "Ichidan verb": "v1",
    "Godan verb with 'u' ending": "v5u",
    "Godan verb with 'ku' ending": "v5k",
    "Godan verb with 'gu' ending": "v5g",
    "Godan verb with 'su' ending": "v5s",
    "Godan verb with 'tsu' ending": "v5t",
    "Godan verb with 'nu' ending": "v5n",
    "Godan verb with 'bu' ending": "v5b",
    "Godan verb with 'mu' ending": "v5m",
    "Godan verb with 'ru' ending": "v5r",
    "Godan verb - Iku/Yuku special class": "v5k-s",
    "Kuru verb - special class": "vk",
    "suru verb - included": "vs-i",
}

SURU_NOUN = "noun or participle which takes the aux. verb suru"
SURU_SPECIAL = "suru verb - special class"


def _sense_pairs(
    entry: JmdictEntryResponse,
    sense: JmdictSenseResponse,
) -> list[tuple[str, str]]:
    pairs = []

    for reading in entry.readings:
        if (
            sense.restricted_to_readings
            and reading.text not in sense.restricted_to_readings
        ):
            continue

        if reading.no_kanji or not entry.written_forms:
            if not sense.restricted_to_written_forms:
                pairs.append((reading.text, normalize_reading(reading.text)))
            continue

        for written in entry.written_forms:
            if reading.restricted_to and written not in reading.restricted_to:
                continue

            if (
                sense.restricted_to_written_forms
                and written not in sense.restricted_to_written_forms
            ):
                continue

            pairs.append((written, normalize_reading(reading.text)))

    return pairs


def build_conjugation_tables(
    entry: JmdictEntryResponse,
) -> tuple[list[ConjugationTableResponse], bool]:
    tables: dict[tuple[str, str, str], ConjugationTableResponse] = {}
    incomplete = False

    for position, sense in enumerate(entry.senses, start=1):
        pairs = _sense_pairs(entry, sense)

        for label in sense.parts_of_speech:
            if label not in VERB_CLASSES and label not in {
                SURU_NOUN,
                SURU_SPECIAL,
            }:
                if label.startswith(
                    (
                        "Ichidan verb",
                        "Godan verb",
                        "Nidan verb",
                        "Yodan verb",
                        "Kuru verb",
                        "suru verb",
                        "su verb",
                        "zuru verb",
                    )
                ):
                    incomplete = True
                continue

            for original_written, original_reading in pairs:
                written = original_written
                reading = original_reading

                if label == SURU_NOUN:
                    verb_class = "vs-i"
                    written += "する"
                    reading += "する"
                elif label == SURU_SPECIAL:
                    # Standalone する follows the supported pattern.
                    # Other special suru verbs need their own rules.
                    if reading != "する":
                        incomplete = True
                        continue
                    verb_class = "vs-i"
                    written = "する"
                else:
                    verb_class = VERB_CLASSES[label]
                if verb_class == "vs-i" and reading == "する":
                    written = "する"
                key = (written, reading, verb_class)
                previous = tables.get(key)

                if previous is not None:
                    if position not in previous.sense_positions:
                        previous.sense_positions.append(position)
                    continue

                try:
                    forms = conjugate_verb(written, reading, verb_class)
                except ValueError:
                    # Some dictionary spellings cannot yet be generated.
                    # Keep other supported tables and disclose the omission.
                    incomplete = True
                    continue

                tables[key] = ConjugationTableResponse(
                    written=written,
                    reading=reading,
                    verb_class=verb_class,
                    sense_positions=[position],
                    forms=list(forms),
                )

    return list(tables.values()), incomplete
