"""Pytest configuration and test database isolation fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import mindtrack_ai.database as db_module


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolate each test run with a dedicated temporary SQLite database."""
    test_db_path = tmp_path / "test_mindtrack.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    test_session = sessionmaker(bind=test_engine, expire_on_commit=False)

    orig_engine = db_module.engine
    orig_session = db_module.SessionLocal
    orig_path = db_module.DATABASE_PATH

    db_module.engine = test_engine
    db_module.SessionLocal = test_session
    db_module.DATABASE_PATH = test_db_path

    db_module.Base.metadata.create_all(bind=test_engine)

    yield

    db_module.engine = orig_engine
    db_module.SessionLocal = orig_session
    db_module.DATABASE_PATH = orig_path
