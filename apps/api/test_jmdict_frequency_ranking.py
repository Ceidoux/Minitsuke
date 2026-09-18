import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_latin_matches, find_reading_matches


@pytest.fixture(
    params=[
        (find_reading_matches, "がっこう"),
        (find_latin_matches, "school"),
    ],
    ids=["reading", "translation"],
)
def search_case(request: pytest.FixtureRequest):
    return request.param


def add_entry(
    session: Session,
    source_id: int,
    *,
    band: int | None,
    is_common: bool = True,
    reading: str = "がっこう",
    gloss: str = "school",
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=(),
            readings=(JmdictReading(text=reading),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text=gloss, language="eng"),),
                ),
            ),
            is_common=is_common,
            frequency_band=band,
        ),
    )


def test_lower_bands_rank_first_and_unknown_last(
    db_session: Session,
    search_case,
):
    find_matches, query = search_case

    add_entry(db_session, 100, band=None)
    add_entry(db_session, 200, band=48)
    add_entry(db_session, 300, band=3)
    add_entry(db_session, 400, band=1)

    page = find_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [
        400,
        300,
        200,
        100,
    ]


def test_commonness_precedes_frequency_band(
    db_session: Session,
    search_case,
):
    find_matches, query = search_case

    add_entry(db_session, 100, band=1, is_common=False)
    add_entry(db_session, 200, band=None, is_common=True)

    page = find_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [200, 100]


def test_exact_match_precedes_frequent_partial_match(
    db_session: Session,
    search_case,
):
    find_matches, query = search_case

    add_entry(db_session, 200, band=None, is_common=False)
    add_entry(
        db_session,
        100,
        band=1,
        reading="がっこうせいかつ",
        gloss="school life",
    )

    page = find_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [200, 100]


def test_equal_bands_keep_stable_source_id_order(
    db_session: Session,
    search_case,
):
    find_matches, query = search_case

    add_entry(db_session, 300, band=3)
    add_entry(db_session, 100, band=3)
    add_entry(db_session, 200, band=3)

    page = find_matches(db_session, query)

    assert [match.source_id for match in page.matches] == [100, 200, 300]


def test_frequency_ranking_happens_before_pagination(
    db_session: Session,
    search_case,
):
    find_matches, query = search_case

    add_entry(db_session, 100, band=None)
    add_entry(db_session, 200, band=3)
    add_entry(db_session, 300, band=1)

    first = find_matches(db_session, query, limit=2)
    second = find_matches(db_session, query, limit=2, offset=2)

    assert [match.source_id for match in first.matches] == [300, 200]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [100]
    assert second.has_more is False


def test_primary_translation_beats_more_frequent_secondary_meaning(
    db_session: Session,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=100,
            written_forms=(),
            readings=(JmdictReading(text="ながれ"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="flow", language="eng"),),
                ),
                JmdictSense(
                    glosses=(JmdictGloss(text="school", language="eng"),),
                ),
            ),
            is_common=True,
            frequency_band=2,
        ),
    )
    add_entry(
        db_session,
        200,
        band=3,
        reading="がくえん",
        gloss="school",
    )

    page = find_latin_matches(db_session, "school")

    assert [match.source_id for match in page.matches] == [200, 100]
