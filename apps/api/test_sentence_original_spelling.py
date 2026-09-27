from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from sentence_analysis import SentenceAnalyzer, SentenceToken
from sentence_service import resolve_sentence


def add_entry(
    session: Session,
    source_id: int,
    *,
    reading: str,
    written_forms: tuple[str, ...],
    band: int | None,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=written_forms,
            readings=(JmdictReading(text=reading),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="example", language="eng"),),
                    parts_of_speech=("noun (common) (futsuumeishi)",),
                ),
            ),
            is_common=True,
            frequency_band=band,
        ),
    )


@pytest.mark.parametrize(
    ("surface", "dictionary_form", "expected"),
    [
        ("ジム", "ジム", [200, 100]),
        ("ｼﾞﾑ", "ジム", [200, 100]),
        ("じむ", "じむ", [100, 200]),
    ],
)
def test_original_kana_script_precedes_frequency(
    db_session: Session,
    surface,
    dictionary_form,
    expected,
):
    add_entry(
        db_session,
        100,
        reading="じむ",
        written_forms=("事務",),
        band=1,
    )
    add_entry(
        db_session,
        200,
        reading="ジム",
        written_forms=(),
        band=None,
    )

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = (
        SentenceToken(
            surface=surface,
            start=0,
            end=len(surface),
            dictionary_form=dictionary_form,
            normalized_form="ジム",
            reading="ジム",
            part_of_speech=("名詞", "普通名詞", "一般", "*", "*", "*"),
            is_unknown=False,
        ),
    )

    result = resolve_sentence(
        db_session,
        surface,
        analyzer=analyzer,
    )

    assert [candidate.source_id for candidate in result[0].candidates] == expected
