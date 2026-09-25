"""Creates the database connection and hands out sessions to the routes."""

import os
from collections.abc import Iterator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL


def _normalise(url: str) -> str:
    """Names the driver SQLAlchemy should use to reach the database.

    Neon hands out 'postgresql://' URLs, and some hosts still use the older
    'postgres://' spelling. SQLAlchemy needs to be told which driver speaks
    to the server, hence 'postgresql+psycopg://'. Doing the rewrite here is
    why the same code runs on SQLite locally and PostgreSQL in production.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_url = _normalise(DATABASE_URL)

# check_same_thread is a SQLite-only quirk; it lets FastAPI's threads share the file.
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

# On a serverless host every request may run in a fresh short-lived process,
# so keeping a pool of open connections wastes the database's connection
# limit. NullPool opens one connection per request and closes it after.
_pool_args = {"poolclass": NullPool} if os.getenv("VERCEL") else {"pool_recycle": 300}

engine = create_engine(
    _url,
    connect_args=_connect_args,
    **_pool_args,
    # Free hosted databases drop idle connections. pool_pre_ping checks that
    # a connection is alive before handing it over, so a sleeping database
    # waking up never shows the user an error.
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Creates any missing tables. Safe to call on every startup."""
    # Importing the models is what registers them on SQLModel.metadata.
    # Without this line create_all() finds nothing to create and silently
    # does nothing, which is much harder to debug than an error.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI calls this for each request and closes the session afterwards."""
    with Session(engine) as session:
        yield session
