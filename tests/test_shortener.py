"""Unit tests for the rules that don't touch the web layer."""

import pytest

from app.security import hash_password, verify_password
from app.shortener import normalise_url, validate_custom_code


def test_adds_https_when_missing():
    assert normalise_url("example.com/page") == "https://example.com/page"


def test_keeps_existing_scheme():
    assert normalise_url("http://example.com") == "http://example.com"


@pytest.mark.parametrize("bad", ["", "   ", "javascript:alert(1)", "not-a-url", "ftp://files.com"])
def test_rejects_bad_urls(bad):
    with pytest.raises(ValueError):
        normalise_url(bad)


def test_password_round_trip():
    stored = hash_password("password123")
    assert stored != "password123"          # never stored in plain text
    assert verify_password("password123", stored)
    assert not verify_password("wrong-password", stored)


def test_two_hashes_of_same_password_differ():
    # Different random salts, so identical passwords look different in the DB.
    assert hash_password("same") != hash_password("same")


def test_reserved_code_rejected(session):
    with pytest.raises(ValueError):
        validate_custom_code(session, "login")


def test_short_code_rejected(session):
    with pytest.raises(ValueError):
        validate_custom_code(session, "ab")
