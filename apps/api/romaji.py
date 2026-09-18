import re
import unicodedata
from dataclasses import dataclass

import romkan2 as romkan

from japanese_text import normalize_reading

ROMAJI_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)*'?")

# Possible endings for an unfinished syllable.
SYLLABLE_ENDINGS = ("a", "i", "u", "e", "o", "ya", "yu", "yo")


@dataclass(frozen=True)
class RomajiInterpretation:
    complete_reading: str | None
    completion_prefixes: tuple[str, ...]


def _convert_complete(text: str) -> str | None:
    converted = normalize_reading(romkan.to_hiragana(text))

    if converted and all(
        "ぁ" <= character <= "ゖ" or character in "ーゝゞ" for character in converted
    ):
        return converted

    return None


def interpret_romaji(text: str) -> RomajiInterpretation:
    normalized = unicodedata.normalize("NFKC", text).strip().casefold()

    if ROMAJI_PATTERN.fullmatch(normalized) is None:
        return RomajiInterpretation(None, ())

    complete = _convert_complete(normalized)

    # A final "n" is ambiguous while typing:
    # "kan" can mean かん, or be the beginning of "kana", etc.
    needs_completions = complete is None or normalized.endswith("n")

    completions: set[str] = set()

    if needs_completions:
        for ending in SYLLABLE_ENDINGS:
            candidate = _convert_complete(normalized + ending)
            if candidate is not None and candidate != complete:
                completions.add(candidate)

    return RomajiInterpretation(
        complete_reading=complete,
        completion_prefixes=tuple(sorted(completions)),
    )
