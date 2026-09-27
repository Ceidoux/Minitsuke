from sqlalchemy.orm import Session

from deconjugation import InflectionCandidate
from japanese_text import normalize_reading, normalize_written_form
from jmdict_entry_service import load_entries
from jmdict_exact_repository import ExactCandidate, find_exact_candidates
from schemas import JmdictEntryResponse, JmdictSenseResponse


def _compatible_grammar(
    sense: JmdictSenseResponse,
    candidate: InflectionCandidate,
    form: str,
) -> bool:
    labels = set(sense.parts_of_speech)

    if candidate.grammatical_class == "adjective":
        return "adjective (keiyoushi)" in labels

    if candidate.grammatical_class == "suru":
        if form.endswith("する"):
            return bool(
                labels
                & {
                    "suru verb - included",
                    "suru verb - special class",
                }
            )

        return "noun or participle which takes the aux. verb suru" in labels

    return any(
        label.startswith(("Ichidan verb", "Godan verb"))
        or label == "Kuru verb - special class"
        for label in labels
    )


def _matching_pairs(
    entry: JmdictEntryResponse,
    form: str,
) -> tuple[tuple[str | None, str], ...]:
    written_key = normalize_written_form(form)
    reading_key = normalize_reading(form)
    pairs = []

    for reading in entry.readings:
        if reading.no_kanji or not entry.written_forms:
            spellings: tuple[str | None, ...] = (None,)
        else:
            spellings = tuple(
                written
                for written in entry.written_forms
                if not reading.restricted_to or written in reading.restricted_to
            )

        for written in spellings:
            written_matches = (
                written is not None and normalize_written_form(written) == written_key
            )
            reading_matches = normalize_reading(reading.text) == reading_key

            if written_matches or reading_matches:
                pairs.append((written, reading.text))

    return tuple(pairs)


def entry_supports_inflection(
    entry: JmdictEntryResponse,
    candidate: InflectionCandidate,
    form: str,
) -> bool:
    pairs = _matching_pairs(entry, form)

    for sense in entry.senses:
        if not _compatible_grammar(sense, candidate, form):
            continue

        for written, reading in pairs:
            if (
                sense.restricted_to_written_forms
                and written not in sense.restricted_to_written_forms
            ):
                continue

            if (
                sense.restricted_to_readings
                and reading not in sense.restricted_to_readings
            ):
                continue

            return True

    return False


def find_inflection_matches(
    session: Session,
    candidate: InflectionCandidate,
) -> tuple[ExactCandidate, ...]:
    matches_by_form = find_exact_candidates(session, candidate.lookup_forms)

    entry_ids = tuple(
        dict.fromkeys(
            match.entry_id for matches in matches_by_form.values() for match in matches
        )
    )

    if not entry_ids:
        return ()

    entries_by_source_id = {
        entry.source_id: entry for entry in load_entries(session, entry_ids)
    }
    accepted: dict[int, ExactCandidate] = {}

    for form in candidate.lookup_forms:
        for match in matches_by_form.get(form, ()):
            entry = entries_by_source_id.get(match.source_id)

            if entry is None or not entry_supports_inflection(entry, candidate, form):
                continue

            previous = accepted.get(match.entry_id)
            if previous is None or match.match_tier < previous.match_tier:
                accepted[match.entry_id] = match

    return tuple(
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
