import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search import search_jmdict


def add_entry(
    session: Session,
    source_id: int,
    *,
    forms: tuple[str, ...],
    reading: str,
    label: str,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=forms,
            readings=(JmdictReading(text=reading),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="test definition", language="eng"),),
                    parts_of_speech=(label,),
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    ("query", "forms", "reading", "label"),
    [
        ("食べました", ("食べる",), "たべる", "Ichidan verb"),
        ("たべました", ("食べる",), "たべる", "Ichidan verb"),
        ("されている", ("為る",), "する", "suru verb - included"),
        (
            "確認しました",
            ("確認",),
            "かくにん",
            "noun or participle which takes the aux. verb suru",
        ),
        ("高かった", ("高い",), "たかい", "adjective (keiyoushi)"),
    ],
)
def test_search_returns_base_entry(
    db_session: Session,
    query: str,
    forms: tuple[str, ...],
    reading: str,
    label: str,
):
    add_entry(
        db_session,
        100,
        forms=forms,
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.has_more is False


def test_combines_matches_before_pagination(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("食べました",),
        reading="たべました",
        label="expression",
    )
    add_entry(
        db_session,
        200,
        forms=("食べる",),
        reading="たべる",
        label="Ichidan verb",
    )
    add_entry(
        db_session,
        300,
        forms=("食べましたか",),
        reading="たべましたか",
        label="expression",
    )

    pages = [
        search_jmdict(db_session, "食べました", limit=1, offset=offset)
        for offset in range(4)
    ]

    assert [[entry.source_id for entry in page.results] for page in pages] == [
        [100],
        [200],
        [300],
        [],
    ]
    assert [page.has_more for page in pages] == [True, True, False, False]


@pytest.mark.parametrize("exact", [True, False])
def test_deduplicates_direct_and_inflected_matches(
    db_session: Session,
    exact: bool,
):
    # Synthetic entry to exercise overlap between both match sources.
    extra_form = "食べました" if exact else "食べましたか"
    add_entry(
        db_session,
        100,
        forms=("食べる", extra_form),
        reading="たべる",
        label="Ichidan verb",
    )

    first = search_jmdict(db_session, "食べました", limit=1)
    second = search_jmdict(db_session, "食べました", limit=1, offset=1)

    assert [entry.source_id for entry in first.results] == [100]
    assert first.has_more is False
    assert second.results == []


def test_excludes_grammatically_incompatible_entry(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("確認",),
        reading="かくにん",
        label="noun (common) (futsuumeishi)",
    )

    response = search_jmdict(db_session, "確認しました")

    assert response.results == []
