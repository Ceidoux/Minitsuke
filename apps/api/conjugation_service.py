from adjective_conjugation import conjugate_adjective
from conjugation import conjugate_verb
from copula_conjugation import conjugate_copula
from japanese_text import normalize_reading
from schemas import (
    ConjugationTableResponse,
    JmdictEntryResponse,
    JmdictSenseResponse,
)

VERB_CLASSES = {
    "Ichidan verb": "v1",
    "Ichidan verb - kureru special class": "v1-s",
    "Godan verb - -aru special class": "v5aru",
    "Godan verb with 'ru' ending (irregular verb)": "v5r-i",
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
    "Ichidan verb - zuru verb (alternative form of -jiru verbs)": "vz",
}

ADJECTIVE_CLASSES = {
    "adjective (keiyoushi)": "adj-i",
    "adjective (keiyoushi) - yoi/ii class": "adj-ix",
    "adjectival nouns or quasi-adjectives (keiyodoshi)": "adj-na",
}

SURU_NOUN = "noun or participle which takes the aux. verb suru"
SURU_SPECIAL = "suru verb - special class"
UNSUPPORTED_INFLECTING_CLASSES = frozenset(
    {
        "'ku' adjective (archaic)",
        "'shiku' adjective (archaic)",
        "'taru' adjective",
        "archaic/formal form of na-adjective",
        "irregular nu verb",
        "irregular ru verb, plain form ends with -ri",
        "verb unspecified",
    }
)


def _sense_pairs(
    entry: JmdictEntryResponse,
    sense: JmdictSenseResponse,
    *,
    include_search_only: bool = False,
) -> list[tuple[str, str]]:
    pairs = []

    written_forms = [
        written
        for written in entry.written_forms
        if include_search_only
        or "search-only kanji form" not in entry.written_form_info.get(written, [])
    ]

    for reading in entry.readings:
        if not include_search_only and "search-only kana form" in reading.info:
            continue

        if (
            sense.restricted_to_readings
            and reading.text not in sense.restricted_to_readings
        ):
            continue

        if reading.no_kanji or not entry.written_forms:
            if not sense.restricted_to_written_forms:
                pairs.append((reading.text, normalize_reading(reading.text)))
            continue

        if not written_forms:
            if not reading.restricted_to and not sense.restricted_to_written_forms:
                pairs.append((reading.text, normalize_reading(reading.text)))
            continue

        for written in written_forms:
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
    *,
    include_search_only: bool = False,
) -> tuple[list[ConjugationTableResponse], bool]:
    tables: dict[tuple[str, str, str], ConjugationTableResponse] = {}
    incomplete = False

    for position, sense in enumerate(entry.senses, start=1):
        pairs = _sense_pairs(
            entry,
            sense,
            include_search_only=include_search_only,
        )

        if "copula" in sense.parts_of_speech:
            for written, reading in pairs:
                key = (written, reading, "cop")
                previous = tables.get(key)

                if previous is not None:
                    if position not in previous.sense_positions:
                        previous.sense_positions.append(position)
                    continue

                try:
                    forms = conjugate_copula(written, reading)
                except ValueError:
                    incomplete = True
                    continue

                tables[key] = ConjugationTableResponse(
                    written=written,
                    reading=reading,
                    verb_class="cop",
                    sense_positions=[position],
                    forms=list(forms),
                )

            # Copulas can also carry a verb tag, as with である.
            # Their dedicated paradigm takes priority for this sense.
            continue

        for label in sense.parts_of_speech:
            if (
                label not in VERB_CLASSES
                and label not in ADJECTIVE_CLASSES
                and label not in {SURU_NOUN, SURU_SPECIAL}
            ):
                if label in UNSUPPORTED_INFLECTING_CLASSES or label.startswith(
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
                if label in ADJECTIVE_CLASSES:
                    verb_class = ADJECTIVE_CLASSES[label]
                elif label == SURU_NOUN:
                    verb_class = "vs-i"
                    written += "する"
                    reading += "する"
                elif label == SURU_SPECIAL:
                    if reading == "する":
                        verb_class = "vs-i"
                        written = "する"
                    elif written.endswith(("愛する", "あいする")) and reading.endswith(
                        "あいする"
                    ):
                        verb_class = "vs-s-aisu"
                    else:
                        verb_class = "vs-s"
                        # Shared forms are available, but this class
                        # still needs additional word-specific rules.
                        incomplete = True
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
                    if verb_class in ADJECTIVE_CLASSES.values():
                        forms = conjugate_adjective(written, reading, verb_class)
                    else:
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
