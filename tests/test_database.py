
import os

from sqlalchemy.orm import DeclarativeBase

import app.database as database


def test_database_url_uses_environment_variables():
    assert database.DATABASE_URL.drivername == "postgresql+psycopg"
    assert database.DATABASE_URL.username == os.getenv("DB_USER")
    assert database.DATABASE_URL.password == os.getenv("DB_PASSWORD")
    assert database.DATABASE_URL.host == os.getenv("DB_HOST")
    assert database.DATABASE_URL.port == int(os.getenv("DB_PORT"))
    assert database.DATABASE_URL.database == os.getenv("DB_NAME")


def test_engine_uses_database_url():
    assert database.engine.url == database.DATABASE_URL


def test_session_local_configuration():
    assert database.SessionLocal.kw["bind"] is database.engine
    assert database.SessionLocal.kw["autoflush"] is False
    assert database.SessionLocal.kw["autocommit"] is False


def test_base_is_declarative_base():
    assert issubclass(database.Base, DeclarativeBase)
    assert hasattr(database.Base, "metadata")
