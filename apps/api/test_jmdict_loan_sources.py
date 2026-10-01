from xml.etree import ElementTree as ET

from jmdict import JmdictGloss, JmdictLoanSource, parse_entry


def test_preserves_loan_sources_and_their_order():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>100</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <lsource xml:lang="ger">Arbeit</lsource>
                <lsource xml:lang="fre" ls_type="part">travail</lsource>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.loan_sources == (
        JmdictLoanSource(text="Arbeit", language="ger"),
        JmdictLoanSource(
            text="travail",
            language="fre",
            source_type="part",
        ),
    )


def test_preserves_empty_sources_and_default_attributes():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>101</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <lsource/>
                <lsource xml:lang="fre"/>
                <lsource ls_wasei="y"/>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.loan_sources == (
        JmdictLoanSource(),
        JmdictLoanSource(language="fre"),
        JmdictLoanSource(wasei=True),
    )


def test_preserves_wasei_source_text():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>102</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <lsource ls_wasei="y">salaryman</lsource>
                <gloss>test definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.loan_sources == (JmdictLoanSource(text="salaryman", wasei=True),)


def test_keeps_sources_attached_to_their_sense():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>103</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <lsource xml:lang="ger">Arbeit</lsource>
                <gloss>first meaning</gloss>
            </sense>
            <sense>
                <gloss>second meaning</gloss>
            </sense>
        </entry>
        """
    )

    first, second = parse_entry(element).senses

    assert first.loan_sources == (JmdictLoanSource(text="Arbeit", language="ger"),)
    assert second.loan_sources == ()


def test_preserves_gloss_qualifiers_without_changing_text():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>104</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <gloss>ordinary meaning</gloss>
                <gloss g_type="lit">literal meaning</gloss>
                <gloss g_type="fig">figurative meaning</gloss>
                <gloss g_type="expl">explanation</gloss>
                <gloss xml:lang="fre" g_gend="f">école</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.glosses == (
        JmdictGloss("ordinary meaning", "eng"),
        JmdictGloss("literal meaning", "eng", gloss_type="lit"),
        JmdictGloss("figurative meaning", "eng", gloss_type="fig"),
        JmdictGloss("explanation", "eng", gloss_type="expl"),
        JmdictGloss("école", "fre", gender="f"),
    )


def test_preserves_unfamiliar_attribute_values():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>105</ent_seq>
            <r_ele>
                <reb>てすと</reb>
            </r_ele>
            <sense>
                <lsource xml:lang="xyz" ls_type="other">original</lsource>
                <gloss g_type="other" g_gend="other">definition</gloss>
            </sense>
        </entry>
        """
    )

    sense = parse_entry(element).senses[0]

    assert sense.loan_sources[0].language == "xyz"
    assert sense.loan_sources[0].source_type == "other"
    assert sense.glosses[0].gloss_type == "other"
    assert sense.glosses[0].gender == "other"
