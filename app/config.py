"""Reads settings from environment variables, with safe defaults for local work."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """Tiny .env reader so you don't need an extra library.

    Lines look like KEY=value. Blank lines and #comments are ignored.
    Real environment variables always win, which is what production wants.
    """
    env_file = BASE_DIR.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shortener.db")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Route names that can never be used as a short code, because the app
# already uses those web addresses for its own pages.
RESERVED_CODES = {
    "signup", "login", "logout", "links", "static", "api",
    "health", "docs", "redoc", "openapi.json", "favicon.ico", "",
}
