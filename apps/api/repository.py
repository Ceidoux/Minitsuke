from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models import Meaning, Word


def find_word_rows(
    session: Session,
    query: str,
) -> list[tuple[int, str, str, str | None]]:
    statement = (
        select(Word.id, Word.written_form, Word.reading, Meaning.meaning)
        .outerjoin(Meaning, Word.id == Meaning.word_id)
        .where(
            or_(
                Word.written_form == query,
                Word.reading == query,
            )
        )
        .order_by(Word.id, Meaning.id)
    )

    rows = session.execute(statement).all()

    return [
        (word_id, written_form, reading, meaning)
        for word_id, written_form, reading, meaning in rows
    ]
