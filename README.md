# Shortly — a link shortener with click analytics

![tests](https://github.com/LaibaZaffar/link-shortener/actions/workflows/ci.yml/badge.svg)

Paste a long web address, get a short one, and see a dashboard of who clicked it,
when, and where they came from.

**Live demo:** _add your URL here after deploying_
**Built with:** Python · FastAPI · SQLModel · PostgreSQL · Jinja2 · Chart.js · Docker

<!-- Add a screenshot once you have deployed:  ![screenshot](docs/screenshot.png) -->

---

## What it does

- Sign up and log in (passwords hashed with PBKDF2, never stored as text)
- Create a short link, with an optional custom code like `/my-resume`
- Change where a link points **without changing its short code**, so a link
  already printed on a CV keeps working
- Optional expiry dates; an expired link answers `410 Gone` with an explanation
- Every visit is recorded as its own row, so the stats are real history
- Per-link dashboard: clicks per day, top referrers, browser breakdown
- A QR code per link, ready to print
- Sort by newest, oldest or most clicked, and search across your links
- A JSON API (`/api/links/{id}/stats`) that the charts read from
- Auto-generated API documentation at `/docs`

## Run it on your computer

You need Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put a random SECRET_KEY in it
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and sign up. The database is a single file
(`shortener.db`) created automatically on first run.

## Run the tests

```bash
pytest -q
```

43 tests cover URL cleaning, password hashing, login, redirects, click
recording, sorting, searching, QR output, expiry, editing, and the rule that
you can only ever touch your own links.

## How it is put together

```
app/
  main.py        every web page and the redirect endpoint
  models.py      the three database tables: User, Link, Click
  database.py    the database connection
  shortener.py   URL cleaning and short-code rules
  security.py    password hashing and random code generation
  config.py      settings read from environment variables
  templates/     the HTML pages
  static/        the stylesheet
tests/           pytest suite
```

Two design decisions worth knowing:

**Clicks are stored as events, not a counter.** A `clicks` column would only
ever answer "how many". A row per visit answers "how many, on which day, from
where, on what browser" — which is what makes the charts possible.

**The `/{code}` route is declared last.** FastAPI matches routes in the order
they are written, so putting the catch-all at the bottom stops it from
swallowing real pages like `/login`.

**Dates read back from SQLite have no timezone attached.** Comparing one of
those with a timezone-aware "now" raises `TypeError`, so every date coming out
of the database passes through `as_utc()` in `models.py` first.

## Deploy it

See [ROADMAP.md](ROADMAP.md) for the full walkthrough. The short version:
a free [Neon](https://neon.tech) PostgreSQL database, plus a free web service
on [Render](https://render.com) created from `render.yaml`.

The free web service sleeps after 15 minutes of no traffic, so the very first
visit can take up to a minute to wake it up. Everything after that is instant.
