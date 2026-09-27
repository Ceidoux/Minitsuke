import pytest

from deconjugation import InflectionCandidate
from deconjugation_service import entry_supports_inflection
from schemas import (
    JmdictEntryResponse,
    JmdictReadingResponse,
    JmdictSenseResponse,
)


def make_entry(
    label: str,
    *,
    written: str = "確認",
    reading: str = "かくにん",
) -> JmdictEntryResponse:
    return JmdictEntryResponse(
        source_id=100,
        is_common=True,
        written_forms=[written],
        readings=[
            JmdictReadingResponse(
                text=reading,
                no_kanji=False,
                restricted_to=[],
            )
        ],
        senses=[
            JmdictSenseResponse(
                glosses=[],
                parts_of_speech=[label],
                restricted_to_written_forms=[],
                restricted_to_readings=[],
            )
        ],
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("noun or participle which takes the aux. verb suru", True),
        ("noun (common) (futsuumeishi)", False),
        ("suru verb - included", False),
    ],
)
def test_requires_suru_noun_tag_for_noun_lookup(label: str, expected: bool):
    entry = make_entry(label)
    candidate = InflectionCandidate(
        lookup_forms=("確認する", "確認"),
        grammatical_class="suru",
        ending_forms=("ます", "た"),
    )

    assert entry_supports_inflection(entry, candidate, "確認") is expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Ichidan verb", True),
        ("noun (common) (futsuumeishi)", False),
        ("transitive verb", False),
    ],
)
def test_requires_verb_class_not_just_transitivity(label: str, expected: bool):
    entry = make_entry(label, written="食べる", reading="たべる")
    candidate = InflectionCandidate(
        lookup_forms=("食べる",),
        grammatical_class="verb",
        ending_forms=("ます", "た"),
    )

    assert entry_supports_inflection(entry, candidate, "食べる") is expected


def test_rejects_grammar_restricted_to_another_spelling():
    entry = make_entry("Ichidan verb", written="食べる", reading="たべる")
    entry.written_forms.append("喰べる")
    entry.senses[0].restricted_to_written_forms = ["喰べる"]
    candidate = InflectionCandidate(("食べる",), "verb", ("ます", "た"))

    assert not entry_supports_inflection(entry, candidate, "食べる")
    assert entry_supports_inflection(entry, candidate, "たべる")


def test_respects_reading_restrictions():
    entry = make_entry("Ichidan verb", written="食べる", reading="たべる")
    entry.written_forms.append("喰べる")
    entry.readings[0].restricted_to = ["食べる"]
    entry.senses[0].restricted_to_written_forms = ["喰べる"]
    candidate = InflectionCandidate(("たべる",), "verb", ("ます", "た"))

    assert not entry_supports_inflection(entry, candidate, "たべる")


def test_respects_sense_reading_restrictions():
    entry = make_entry("Ichidan verb", written="食べる", reading="たべる")
    entry.readings.append(
        JmdictReadingResponse(
            text="くべる",
            no_kanji=False,
            restricted_to=[],
        )
    )
    entry.senses[0].restricted_to_readings = ["くべる"]
    candidate = InflectionCandidate(("たべる",), "verb", ("ます", "た"))

    assert not entry_supports_inflection(entry, candidate, "たべる")


def test_no_kanji_reading_cannot_support_a_written_only_sense():
    entry = make_entry("Ichidan verb", written="食べる", reading="たべる")
    entry.readings[0].no_kanji = True
    entry.senses[0].restricted_to_written_forms = ["食べる"]
    candidate = InflectionCandidate(("たべる",), "verb", ("ます", "た"))

    assert not entry_supports_inflection(entry, candidate, "たべる")
