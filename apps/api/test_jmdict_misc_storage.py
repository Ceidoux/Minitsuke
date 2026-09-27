from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from jmdict import JmdictEntry, JmdictGloss, JmdictReading, JmdictSense
from jmdict_importer import save_jmdict_entry
from models import JmdictEntryRecord, JmdictMiscRecord, JmdictSenseRecord

KANA_LABEL = "word usually written using kana alone"


def make_entry(
    source_id: int,
    tags_by_sense: tuple[tuple[str, ...], ...],
) -> JmdictEntry:
    return JmdictEntry(
        source_id=source_id,
        written_forms=(),
        readings=(JmdictReading(text="ことば"),),
        senses=tuple(
            JmdictSense(
                glosses=(JmdictGloss(text="example", language="eng"),),
                misc=tags,
            )
            for tags in tags_by_sense
        ),
    )


def stored_tags(session: Session, entry_id: int):
    return session.execute(
        select(
            JmdictSenseRecord.position,
            JmdictMiscRecord.position,
            JmdictMiscRecord.label,
        )
        .join(
            JmdictMiscRecord,
            JmdictMiscRecord.sense_id == JmdictSenseRecord.id,
        )
        .where(JmdictSenseRecord.entry_id == entry_id)
        .order_by(
            JmdictSenseRecord.position,
            JmdictMiscRecord.position,
        )
    ).all()


def test_preserves_tag_order_and_sense_scope(db_session: Session):
    entry_id = save_jmdict_entry(
        db_session,
        make_entry(
            100,
            (
                (KANA_LABEL, "colloquial"),
                (),
                ("abbreviation",),
            ),
        ),
    )

    assert stored_tags(db_session, entry_id) == [
        (1, 1, KANA_LABEL),
        (1, 2, "colloquial"),
        (3, 1, "abbreviation"),
    ]


def test_replacement_removes_old_tags_and_preserves_other_entries(
    db_session: Session,
):
    entry_id = save_jmdict_entry(
        db_session,
        make_entry(100, ((KANA_LABEL,), ("abbreviation",))),
    )
    other_id = save_jmdict_entry(
        db_session,
        make_entry(200, (("colloquial",),)),
    )

    replacement_id = save_jmdict_entry(
        db_session,
        make_entry(100, (("archaic",),)),
    )

    assert replacement_id == entry_id
    assert stored_tags(db_session, entry_id) == [(1, 1, "archaic")]
    assert stored_tags(db_session, other_id) == [(1, 1, "colloquial")]

    # Query the tag table directly to catch any orphaned old rows.
    assert sorted(db_session.scalars(select(JmdictMiscRecord.label)).all()) == [
        "archaic",
        "colloquial",
    ]


def test_replacement_can_remove_all_tags(db_session: Session):
    entry_id = save_jmdict_entry(
        db_session,
        make_entry(100, ((KANA_LABEL,),)),
    )

    save_jmdict_entry(
        db_session,
        make_entry(100, ((),)),
    )

    assert stored_tags(db_session, entry_id) == []
    assert db_session.scalars(select(JmdictMiscRecord.id)).all() == []


def test_deleting_entry_cascades_to_usage_tags(db_session: Session):
    entry_id = save_jmdict_entry(
        db_session,
        make_entry(100, ((KANA_LABEL,),)),
    )

    db_session.execute(
        delete(JmdictEntryRecord).where(JmdictEntryRecord.id == entry_id)
    )
    db_session.flush()

    assert db_session.scalars(select(JmdictMiscRecord.id)).all() == []
