"""All the web pages and the redirect endpoint live here."""

import io
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, BASE_URL, SECRET_KEY
from app.database import create_db_and_tables, get_session
from app.models import Click, Link, User, as_utc, utcnow
from app.security import hash_password, verify_password
from app.shortener import normalise_url, unique_code, validate_custom_code

# How long a link can be set to live for. None means "never expires".
EXPIRY_CHOICES = {"": None, "1": 1, "7": 7, "30": 30, "90": 90}

SORT_CHOICES = {"newest", "oldest", "clicks"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the app boots: make sure the tables exist."""
    create_db_and_tables()
    yield


app = FastAPI(title="Link Shortener", lifespan=lifespan)

# Signs a small cookie holding the logged-in user's id. Nothing secret is
# stored in the browser, only a tamper-proof reference.
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def current_user(request: Request, session: Session) -> User | None:
    """Returns the logged-in user, or None if nobody is logged in."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def flash(request: Request, message: str, kind: str = "error") -> None:
    """Stores a one-time message to show on the *next* page the user sees.

    This is why the app can redirect after a form submission and still say
    what happened, without putting the message in the web address.
    """
    request.session["flash"] = {"message": message, "kind": kind}


def render(request: Request, template: str, status_code: int = 200, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template,
        # .pop() reads the flash message and deletes it in one go, so it
        # shows once and does not follow the user around.
        context={
            "base_url": BASE_URL,
            "flash": request.session.pop("flash", None),
            **context,
        },
        status_code=status_code,
    )


def redirect(path: str) -> RedirectResponse:
    # 303 tells the browser "now do a normal GET", which is the correct
    # response after handling a form submission.
    return RedirectResponse(url=path, status_code=303)


def expiry_from_choice(choice: str) -> datetime | None:
    """Turns the dropdown value ("", "7", "30"...) into a real date."""
    days = EXPIRY_CHOICES.get(choice)
    return None if days is None else utcnow() + timedelta(days=days)


def owned_link(link_id: int, user: User, session: Session) -> Link | None:
    """Loads a link only if it belongs to this user.

    Every page that shows or changes a link goes through here, so nobody can
    reach a stranger's link by guessing an id in the web address.
    """
    link = session.get(Link, link_id)
    return link if link and link.user_id == user.id else None


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return render(request, "signup.html")


@app.post("/signup")
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    if len(password) < 8:
        return render(request, "signup.html", error="Password must be at least 8 characters.", email=email)
    if session.exec(select(User).where(User.email == email)).first():
        return render(request, "signup.html", error="That email already has an account.", email=email)

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)

    request.session["user_id"] = user.id
    return redirect("/")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html")


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    # One vague message for both cases, so nobody can use this form to
    # discover which email addresses are registered.
    if user is None or not verify_password(password, user.password_hash):
        return render(request, "login.html", error="Wrong email or password.", email=email)

    request.session["user_id"] = user.id
    return redirect("/")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    sort: str = Query("newest"),
    q: str = Query(""),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    if sort not in SORT_CHOICES:
        sort = "newest"
    search = q.strip()

    # One query does the whole job: fetch each link together with how many
    # clicks it has. An "outer join" keeps links that have no clicks at all,
    # which an ordinary join would silently drop.
    clicks = func.count(Click.id)
    query = (
        select(Link, clicks)
        .outerjoin(Click, Click.link_id == Link.id)
        .where(Link.user_id == user.id)
        .group_by(Link.id)
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Link.code.ilike(pattern),
                Link.title.ilike(pattern),
                Link.target_url.ilike(pattern),
            )
        )

    order = {
        "newest": Link.created_at.desc(),
        "oldest": Link.created_at.asc(),
        "clicks": clicks.desc(),
    }[sort]
    rows = session.exec(query.order_by(order)).all()

    return render(
        request,
        "dashboard.html",
        user=user,
        rows=rows,
        sort=sort,
        q=search,
        # Needed to tell "you have no links yet" apart from "your search
        # matched nothing", which are two different messages.
        has_any_links=session.exec(
            select(func.count(Link.id)).where(Link.user_id == user.id)
        ).one()
        > 0,
    )


