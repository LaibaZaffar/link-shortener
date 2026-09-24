"""Shared test setup: every test gets a fresh, empty database."""

import os

# Point the app at a throwaway in-memory database BEFORE importing it, so
# running the tests never touches your real shortener.db file.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    # An in-memory SQLite database: fast, and thrown away after each test.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    # Tell the app to use the test database instead of the real one.
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="logged_in")
def logged_in_fixture(client):
    """A client that has already signed up, so tests can skip that step."""
    client.post("/signup", data={"email": "me@example.com", "password": "password123"})
    return client
