import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jmdict import (
    JmdictEntry,
    JmdictGloss,
    JmdictLoanSource,
    JmdictReading,
    JmdictSense,
)
from jmdict_importer import save_jmdict_entry


@pytest.mark.parametrize("language", ["eng", "fre"])
def test_loan_sources_and_gloss_qualifiers_reach_api(
    db_session: Session,
    client: TestClient,
    language: str,
):
    save_jmdict_entry(
        db_session,
        JmdictEntry(
            source_id=1000001,
            written_forms=(),
            readings=(JmdictReading(text="てすと"),),
            senses=(
                JmdictSense(
                    glosses=(
                        JmdictGloss(
                            "literal meaning",
                            "eng",
                            gloss_type="lit",
                        ),
                        JmdictGloss("école", "fre", gender="f"),
                    ),
                    loan_sources=(
                        JmdictLoanSource(text="Arbeit", language="ger"),
                        JmdictLoanSource(
                            text="travail",
                            language="fre",
                            source_type="part",
                        ),
                        JmdictLoanSource(wasei=True),
                    ),
                ),
                JmdictSense(
                    glosses=(JmdictGloss("ordinary meaning", "eng"),),
                ),
            ),
        ),
    )

    search = client.get(
        "/api/v1/search",
        params={"q": "てすと", "languages": language},
    )
    assert search.status_code == 200

    search_entry = next(
        entry for entry in search.json()["results"] if entry["source_id"] == 1000001
    )

    detail = client.get(
        "/api/v1/entries/1000001",
        params={"languages": language},
    )
    assert detail.status_code == 200

    expected_gloss = (
        {
            "text": "literal meaning",
            "language": "eng",
            "gloss_type": "lit",
            "gender": None,
        }
        if language == "eng"
        else {
            "text": "école",
            "language": "fre",
            "gloss_type": None,
            "gender": "f",
        }
    )

    for entry in (search_entry, detail.json()):
        first, second = entry["senses"]

        assert first["glosses"] == [expected_gloss]
        assert first["loan_sources"] == [
            {
                "text": "Arbeit",
                "language": "ger",
                "source_type": "full",
                "wasei": False,
            },
            {
                "text": "travail",
                "language": "fre",
                "source_type": "part",
                "wasei": False,
            },
            {
                "text": None,
                "language": "eng",
                "source_type": "full",
                "wasei": True,
            },
        ]

        assert second["loan_sources"] == []

        if language == "eng":
            assert second["glosses"] == [
                {
                    "text": "ordinary meaning",
                    "language": "eng",
                    "gloss_type": None,
                    "gender": None,
                },
            ]
        else:
            assert second["glosses"] == []
