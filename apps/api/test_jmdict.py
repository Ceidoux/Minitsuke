from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from jmdict import (
    JmdictEntry,
    JmdictGloss,
    JmdictReading,
    JmdictSense,
    parse_entry,
    read_jmdict,
)


def test_parses_basic_entry() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>123</ent_seq>
            <k_ele>
                <keb>学校</keb>
            </k_ele>
            <r_ele>
                <reb>がっこう</reb>
            </r_ele>
            <sense>
                <gloss>school</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element) == JmdictEntry(
        source_id=123,
        written_forms=("学校",),
        readings=(JmdictReading(text="がっこう"),),
        senses=(JmdictSense(glosses=(JmdictGloss(text="school", language="eng"),)),),
    )


def test_parses_two_sense_entry() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>123</ent_seq>
            <k_ele>
                <keb>学校</keb>
            </k_ele>
            <r_ele>
                <reb>がっこう</reb>
            </r_ele>
            <sense>
                <gloss>school</gloss>
            </sense>
            <sense>
                <gloss>establishment</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element) == JmdictEntry(
        source_id=123,
        written_forms=("学校",),
        readings=(JmdictReading(text="がっこう"),),
        senses=(
            JmdictSense(glosses=(JmdictGloss(text="school", language="eng"),)),
            JmdictSense(glosses=(JmdictGloss(text="establishment", language="eng"),)),
        ),
    )


def test_parses_kana_only_entry() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>124</ent_seq>
            <r_ele>
                <reb>ありがとう</reb>
            </r_ele>
            <sense>
                <gloss>thank you</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element) == JmdictEntry(
        source_id=124,
        written_forms=(),
        readings=(JmdictReading(text="ありがとう"),),
        senses=(JmdictSense(glosses=(JmdictGloss(text="thank you", language="eng"),)),),
    )


def test_preserves_gloss_languages() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>125</ent_seq>
            <r_ele>
                <reb>がっこう</reb>
            </r_ele>
            <sense>
                <gloss xml:lang="eng">school</gloss>
                <gloss xml:lang="fre">école</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element).senses == (
        JmdictSense(
            glosses=(
                JmdictGloss(text="school", language="eng"),
                JmdictGloss(text="école", language="fre"),
            ),
        ),
    )


def test_preserves_reading_restrictions() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>126</ent_seq>
            <k_ele><keb>表記甲</keb></k_ele>
            <k_ele><keb>表記乙</keb></k_ele>
            <r_ele>
                <reb>こう</reb>
                <re_restr>表記甲</re_restr>
            </r_ele>
            <r_ele>
                <reb>おつ</reb>
                <re_restr>表記乙</re_restr>
            </r_ele>
            <sense><gloss>test meaning</gloss></sense>
        </entry>
        """
    )

    assert parse_entry(element).readings == (
        JmdictReading(text="こう", restricted_to=("表記甲",)),
        JmdictReading(text="おつ", restricted_to=("表記乙",)),
    )


def test_preserves_no_kanji() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>126</ent_seq>
            <k_ele><keb>表記甲</keb></k_ele>
            <r_ele>
                <reb>こう</reb>
                <re_nokanji/>
            </r_ele>
            <sense><gloss>test meaning</gloss></sense>
        </entry>
        """
    )

    assert parse_entry(element).readings == (
        JmdictReading(
            text="こう",
            no_kanji=True,
        ),
    )


def test_preserves_sense_restrictions() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>127</ent_seq>
            <k_ele><keb>表記甲</keb></k_ele>
            <k_ele><keb>表記乙</keb></k_ele>
            <r_ele><reb>こう</reb></r_ele>
            <r_ele><reb>おつ</reb></r_ele>
            <sense>
                <stagk>表記甲</stagk>
                <stagr>こう</stagr>
                <gloss>restricted test meaning</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element).senses == (
        JmdictSense(
            glosses=(
                JmdictGloss(
                    text="restricted test meaning",
                    language="eng",
                ),
            ),
            restricted_to_written_forms=("表記甲",),
            restricted_to_readings=("こう",),
        ),
    )


