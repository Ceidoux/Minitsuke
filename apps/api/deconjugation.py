from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

from sentence_analysis import SentenceToken

GrammaticalClass = Literal["verb", "adjective", "suru"]


@dataclass(frozen=True)
class InflectionCandidate:
    lookup_forms: tuple[str, ...]
    grammatical_class: GrammaticalClass
    ending_forms: tuple[str, ...]


VERB_ENDINGS = frozenset(
    {
        ("ます",),
        ("ます", "た"),
        ("ない",),
        ("ない", "た"),
        ("た",),
        ("れる",),
        ("られる",),
        ("て", "いる"),
        ("で", "いる"),
        ("れる", "て", "いる"),
        ("られる", "て", "いる"),
        ("させる", "られる", "ます", "た"),
        ("せる", "られる", "ます", "た"),
    }
)

ADJECTIVE_ENDINGS = frozenset(
    {
        ("た",),
        ("ない",),
        ("ない", "た"),
    }
)


def _category(token: SentenceToken) -> str:
    return token.part_of_speech[0] if token.part_of_speech else ""


def _is_supported_ending_token(token: SentenceToken) -> bool:
    category = _category(token)

    if category == "助動詞":
        return True

    if category == "助詞" and token.part_of_speech[1:2] == ("接続助詞",):
        return token.dictionary_form in {"て", "で"}

    return (
        category == "動詞"
        and token.part_of_speech[1:2] == ("非自立可能",)
        and token.dictionary_form == "いる"
    )


def extract_inflection_candidate(
    text: str,
    tokens: tuple[SentenceToken, ...],
) -> InflectionCandidate | None:
    if not tokens or any(token.is_unknown for token in tokens):
        return None

    if tokens[0].start != 0 or tokens[-1].end != len(text):
        return None

    if any(left.end != right.start for left, right in pairwise(tokens)):
        return None

    if any(
        token.surface != text[token.start : token.end] or not token.surface.strip()
        for token in tokens
    ):
        return None

    first = tokens[0]
    head_index = 0
    category = _category(first)

    if category == "動詞":
        grammatical_class: GrammaticalClass = (
            "suru" if first.dictionary_form == "する" else "verb"
        )
        lookup_forms = (first.dictionary_form,)
    elif category == "形容詞":
        grammatical_class = "adjective"
        lookup_forms = (first.dictionary_form,)
    elif (
        first.part_of_speech[:3] == ("名詞", "普通名詞", "サ変可能")
        and len(tokens) > 1
        and _category(tokens[1]) == "動詞"
        and tokens[1].dictionary_form == "する"
    ):
        head_index = 1
        grammatical_class = "suru"
        noun = first.dictionary_form
        lookup_forms = (noun + "する", noun)
    else:
        return None

    ending = tokens[head_index + 1 :]
    ending_forms = tuple(token.dictionary_form for token in ending)
    supported_endings = (
        ADJECTIVE_ENDINGS if grammatical_class == "adjective" else VERB_ENDINGS
    )

    if ending_forms not in supported_endings:
        return None

    if not all(_is_supported_ending_token(token) for token in ending):
        return None

    return InflectionCandidate(
        lookup_forms=lookup_forms,
        grammatical_class=grammatical_class,
        ending_forms=ending_forms,
    )
