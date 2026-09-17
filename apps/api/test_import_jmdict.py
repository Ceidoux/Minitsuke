from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from import_jmdict import import_jmdict_file, main
from models import JmdictEntryRecord, JmdictGlossRecord

FIRST_ENTRY = """
<entry>
    <ent_seq>1000001</ent_seq>
    <k_ele><keb>学校</keb></k_ele>
    <r_ele><reb>がっこう</reb></r_ele>
    <sense><gloss>school</gloss></sense>
</entry>
"""

SECOND_ENTRY = """
<entry>
    <ent_seq>1000002</ent_seq>
    <k_ele><keb>食べる</keb></k_ele>
    <r_ele><reb>たべる</reb></r_ele>
    <sense><gloss>to eat</gloss></sense>
</entry>
"""

INVALID_ENTRY = """
<entry>
    <ent_seq>1000003</ent_seq>
    <r_ele>
        <reb>ねこ</reb>
        <re_restr>猫</re_restr>
    </r_ele>
    <sense><gloss>cat</gloss></sense>
</entry>
"""


@pytest.fixture
def import_sessions(db_session: Session) -> sessionmaker[Session]:
    return sessionmaker(
        bind=db_session.connection(),
        join_transaction_mode="create_savepoint",
    )


def write_xml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "JMdict"
    path.write_text(content, encoding="utf-8")
    return path


def test_imports_file_and_reports_progress(
    db_session: Session,
    import_sessions: sessionmaker[Session],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    path = write_xml(
        tmp_path,
        f"<JMdict>{FIRST_ENTRY}{SECOND_ENTRY}</JMdict>",
    )

    count = import_jmdict_file(import_sessions, path, progress_every=1)

    assert count == 2
    assert set(db_session.scalars(select(JmdictEntryRecord.source_id))) == {
        1000001,
        1000002,
    }
    assert set(db_session.scalars(select(JmdictGlossRecord.text))) == {
        "school",
        "to eat",
    }

    assert capsys.readouterr().out.splitlines() == [
        "Processed 1 entries (not yet committed)...",
        "Processed 2 entries (not yet committed)...",
    ]


@pytest.mark.parametrize("failure", ["validation", "xml"])
def test_failure_rolls_back_updates_and_new_entries(
    db_session: Session,
    import_sessions: sessionmaker[Session],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    failure: str,
):
    path = write_xml(tmp_path, f"<JMdict>{FIRST_ENTRY}</JMdict>")
    import_jmdict_file(import_sessions, path)

    original_id = db_session.scalars(select(JmdictEntryRecord.id)).one()

    updated_first = FIRST_ENTRY.replace(
        "<gloss>school</gloss>",
        "<gloss>updated school</gloss>",
    )

    if failure == "validation":
        content = f"<JMdict>{updated_first}{SECOND_ENTRY}{INVALID_ENTRY}</JMdict>"
        error_type = ValueError
        message = "Entry 1000003"
    else:
        content = f"<JMdict>{updated_first}{SECOND_ENTRY}"
        error_type = ET.ParseError
        message = "no element found"

    write_xml(tmp_path, content)

    with pytest.raises(error_type, match=message):
        import_jmdict_file(import_sessions, path, progress_every=1)

    rows = db_session.execute(
        select(JmdictEntryRecord.id, JmdictEntryRecord.source_id)
    ).all()

    assert [tuple(row) for row in rows] == [(original_id, 1000001)]
    assert db_session.scalars(select(JmdictGlossRecord.text)).all() == ["school"]

    assert capsys.readouterr().out.splitlines() == [
        "Processed 1 entries (not yet committed)...",
        "Processed 2 entries (not yet committed)...",
    ]


def test_missing_file_is_reported(
    import_sessions: sessionmaker[Session],
    tmp_path: Path,
):
    with pytest.raises(FileNotFoundError):
        import_jmdict_file(import_sessions, tmp_path / "missing.xml")


@pytest.mark.parametrize("interval", [0, -1])
def test_rejects_invalid_progress_interval(
    import_sessions: sessionmaker[Session],
    tmp_path: Path,
    interval: int,
):
    with pytest.raises(ValueError, match="Progress interval must be positive"):
        import_jmdict_file(
            import_sessions,
            tmp_path / "JMdict",
            progress_every=interval,
        )


def test_help_does_not_require_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0
    assert "--progress-every" in capsys.readouterr().out


def test_command_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as error:
        main(["JMdict"])

    assert error.value.code == 2
    assert "DATABASE_URL must be set" in capsys.readouterr().err
