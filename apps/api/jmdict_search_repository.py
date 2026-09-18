from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from japanese_text import normalize_reading
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictWrittenFormRecord,
)


@dataclass(frozen=True)
class EntryMatch:
    entry_id: int
    source_id: int
    tier: int
    is_common: bool


@dataclass(frozen=True)
class MatchPage:
    matches: tuple[EntryMatch, ...]
    has_more: bool


def _paginate_matches(
    session: Session,
    best_matches: Subquery,
    *,
    limit: int,
    offset: int,
) -> MatchPage:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("Offset must not be negative")

    statement = (
        select(
            JmdictEntryRecord.id.label("entry_id"),
            JmdictEntryRecord.source_id,
            best_matches.c.tier,
            JmdictEntryRecord.is_common,
        )
        .join(
            best_matches,
            best_matches.c.entry_id == JmdictEntryRecord.id,
        )
        .order_by(
            best_matches.c.tier,
            JmdictEntryRecord.is_common.desc(),
            JmdictEntryRecord.source_id,
        )
        .offset(offset)
        .limit(limit + 1)
    )

    rows = session.execute(statement).all()

    return MatchPage(
        matches=tuple(
            EntryMatch(
                entry_id=row.entry_id,
                source_id=row.source_id,
                tier=row.tier,
                is_common=row.is_common,
            )
            for row in rows[:limit]
        ),
        has_more=len(rows) > limit,
    )


def find_reading_matches(
    session: Session,
    query: str,
    *,
    limit: int = 30,
    offset: int = 0,
) -> MatchPage:
    normalized = normalize_reading(query.strip())
    if not normalized:
        raise ValueError("Search query must not be empty")

    reading = JmdictReadingRecord.search_text

    reading_tier = case(
        (reading == normalized, 0),
        (reading.startswith(normalized, autoescape=True), 1),
        else_=2,
    )

    best_matches = (
        select(
            JmdictReadingRecord.entry_id.label("entry_id"),
            func.min(reading_tier).label("tier"),
        )
        .where(reading.contains(normalized, autoescape=True))
        .group_by(JmdictReadingRecord.entry_id)
        .subquery()
    )

    return _paginate_matches(
        session,
        best_matches,
        limit=limit,
        offset=offset,
    )


def find_written_form_matches(
    session: Session,
    query: str,
    *,
    limit: int = 30,
    offset: int = 0,
) -> MatchPage:
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Search query must not be empty")

    written_form = JmdictWrittenFormRecord.text
    form_tier = case(
        (written_form == cleaned, 0),
        else_=1,
    )

    best_matches = (
        select(
            JmdictWrittenFormRecord.entry_id.label("entry_id"),
            func.min(form_tier).label("tier"),
        )
        .where(written_form.contains(cleaned, autoescape=True))
        .group_by(JmdictWrittenFormRecord.entry_id)
        .subquery()
    )

    return _paginate_matches(
        session,
        best_matches,
        limit=limit,
        offset=offset,
    )
