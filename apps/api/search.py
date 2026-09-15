from sample_data import SAMPLE_WORDS
from schemas import WordEntry


def normalize_query(query: str) -> str:
    normalized_query: str = query.strip()
    if not normalized_query:
        raise ValueError("Search query must not be empty")
    return normalized_query


def find_words(query: str) -> list[WordEntry]:
    result: list[WordEntry] = []
    for element in SAMPLE_WORDS:
        if query == element.written_form or query == element.reading:
            result.append(element)
    return result
