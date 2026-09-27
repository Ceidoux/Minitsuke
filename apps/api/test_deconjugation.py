
import pytest

from deconjugation import extract_inflection_candidate
from sentence_analysis import SentenceAnalyzer


@pytest.fixture(scope="module")
def analyzer() -> SentenceAnalyzer:
    return SentenceAnalyzer()


@pytest.mark.parametrize(
    ("text", "lookup_forms", "grammatical_class", "ending_forms"),
    [
        ("食べました", ("食べる",), "verb", ("ます", "た")),
        ("行かなかった", ("行く",), "verb", ("ない", "た")),
        ("高かった", ("高い",), "adjective", ("た",)),
        ("されている", ("する",), "suru", ("れる", "て", "いる")),
        (
            "確認しました",
            ("確認する", "確認"),
            "suru",
            ("ます", "た"),
        ),
        (
            "食べさせられました",
            ("食べる",),
            "verb",
            ("させる", "られる", "ます", "た"),
        ),
    ],
)
def test_extracts_supported_inflections(
    analyzer: SentenceAnalyzer,
    text: str,
    lookup_forms: tuple[str, ...],
    grammatical_class: str,
    ending_forms: tuple[str, ...],
):
    candidate = extract_inflection_candidate(text, analyzer.analyze(text))

    assert candidate is not None
    assert candidate.lookup_forms == lookup_forms
    assert candidate.grammatical_class == grammatical_class
    assert candidate.ending_forms == ending_forms


@pytest.mark.parametrize(
    "text",
    [
        "学校",
        "国家公務員",
        "食べる",
        "学校に行かなかった",
        "昨日食べました",
        "食べました。",
        "食べ ました",
    ],
)
def test_does_not_treat_other_queries_as_supported_inflections(
    analyzer: SentenceAnalyzer,
    text: str,
):
    candidate = extract_inflection_candidate(text, analyzer.analyze(text))

    assert candidate is None


def test_empty_tokens_produce_no_candidate():
    assert extract_inflection_candidate("", ()) is None
