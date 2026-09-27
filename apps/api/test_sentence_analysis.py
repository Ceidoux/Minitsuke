import pytest

from sentence_analysis import MAX_SENTENCE_LENGTH, SentenceAnalyzer


@pytest.fixture(scope="module")
def analyzer() -> SentenceAnalyzer:
    return SentenceAnalyzer()


def test_segments_sentence_into_words(analyzer: SentenceAnalyzer):
    tokens = analyzer.analyze("このりんごを食べる")

    assert [token.surface for token in tokens] == [
        "この",
        "りんご",
        "を",
        "食べる",
    ]

    apple = tokens[1]
    assert apple.dictionary_form == "りんご"
    assert apple.normalized_form == "林檎"
    assert apple.reading == "リンゴ"
    assert apple.is_unknown is False


@pytest.mark.parametrize(
    ("text", "surface", "dictionary_form"),
    [
        ("昨日りんごを食べました。", "食べ", "食べる"),
        ("学校に行かなかった。", "行か", "行く"),
        ("内容を確認してください。", "し", "する"),
    ],
)
def test_recovers_dictionary_forms(
    analyzer: SentenceAnalyzer,
    text: str,
    surface: str,
    dictionary_form: str,
):
    tokens = analyzer.analyze(text)
    token = next(token for token in tokens if token.surface == surface)

    assert token.dictionary_form == dictionary_form


def test_preserves_compound_word(analyzer: SentenceAnalyzer):
    tokens = analyzer.analyze("国家公務員")

    assert [token.surface for token in tokens] == ["国家公務員"]


def test_positions_refer_to_original_text(analyzer: SentenceAnalyzer):
    text = "🍎 このりんごを食べました。"
    tokens = analyzer.analyze(text)

    for token in tokens:
        assert 0 <= token.start <= token.end <= len(text)
        assert token.surface == text[token.start : token.end]

    apple = next(token for token in tokens if token.surface == "りんご")
    assert apple.start == text.index("りんご")

    punctuation = tokens[-1]
    assert punctuation.surface == "。"
    assert punctuation.end == len(text)


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_rejects_blank_input(
    analyzer: SentenceAnalyzer,
    text: str,
):
    with pytest.raises(ValueError, match="Sentence must not be empty"):
        analyzer.analyze(text)


def test_rejects_oversized_input(analyzer: SentenceAnalyzer):
    with pytest.raises(ValueError, match="at most"):
        analyzer.analyze("あ" * (MAX_SENTENCE_LENGTH + 1))
