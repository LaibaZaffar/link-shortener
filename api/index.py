"""Entry point for Vercel.

Vercel looks for a variable named "app" in this file and serves it as the
web application. All the real code lives in app/main.py; this file only
exposes it at the path Vercel expects.
"""

from app.main import app

__all__ = ["app"]
