from sqlalchemy import event
from sqlalchemy.orm import Session

from japanese_text import normalize_reading, normalize_written_form
from jmdict_exact_repository import find_exact_candidates
from models import (
    JmdictEntryRecord,
    JmdictReadingRecord,
    JmdictWrittenFormRecord,
)


def add_entry(
    session: Session,
    source_id: int,
    *,
    forms: tuple[str, ...] = (),
    readings: tuple[str, ...] = (),
    common: bool = False,
    band: int | None = None,
) -> None:
    entry = JmdictEntryRecord(
        source_id=source_id,
        is_common=common,
        frequency_band=band,
    )
    session.add(entry)
    session.flush()

    for position, text in enumerate(forms, start=1):
        session.add(
            JmdictWrittenFormRecord(
                entry_id=entry.id,
                text=text,
                search_text=normalize_written_form(text),
                position=position,
            )
        )

    for position, text in enumerate(readings, start=1):
        session.add(
            JmdictReadingRecord(
                entry_id=entry.id,
                text=text,
                search_text=normalize_reading(text),
                position=position,
                no_kanji=False,
            )
        )

    session.flush()


def test_matches_whole_forms_only(db_session: Session):
    add_entry(db_session, 100, forms=("学校",))
    add_entry(db_session, 200, forms=("小学校",))
    add_entry(db_session, 300, forms=("学校生活",))

    result = find_exact_candidates(db_session, ("学校", "不存在"))

    assert [item.source_id for item in result["学校"]] == [100]
    assert result["不存在"] == ()


def test_normalizes_kana_and_mixed_written_forms(db_session: Session):
    add_entry(db_session, 100, readings=("リンゴ",))
    add_entry(db_session, 200, forms=("Ｔシャツ",))

    result = find_exact_candidates(
        db_session,
        ("りんご", "ﾘﾝｺﾞ", "tしゃつ"),
    )

    assert [item.source_id for item in result["りんご"]] == [100]
    assert [item.source_id for item in result["ﾘﾝｺﾞ"]] == [100]
    assert [item.source_id for item in result["tしゃつ"]] == [200]


def test_preserves_homophones_and_prefers_written_matches(db_session: Session):
    add_entry(db_session, 300, forms=("はし",), readings=("はし",))
    add_entry(db_session, 100, forms=("橋",), readings=("はし",), common=True)
    add_entry(db_session, 200, forms=("箸",), readings=("はし",), common=True)

    result = find_exact_candidates(db_session, ("はし",))

    assert [(item.source_id, item.match_tier) for item in result["はし"]] == [
        (300, 0),
        (100, 1),
        (200, 1),
    ]


def test_ranks_equal_match_types_by_commonness_and_frequency(db_session: Session):
    add_entry(db_session, 100, readings=("こう",), band=1)
    add_entry(db_session, 200, readings=("こう",), common=True)
    add_entry(db_session, 400, readings=("こう",), common=True, band=2)
    add_entry(db_session, 300, readings=("こう",), common=True, band=2)

    result = find_exact_candidates(db_session, ("こう",))

    assert [item.source_id for item in result["こう"]] == [
        300,
        400,
        200,
        100,
    ]


def test_deduplicates_normalized_variants_and_input_forms(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("Ｔシャツ", "Tシャツ"),
    )

    result = find_exact_candidates(
        db_session,
        ("tしゃつ", "tしゃつ", "  tしゃつ  "),
    )

    assert list(result) == ["tしゃつ"]
    assert [item.source_id for item in result["tしゃつ"]] == [100]


def test_batches_multiple_forms_into_one_statement(db_session: Session):
    add_entry(db_session, 100, forms=("学校",))
    add_entry(db_session, 200, readings=("りんご",))

    connection = db_session.connection()
    statements = []

    def record_statement(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", record_statement)

    try:
        assert find_exact_candidates(db_session, ("", "   ")) == {}
        assert statements == []

        result = find_exact_candidates(
            db_session,
            ("学校", "りんご", "不存在"),
        )
    finally:
        event.remove(connection, "before_cursor_execute", record_statement)

    assert len(statements) == 1
    assert [item.source_id for item in result["学校"]] == [100]
    assert [item.source_id for item in result["りんご"]] == [200]
    assert result["不存在"] == ()
