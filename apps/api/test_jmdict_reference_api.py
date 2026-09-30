from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry


def test_references_reach_search_and_details(
    db_session: Session,
    client: TestClient,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=100,
            written_forms=(),
            readings=(JmdictReading(text="もと"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss("source", "eng"),),
                    cross_references=("丸・まる・2", "存在しない語"),
                    antonyms=("まる",),
                ),
                JmdictSense(
                    glosses=(JmdictGloss("source secondaire", "fre"),),
                    cross_references=("丸・1",),
                ),
            ),
        ),
    )

    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=200,
            written_forms=("丸",),
            readings=(JmdictReading(text="まる"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss("circle", "eng"),),
                    cross_references=("もと",),
                ),
                JmdictSense(
                    glosses=(JmdictGloss("zero", "eng"),),
                ),
            ),
        ),
    )

    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=300,
            written_forms=(),
            readings=(JmdictReading(text="まる"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss("another meaning", "eng"),),
                ),
            ),
        ),
    )

    search = client.get(
        "/api/v1/search",
        params={"q": "もと", "languages": "fre"},
    )
    assert search.status_code == 200

    source = next(
        entry for entry in search.json()["results"] if entry["source_id"] == 100
    )

    detail = client.get(
        "/api/v1/entries/100",
        params={"languages": "fre"},
    )
    assert detail.status_code == 200

    for entry in (source, detail.json()):
        first, second = entry["senses"]

        # Filtering out glosses must not shift the original sense positions.
        assert first["glosses"] == []
        assert first["cross_references"] == [
            {
                "text": "丸・まる・2",
                "targets": [
                    {"source_id": 200, "sense_position": 2},
                ],
            },
            {
                "text": "存在しない語",
                "targets": [],
            },
        ]
        assert first["antonyms"] == [
            {
                "text": "まる",
                "targets": [
                    {"source_id": 200, "sense_position": None},
                    {"source_id": 300, "sense_position": None},
                ],
            },
        ]

        assert second["cross_references"] == [
            {
                "text": "丸・1",
                "targets": [
                    {"source_id": 200, "sense_position": 1},
                ],
            },
        ]
        assert second["antonyms"] == []

    # The reverse link resolves without recursively expanding the source.
    target = client.get("/api/v1/entries/200")
    assert target.status_code == 200
    assert target.json()["senses"][0]["cross_references"] == [
        {
            "text": "もと",
            "targets": [
                {"source_id": 100, "sense_position": None},
            ],
        },
    ]
