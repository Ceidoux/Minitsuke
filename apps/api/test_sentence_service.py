from unittest.mock import Mock

import pytest

import sentence_service
from jmdict_exact_repository import ExactCandidate
from sentence_analysis import SentenceAnalyzer, SentenceToken
from sentence_service import resolve_sentence


@pytest.fixture(autouse=True)
def candidate_labels_lookup(monkeypatch):
    lookup = Mock(return_value={})
    monkeypatch.setattr(sentence_service, "load_candidate_labels", lookup)
    monkeypatch.setattr(
        sentence_service,
        "load_candidate_spellings",
        Mock(return_value={}),
    )
    return lookup


def make_token(
    surface: str,
    *,
    dictionary_form: str | None = None,
    normalized_form: str | None = None,
    reading: str = "",
    pos: str = "名詞",
    start: int = 0,
    is_unknown: bool = False,
) -> SentenceToken:
    return SentenceToken(
        surface=surface,
        start=start,
        end=start + len(surface),
        dictionary_form=(surface if dictionary_form is None else dictionary_form),
        normalized_form=(surface if normalized_form is None else normalized_form),
        reading=reading,
        part_of_speech=(pos, "*", "*", "*", "*", "*"),
        is_unknown=is_unknown,
    )


def make_candidate(entry_id: int) -> ExactCandidate:
    return ExactCandidate(
        entry_id=entry_id,
        source_id=entry_id + 1_000_000,
        match_tier=0,
        is_common=False,
        frequency_band=None,
    )


def test_batches_forms_and_preserves_original_tokens(monkeypatch):
    tokens = (
        make_token("りんご", normalized_form="林檎"),
        make_token("を", pos="助詞", start=3),
        make_token(
            "食べ",
            dictionary_form="食べる",
            normalized_form="食べる",
            reading="タベ",
            pos="動詞",
            start=4,
        ),
    )
    apple = make_candidate(1)
    eat = make_candidate(2)

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = tokens

    lookup = Mock(
        return_value={
            "りんご": (apple,),
            "林檎": (apple,),
            "を": (),
            "食べる": (eat,),
        }
    )
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)
    session = Mock()

    result = resolve_sentence(
        session,
        "りんごを食べ",
        analyzer=analyzer,
    )

    analyzer.analyze.assert_called_once_with("りんごを食べ")
    lookup.assert_called_once_with(
        session,
        ("りんご", "林檎", "を", "食べる"),
    )

    assert tuple(item.token for item in result) == tokens
    assert result[0].candidates == (apple,)
    assert result[1].candidates == ()
    assert result[2].lookup_forms == ("食べる",)
    assert result[2].candidates == (eat,)


def test_combines_form_evidence_and_deduplicates(monkeypatch):
    first = make_candidate(1)
    second = make_candidate(2)
    additional = make_candidate(3)

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = (make_token("りんご", normalized_form="林檎"),)

    lookup = Mock(
        return_value={
            "りんご": (second, first),
            "林檎": (first, additional),
        }
    )
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)

    result = resolve_sentence(Mock(), "りんご", analyzer=analyzer)

    assert result[0].candidates == (first, second, additional)


def test_preserves_repeated_tokens_but_looks_up_form_once(monkeypatch):
    candidate = make_candidate(1)
    tokens = (
        make_token("学校"),
        make_token("学校", start=2),
    )

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = tokens

    lookup = Mock(return_value={"学校": (candidate,)})
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)
    session = Mock()

    result = resolve_sentence(session, "学校学校", analyzer=analyzer)

    lookup.assert_called_once_with(session, ("学校",))
    assert len(result) == 2
    assert result[0].token.start == 0
    assert result[1].token.start == 2
    assert result[0].candidates == (candidate,)
    assert result[1].candidates == (candidate,)


def test_preserves_punctuation_and_spaces_without_lookup(monkeypatch):
    tokens = (
        make_token("。", pos="補助記号"),
        make_token(" ", pos="空白", start=1),
    )

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = tokens

    lookup = Mock()
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)

    result = resolve_sentence(Mock(), "。 ", analyzer=analyzer)

    lookup.assert_not_called()
    assert tuple(item.token for item in result) == tokens
    assert all(item.lookup_forms == () for item in result)
    assert all(item.candidates == () for item in result)


def test_preserves_unknown_word_without_candidates(monkeypatch):
    token = make_token("ほげぴょん", is_unknown=True)

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = (token,)

    lookup = Mock(return_value={"ほげぴょん": ()})
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)

    result = resolve_sentence(Mock(), "ほげぴょん", analyzer=analyzer)

    assert result[0].token == token
    assert result[0].token.is_unknown
    assert result[0].lookup_forms == ("ほげぴょん",)
    assert result[0].candidates == ()


def test_uses_batched_grammar_labels_to_rank_particles(
    monkeypatch,
    candidate_labels_lookup,
):
    noun = make_candidate(1)
    particle = make_candidate(2)

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = (
        make_token("に", pos="助詞"),
        make_token("に", pos="助詞", start=1),
    )

    lookup = Mock(return_value={"に": (noun, particle)})
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)

    candidate_labels_lookup.return_value = {
        1: frozenset({"numeric"}),
        2: frozenset({"particle"}),
    }
    session = Mock()

    result = resolve_sentence(session, "にに", analyzer=analyzer)

    candidate_labels_lookup.assert_called_once_with(session, (1, 2))
    assert result[0].candidates == (particle, noun)
    assert result[1].candidates == (particle, noun)


def test_dictionary_form_support_beats_shared_normalized_spelling(
    monkeypatch,
    candidate_labels_lookup,
):
    suru = ExactCandidate(
        entry_id=1,
        source_id=1157170,
        match_tier=1,
        is_common=True,
        frequency_band=None,
    )
    suru_written = ExactCandidate(
        entry_id=1,
        source_id=1157170,
        match_tier=0,
        is_common=True,
        frequency_band=None,
    )
    naru = ExactCandidate(
        entry_id=2,
        source_id=1375610,
        match_tier=0,
        is_common=True,
        frequency_band=34,
    )

    analyzer = Mock(spec=SentenceAnalyzer)
    analyzer.analyze.return_value = (
        make_token(
            "し",
            dictionary_form="する",
            normalized_form="為る",
            pos="動詞",
        ),
    )

    lookup = Mock(
        return_value={
            "する": (suru,),
            "為る": (naru, suru_written),
        }
    )
    monkeypatch.setattr(sentence_service, "find_exact_candidates", lookup)

    candidate_labels_lookup.return_value = {
        1: frozenset({"suru verb - included", "transitive verb"}),
        2: frozenset({"Godan verb with 'ru' ending", "intransitive verb"}),
    }

    result = resolve_sentence(Mock(), "し", analyzer=analyzer)

    assert result[0].candidates == (suru_written, naru)
