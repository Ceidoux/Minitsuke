from xml.etree import ElementTree as ET

from jmdict import parse_entry


def test_preserves_annotations_on_their_written_forms():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>100</ent_seq>
            <k_ele>
                <keb>学校</keb>
            </k_ele>
            <k_ele>
                <keb>學校</keb>
                <ke_inf>out-dated kanji or kanji usage</ke_inf>
                <ke_inf>rarely used kanji form</ke_inf>
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

    entry = parse_entry(element)

    assert entry.written_forms == ("学校", "學校")
    assert entry.written_form_info == {
        "學校": (
            "out-dated kanji or kanji usage",
            "rarely used kanji form",
        ),
    }
    assert entry.readings[0].info == ()


def test_preserves_reading_annotations_and_restrictions():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>101</ent_seq>
            <k_ele>
                <keb>明日</keb>
            </k_ele>
            <r_ele>
                <reb>あした</reb>
            </r_ele>
            <r_ele>
                <reb>あす</reb>
                <re_restr>明日</re_restr>
                <re_inf>out-dated or obsolete kana usage</re_inf>
                <re_inf>rarely used kana form</re_inf>
            </r_ele>
            <sense>
                <gloss>tomorrow</gloss>
            </sense>
        </entry>
        """
    )

    entry = parse_entry(element)
    first, second = entry.readings

    assert first.info == ()
    assert second.text == "あす"
    assert second.restricted_to == ("明日",)
    assert second.info == (
        "out-dated or obsolete kana usage",
        "rarely used kana form",
    )
    assert entry.written_form_info == {}


def test_missing_form_annotations_have_empty_defaults():
    element = ET.fromstring(
        """
        <entry>
            <ent_seq>102</ent_seq>
            <r_ele>
                <reb>こんにちは</reb>
                <re_nokanji/>
            </r_ele>
            <sense>
                <gloss>hello</gloss>
            </sense>
        </entry>
        """
    )

    entry = parse_entry(element)

    assert entry.written_forms == ()
    assert entry.written_form_info == {}
    assert entry.readings[0].info == ()
    assert entry.readings[0].no_kanji is True


def test_resolves_entities_in_form_annotations():
    element = ET.fromstring(
        """
        <!DOCTYPE entry [
            <!ENTITY iK "word containing irregular kanji usage">
            <!ENTITY ik "word containing irregular kana usage">
        ]>
        <entry>
            <ent_seq>103</ent_seq>
            <k_ele>
                <keb>試験</keb>
                <ke_inf>&iK;</ke_inf>
            </k_ele>
            <r_ele>
                <reb>しけん</reb>
                <re_inf>&ik;</re_inf>
            </r_ele>
            <sense>
                <gloss>test</gloss>
            </sense>
        </entry>
        """
    )

    entry = parse_entry(element)

    assert entry.written_form_info == {
        "試験": ("word containing irregular kanji usage",),
    }
    assert entry.readings[0].info == ("word containing irregular kana usage",)
