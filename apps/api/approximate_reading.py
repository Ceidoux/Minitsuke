from japanese_text import normalize_reading

VOICING_GROUPS = (
    "かが",
    "きぎ",
    "くぐ",
    "けげ",
    "こご",
    "さざ",
    "しじ",
    "すず",
    "せぜ",
    "そぞ",
    "ただ",
    "ちぢ",
    "つづ",
    "てで",
    "とど",
    "はばぱ",
    "ひびぴ",
    "ふぶぷ",
    "へべぺ",
    "ほぼぽ",
    "うゔ",
)

VOICING_ALTERNATIVES = {
    character: tuple(other for other in group if other != character)
    for group in VOICING_GROUPS
    for character in group
}


def reading_prefix_alternatives(query: str) -> tuple[str, ...]:
    """Generate prefixes differing by exactly one kana voicing change."""
    normalized = normalize_reading(query.strip())

    if not all(
        "ぁ" <= character <= "ゖ" or character in "ーゝゞ" for character in normalized
    ):
        return ()

    kana_count = sum("ぁ" <= character <= "ゖ" for character in normalized)
    if kana_count < 2:
        return ()

    alternatives = {
        normalized[:position] + replacement + normalized[position + 1 :]
        for position, character in enumerate(normalized)
        for replacement in VOICING_ALTERNATIVES.get(character, ())
    }

    return tuple(sorted(alternatives))
