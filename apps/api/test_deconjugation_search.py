import pytest
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from jmdict_search import search_jmdict


def add_entry(
    session: Session,
    source_id: int,
    *,
    forms: tuple[str, ...],
    reading: str,
    label: str,
) -> None:
    save_jmdict_entry(
        session,
        JmdictEntry(
            source_id=source_id,
            written_forms=forms,
            readings=(JmdictReading(text=reading),),
            senses=(
                JmdictSense(
                    glosses=(JmdictGloss(text="test definition", language="eng"),),
                    parts_of_speech=(label,),
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    ("query", "forms", "reading", "label"),
    [
        ("食べました", ("食べる",), "たべる", "Ichidan verb"),
        ("たべました", ("食べる",), "たべる", "Ichidan verb"),
        ("されている", ("為る",), "する", "suru verb - included"),
        (
            "確認しました",
            ("確認",),
            "かくにん",
            "noun or participle which takes the aux. verb suru",
        ),
        ("高かった", ("高い",), "たかい", "adjective (keiyoushi)"),
    ],
)
def test_search_returns_base_entry(
    db_session: Session,
    query: str,
    forms: tuple[str, ...],
    reading: str,
    label: str,
):
    add_entry(
        db_session,
        100,
        forms=forms,
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.has_more is False


def test_combines_matches_before_pagination(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("食べました",),
        reading="たべました",
        label="expression",
    )
    add_entry(
        db_session,
        200,
        forms=("食べる",),
        reading="たべる",
        label="Ichidan verb",
    )
    add_entry(
        db_session,
        300,
        forms=("食べましたか",),
        reading="たべましたか",
        label="expression",
    )

    pages = [
        search_jmdict(db_session, "食べました", limit=1, offset=offset)
        for offset in range(4)
    ]

    assert [[entry.source_id for entry in page.results] for page in pages] == [
        [100],
        [200],
        [300],
        [],
    ]
    assert [page.has_more for page in pages] == [True, True, False, False]


@pytest.mark.parametrize("exact", [True, False])
def test_deduplicates_direct_and_inflected_matches(
    db_session: Session,
    exact: bool,
):
    # Synthetic entry to exercise overlap between both match sources.
    extra_form = "食べました" if exact else "食べましたか"
    add_entry(
        db_session,
        100,
        forms=("食べる", extra_form),
        reading="たべる",
        label="Ichidan verb",
    )

    first = search_jmdict(db_session, "食べました", limit=1)
    second = search_jmdict(db_session, "食べました", limit=1, offset=1)

    assert [entry.source_id for entry in first.results] == [100]
    assert first.has_more is False
    assert second.results == []


def test_excludes_grammatically_incompatible_entry(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("確認",),
        reading="かくにん",
        label="noun (common) (futsuumeishi)",
    )

    response = search_jmdict(db_session, "確認しました")

    assert response.results == []


def test_returns_inflection_explanation_beyond_first_page(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("食べる",),
        reading="たべる",
        label="Ichidan verb",
    )

    for offset in (0, 30):
        response = search_jmdict(
            db_session,
            "食べました",
            offset=offset,
        )

        assert response.inflection is not None
        assert response.inflection.source_ids == [100]
        assert response.inflection.description == "polite past"


def test_unvalidated_construction_has_no_inflection_metadata(
    db_session: Session,
):
    response = search_jmdict(db_session, "食べました")

    assert response.inflection is None


@pytest.mark.parametrize(
    ("query", "description"),
    [
        ("tabemasu", "polite non-past"),
        ("TABEMASU", "polite non-past"),
        ("tabemashita", "polite past"),
    ],
)
def test_romaji_inflection_search(
    db_session: Session,
    query: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=("食べる",),
        reading="たべる",
        label="Ichidan verb",
    )

    response = search_jmdict(db_session, query)

    assert response.query == query
    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.source_ids == [100]
    assert response.inflection.description == description


def test_romaji_preserves_direct_matches_and_pagination(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("たべます",),
        reading="たべます",
        label="expression",
    )
    add_entry(
        db_session,
        200,
        forms=("食べる",),
        reading="たべる",
        label="Ichidan verb",
    )

    first = search_jmdict(db_session, "tabemasu", limit=1)
    second = search_jmdict(db_session, "tabemasu", limit=1, offset=1)

    assert [entry.source_id for entry in first.results] == [100]
    assert first.has_more is True
    assert [entry.source_id for entry in second.results] == [200]
    assert second.has_more is False
    assert first.inflection is not None
    assert first.inflection.source_ids == [200]


@pytest.mark.parametrize(
    ("query", "written", "reading", "label", "expected"),
    [
        (
            "でかけられる",
            "出かける",
            "でかける",
            "Ichidan verb",
            {"potential", "passive"},
        ),
        (
            "dekakerareru",
            "出かける",
            "でかける",
            "Ichidan verb",
            {"potential", "passive"},
        ),
        (
            "食べません",
            "食べる",
            "たべる",
            "Ichidan verb",
            {"polite negative"},
        ),
        (
            "tabemasen",
            "食べる",
            "たべる",
            "Ichidan verb",
            {"polite negative"},
        ),
        (
            "食べませんでした",
            "食べる",
            "たべる",
            "Ichidan verb",
            {"polite negative past"},
        ),
        (
            "書ける",
            "書く",
            "かく",
            "Godan verb with 'ku' ending",
            {"potential"},
        ),
        (
            "kakemasen",
            "書く",
            "かく",
            "Godan verb with 'ku' ending",
            {"potential, polite negative"},
        ),
        (
            "確認しません",
            "確認",
            "かくにん",
            "noun or participle which takes the aux. verb suru",
            {"polite negative"},
        ),
    ],
)
def test_search_validates_generated_forms(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    label: str,
    expected: set[str],
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert set(response.inflection.descriptions[100]) == expected


def test_generated_lookup_requires_the_correct_verb_class(
    db_session: Session,
):
    from conjugation_lookup import find_generated_inflections

    add_entry(
        db_session,
        100,
        forms=("帰る",),
        reading="かえる",
        label="Godan verb with 'ru' ending",
    )

    # 帰る is Godan: the polite negative is 帰りません.
    matches, descriptions = find_generated_inflections(
        db_session,
        "帰ません",
    )

    assert matches == ()
    assert descriptions == {}


@pytest.mark.parametrize("query", ["出れる", "でれる", "dereru"])
def test_search_finds_colloquial_potential(
    db_session: Session,
    query: str,
):
    add_entry(
        db_session,
        100,
        forms=("出る",),
        reading="でる",
        label="Ichidan verb",
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == ["potential — colloquial"]


@pytest.mark.parametrize(
    ("query", "written", "reading", "description"),
    [
        ("だった", None, "だ", "past"),
        ("datta", None, "だ", "past"),
        (
            "ではありませんでした",
            None,
            "です",
            "polite negative past",
        ),
        (
            "dehaarimasendeshita",
            None,
            "です",
            "polite negative past",
        ),
        (
            "dewaarimasendeshita",
            None,
            "です",
            "polite negative past",
        ),
        ("であった", None, "である", "past"),
        ("deatta", None, "である", "past"),
        (
            "では御座いません",
            "で御座います",
            "でございます",
            "negative",
        ),
        (
            "dehagozaimasen",
            "で御座います",
            "でございます",
            "negative",
        ),
        (
            "dewagozaimasen",
            "で御座います",
            "でございます",
            "negative",
        ),
    ],
)
def test_search_finds_copula_forms(
    db_session: Session,
    query: str,
    written: str | None,
    reading: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,) if written is not None else (),
        reading=reading,
        label="copula",
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == [description]


def test_copula_lookup_excludes_homophone_nouns(db_session: Session):
    from conjugation_lookup import find_generated_inflections

    add_entry(
        db_session,
        100,
        forms=("打",),
        reading="だ",
        label="noun (common) (futsuumeishi)",
    )

    matches, descriptions = find_generated_inflections(db_session, "だった")

    assert matches == ()
    assert descriptions == {}


def test_copula_pronunciation_alias_requires_explicit_opt_in(
    db_session: Session,
):
    from conjugation_lookup import find_generated_inflections

    add_entry(
        db_session,
        100,
        forms=(),
        reading="です",
        label="copula",
    )

    matches, descriptions = find_generated_inflections(
        db_session,
        "でわありませんでした",
    )

    assert matches == ()
    assert descriptions == {}


@pytest.mark.parametrize(
    ("query", "written", "reading", "label", "description"),
    [
        (
            "高くありませんでした",
            "高い",
            "たかい",
            "adjective (keiyoushi)",
            "polite negative past alternative",
        ),
        (
            "takakunakatta",
            "高い",
            "たかい",
            "adjective (keiyoushi)",
            "negative past",
        ),
        (
            "よかった",
            None,
            "いい",
            "adjective (keiyoushi) - yoi/ii class",
            "past",
        ),
        (
            "yokatta",
            None,
            "いい",
            "adjective (keiyoushi) - yoi/ii class",
            "past",
        ),
        (
            "格好良くない",
            "格好良い",
            "かっこいい",
            "adjective (keiyoushi) - yoi/ii class",
            "negative",
        ),
        (
            "kakkoyokatta",
            "格好いい",
            "かっこいい",
            "adjective (keiyoushi) - yoi/ii class",
            "past",
        ),
        (
            "静かだった",
            "静か",
            "しずか",
            "adjectival nouns or quasi-adjectives (keiyodoshi)",
            "past",
        ),
        (
            "shizukajanai",
            "静か",
            "しずか",
            "adjectival nouns or quasi-adjectives (keiyodoshi)",
            "negative colloquial",
        ),
        (
            "きれいでした",
            "綺麗",
            "きれい",
            "adjectival nouns or quasi-adjectives (keiyodoshi)",
            "polite past",
        ),
        (
            "かわいかった",
            None,
            "かわいい",
            "adjective (keiyoushi)",
            "past",
        ),
    ],
)
def test_search_finds_generated_adjective_forms(
    db_session: Session,
    query: str,
    written: str | None,
    reading: str,
    label: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,) if written is not None else (),
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == [description]


def test_generated_adjective_lookup_rejects_noun_homophone(
    db_session: Session,
):
    from conjugation_lookup import find_generated_inflections

    add_entry(
        db_session,
        100,
        forms=("鷹井",),
        reading="たかい",
        label="noun (common) (futsuumeishi)",
    )

    matches, descriptions = find_generated_inflections(
        db_session,
        "たかかった",
    )

    assert matches == ()
    assert descriptions == {}


@pytest.mark.parametrize(
    ("query", "written", "reading", "label", "expected"),
    [
        (
            "takakuna",
            "高い",
            "たかい",
            "adjective (keiyoushi)",
            "高くない",
        ),
        (
            "高くな",
            "高い",
            "たかい",
            "adjective (keiyoushi)",
            "高くない",
        ),
        (
            "takakun",
            "高い",
            "たかい",
            "adjective (keiyoushi)",
            "高くない",
        ),
        (
            "食べま",
            "食べる",
            "たべる",
            "Ichidan verb",
            "食べます",
        ),
        (
            "tabemas",
            "食べる",
            "たべる",
            "Ichidan verb",
            "食べます",
        ),
        (
            "shizukajana",
            "静か",
            "しずか",
            "adjectival nouns or quasi-adjectives (keiyodoshi)",
            "静かじゃない",
        ),
    ],
)
def test_search_finds_incomplete_conjugations(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    label: str,
    expected: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.source_ids == []
    assert expected in {item.written for item in response.inflection.completions[100]}


def test_prefix_lookup_rejects_incompatible_dictionary_class(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("鷹井",),
        reading="たかい",
        label="noun (common) (futsuumeishi)",
    )

    response = search_jmdict(db_session, "takakuna")

    assert response.results == []
    assert response.inflection is None


def test_prefix_results_preserve_exact_matches_and_pagination(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("たかくな",),
        reading="たかくな",
        label="expression",
    )
    add_entry(
        db_session,
        200,
        forms=("高い",),
        reading="たかい",
        label="adjective (keiyoushi)",
    )

    first = search_jmdict(db_session, "takakuna", limit=1)
    second = search_jmdict(db_session, "takakuna", limit=1, offset=1)

    assert [entry.source_id for entry in first.results] == [100]
    assert first.has_more is True
    assert [entry.source_id for entry in second.results] == [200]
    assert second.has_more is False


def test_complete_match_keeps_its_existing_explanation(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("高い",),
        reading="たかい",
        label="adjective (keiyoushi)",
    )

    response = search_jmdict(db_session, "takakunai")

    assert response.inflection is not None
    assert response.inflection.descriptions[100] == ["negative"]
    assert 100 not in response.inflection.completions


@pytest.mark.parametrize(
    ("query", "written", "reading", "label", "description"),
    [
        (
            "くれ",
            "呉れる",
            "くれる",
            "Ichidan verb - kureru special class",
            "imperative",
        ),
        (
            "kure",
            "呉れる",
            "くれる",
            "Ichidan verb - kureru special class",
            "imperative",
        ),
        (
            "呉れ",
            "呉れる",
            "くれる",
            "Ichidan verb - kureru special class",
            "imperative",
        ),
        (
            "kudasaimasu",
            "下さる",
            "くださる",
            "Godan verb - -aru special class",
            "polite non-past",
        ),
        (
            "なさい",
            "なさる",
            "なさる",
            "Godan verb - -aru special class",
            "imperative",
        ),
        (
            "ありません",
            "有る",
            "ある",
            "Godan verb with 'ru' ending (irregular verb)",
            "polite negative",
        ),
        (
            "arimasen",
            "有る",
            "ある",
            "Godan verb with 'ru' ending (irregular verb)",
            "polite negative",
        ),
        (
            "ない",
            "有る",
            "ある",
            "Godan verb with 'ru' ending (irregular verb)",
            "negative",
        ),
    ],
)
def test_search_finds_irregular_verb_forms(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    label: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == [description]


@pytest.mark.parametrize(
    ("query", "written", "reading", "label", "expected"),
    [
        (
            "kudasaim",
            "下さる",
            "くださる",
            "Godan verb - -aru special class",
            "くださいます",
        ),
        (
            "ありませんで",
            "有る",
            "ある",
            "Godan verb with 'ru' ending (irregular verb)",
            "ありませんでした",
        ),
        (
            "くれま",
            "呉れる",
            "くれる",
            "Ichidan verb - kureru special class",
            "くれます",
        ),
    ],
)
def test_search_finds_irregular_verb_completions(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    label: str,
    expected: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label=label,
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert expected in {item.reading for item in response.inflection.completions[100]}


def test_kureru_imperative_does_not_match_regular_homophone(
    db_session: Session,
):
    from conjugation_lookup import find_generated_inflections

    add_entry(
        db_session,
        100,
        forms=("暮れる",),
        reading="くれる",
        label="Ichidan verb",
    )

    matches, descriptions = find_generated_inflections(db_session, "くれ")

    assert matches == ()
    assert descriptions == {}


@pytest.mark.parametrize(
    ("query", "description"),
    [
        ("信じました", "polite past"),
        ("shinjimashita", "polite past"),
        ("信ずれば", "conditional ba"),
        ("信じれば", "conditional ba alternative"),
        ("信ぜよ", "imperative alternative"),
    ],
)
def test_search_finds_zuru_forms(
    db_session: Session,
    query: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=("信ずる",),
        reading="しんずる",
        label="Ichidan verb - zuru verb (alternative form of -jiru verbs)",
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == [description]


def test_search_finds_incomplete_zuru_form(db_session: Session):
    add_entry(
        db_session,
        100,
        forms=("信ずる",),
        reading="しんずる",
        label="Ichidan verb - zuru verb (alternative form of -jiru verbs)",
    )

    response = search_jmdict(db_session, "shinjima")

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert "しんじます" in {
        item.reading for item in response.inflection.completions[100]
    }


def test_search_preserves_jiru_and_zuru_interpretations(
    db_session: Session,
):
    add_entry(
        db_session,
        100,
        forms=("信ずる",),
        reading="しんずる",
        label="Ichidan verb - zuru verb (alternative form of -jiru verbs)",
    )
    add_entry(
        db_session,
        200,
        forms=("信じる",),
        reading="しんじる",
        label="Ichidan verb",
    )

    response = search_jmdict(db_session, "信じました")

    assert {entry.source_id for entry in response.results} == {100, 200}
    assert response.inflection is not None
    assert set(response.inflection.source_ids) == {100, 200}


@pytest.mark.parametrize(
    ("query", "written", "reading", "description"),
    [
        ("aishimasu", "愛する", "あいする", "polite non-past"),
        ("aisanai", "愛する", "あいする", "negative"),
        ("愛せる", "愛する", "あいする", "potential"),
        ("aiseru", "愛する", "あいする", "potential"),
        ("愛せよ", "愛する", "あいする", "imperative formal"),
        ("tasshimashita", "達する", "たっする", "polite past"),
        (
            "不問に付した",
            "不問に付する",
            "ふもんにふする",
            "past",
        ),
    ],
)
def test_search_finds_special_suru_forms(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    description: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label="suru verb - special class",
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert response.inflection.descriptions[100] == [description]


@pytest.mark.parametrize(
    ("query", "written", "reading", "expected"),
    [
        ("aishima", "愛する", "あいする", "愛します"),
        ("aisana", "愛する", "あいする", "愛さない"),
        ("tasshima", "達する", "たっする", "達します"),
    ],
)
def test_search_finds_special_suru_completions(
    db_session: Session,
    query: str,
    written: str,
    reading: str,
    expected: str,
):
    add_entry(
        db_session,
        100,
        forms=(written,),
        reading=reading,
        label="suru verb - special class",
    )

    response = search_jmdict(db_session, query)

    assert [entry.source_id for entry in response.results] == [100]
    assert response.inflection is not None
    assert expected in {item.written for item in response.inflection.completions[100]}
