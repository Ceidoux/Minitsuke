from xml.etree import ElementTree as ET

from jmdict import parse_entry


def test_preserves_sense_metadata_and_order():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>100</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <pos>noun</pos>
                <field>computing</field>
                <field>telecommunications</field>
                <dial>Kansai-ben</dial>
                <dial>Kyoto-ben</dial>
                <s_inf>Used in technical contexts.</s_inf>
                <s_inf>Additional explanation.</s_inf>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    entry = parse_entry(element)
    sense = entry.senses[0]

    assert sense.fields == ("computing", "telecommunications")
    assert sense.dialects == ("Kansai-ben", "Kyoto-ben")
    assert sense.notes == (
        "Used in technical contexts.",
        "Additional explanation.",
    )
    assert sense.parts_of_speech == ("noun",)
    assert sense.glosses[0].text == "test definition"


def test_missing_sense_metadata_defaults_to_empty_tuples():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>101</ent_seq>
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

    assert sense.fields == ()
    assert sense.dialects == ()
    assert sense.notes == ()


def test_keeps_explicit_metadata_attached_to_its_sense():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>102</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <field>music</field>
                <dial>Kansai-ben</dial>
                <s_inf>Explanation for the first meaning.</s_inf>
                <gloss>first meaning</gloss>
            </sense>
            <sense>
                <field>medicine</field>
                <dial>Tosa-ben</dial>
                <s_inf>Explanation for the second meaning.</s_inf>
                <gloss>second meaning</gloss>
            </sense>
        </entry>
        """
    )

    first, second = parse_entry(element).senses

    assert first.fields == ("music",)
    assert first.dialects == ("Kansai-ben",)
    assert first.notes == ("Explanation for the first meaning.",)

    assert second.fields == ("medicine",)
    assert second.dialects == ("Tosa-ben",)
    assert second.notes == ("Explanation for the second meaning.",)


def test_resolves_entity_labels_in_sense_metadata():
    element = ET.fromstring(
        """
        <!DOCTYPE entry [
            <!ENTITY comp "computing">
            <!ENTITY ksb "Kansai-ben">
        ]>
        <entry>
            <ent_seq>103</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <field>&comp;</field>
                <dial>&ksb;</dial>
                <s_inf>Includes A &amp; B.</s_inf>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.fields == ("computing",)
    assert sense.dialects == ("Kansai-ben",)
    assert sense.notes == ("Includes A & B.",)
