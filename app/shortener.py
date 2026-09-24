"""Business rules that are not about the web or the database."""

from urllib.parse import urlparse

from sqlmodel import Session, select

from app.config import RESERVED_CODES
from app.models import Link
from app.security import generate_code

ALLOWED_SCHEMES = {"http", "https"}


def normalise_url(raw: str) -> str:
    """Cleans up what the user typed, or raises ValueError with a message
    the page can show them."""
    url = (raw or "").strip()
    if not url:
        raise ValueError("Please paste a link.")

    # Being friendly: "example.com" becomes "https://example.com".
    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http:// and https:// links are allowed.")
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValueError("That does not look like a real web address.")
    if len(url) > 2000:
        raise ValueError("That link is too long.")
    return url


def unique_code(session: Session, length: int = 6, attempts: int = 10) -> str:
    """Keeps generating codes until one is free.

    Two random codes can collide, so we check the database instead of hoping.
    """
    for _ in range(attempts):
        code = generate_code(length)
        if code.lower() in RESERVED_CODES:
            continue
        taken = session.exec(select(Link).where(Link.code == code)).first()
        if taken is None:
            return code
    # Extremely unlikely. Growing the code makes a clash even rarer.
    return unique_code(session, length=length + 1, attempts=attempts)


def validate_custom_code(session: Session, code: str) -> str:
    """Checks a code the user chose themselves."""
    code = (code or "").strip()
    if not code:
        raise ValueError("Custom code cannot be empty.")
    if len(code) < 3 or len(code) > 32:
        raise ValueError("Custom code must be 3 to 32 characters.")
    if not all(c.isalnum() or c in "-_" for c in code):
        raise ValueError("Use only letters, numbers, hyphens and underscores.")
    if code.lower() in RESERVED_CODES:
        raise ValueError("That code is reserved by the app. Try another.")
    if session.exec(select(Link).where(Link.code == code)).first():
        raise ValueError("That code is already taken.")
    return code
