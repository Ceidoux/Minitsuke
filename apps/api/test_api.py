from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_search_returns_normalized_query() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "  食べる  "},
    )

    assert response.status_code == 200
    assert response.json() == {"query": "食べる"}


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
