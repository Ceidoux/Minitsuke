import pytest

from jmdict_reference import ReferenceCandidate, parse_reference_candidates


def test_simple_reference_has_one_candidate():
    assert parse_reference_candidates("同上") == (ReferenceCandidate(form="同上"),)


def test_proposes_form_and_sense_number():
    candidates = parse_reference_candidates("インナー・1")

    assert (
        ReferenceCandidate(
            form="インナー",
            sense_position=1,
        )
        in candidates
    )

    assert ReferenceCandidate(form="インナー・1") in candidates

    # Do not silently discard an explicit sense number.
    assert ReferenceCandidate(form="インナー") not in candidates


def test_proposes_written_form_reading_and_sense():
    candidates = parse_reference_candidates("丸・まる・1")

    assert (
        ReferenceCandidate(
            form="丸",
            reading="まる",
            sense_position=1,
        )
        in candidates
    )

    assert (
        ReferenceCandidate(
            form="丸・まる",
            sense_position=1,
        )
        in candidates
    )

    assert ReferenceCandidate(form="丸・まる・1") in candidates


def test_preserves_middle_dots_inside_a_dictionary_form():
    candidates = parse_reference_candidates("リズム・アンド・ブルース")

    assert (
        ReferenceCandidate(
            form="リズム・アンド・ブルース",
        )
        in candidates
    )


def test_preserves_middle_dots_before_a_sense_number():
    candidates = parse_reference_candidates("リズム・アンド・ブルース・1")

    assert (
        ReferenceCandidate(
            form="リズム・アンド・ブルース",
            sense_position=1,
        )
        in candidates
    )


def test_proposes_a_reading_that_contains_a_middle_dot():
    candidates = parse_reference_candidates("甲・こう・おつ・2")

    assert (
        ReferenceCandidate(
            form="甲",
            reading="こう・おつ",
            sense_position=2,
        )
        in candidates
    )

    assert (
        ReferenceCandidate(
            form="甲・こう",
            reading="おつ",
            sense_position=2,
        )
        in candidates
    )


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
def test_empty_reference_has_no_candidates(text: str):
    assert parse_reference_candidates(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "丸・0",
        "丸・-1",
        "丸・abc",
        "丸・１",
    ],
)
def test_does_not_interpret_invalid_sense_suffixes(text: str):
    candidates = parse_reference_candidates(text)

    assert ReferenceCandidate(form=text) in candidates
    assert all(candidate.sense_position is None for candidate in candidates)


def test_trims_outer_whitespace():
    assert parse_reference_candidates("  同上\n") == (ReferenceCandidate(form="同上"),)


def test_does_not_create_empty_form_or_reading_components():
    candidates = parse_reference_candidates("・丸・")

    assert all(candidate.form for candidate in candidates)
    assert all(candidate.reading != "" for candidate in candidates)


def test_candidates_are_unique():
    candidates = parse_reference_candidates("丸・まる・1")

    assert len(candidates) == len(set(candidates))
