from conjugation_service import build_conjugation_tables
from schemas import (
    JmdictEntryResponse,
    JmdictReadingResponse,
    JmdictSenseResponse,
)


def make_entry(
    written: str,
    reading: str,
    label: str,
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


def test_builds_suru_verb_from_noun():
    entry = make_entry(
        "確認",
        "かくにん",
        "noun or participle which takes the aux. verb suru",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].written == "確認する"
    assert tables[0].reading == "かくにんする"
    assert any(form.written == "確認しません" for form in tables[0].forms)


def test_respects_sense_and_reading_restrictions():
    entry = make_entry("食べる", "たべる", "Ichidan verb")
    entry.written_forms.append("喰べる")
    entry.readings[0].restricted_to = ["食べる"]
    entry.senses[0].restricted_to_written_forms = ["喰べる"]

    tables, _ = build_conjugation_tables(entry)
    assert tables == []

    entry.readings[0].restricted_to = ["喰べる"]
    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert [table.written for table in tables] == ["喰べる"]


def test_deduplicates_tables_and_preserves_sense_scope():
    entry = make_entry("食べる", "たべる", "Ichidan verb")
    entry.senses.append(entry.senses[0].model_copy(deep=True))

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].sense_positions == [1, 2]


def test_handles_standalone_suru_spelling():
    entry = make_entry("為る", "する", "suru verb - special class")

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert tables[0].written == "する"
    assert any(form.written == "します" for form in tables[0].forms)


def test_reports_unsupported_class():
    entry = make_entry(
        "得る",
        "うる",
        "Nidan verb with 'u' ending (archaic)",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert tables == []
    assert incomplete is True


def test_ordinary_noun_has_no_conjugation_section():
    entry = make_entry("学校", "がっこう", "noun (common) (futsuumeishi)")

    assert build_conjugation_tables(entry) == ([], False)


def test_copula_takes_priority_over_irregular_verb_tag():
    entry = make_entry("である", "である", "copula")
    entry.senses[0].parts_of_speech.insert(
        0,
        "Godan verb with 'ru' ending (irregular verb)",
    )
    entry.senses.append(entry.senses[0].model_copy(deep=True))

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "cop"
    assert tables[0].sense_positions == [1, 2]
    assert any(form.written == "であった" for form in tables[0].forms)
    assert {form.group for form in tables[0].forms} == {"basic"}


def test_builds_kana_only_copula():
    entry = make_entry("だ", "だ", "copula")
    entry.written_forms = []
    entry.readings[0].no_kanji = True

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].written == "だ"
    assert any(form.written == "だった" for form in tables[0].forms)


def test_builds_i_adjective_table():
    entry = make_entry("高い", "たかい", "adjective (keiyoushi)")

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "adj-i"
    assert any(form.written == "高かった" for form in tables[0].forms)


def test_builds_kana_only_ii_adjective_table():
    entry = make_entry(
        "いい",
        "いい",
        "adjective (keiyoushi) - yoi/ii class",
    )
    entry.written_forms = []
    entry.readings[0].no_kanji = True

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "adj-ix"
    assert any(form.reading == "よかった" for form in tables[0].forms)


def test_na_adjective_uses_tag_instead_of_final_kana():
    entry = make_entry(
        "きれい",
        "きれい",
        "adjectival nouns or quasi-adjectives (keiyodoshi)",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "adj-na"
    assert any(form.written == "きれいだった" for form in tables[0].forms)
    assert not any(form.written == "きれかった" for form in tables[0].forms)


def test_adjective_tables_preserve_sense_restrictions():
    entry = make_entry("高い", "たかい", "adjective (keiyoushi)")
    entry.senses[0].restricted_to_readings = ["別の読み"]

    assert build_conjugation_tables(entry) == ([], False)


def test_unsupported_adjective_reading_marks_tables_incomplete():
    entry = make_entry("高い", "たっけー", "adjective (keiyoushi)")

    assert build_conjugation_tables(entry) == ([], True)


def test_builds_kureru_special_table():
    entry = make_entry(
        "呉れる",
        "くれる",
        "Ichidan verb - kureru special class",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "v1-s"
    assert any(
        form.form == "imperative" and form.reading == "くれ" for form in tables[0].forms
    )


def test_builds_honorific_aru_table():
    entry = make_entry(
        "下さる",
        "くださる",
        "Godan verb - -aru special class",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "v5aru"
    assert any(
        form.written == "下さいます" and form.reading == "くださいます"
        for form in tables[0].forms
    )


def test_builds_existential_aru_table():
    entry = make_entry(
        "有る",
        "ある",
        "Godan verb with 'ru' ending (irregular verb)",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "v5r-i"
    assert any(
        form.form == "negative" and form.written == "ない" for form in tables[0].forms
    )


def test_builds_zuru_table():
    entry = make_entry(
        "信ずる",
        "しんずる",
        "Ichidan verb - zuru verb (alternative form of -jiru verbs)",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "vz"
    assert tables[0].written == "信ずる"
    assert any(
        form.written == "信じます" and form.reading == "しんじます"
        for form in tables[0].forms
    )


def test_builds_aisuru_table():
    entry = make_entry(
        "愛する",
        "あいする",
        "suru verb - special class",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert len(tables) == 1
    assert tables[0].verb_class == "vs-s-aisu"
    assert any(form.written == "愛さない" for form in tables[0].forms)
    assert any(form.written == "愛せる" for form in tables[0].forms)


def test_aisuru_profile_applies_to_expression():
    entry = make_entry(
        "こよなく愛する",
        "こよなくあいする",
        "suru verb - special class",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is False
    assert tables[0].verb_class == "vs-s-aisu"
    assert any(form.written == "こよなく愛さない" for form in tables[0].forms)


def test_shared_special_suru_table_reports_partial_coverage():
    entry = make_entry(
        "達する",
        "たっする",
        "suru verb - special class",
    )

    tables, incomplete = build_conjugation_tables(entry)

    assert incomplete is True
    assert len(tables) == 1
    assert tables[0].verb_class == "vs-s"
    assert any(form.written == "達します" for form in tables[0].forms)
    assert not any(form.group == "potential" for form in tables[0].forms)
