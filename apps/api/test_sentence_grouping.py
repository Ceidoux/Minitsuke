import pytest

from jmdict_exact_repository import ExactCandidate
from sentence_analysis import SentenceToken
from sentence_grouping import group_sentence
from sentence_service import ResolvedToken


def make_resolved(
    surface: str,
    start: int,
    category: str,
    *,
    candidates: tuple[ExactCandidate, ...] = (),
) -> ResolvedToken:
    token = SentenceToken(
        surface=surface,
        start=start,
        end=start + len(surface),
        dictionary_form=surface,
        normalized_form=surface,
        reading="",
        part_of_speech=(category, "*", "*", "*", "*", "*"),
        is_unknown=False,
    )

    return ResolvedToken(
        token=token,
        lookup_forms=(surface,),
        candidates=candidates,
    )


@pytest.mark.parametrize(
    ("text", "pieces"),
    [
        (
            "食べました",
            (
                ("食べ", 0, "動詞"),
                ("まし", 2, "助動詞"),
                ("た", 4, "助動詞"),
            ),
        ),
        (
            "行かなかった",
            (
                ("行か", 0, "動詞"),
                ("なかっ", 2, "助動詞"),
                ("た", 5, "助動詞"),
            ),
        ),
        (
            "高かった",
            (
                ("高かっ", 0, "形容詞"),
                ("た", 3, "助動詞"),
            ),
        ),
    ],
)
def test_groups_predicate_and_following_auxiliaries(text, pieces):
    resolved = tuple(
        make_resolved(surface, start, category) for surface, start, category in pieces
    )

    groups = group_sentence(text, resolved)

    assert len(groups) == 1
    assert groups[0].surface == text
    assert groups[0].start == 0
    assert groups[0].end == len(text)
    assert groups[0].tokens == resolved


def test_group_uses_head_candidates_and_preserves_auxiliary_candidates():
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

    resolved = (
        make_resolved("食べ", 0, "動詞", candidates=(verb,)),
        make_resolved("た", 2, "助動詞", candidates=(auxiliary,)),
    )

    group = group_sentence("食べた", resolved)[0]

    assert group.candidates == (verb,)
    assert group.tokens[1].candidates == (auxiliary,)


def test_particles_and_punctuation_remain_separate():
    text = "りんごを食べました。"
    resolved = (
        make_resolved("りんご", 0, "名詞"),
        make_resolved("を", 3, "助詞"),
        make_resolved("食べ", 4, "動詞"),
        make_resolved("まし", 6, "助動詞"),
        make_resolved("た", 8, "助動詞"),
        make_resolved("。", 9, "補助記号"),
    )

    groups = group_sentence(text, resolved)

    assert [group.surface for group in groups] == [
        "りんご",
        "を",
        "食べました",
        "。",
    ]
    assert "".join(group.surface for group in groups) == text


def test_space_prevents_grouping():
    text = "食べ た"
    resolved = (
        make_resolved("食べ", 0, "動詞"),
        make_resolved(" ", 2, "空白"),
        make_resolved("た", 3, "助動詞"),
    )

    groups = group_sentence(text, resolved)

    assert [group.surface for group in groups] == ["食べ", " ", "た"]


def test_offset_gap_prevents_grouping_even_without_space_token():
    resolved = (
        make_resolved("食べ", 0, "動詞"),
        make_resolved("た", 3, "助動詞"),
    )

    groups = group_sentence("食べ た", resolved)

    assert [group.surface for group in groups] == ["食べ", "た"]


def test_does_not_merge_across_connecting_particle():
    text = "確認してください"
    resolved = (
        make_resolved("確認", 0, "名詞"),
        make_resolved("し", 2, "動詞"),
        make_resolved("て", 3, "助詞"),
        make_resolved("ください", 4, "動詞"),
    )

    groups = group_sentence(text, resolved)

    assert [group.surface for group in groups] == [
        "確認",
        "し",
        "て",
        "ください",
    ]


def test_does_not_attach_auxiliary_to_noun():
    resolved = (
        make_resolved("学生", 0, "名詞"),
        make_resolved("だ", 2, "助動詞"),
    )

    groups = group_sentence("学生だ", resolved)

    assert [group.surface for group in groups] == ["学生", "だ"]


def test_empty_tokens_produce_no_groups():
    assert group_sentence("", ()) == ()
