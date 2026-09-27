import unicodedata

from sqlalchemy.orm import Session

from deconjugation import describe_inflection, extract_inflection_candidate
from deconjugation_service import find_inflection_matches
from japanese_text import normalize_reading
from jmdict_entry_service import load_entries
from jmdict_search_repository import (
    find_latin_matches,
    find_reading_matches,
    find_written_form_matches,
)
from romaji import interpret_romaji
from schemas import InflectionResponse, JmdictSearchResponse
from sentence_analysis import MAX_SENTENCE_LENGTH, get_sentence_analyzer


def _is_kana(character: str) -> bool:
    return "ぁ" <= character <= "ゖ" or character in "ーゝゞ\u3099\u309a"


def _is_japanese_character(character: str) -> bool:
    name = unicodedata.name(character, "")

    return (
        name.startswith(
            (
                "HIRAGANA",
                "KATAKANA",
                "CJK UNIFIED IDEOGRAPH",
                "CJK COMPATIBILITY IDEOGRAPH",
            )
        )
        or character in "々〆〇ー"
    )


def search_jmdict(
    session: Session,
    query: str,
    *,
    languages: tuple[str, ...] = ("eng",),
    limit: int = 30,
    offset: int = 0,
) -> JmdictSearchResponse:
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Search query must not be empty")

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("Offset must not be negative")

    normalized = normalize_reading(cleaned)
    contains_japanese = any(
        _is_japanese_character(character) for character in normalized
    )

    inflection_entry_ids: tuple[int, ...] = ()
    inflection = None

    analysis_text = (
        cleaned if contains_japanese else interpret_romaji(cleaned).complete_reading
    )

    if analysis_text is not None and len(analysis_text) <= MAX_SENTENCE_LENGTH:
        analyzer = get_sentence_analyzer()
        candidate = extract_inflection_candidate(
            analysis_text,
            analyzer.analyze(analysis_text),
        )

        if candidate is not None:
            matches = find_inflection_matches(session, candidate)
            inflection_entry_ids = tuple(match.entry_id for match in matches)

            if matches:
                inflection = InflectionResponse(
                    source_ids=[match.source_id for match in matches],
                    description=describe_inflection(candidate),
                )
    if all(_is_kana(character) for character in normalized):
        page = find_reading_matches(
            session,
            cleaned,
            limit=limit,
            offset=offset,
            inflection_entry_ids=inflection_entry_ids,
        )
    elif contains_japanese:
        page = find_written_form_matches(
            session,
            cleaned,
            limit=limit,
            offset=offset,
            inflection_entry_ids=inflection_entry_ids,
        )
    else:
        page = find_latin_matches(
            session,
            cleaned,
            languages=languages,
            limit=limit,
            offset=offset,
            inflection_entry_ids=inflection_entry_ids,
        )

    entry_ids = tuple(match.entry_id for match in page.matches)
    entries = load_entries(session, entry_ids)

    enabled_languages = set(languages)

    for entry in entries:
        for sense in entry.senses:
            sense.glosses = [
                gloss for gloss in sense.glosses if gloss.language in enabled_languages
            ]

    return JmdictSearchResponse(
        query=cleaned,
        results=entries,
        limit=limit,
        offset=offset,
        has_more=page.has_more,
        inflection=inflection,
    )
