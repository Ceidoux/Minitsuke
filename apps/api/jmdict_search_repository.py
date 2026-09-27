import re
from dataclasses import dataclass
from unicodedata import normalize

from sqlalchemy import (
    Integer,
    case,
    false,
    func,
    literal,
    literal_column,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from approximate_reading import reading_prefix_alternatives
from japanese_text import normalize_reading, normalize_written_form
from models import (
    JmdictEntryRecord,
    JmdictGlossRecord,
    JmdictMiscRecord,
    JmdictReadingRecord,
    JmdictReadingRestrictionRecord,
    JmdictSenseReadingRestrictionRecord,
    JmdictSenseRecord,
    JmdictSenseWrittenFormRestrictionRecord,
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


def _reading_kana_preference():
    reading = JmdictReadingRecord
    sense = JmdictSenseRecord
    reading_restriction = JmdictSenseReadingRestrictionRecord
    written_restriction = JmdictSenseWrittenFormRestrictionRecord

    has_reading_restriction = (
        select(reading_restriction.sense_id)
        .where(reading_restriction.sense_id == sense.id)
        .correlate(sense)
        .exists()
    )

    allows_this_reading = (
        select(reading_restriction.sense_id)
        .where(
            reading_restriction.sense_id == sense.id,
            reading_restriction.reading_id == reading.id,
        )
        .correlate(sense, reading)
        .exists()
    )

    has_written_restriction = (
        select(written_restriction.sense_id)
        .where(written_restriction.sense_id == sense.id)
        .correlate(sense)
        .exists()
    )

    has_applicable_tag = (
        select(sense.id)
        .join(
            JmdictMiscRecord,
            JmdictMiscRecord.sense_id == sense.id,
        )
        .where(
            sense.entry_id == reading.entry_id,
            JmdictMiscRecord.label == "word usually written using kana alone",
            ~has_reading_restriction | allows_this_reading,
            ~has_written_restriction,
        )
        .correlate(reading)
        .exists()
    )

    return case((has_applicable_tag, 0), else_=1)


def _candidate_order(candidates: Subquery):
    return (
        candidates.c.tier,
        candidates.c.sense_position,
        candidates.c.gloss_position,
        candidates.c.reading_position,
        candidates.c.kana_preference,
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
        candidates.c.reading_position,
        candidates.c.kana_preference,
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
            numbered.c.reading_position,
            numbered.c.kana_preference,
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

    ordering = []

    if "script_group" in best_matches.c:
        ordering.append(best_matches.c.script_group)

    ordering.extend(
        [
            best_matches.c.tier,
            JmdictEntryRecord.is_common.desc(),
        ]
    )

    if "sense_position" in best_matches.c:
        ordering.extend(
            [
                best_matches.c.sense_position,
                best_matches.c.gloss_position,
            ]
        )
    if "reading_position" in best_matches.c:
        ordering.append(best_matches.c.reading_position)
    if "kana_preference" in best_matches.c:
        ordering.append(best_matches.c.kana_preference)
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


def _original_script_match(original: str):
    reading = JmdictReadingRecord
    written = JmdictWrittenFormRecord
    restriction = JmdictReadingRestrictionRecord

    original_reading = func.normalize(
        reading.text,
        literal_column("NFKC"),
    ).contains(original, autoescape=True)

    has_restrictions = (
        select(restriction.reading_id)
        .where(restriction.reading_id == reading.id)
        .correlate(reading)
        .exists()
    )

    allows_written_form = (
        select(restriction.reading_id)
        .where(
            restriction.reading_id == reading.id,
            restriction.written_form_id == written.id,
        )
        .correlate(reading, written)
        .exists()
    )

    matching_written_form = (
        select(written.id)
        .where(
            written.entry_id == reading.entry_id,
            ~reading.no_kanji,
            ~has_restrictions | allows_written_form,
            func.normalize(
                written.text,
                literal_column("NFKC"),
            ).contains(original, autoescape=True),
        )
        .correlate(reading)
        .exists()
    )

    return original_reading | matching_written_form


def find_reading_matches(
    session: Session,
    query: str,
    *,
    limit: int = 30,
    offset: int = 0,
) -> MatchPage:
    original = normalize("NFKC", query.strip())
    normalized = normalize_reading(original)

    if not normalized:
        raise ValueError("Search query must not be empty")

    reading = JmdictReadingRecord.search_text
    alternatives = reading_prefix_alternatives(normalized)

    original_exact = reading == normalized
    original_prefix = reading.startswith(normalized, autoescape=True)
    original_substring = reading.contains(normalized, autoescape=True)

    alternative_exact = reading.in_(alternatives)
    alternative_prefix = or_(
        false(),
        *(
            reading.startswith(alternative, autoescape=True)
            for alternative in alternatives
        ),
    )

    reading_tier = case(
        (original_exact, 0),
        (original_prefix, 1),
        (original_substring, 2),
        (alternative_exact, 3),
        else_=4,
    )

    script_group = case(
        (original_substring & _original_script_match(original), 0),
        (original_substring, 1),
        else_=2,
    )

    candidates = (
        select(
            JmdictReadingRecord.entry_id.label("entry_id"),
            reading_tier.label("tier"),
            script_group.label("script_group"),
            JmdictReadingRecord.position.label("reading_position"),
            _reading_kana_preference().label("kana_preference"),
        )
        .where(original_substring | alternative_prefix)
        .subquery()
    )

    numbered = select(
        candidates.c.entry_id,
        candidates.c.tier,
        candidates.c.script_group,
        candidates.c.reading_position,
        candidates.c.kana_preference,
        func.row_number()
        .over(
            partition_by=candidates.c.entry_id,
            order_by=(
                candidates.c.script_group,
                candidates.c.tier,
                candidates.c.reading_position,
                candidates.c.kana_preference,
            ),
        )
        .label("candidate_number"),
    ).subquery()

    best_matches = (
        select(
            numbered.c.entry_id,
            numbered.c.tier,
            numbered.c.script_group,
            numbered.c.reading_position,
            numbered.c.kana_preference,
        )
        .where(numbered.c.candidate_number == 1)
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
            literal(1).label("reading_position"),
            literal(1).label("kana_preference"),
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
        literal(1).label("reading_position"),
        literal(1).label("kana_preference"),
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
        JmdictReadingRecord.position.label("reading_position"),
        _reading_kana_preference().label("kana_preference"),
    ).where(or_(*reading_conditions))

    alternatives = (
        reading_prefix_alternatives(interpretation.complete_reading)
        if interpretation.complete_reading is not None
        else ()
    )

    alternative_prefix = or_(
        false(),
        *(
            reading.startswith(alternative, autoescape=True)
            for alternative in alternatives
        ),
    )

    approximate_candidates = select(
        JmdictReadingRecord.entry_id.label("entry_id"),
        case(
            (reading.in_(alternatives), 7),
            else_=8,
        ).label("tier"),
        literal(None, type_=Integer).label("gloss_length"),
        literal(0).label("sense_position"),
        literal(0).label("gloss_position"),
        JmdictReadingRecord.position.label("reading_position"),
        _reading_kana_preference().label("kana_preference"),
    ).where(alternative_prefix)
    gloss_candidates = _gloss_candidates(query, languages)

    candidates = union_all(
        written_candidates,
        reading_candidates,
        approximate_candidates,
        select(
            gloss_candidates.c.entry_id,
            gloss_candidates.c.tier,
            gloss_candidates.c.gloss_length,
            gloss_candidates.c.sense_position,
            gloss_candidates.c.gloss_position,
            gloss_candidates.c.reading_position,
            gloss_candidates.c.kana_preference,
        ),
    ).subquery()

    best_matches = _best_candidate_per_entry(candidates)

    return _paginate_matches(
        session,
        best_matches,
        limit=limit,
        offset=offset,
    )
