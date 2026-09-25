"""Tests that drive the app the way a browser would."""

import os
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.models import Click, Link


def test_dashboard_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_signup_then_see_dashboard(client):
    response = client.post(
        "/signup", data={"email": "new@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "Shorten a link" in response.text


def test_signup_rejects_short_password(client):
    response = client.post("/signup", data={"email": "a@b.com", "password": "short"})
    assert "at least 8 characters" in response.text


def test_login_with_wrong_password_fails(logged_in):
    logged_in.post("/logout")
    response = logged_in.post(
        "/login", data={"email": "me@example.com", "password": "nope-nope-nope"}
    )
    assert "Wrong email or password" in response.text


def test_create_link_and_redirect(logged_in, session):
    logged_in.post("/links", data={"target_url": "example.com/hello", "title": "Hi"})

    link = session.exec(select(Link)).one()
    assert link.target_url == "https://example.com/hello"
    assert len(link.code) == 6

    response = logged_in.get(f"/{link.code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/hello"


def test_redirect_records_a_click(logged_in, session):
    logged_in.post("/links", data={"target_url": "https://example.com"})
    code = session.exec(select(Link)).one().code

    logged_in.get(f"/{code}", follow_redirects=False)
    logged_in.get(f"/{code}", follow_redirects=False)

    assert len(session.exec(select(Click)).all()) == 2


def test_custom_code_is_used(logged_in, session):
    logged_in.post(
        "/links", data={"target_url": "https://example.com", "custom_code": "my-resume"}
    )
    assert session.exec(select(Link)).one().code == "my-resume"


def test_duplicate_custom_code_is_refused(logged_in, session):
    for _ in range(2):
        logged_in.post(
            "/links", data={"target_url": "https://example.com", "custom_code": "taken"}
        )
    assert len(session.exec(select(Link)).all()) == 1


def test_unknown_code_returns_404(client):
    assert client.get("/nosuchcode").status_code == 404


def test_stats_api_returns_totals(logged_in, session):
    logged_in.post("/links", data={"target_url": "https://example.com"})
    link = session.exec(select(Link)).one()
    logged_in.get(f"/{link.code}", follow_redirects=False)

    data = logged_in.get(f"/api/links/{link.id}/stats").json()
    assert data["total"] == 1
    assert len(data["timeline"]["labels"]) == 30
    assert sum(data["timeline"]["values"]) == 1


def test_cannot_see_someone_elses_stats(logged_in, client, session):
    logged_in.post("/links", data={"target_url": "https://example.com"})
    link_id = session.exec(select(Link)).one().id

    logged_in.post("/logout")
    client.post("/signup", data={"email": "other@example.com", "password": "password123"})
    assert client.get(f"/api/links/{link_id}/stats").status_code == 404


def test_health_check(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Phase 1 features
# ---------------------------------------------------------------------------

def _make_link(client, session, **overrides):
    """Creates a link through the form and returns the Link row."""
    data = {"target_url": "https://example.com", "title": "", "custom_code": "", "expires_in": ""}
    data.update(overrides)
    client.post("/links", data=data)
    return session.exec(select(Link).order_by(Link.id.desc())).first()


def test_dashboard_sorts_newest_first_by_default(logged_in, session):
    _make_link(logged_in, session, custom_code="first")
    _make_link(logged_in, session, custom_code="second")

    body = logged_in.get("/").text
    assert body.index("/second") < body.index("/first")


def test_dashboard_can_sort_oldest_first(logged_in, session):
    _make_link(logged_in, session, custom_code="first")
    _make_link(logged_in, session, custom_code="second")

    body = logged_in.get("/?sort=oldest").text
    assert body.index("/first") < body.index("/second")


def test_dashboard_can_sort_by_clicks(logged_in, session):
    _make_link(logged_in, session, custom_code="quiet")
    popular = _make_link(logged_in, session, custom_code="popular")
    for _ in range(3):
        logged_in.get(f"/{popular.code}", follow_redirects=False)

    body = logged_in.get("/?sort=clicks").text
    assert body.index("/popular") < body.index("/quiet")


def test_links_with_no_clicks_still_appear(logged_in, session):
    # An inner join would silently drop these; the dashboard uses an outer join.
    _make_link(logged_in, session, custom_code="never-clicked")
    assert "never-clicked" in logged_in.get("/").text


def test_search_filters_by_label(logged_in, session):
    _make_link(logged_in, session, custom_code="keep-me", title="Scholarship form")
    _make_link(logged_in, session, custom_code="hide-me", title="Holiday photos")

    body = logged_in.get("/?q=scholarship").text
    assert "keep-me" in body
    assert "hide-me" not in body


def test_search_with_no_matches_shows_a_message(logged_in, session):
    _make_link(logged_in, session, custom_code="anything")
    assert "No links match" in logged_in.get("/?q=zzzznothing").text


def test_empty_dashboard_shows_getting_started_message(logged_in):
    assert "No links yet" in logged_in.get("/").text


def test_bad_sort_value_falls_back_to_default(logged_in, session):
    _make_link(logged_in, session)
    assert logged_in.get("/?sort=; DROP TABLE link").status_code == 200


def test_qr_code_is_a_png(logged_in, session):
    link = _make_link(logged_in, session)
    response = logged_in.get(f"/links/{link.id}/qr.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # Every PNG file starts with these bytes.
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_cannot_get_someone_elses_qr_code(logged_in, client, session):
    link = _make_link(logged_in, session)
    logged_in.post("/logout")
    client.post("/signup", data={"email": "other@example.com", "password": "password123"})

    assert client.get(f"/links/{link.id}/qr.png").status_code == 404


def test_expired_link_does_not_redirect(logged_in, session):
    link = _make_link(logged_in, session)
    link.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    session.add(link)
    session.commit()

    response = logged_in.get(f"/{link.code}", follow_redirects=False)
    assert response.status_code == 410
    assert "expired" in response.text.lower()


def test_expired_link_records_no_clicks(logged_in, session):
    link = _make_link(logged_in, session)
    link.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    session.add(link)
    session.commit()

    logged_in.get(f"/{link.code}", follow_redirects=False)
    assert session.exec(select(Click)).all() == []


def test_future_expiry_still_redirects(logged_in, session):
    link = _make_link(logged_in, session, expires_in="30")
    assert link.expires_at is not None
    assert logged_in.get(f"/{link.code}", follow_redirects=False).status_code == 307


def test_expiry_survives_being_read_back_from_the_database(logged_in, session):
    """SQLite returns dates without a timezone; is_expired must cope."""
    link = _make_link(logged_in, session, expires_in="7")
    session.expire_all()  # force a genuine re-read from the database

    assert session.get(Link, link.id).is_expired is False


def test_edit_changes_destination_but_keeps_the_code(logged_in, session):
    link = _make_link(logged_in, session, custom_code="my-resume")
    logged_in.post(
        f"/links/{link.id}/edit",
        data={"target_url": "https://example.com/resume-v2.pdf", "title": "CV", "expires_in": "keep"},
    )

    session.expire_all()
    updated = session.get(Link, link.id)
    assert updated.code == "my-resume"
    assert updated.target_url == "https://example.com/resume-v2.pdf"
    assert updated.title == "CV"


def test_edit_keeps_expiry_when_asked_to(logged_in, session):
    link = _make_link(logged_in, session, expires_in="30")
    original = link.expires_at

    logged_in.post(
        f"/links/{link.id}/edit",
        data={"target_url": "https://example.com/new", "title": "", "expires_in": "keep"},
    )
    session.expire_all()
    assert session.get(Link, link.id).expires_at == original


def test_edit_rejects_a_bad_url(logged_in, session):
    link = _make_link(logged_in, session)
    response = logged_in.post(
        f"/links/{link.id}/edit",
        data={"target_url": "not a url", "title": "", "expires_in": "keep"},
    )

    assert "does not look like a real web address" in response.text
    session.expire_all()
    assert session.get(Link, link.id).target_url == "https://example.com"


def test_cannot_edit_someone_elses_link(logged_in, client, session):
    link = _make_link(logged_in, session)
    logged_in.post("/logout")
    client.post("/signup", data={"email": "other@example.com", "password": "password123"})

    client.post(
        f"/links/{link.id}/edit",
        data={"target_url": "https://evil.example.com", "title": "", "expires_in": "keep"},
    )
    session.expire_all()
    assert session.get(Link, link.id).target_url == "https://example.com"


def test_error_message_appears_without_putting_it_in_the_url(logged_in, session):
    _make_link(logged_in, session, custom_code="taken")
    response = logged_in.post(
        "/links",
        data={"target_url": "https://example.com", "title": "", "custom_code": "taken", "expires_in": ""},
        follow_redirects=False,
    )

    assert response.headers["location"] == "/"          # no ?error=... in the address
    assert "already taken" in logged_in.get("/").text   # but the message still shows


def test_flash_message_only_shows_once(logged_in):
    # The POST redirects to "/", and the client follows it, so this response
    # IS the dashboard the user lands on after submitting the form.
    landing = logged_in.post(
        "/links",
        data={"target_url": "https://example.com", "title": "", "custom_code": "", "expires_in": ""},
    )

    assert "Created" in landing.text
    assert "Created" not in logged_in.get("/").text   # gone on the next visit


def test_init_db_actually_creates_the_tables(tmp_path):
    """Regression: create_all() creates nothing unless the models are imported.

    This once "succeeded" while creating zero tables, which would only have
    shown up as a crash on the deployed site.
    """
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    database = tmp_path / "fresh.db"
    project_root = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "app.init_db"],
        cwd=project_root,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{database}"},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    tables = {
        row[0]
        for row in sqlite3.connect(database).execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"user", "link", "click"} <= tables


def test_init_db_rejects_a_url_that_is_not_a_url(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    result = subprocess.run(
        [sys.executable, "-m", "app.init_db"],
        cwd=Path(__file__).resolve().parent.parent,
        env={**os.environ, "DATABASE_URL": "paste-your-neon-string-here"},
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "does not look like a database address" in result.stderr
