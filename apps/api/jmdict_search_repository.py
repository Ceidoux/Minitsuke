import re
from dataclasses import dataclass

from sqlalchemy import (
    Integer,
    case,
    false,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from japanese_text import normalize_reading, normalize_written_form
from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictReadingRecord,
    JmdictSenseRecord,
    JmdictWrittenFormRecord,
)
from romaji import interpret_romaji


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


def _candidate_order(candidates: Subquery):
    return (
        candidates.c.tier,
        candidates.c.sense_position,
        candidates.c.gloss_position,
        case(
            (candidates.c.tier == 3, candidates.c.gloss_length),
            else_=0,
        ),
    )


def _best_candidate_per_entry(candidates: Subquery) -> Subquery:
    numbered = select(
        candidates.c.entry_id,
        candidates.c.tier,
        candidates.c.sense_position,
        candidates.c.gloss_position,
        candidates.c.gloss_length,
        func.row_number()
        .over(
            partition_by=candidates.c.entry_id,
            order_by=_candidate_order(candidates),
        )
        .label("candidate_number"),
    ).subquery()

    return (
        select(
            numbered.c.entry_id,
            numbered.c.tier,
            numbered.c.sense_position,
            numbered.c.gloss_position,
            numbered.c.gloss_length,
        )
        .where(numbered.c.candidate_number == 1)
        .subquery()
    )


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

    ordering = [
        best_matches.c.tier,
        JmdictEntryRecord.is_common.desc(),
    ]

    if "sense_position" in best_matches.c:
        ordering.extend(
            [
                best_matches.c.sense_position,
                best_matches.c.gloss_position,
            ]
        )

    ordering.append(JmdictEntryRecord.frequency_band.asc().nulls_last())

    if "gloss_length" in best_matches.c:
        ordering.append(
            case(
                (best_matches.c.tier == 3, best_matches.c.gloss_length),
                else_=0,
            )
        )

    ordering.append(JmdictEntryRecord.source_id)

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
        .order_by(*ordering)
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
    cleaned = normalize_written_form(query.strip())
    if not cleaned:
        raise ValueError("Search query must not be empty")

    written_form = JmdictWrittenFormRecord.search_text
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


def _gloss_candidates(
    query: str,
    languages: tuple[str, ...],
) -> Subquery:
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Search query must not be empty")

    gloss = JmdictGlossRecord.text
    escaped = re.escape(cleaned)

    exact = func.lower(gloss) == func.lower(cleaned)
    whole_word = gloss.bool_op("~*")(rf"\m{escaped}\M")
    starts_gloss = gloss.bool_op("~*")(rf"^{escaped}")
    word_prefix = gloss.bool_op("~*")(rf"\m{escaped}")

    main_definition = func.split_part(gloss, "(", 1)
    main_word_prefix = main_definition.bool_op("~*")(rf"\m{escaped}")

    tier = case(
        (exact, 0),
        (whole_word, 1),
        (starts_gloss, 3),
        (main_word_prefix, 4),
        else_=5,
    )

    return (
        select(
            JmdictSenseRecord.entry_id.label("entry_id"),
            tier.label("tier"),
            case(
                (starts_gloss, func.length(gloss)),
                else_=None,
            ).label("gloss_length"),
            JmdictSenseRecord.position.label("sense_position"),
            JmdictGlossRecord.position.label("gloss_position"),
        )
        .select_from(JmdictGlossRecord)
        .join(
            JmdictSenseRecord,
            JmdictSenseRecord.id == JmdictGlossRecord.sense_id,
        )
        .where(
            JmdictGlossRecord.language.in_(languages),
            exact | word_prefix,
        )
        .subquery()
    )


def find_gloss_matches(
    session: Session,
    query: str,
    *,
    languages: tuple[str, ...] = ("eng",),
    limit: int = 30,
    offset: int = 0,
) -> MatchPage:
    candidates = _gloss_candidates(query, languages)

    best_matches = _best_candidate_per_entry(candidates)

    return _paginate_matches(
        session,
        best_matches,
        limit=limit,
        offset=offset,
    )


def find_latin_matches(
    session: Session,
    query: str,
    *,
    languages: tuple[str, ...] = ("eng",),
    limit: int = 30,
    offset: int = 0,
) -> MatchPage:
    cleaned = normalize_written_form(query.strip())
    if not cleaned:
        raise ValueError("Search query must not be empty")

    # Search the literal spelling, including Latin letters in Japanese words.
    written = JmdictWrittenFormRecord.search_text
    written_candidates = select(
        JmdictWrittenFormRecord.entry_id.label("entry_id"),
        case(
            (written == cleaned, 0),
            (written.startswith(cleaned, autoescape=True), 2),
            else_=6,
        ).label("tier"),
        literal(None, type_=Integer).label("gloss_length"),
        literal(0).label("sense_position"),
        literal(0).label("gloss_position"),
    ).where(written.contains(cleaned, autoescape=True))

    # Search readings through complete and unfinished romaji interpretations.
    interpretation = interpret_romaji(cleaned)
    reading = JmdictReadingRecord.search_text

    exact_reading = false()
    reading_conditions = [false()]
    prefix_conditions = [false()]

    if interpretation.complete_reading is not None:
        complete = interpretation.complete_reading
        exact_reading = reading == complete
        reading_conditions.append(reading.contains(complete, autoescape=True))
        prefix_conditions.append(reading.startswith(complete, autoescape=True))

    for completion in interpretation.completion_prefixes:
        prefix = reading.startswith(completion, autoescape=True)
        reading_conditions.append(prefix)
        prefix_conditions.append(prefix)

    reading_candidates = select(
        JmdictReadingRecord.entry_id.label("entry_id"),
        case(
            (exact_reading, 0),
            (or_(*prefix_conditions), 2),
            else_=6,
        ).label("tier"),
        literal(None, type_=Integer).label("gloss_length"),
        literal(0).label("sense_position"),
        literal(0).label("gloss_position"),
    ).where(or_(*reading_conditions))

    gloss_candidates = _gloss_candidates(query, languages)

    candidates = union_all(
        written_candidates,
        reading_candidates,
        select(
            gloss_candidates.c.entry_id,
            gloss_candidates.c.tier,
            gloss_candidates.c.gloss_length,
            gloss_candidates.c.sense_position,
            gloss_candidates.c.gloss_position,
        ),
    ).subquery()

    best_matches = _best_candidate_per_entry(candidates)

    return _paginate_matches(
        session,
        best_matches,
        limit=limit,
        offset=offset,
    )
