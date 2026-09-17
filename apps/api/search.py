from repository import find_word_rows
from schemas import WordEntry
from sqlalchemy.orm import Session


def normalize_query(query: str) -> str:
    normalized_query: str = query.strip()
    if not normalized_query:
        raise ValueError("Search query must not be empty")
    return normalized_query


def find_words(session: Session, query: str) -> list[WordEntry]:
    entries: dict[int, WordEntry] = {}

    for word_id, written_form, reading, meaning in find_word_rows(session, query):
        if word_id not in entries:
            entries[word_id] = WordEntry(
                written_form=written_form,
                reading=reading,
                meanings=[],
            )

        if meaning is not None:
            entries[word_id].meanings.append(meaning)

    return list(entries.values())
