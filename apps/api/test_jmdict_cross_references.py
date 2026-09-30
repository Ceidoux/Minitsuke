from xml.etree import ElementTree as ET

from jmdict import parse_entry


def test_preserves_reference_text_and_order():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>100</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <xref>同上</xref>
                <xref>丸・まる・1</xref>
                <xref>二重丸</xref>
                <ant>インナー・1</ant>
                <ant>ルーラル</ant>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.cross_references == (
        "同上",
        "丸・まる・1",
        "二重丸",
    )
    assert sense.antonyms == (
        "インナー・1",
        "ルーラル",
    )


def test_keeps_references_attached_to_their_senses():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>101</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <xref>丸・まる・1</xref>
                <ant>インナー・1</ant>
                <gloss>first meaning</gloss>
            </sense>
            <sense>
                <xref>二重丸</xref>
                <ant>ルーラル</ant>
                <gloss>second meaning</gloss>
            </sense>
            <sense>
                <gloss>third meaning</gloss>
            </sense>
        </entry>
        """
    )

    first, second, third = parse_entry(element).senses

    assert first.cross_references == ("丸・まる・1",)
    assert first.antonyms == ("インナー・1",)

    assert second.cross_references == ("二重丸",)
    assert second.antonyms == ("ルーラル",)

    assert third.cross_references == ()
    assert third.antonyms == ()


def test_does_not_split_middle_dots_during_xml_parsing():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>102</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <xref>リズム・アンド・ブルース</xref>
                <xref>リズム・アンド・ブルース・1</xref>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.cross_references == (
        "リズム・アンド・ブルース",
        "リズム・アンド・ブルース・1",
    )


def test_missing_references_default_to_empty_tuples():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>103</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.cross_references == ()
    assert sense.antonyms == ()
