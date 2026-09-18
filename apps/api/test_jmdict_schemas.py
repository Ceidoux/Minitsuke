from schemas import JmdictSearchResponse


def test_response_preserves_senses_languages_and_restrictions():
    payload = {
        "query": "学校",
        "results": [
            {
                "source_id": 1206730,
                "is_common": True,
                "written_forms": ["学校", "學校"],
                "readings": [
                    {
                        "text": "がっこう",
                        "no_kanji": False,
                        "restricted_to": ["学校"],
                    },
                ],
                "senses": [
                    {
                        "glosses": [
                            {"text": "school", "language": "eng"},
                            {"text": "école", "language": "fre"},
                        ],
                        "parts_of_speech": ["noun"],
                        "restricted_to_written_forms": ["学校"],
                        "restricted_to_readings": ["がっこう"],
                    },
                    {
                        "glosses": [
                            {"text": "academy", "language": "eng"},
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
        "has_more": True,
    }

    response = JmdictSearchResponse.model_validate(payload)

    assert response.model_dump(mode="json") == payload
    assert len(response.results[0].senses) == 2


def test_response_supports_kana_only_entry():
    response = JmdictSearchResponse.model_validate(
        {
            "query": "ありがとう",
            "results": [
                {
                    "source_id": 1000001,
                    "is_common": True,
                    "written_forms": [],
                    "readings": [
                        {
                            "text": "ありがとう",
                            "no_kanji": True,
                            "restricted_to": [],
                        },
                    ],
                    "senses": [
                        {
                            "glosses": [
                                {"text": "thank you", "language": "eng"},
                            ],
                            "parts_of_speech": [],
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
    )

    result = response.model_dump(mode="json")["results"][0]

    assert result["written_forms"] == []
    assert result["readings"] == [
        {
            "text": "ありがとう",
            "no_kanji": True,
            "restricted_to": [],
        },
    ]


def test_response_supports_empty_results():
    response = JmdictSearchResponse(
        query="存在しない検索語",
        results=[],
        limit=30,
        offset=0,
        has_more=False,
    )

    assert response.model_dump(mode="json") == {
        "query": "存在しない検索語",
        "results": [],
        "limit": 30,
        "offset": 0,
        "has_more": False,
    }