@app.post("/links")
def create_link(
    request: Request,
    target_url: str = Form(...),
    title: str = Form(""),
    custom_code: str = Form(""),
    expires_in: str = Form(""),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    try:
        url = normalise_url(target_url)
        code = (
            validate_custom_code(session, custom_code)
            if custom_code.strip()
            else unique_code(session)
        )
    except ValueError as exc:
        flash(request, str(exc))
        return redirect("/")

    session.add(
        Link(
            code=code,
            target_url=url,
            title=title.strip() or None,
            user_id=user.id,
            expires_at=expiry_from_choice(expires_in),
        )
    )
    session.commit()
    flash(request, f"Created {BASE_URL}/{code}", kind="success")
    return redirect("/")


@app.get("/links/{link_id}/edit", response_class=HTMLResponse)
def edit_page(link_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    link = owned_link(link_id, user, session)
    if link is None:
        flash(request, "Link not found.")
        return redirect("/")

    return render(request, "edit.html", user=user, link=link)


@app.post("/links/{link_id}/edit")
def edit_link(
    link_id: int,
    request: Request,
    target_url: str = Form(...),
    title: str = Form(""),
    expires_in: str = Form("keep"),
    session: Session = Depends(get_session),
):
    """Changes where a link points, but never its short code.

    That is the whole point: a code printed on a CV keeps working while the
    page it leads to can be swapped out later.
    """
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    link = owned_link(link_id, user, session)
    if link is None:
        flash(request, "Link not found.")
        return redirect("/")

    try:
        link.target_url = normalise_url(target_url)
    except ValueError as exc:
        return render(request, "edit.html", user=user, link=link, error=str(exc))

    link.title = title.strip() or None
    if expires_in != "keep":
        link.expires_at = expiry_from_choice(expires_in)

    session.add(link)
    session.commit()
    flash(request, "Link updated.", kind="success")
    return redirect("/")


@app.post("/links/{link_id}/delete")
def delete_link(link_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    link = owned_link(link_id, user, session)
    if link is None:
        flash(request, "Link not found.")
        return redirect("/")

    for click in session.exec(select(Click).where(Click.link_id == link.id)).all():
        session.delete(click)
    session.delete(link)
    session.commit()
    flash(request, "Link deleted.", kind="success")
    return redirect("/")


@app.get("/links/{link_id}/qr.png")
def qr_png(link_id: int, request: Request, session: Session = Depends(get_session)):
    """Draws a QR code holding the short link, as a PNG image."""
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    link = owned_link(link_id, user, session)
    if link is None:
        return Response(status_code=404)

    image = qrcode.make(f"{BASE_URL}/{link.code}")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{link.code}.png"'},
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _browser_of(user_agent: str | None) -> str:
    """A deliberately simple guess, good enough for a chart."""
    ua = (user_agent or "").lower()
    for needle, name in (
        ("edg/", "Edge"), ("opr/", "Opera"), ("chrome", "Chrome"),
        ("safari", "Safari"), ("firefox", "Firefox"), ("bot", "Bot"),
    ):
        if needle in ua:
            return name
    return "Other"


@app.get("/links/{link_id}/stats", response_class=HTMLResponse)
def stats_page(link_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user is None:
        return redirect("/login")

    link = owned_link(link_id, user, session)
    if link is None:
        flash(request, "Link not found.")
        return redirect("/")

    total = session.exec(
        select(func.count(Click.id)).where(Click.link_id == link.id)
    ).one()
    return render(request, "stats.html", user=user, link=link, total=total)


@app.get("/api/links/{link_id}/stats")
def stats_data(link_id: int, request: Request, session: Session = Depends(get_session)):
    """The numbers behind the charts, as JSON. The stats page fetches this."""
    user = current_user(request, session)
    if user is None:
        return JSONResponse({"detail": "Not logged in"}, status_code=401)

    link = owned_link(link_id, user, session)
    if link is None:
        return JSONResponse({"detail": "Not found"}, status_code=404)

    clicks = session.exec(select(Click).where(Click.link_id == link.id)).all()

    # Last 30 days, including days with zero clicks so the line has no gaps.
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=offset) for offset in range(29, -1, -1)]
    per_day = Counter(as_utc(click.clicked_at).date() for click in clicks)

    referrers = Counter(
        (click.referrer or "Direct / typed in") for click in clicks
    ).most_common(5)
    browsers = Counter(_browser_of(click.user_agent) for click in clicks).most_common()

    return {
        "total": len(clicks),
        "timeline": {
            "labels": [day.isoformat() for day in days],
            "values": [per_day.get(day, 0) for day in days],
        },
        "referrers": {
            "labels": [name for name, _ in referrers],
            "values": [count for _, count in referrers],
        },
        "browsers": {
            "labels": [name for name, _ in browsers],
            "values": [count for _, count in browsers],
        },
    }


@app.get("/health")
def health():
    """Hosting platforms ping this to check the app is alive."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# The redirect. Declared LAST so it never swallows the pages above.
# ---------------------------------------------------------------------------

@app.get("/{code}")
def follow(code: str, request: Request, session: Session = Depends(get_session)):
    link = session.exec(select(Link).where(Link.code == code)).first()
    if link is None:
        return render(request, "not_found.html", status_code=404, code=code)

    if link.is_expired:
        # 410 Gone means "this existed, and deliberately does not any more",
        # which is more honest than a plain 404.
        return render(request, "expired.html", status_code=410, link=link)

    referrer = request.headers.get("referer")
    session.add(
        Click(
            link_id=link.id,
            referrer=referrer[:300] if referrer else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    session.commit()

    # 307 keeps browsers from caching the redirect, so every visit is counted.
    return RedirectResponse(url=link.target_url, status_code=307)
