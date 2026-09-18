from xml.etree import ElementTree as ET

import pytest

from jmdict import parse_entry


def make_entry(
    written_tags: tuple[str, ...] = (),
    reading_tags: tuple[str, ...] = (),
    *,
    include_written_form: bool = True,
) -> ET.Element:
    entry = ET.Element("entry")
    ET.SubElement(entry, "ent_seq").text = "1000001"

    if include_written_form:
        written = ET.SubElement(entry, "k_ele")
        ET.SubElement(written, "keb").text = "学校"

        for tag in written_tags:
            ET.SubElement(written, "ke_pri").text = tag

    reading = ET.SubElement(entry, "r_ele")
    ET.SubElement(reading, "reb").text = "がっこう"

    for tag in reading_tags:
        ET.SubElement(reading, "re_pri").text = tag

    sense = ET.SubElement(entry, "sense")
    ET.SubElement(sense, "gloss").text = "school"

    return entry


@pytest.mark.parametrize(
    ("written_tags", "reading_tags", "expected"),
    [
        ((), (), None),
        (("nf01",), (), 1),
        ((), ("nf48",), 48),
        (("nf12",), ("nf03",), 3),
        (("nf03", "nf03"), ("nf03",), 3),
        (("news1", "ichi1"), ("gai1",), None),
    ],
)
def test_extracts_best_frequency_band(
    written_tags: tuple[str, ...],
    reading_tags: tuple[str, ...],
    expected: int | None,
):
    entry = parse_entry(make_entry(written_tags, reading_tags))

    assert entry.frequency_band == expected


@pytest.mark.parametrize(
    "tag",
    ["nf00", "nf", "nfxx", "nf-1", "nf1", "nf001"],
)
def test_ignores_malformed_frequency_tags(tag: str):
    entry = parse_entry(make_entry(written_tags=(tag,)))

    assert entry.frequency_band is None


def test_frequency_band_does_not_make_entry_common():
    entry = parse_entry(make_entry(written_tags=("nf01",)))

    assert entry.frequency_band == 1
    assert entry.is_common is False


def test_frequency_band_and_commonness_are_independent():
    entry = parse_entry(
        make_entry(written_tags=("ichi1", "nf12")),
    )

    assert entry.frequency_band == 12
    assert entry.is_common is True


def test_kana_only_entry_can_have_frequency_band():
    entry = parse_entry(
        make_entry(
            reading_tags=("nf05",),
            include_written_form=False,
        )
    )

    assert entry.written_forms == ()
    assert entry.frequency_band == 5


def test_checks_all_written_forms():
    element = make_entry(written_tags=("nf12",))

    alternative = ET.SubElement(element, "k_ele")
    ET.SubElement(alternative, "keb").text = "學校"
    ET.SubElement(alternative, "ke_pri").text = "nf02"

    entry = parse_entry(element)

    assert entry.frequency_band == 2
