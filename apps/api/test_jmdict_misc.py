from xml.etree import ElementTree as ET

from jmdict import parse_entry


def test_preserves_multiple_misc_tags_in_order():
    entry = parse_entry(
        ET.fromstring("""
        <entry>
          <ent_seq>100</ent_seq>
          <r_ele><reb>ことば</reb></r_ele>
          <sense>
            <misc>word usually written using kana alone</misc>
            <misc>abbreviation</misc>
            <gloss>example</gloss>
          </sense>
        </entry>
        """)
    )

    assert entry.senses[0].misc == (
        "word usually written using kana alone",
        "abbreviation",
    )


def test_misc_tags_do_not_leak_into_other_senses_or_languages():
    entry = parse_entry(
        ET.fromstring("""
        <entry>
          <ent_seq>100</ent_seq>
          <r_ele><reb>その</reb></r_ele>
          <sense>
            <misc>word usually written using kana alone</misc>
            <gloss>that</gloss>
          </sense>
          <sense>
            <gloss>um</gloss>
          </sense>
          <sense>
            <gloss xml:lang="fre">ce</gloss>
          </sense>
        </entry>
        """)
    )

    assert entry.senses[0].misc == ("word usually written using kana alone",)
    assert entry.senses[1].misc == ()
    assert entry.senses[2].misc == ()


def test_preserves_misc_alongside_sense_restrictions():
    entry = parse_entry(
        ET.fromstring("""
        <entry>
          <ent_seq>1000480</ent_seq>
          <k_ele><keb>阿呆陀羅</keb></k_ele>
          <r_ele><reb>あほんだら</reb></r_ele>
          <r_ele><reb>あほだら</reb></r_ele>
          <sense>
            <misc>word usually written using kana alone</misc>
            <gloss>fool</gloss>
          </sense>
          <sense>
            <stagr>あほだら</stagr>
            <misc>abbreviation</misc>
            <gloss>mock Buddhist sutra</gloss>
          </sense>
        </entry>
        """)
    )

    assert entry.senses[0].misc == ("word usually written using kana alone",)
    assert entry.senses[0].restricted_to_readings == ()
    assert entry.senses[1].misc == ("abbreviation",)
    assert entry.senses[1].restricted_to_readings == ("あほだら",)


def test_kana_usage_annotation_is_separate_from_no_kanji_reading_flag():
    entry = parse_entry(
        ET.fromstring("""
        <entry>
          <ent_seq>100</ent_seq>
          <k_ele><keb>此の</keb></k_ele>
          <r_ele><reb>この</reb></r_ele>
          <r_ele>
            <reb>こん</reb>
            <re_nokanji/>
          </r_ele>
          <sense>
            <misc>word usually written using kana alone</misc>
            <gloss>this</gloss>
          </sense>
        </entry>
        """)
    )

    assert entry.readings[0].no_kanji is False
    assert entry.readings[1].no_kanji is True
    assert entry.senses[0].misc == ("word usually written using kana alone",)
