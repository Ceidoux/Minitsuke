import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_latin_matches, find_reading_matches


@pytest.fixture(
    params=[
        (find_reading_matches, "この"),
        (find_latin_matches, "kono"),
    ],
    ids=["kana", "romaji"],
)
def search_case(request: pytest.FixtureRequest):
    return request.param


def add_entry(
    session: Session,
    source_id: int,
    readings: tuple[str, ...],
    *,
    band: int | None = None,
    is_common: bool = True,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=(),
            readings=tuple(JmdictReading(text=text) for text in readings),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="unrelated definition", language="eng"),),
                ),
            ),
            is_common=is_common,
            frequency_band=band,
        ),
    )


def test_primary_reading_beats_more_frequent_secondary_reading(
    db_session: Session,
    search_case,
):
    search, query = search_case

    add_entry(db_session, 100, ("きゅう", "この"), band=1)
    add_entry(db_session, 200, ("この",), band=None)

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == [200, 100]


def test_position_belongs_to_the_reading_with_the_best_tier(
    db_session: Session,
    search_case,
):
    search, query = search_case

    # Position 1 is only a prefix match. The exact match is at position 3.
    add_entry(
        db_session,
        100,
        ("このみ", "あ", "この"),
        band=1,
    )
    # Its exact match is at position 2, so it must rank first.
    add_entry(
        db_session,
        200,
        ("い", "この"),
        band=48,
    )

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == [200, 100]
    assert [match.tier for match in page.matches] == [0, 0]


def test_reading_position_is_applied_before_pagination(
    db_session: Session,
    search_case,
):
    search, query = search_case

    add_entry(db_session, 100, ("あ", "い", "この"), band=1)
    add_entry(db_session, 200, ("あ", "この"), band=2)
    add_entry(db_session, 300, ("この",), band=None)

    first = search(db_session, query, limit=2)
    second = search(db_session, query, limit=2, offset=2)

    assert [match.source_id for match in first.matches] == [300, 200]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [100]
    assert second.has_more is False
