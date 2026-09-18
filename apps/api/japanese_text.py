import unicodedata

KATAKANA_TO_HIRAGANA = str.maketrans(
    {
        chr(codepoint): chr(codepoint - 0x60)
        for codepoint in range(ord("ァ"), ord("ヶ") + 1)
    }
    | {
        "ヽ": "ゝ",
        "ヾ": "ゞ",
    }
)


def normalize_reading(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return normalized.translate(KATAKANA_TO_HIRAGANA)


def normalize_written_form(text: str) -> str:
    return normalize_reading(text).casefold()
