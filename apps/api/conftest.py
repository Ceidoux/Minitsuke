import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from models import Meaning, Word


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine]:
    database_url = os.environ["TEST_DATABASE_URL"]

    if make_url(database_url).database != "smartjisho_test":
        raise ValueError("Tests must use the smartjisho_test database")

    engine = create_engine(database_url)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session]:
    with test_engine.connect() as connection:
        transaction = connection.begin()

        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as session:
                entries = [
                    ("食べる", "たべる", "to eat"),
                    ("食事", "しょくじ", "meal"),
                    ("学校", "がっこう", "school"),
                ]

                for written_form, reading, meaning_text in entries:
                    word = Word(
                        written_form=written_form,
                        reading=reading,
                    )
                    session.add(word)
                    session.flush()

                    session.add(Meaning(word_id=word.id, meaning=meaning_text))

                session.flush()
                yield session
        finally:
            transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    from database import get_session
    from main import app

    def override_get_session() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        del app.dependency_overrides[get_session]
