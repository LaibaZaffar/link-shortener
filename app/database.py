"""Creates the database connection and hands out sessions to the routes."""

import os
from collections.abc import Iterator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL


def _normalise(url: str) -> str:
    """Render/Heroku hand out 'postgres://' URLs but SQLAlchemy wants
    'postgresql+psycopg://'. Fixing it here means the app runs unchanged
    on your laptop (SQLite) and in production (PostgreSQL)."""
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
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI calls this for each request and closes the session afterwards."""
    with Session(engine) as session:
        yield session
