import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search_repository import find_gloss_matches, find_latin_matches


@pytest.fixture(params=[find_gloss_matches, find_latin_matches])
def find_matches(request: pytest.FixtureRequest):
    return request.param


def add_entry(
    session: Session,
    source_id: int,
    senses: tuple[tuple[str, ...], ...],
    *,
    is_common: bool = False,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            is_common=is_common,
            written_forms=(),
            readings=(JmdictReading(text="てすと"),),
            senses=tuple(
                JmdictSense(
                    glosses=tuple(
                        JmdictGloss(text=text, language="eng") for text in glosses
                    ),
                )
                for glosses in senses
            ),
        ),
    )


def test_commonness_beats_earlier_sense(
    db_session: Session,
    find_matches,
):
    add_entry(
        db_session,
        100,
        (("family",), ("school",)),
        is_common=True,
    )
    add_entry(db_session, 200, (("school",),))

    page = find_matches(db_session, "school")

    assert [match.source_id for match in page.matches] == [100, 200]


def test_commonness_beats_earlier_gloss(
    db_session: Session,
    find_matches,
):
    add_entry(
        db_session,
        100,
        (("academy", "school"),),
        is_common=True,
    )
    add_entry(db_session, 200, (("school",),))

    page = find_matches(db_session, "scho")

    assert [match.source_id for match in page.matches] == [100, 200]


def test_ranking_values_come_from_one_matching_gloss(
    db_session: Session,
    find_matches,
):
    add_entry(
        db_session,
        100,
        (
            ("unrelated", "school"),
            ("school",),
        ),
    )
    add_entry(db_session, 200, (("school",),))

    page = find_matches(db_session, "school")

    assert [match.source_id for match in page.matches] == [200, 100]


def test_better_tier_beats_earlier_sense_before_pagination(
    db_session: Session,
    find_matches,
):
    add_entry(
        db_session,
        100,
        (
            ("schoolhouse",),
            ("school",),
        ),
    )
    add_entry(db_session, 200, (("schoolhouse",),))

    first = find_matches(db_session, "school", limit=1)
    second = find_matches(db_session, "school", limit=1, offset=1)

    assert [(match.source_id, match.tier) for match in first.matches] == [
        (100, 0),
    ]
    assert first.has_more is True
    assert [(match.source_id, match.tier) for match in second.matches] == [
        (200, 3),
    ]
    assert second.has_more is False
