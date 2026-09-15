from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_written_form_search_returns_entry() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "  食べる  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "食べる",
        "results": [
            {"written_form": "食べる", "reading": "たべる", "meanings": ["to eat"]}
        ],
    }


def test_reading_search_returns_entry() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "がっこう"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "がっこう",
        "results": [
            {"written_form": "学校", "reading": "がっこう", "meanings": ["school"]}
        ],
    }


def test_unmatched_query_returns_empty_results() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "不存在の単語"},
    )

    assert response.status_code == 200
    assert response.json() == {"query": "不存在の単語", "results": []}


def test_empty_query() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": ""},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Search query must not be empty"}


def test_whitespace_only_query() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Search query must not be empty"}


def test_missing_query() -> None:
    response = client.get(
        "/api/v1/search",
    )

    assert response.status_code == 422