def test_preserves_multiple_parts_of_speech() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>128</ent_seq>
            <r_ele><reb>てすと</reb></r_ele>
            <sense>
                <pos>noun (common) (futsuumeishi)</pos>
                <pos>adverb (fukushi)</pos>
                <gloss>test meaning</gloss>
            </sense>
        </entry>
        """
    )

    assert parse_entry(element).senses[0].parts_of_speech == (
        "noun (common) (futsuumeishi)",
        "adverb (fukushi)",
    )


def test_inherits_and_replaces_parts_of_speech() -> None:
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>129</ent_seq>
            <r_ele><reb>てすと</reb></r_ele>
            <sense>
                <pos>noun (common) (futsuumeishi)</pos>
                <gloss>first meaning</gloss>
            </sense>
            <sense>
                <gloss>second meaning</gloss>
            </sense>
            <sense>
                <pos>adverb (fukushi)</pos>
                <gloss>third meaning</gloss>
            </sense>
            <sense>
                <gloss>fourth meaning</gloss>
            </sense>
        </entry>
        """
    )

    entry = parse_entry(element)

    assert tuple(sense.parts_of_speech for sense in entry.senses) == (
        ("noun (common) (futsuumeishi)",),
        ("noun (common) (futsuumeishi)",),
        ("adverb (fukushi)",),
        ("adverb (fukushi)",),
    )


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        (
            "<entry><r_ele><reb>ねこ</reb></r_ele><sense/></entry>",
            "JMdict entry is missing ent_seq",
        ),
        (
            """
            <entry>
                <ent_seq>abc</ent_seq>
                <r_ele><reb>ねこ</reb></r_ele>
                <sense/>
            </entry>
            """,
            "JMdict ent_seq must be an integer",
        ),
        (
            "<entry><ent_seq>130</ent_seq><sense/></entry>",
            "JMdict entry must contain at least one reading",
        ),
        (
            """
            <entry>
                <ent_seq>130</ent_seq>
                <r_ele><reb>   </reb></r_ele>
                <sense/>
            </entry>
            """,
            "JMdict reading must not be blank",
        ),
        (
            """
            <entry>
                <ent_seq>130</ent_seq>
                <r_ele><reb>ねこ</reb></r_ele>
            </entry>
            """,
            "JMdict entry must contain at least one sense",
        ),
    ],
    ids=[
        "missing-id",
        "invalid-id",
        "missing-reading",
        "blank-reading",
        "missing-sense",
    ],
)
def test_rejects_invalid_entry(xml: str, message: str) -> None:
    element = ET.fromstring(xml)

    with pytest.raises(ValueError) as error:
        parse_entry(element)

    assert str(error.value) == message


def test_reads_multiple_entries_and_expands_entities(tmp_path: Path) -> None:
    path = tmp_path / "sample.xml"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE JMdict [
            <!ENTITY n "noun (common) (futsuumeishi)">
        ]>
        <JMdict>
            <entry>
                <ent_seq>201</ent_seq>
                <k_ele><keb>学校</keb></k_ele>
                <r_ele><reb>がっこう</reb></r_ele>
                <sense>
                    <pos>&n;</pos>
                    <gloss>school</gloss>
                </sense>
            </entry>
            <entry>
                <ent_seq>202</ent_seq>
                <r_ele><reb>ありがとう</reb></r_ele>
                <sense><gloss>thank you</gloss></sense>
            </entry>
        </JMdict>
        """,
        encoding="utf-8",
    )

    assert list(read_jmdict(path)) == [
        JmdictEntry(
            source_id=201,
            written_forms=("学校",),
            readings=(JmdictReading(text="がっこう"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="school", language="eng"),),
                    parts_of_speech=("noun (common) (futsuumeishi)",),
                ),
            ),
        ),
        JmdictEntry(
            source_id=202,
            written_forms=(),
            readings=(JmdictReading(text="ありがとう"),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="thank you", language="eng"),),
                ),
            ),
        ),
    ]


def test_rejects_wrong_document_root(tmp_path: Path) -> None:
    path = tmp_path / "wrong.xml"
    path.write_text("<other/>", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected JMdict root element"):
        list(read_jmdict(path))
