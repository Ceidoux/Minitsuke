import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry


def add_school(session: Session, source_id: int) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            is_common=True,
            written_forms=("学校",),
            readings=(JmdictReading(text="がっこう"),),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss(text="school", language="eng"),
                        JmdictGloss(text="école", language="fre"),
                    ),
                    parts_of_speech=("noun",),
                ),
            ),
        ),
    )


@pytest.fixture
def school_entry(db_session: Session) -> None:
    add_school(db_session, 100)


@pytest.mark.parametrize(
    "query",
    ["学校", "がっこう", "ガッコウ", "ｶﾞｯｺｳ", "gakkou", "school", "scho"],
)
def test_search_returns_complete_entry(
    client: TestClient,
    school_entry: None,
    query: str,
):
    response = client.get(
        "/api/v1/search",
        params={"q": f"  {query}  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": query,
        "results": [
            {
                "source_id": 100,
                "is_common": True,
                "written_forms": ["学校"],
                "readings": [
                    {
                        "text": "がっこう",
                        "no_kanji": False,
                        "restricted_to": [],
                    },
                ],
                "senses": [
                    {
                        "glosses": [
                            {"text": "school", "language": "eng"},
                        ],
                        "parts_of_speech": ["noun"],
                        "restricted_to_written_forms": [],
                        "restricted_to_readings": [],
                    },
                ],
            },
        ],
        "limit": 30,
        "offset": 0,
        "has_more": False,
    }


def test_unmatched_query_returns_empty_results(
    client: TestClient,
    school_entry: None,
):
    response = client.get(
        "/api/v1/search",
        params={"q": "不存在の単語"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "不存在の単語",
        "results": [],
        "limit": 30,
        "offset": 0,
        "has_more": False,
    }


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query(client: TestClient, query: str):
    response = client.get(
        "/api/v1/search",
        params={"q": query},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Search query must not be empty",
    }


def test_missing_query(client: TestClient):
    response = client.get("/api/v1/search")

    assert response.status_code == 422


@pytest.mark.parametrize(
    "parameters",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"limit": "abc"},
        {"offset": "abc"},
    ],
)
def test_rejects_invalid_pagination(
    client: TestClient,
    parameters: dict,
):
    response = client.get(
        "/api/v1/search",
        params={"q": "school", **parameters},
    )

    assert response.status_code == 422


def test_repeated_language_parameters_control_search_and_display(
    client: TestClient,
    school_entry: None,
):
    default = client.get(
        "/api/v1/search",
        params={"q": "école"},
    )
    multilingual = client.get(
        "/api/v1/search",
        params=[
            ("q", "école"),
            ("languages", "eng"),
            ("languages", "fre"),
        ],
    )

    assert default.status_code == 200
    assert default.json()["results"] == []

    assert multilingual.status_code == 200
    entry = multilingual.json()["results"][0]
    assert entry["source_id"] == 100
    assert entry["senses"][0]["glosses"] == [
        {"text": "school", "language": "eng"},
        {"text": "école", "language": "fre"},
    ]


def test_api_paginates_distinct_entries(
    client: TestClient,
    db_session: Session,
):
    for source_id in reversed(range(100, 131)):
        add_school(db_session, source_id)

    first = client.get(
        "/api/v1/search",
        params={"q": "school"},
    )
    second = client.get(
        "/api/v1/search",
        params={"q": "school", "offset": 30},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_page = first.json()
    second_page = second.json()

    assert [entry["source_id"] for entry in first_page["results"]] == list(
        range(100, 130)
    )
    assert first_page["limit"] == 30
    assert first_page["has_more"] is True

    assert [entry["source_id"] for entry in second_page["results"]] == [130]
    assert second_page["offset"] == 30
    assert second_page["has_more"] is False
