from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry


def test_metadata_reaches_search_and_details(
    db_session: Session,
    client: TestClient,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=1000001,
            written_forms=("試験",),
            readings=(JmdictReading(text="しけん"),),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss("test", "eng"),
                        JmdictGloss("essai", "fre"),
                    ),
                    fields=("computing", "telecommunications"),
                    dialects=("Kansai-ben",),
                    notes=("First note.", "Second note."),
                ),
                JmdictSense(
                    glosses=(JmdictGloss("examination", "eng"),),
                ),
            ),
        ),
    )

    search = client.get(
        "/api/v1/search",
        params={"q": "試験", "languages": "fre"},
    )
    assert search.status_code == 200
    search_entry = next(
        entry for entry in search.json()["results"] if entry["source_id"] == 1000001
    )

    detail = client.get(
        "/api/v1/entries/1000001",
        params={"languages": "fre"},
    )
    assert detail.status_code == 200

    for entry in (search_entry, detail.json()):
        first, second = entry["senses"]

        assert first["fields"] == ["computing", "telecommunications"]
        assert first["dialects"] == ["Kansai-ben"]
        assert first["notes"] == ["First note.", "Second note."]
        assert first["glosses"] == [
            {"text": "essai", "language": "fre"},
        ]

        assert second["fields"] == []
        assert second["dialects"] == []
        assert second["notes"] == []
        assert second["glosses"] == []
