from xml.etree import ElementTree as ET

from jmdict import JmdictEntry, JmdictGloss, JmdictSense, parse_entry


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
        readings=("がっこう",),
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
        readings=("がっこう",),
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
        readings=("ありがとう",),
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
