from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry


def test_form_annotations_reach_search_and_details(
    db_session: Session,
    client: TestClient,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=1000001,
            written_forms=("学校", "學校"),
            written_form_info={
                "學校": (
                    "out-dated kanji or kanji usage",
                    "rarely used kanji form",
                ),
            },
            readings=(
                JmdictReading(text="がっこう"),
                JmdictReading(
                    text="ガッコウ",
                    restricted_to=("學校",),
                    info=("rarely used kana form",),
                ),
            ),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss("school", "eng"),
                        JmdictGloss("école", "fre"),
                    ),
                ),
            ),
        ),
    )

    # Another entry shares the same strings but has no annotations.
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=1000002,
            written_forms=("学校", "學校"),
            readings=(JmdictReading(text="がっこう"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss("another meaning", "eng"),),
                ),
            ),
        ),
    )

    search = client.get(
        "/api/v1/search",
        params={"q": "学校", "languages": "fre"},
    )
    assert search.status_code == 200

    entries = {entry["source_id"]: entry for entry in search.json()["results"]}

    detail = client.get(
        "/api/v1/entries/1000001",
        params={"languages": "fre"},
    )
    assert detail.status_code == 200

    for entry in (entries[1000001], detail.json()):
        assert entry["written_forms"] == ["学校", "學校"]
        assert entry["written_form_info"] == {
            "學校": [
                "out-dated kanji or kanji usage",
                "rarely used kanji form",
            ],
        }
        assert entry["readings"] == [
            {
                "text": "がっこう",
                "no_kanji": False,
                "restricted_to": [],
                "info": [],
            },
            {
                "text": "ガッコウ",
                "no_kanji": False,
                "restricted_to": ["學校"],
                "info": ["rarely used kana form"],
            },
        ]
        assert entry["senses"][0]["glosses"] == [
            {
                "text": "école",
                "language": "fre",
                "gloss_type": None,
                "gender": None,
            },
        ]

    assert entries[1000002]["written_form_info"] == {}
    assert entries[1000002]["readings"][0]["info"] == []


def test_kana_only_entry_preserves_reading_annotations(
    db_session: Session,
    client: TestClient,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=1000003,
            written_forms=(),
            readings=(
                JmdictReading(
                    text="てすと",
                    no_kanji=True,
                    info=("word containing irregular kana usage",),
                ),
            ),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss("test", "eng"),),
                ),
            ),
        ),
    )

    response = client.get("/api/v1/entries/1000003")

    assert response.status_code == 200
    entry = response.json()

    assert entry["written_forms"] == []
    assert entry["written_form_info"] == {}
    assert entry["readings"][0]["no_kanji"] is True
    assert entry["readings"][0]["info"] == [
        "word containing irregular kana usage",
    ]
