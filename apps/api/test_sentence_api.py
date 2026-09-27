from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import sentence_api
from database import get_session
from jmdict_exact_repository import ExactCandidate
from sentence_analysis import MAX_SENTENCE_LENGTH, SentenceAnalyzer, SentenceToken
from sentence_api import get_sentence_analyzer, router
from sentence_service import ResolvedToken


@pytest.fixture
def api_context(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    session = Mock()
    analyzer = Mock(spec=SentenceAnalyzer)
    resolver = Mock(return_value=())

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_sentence_analyzer] = lambda: analyzer

    monkeypatch.setattr(sentence_api, "resolve_sentence", resolver)

    with TestClient(app) as client:
        yield client, resolver, session, analyzer


def test_returns_grouped_tokens_and_public_entry_ids(api_context):
    client, resolver, session, analyzer = api_context

    verb = ExactCandidate(
        entry_id=1,
        source_id=1358280,
        match_tier=0,
        is_common=True,
        frequency_band=None,
    )
    auxiliary = ExactCandidate(
        entry_id=2,
        source_id=2654250,
        match_tier=1,
        is_common=False,
        frequency_band=None,
    )

    resolver.return_value = (
        ResolvedToken(
            token=SentenceToken(
                surface="食べ",
                start=0,
                end=2,
                dictionary_form="食べる",
                normalized_form="食べる",
                reading="タベ",
                part_of_speech=("動詞", "*", "*", "*", "*", "*"),
                is_unknown=False,
            ),
            lookup_forms=("食べる",),
            candidates=(verb,),
        ),
        ResolvedToken(
            token=SentenceToken(
                surface="た",
                start=2,
                end=3,
                dictionary_form="た",
                normalized_form="た",
                reading="タ",
                part_of_speech=("助動詞", "*", "*", "*", "*", "*"),
                is_unknown=False,
            ),
            lookup_forms=("た",),
            candidates=(auxiliary,),
        ),
    )

    response = client.post("/api/v1/analyze", json={"text": "食べた"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["text"] == "食べた"
    assert payload["offset_unit"] == "unicode_code_points"
    assert len(payload["groups"]) == 1

    group = payload["groups"][0]
    assert group["surface"] == "食べた"
    assert (group["start"], group["end"]) == (0, 3)
    assert group["candidate_source_ids"] == [1358280]
    assert group["tokens"][0]["dictionary_form"] == "食べる"
    assert group["tokens"][1]["candidate_source_ids"] == [2654250]

    resolver.assert_called_once_with(
        session,
        "食べた",
        analyzer=analyzer,
    )


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({}, 422),
        ({"text": ""}, 422),
        ({"text": "   "}, 400),
        ({"text": "あ" * (MAX_SENTENCE_LENGTH + 1)}, 422),
    ],
)
def test_rejects_invalid_text_without_resolving(api_context, body, status):
    client, resolver, _, _ = api_context

    response = client.post("/api/v1/analyze", json=body)

    assert response.status_code == status
    resolver.assert_not_called()


def test_preserves_original_input_when_calling_resolver(api_context):
    client, resolver, session, analyzer = api_context
    text = " 🍎 食べました。 "

    response = client.post("/api/v1/analyze", json={"text": text})

    assert response.status_code == 200
    assert response.json()["text"] == text
    resolver.assert_called_once_with(session, text, analyzer=analyzer)
