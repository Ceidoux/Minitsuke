import unicodedata

from sqlalchemy.orm import Session

from japanese_text import normalize_reading
from jmdict_entry_service import load_entries
from jmdict_search_repository import (
    find_latin_matches,
    find_reading_matches,
    find_written_form_matches,
)
from schemas import JmdictSearchResponse


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

    normalized = normalize_reading(cleaned)

    if all(_is_kana(character) for character in normalized):
        page = find_reading_matches(
            session,
            cleaned,
            limit=limit,
            offset=offset,
        )
    elif any(_is_japanese_character(character) for character in normalized):
        page = find_written_form_matches(
            session,
            cleaned,
            limit=limit,
            offset=offset,
        )
    else:
        page = find_latin_matches(
            session,
            cleaned,
            languages=languages,
            limit=limit,
            offset=offset,
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
    )
