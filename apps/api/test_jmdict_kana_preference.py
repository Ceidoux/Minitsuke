import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_latin_matches, find_reading_matches

KANA_LABEL = "word usually written using kana alone"


@pytest.fixture(
    params=[
        (find_reading_matches, "その"),
        (find_latin_matches, "sono"),
    ],
    ids=["kana", "romaji"],
)
def search_case(request: pytest.FixtureRequest):
    return request.param


def add_entry(
    session: Session,
    source_id: int,
    *,
    usually_kana: bool = False,
    restricted_readings: tuple[str, ...] = (),
    restricted_forms: tuple[str, ...] = (),
    readings: tuple[str, ...] = ("その", "そん"),
    band: int | None = None,
    common: bool = True,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=("其の",),
            readings=tuple(JmdictReading(text=text) for text in readings),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="unrelated definition", language="eng"),),
                    misc=(KANA_LABEL,) if usually_kana else (),
                    restricted_to_readings=restricted_readings,
                    restricted_to_written_forms=restricted_forms,
                ),
            ),
            is_common=common,
            frequency_band=band,
        ),
    )


def test_applicable_kana_preference_beats_frequency_before_pagination(
    db_session: Session,
    search_case,
):
    search, query = search_case
    add_entry(db_session, 100, band=1)
    add_entry(db_session, 200, usually_kana=True)

    first = search(db_session, query, limit=1)
    second = search(db_session, query, limit=1, offset=1)

    assert [match.source_id for match in first.matches] == [200]
    assert first.has_more is True
    assert [match.source_id for match in second.matches] == [100]
    assert second.has_more is False


@pytest.mark.parametrize(
    ("restriction", "expected"),
    [
        (("その",), [200, 100]),
        (("そん",), [100, 200]),
    ],
)
def test_preference_respects_the_matching_reading(
    db_session: Session,
    search_case,
    restriction,
    expected,
):
    search, query = search_case
    add_entry(db_session, 100, band=1)
    add_entry(
        db_session,
        200,
        usually_kana=True,
        restricted_readings=restriction,
    )

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == expected


def test_written_restriction_does_not_give_general_kana_boost(
    db_session: Session,
    search_case,
):
    search, query = search_case
    add_entry(db_session, 100, band=1)
    add_entry(
        db_session,
        200,
        usually_kana=True,
        restricted_forms=("其の",),
    )

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == [100, 200]


def test_commonness_still_precedes_kana_preference(
    db_session: Session,
    search_case,
):
    search, query = search_case
    add_entry(db_session, 100)
    add_entry(db_session, 200, usually_kana=True, common=False)

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == [100, 200]


def test_exact_match_still_beats_kana_preferred_prefix(
    db_session: Session,
    search_case,
):
    search, query = search_case
    add_entry(db_session, 100, common=False)
    add_entry(
        db_session,
        200,
        usually_kana=True,
        readings=("そのまま",),
        band=1,
    )

    page = search(db_session, query)

    assert [match.source_id for match in page.matches] == [100, 200]
