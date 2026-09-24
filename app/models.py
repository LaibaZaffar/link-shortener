"""The three database tables, described as Python classes."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_column(**kwargs) -> Column:
    """A timestamp column that remembers its timezone.

    PostgreSQL has two date types: "timestamp" throws the timezone away, and
    "timestamptz" keeps it. Using the second one means a database server set
    to a different timezone can never silently shift our dates. SQLite has no
    real date type either way, so this changes nothing locally.
    """
    return Column(DateTime(timezone=True), **kwargs)


def as_utc(value: datetime) -> datetime:
    """Attaches UTC to a date that came back from the database without one.

    SQLite has no real date type, so it hands dates back "naive" (no timezone
    attached). Comparing a naive date with an aware one raises TypeError, so
    every date read from the database goes through here first.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow, sa_column=utc_column(nullable=False))

    links: list["Link"] = Relationship(back_populates="owner")


class Link(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # index=True makes lookups by code fast, which matters because every
    # single redirect does exactly this lookup.
    code: str = Field(index=True, unique=True)
    target_url: str
    title: str | None = None
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utcnow, sa_column=utc_column(nullable=False))
    # None means "never expires", which is the default.
    expires_at: datetime | None = Field(default=None, sa_column=utc_column(nullable=True))

    owner: User | None = Relationship(back_populates="links")
    clicks: list["Click"] = Relationship(back_populates="link")

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return as_utc(self.expires_at) <= utcnow()


class Click(SQLModel, table=True):
    """One row per visit. Storing raw events (instead of a counter) is what
    lets you draw charts later."""

    id: int | None = Field(default=None, primary_key=True)
    link_id: int = Field(foreign_key="link.id", index=True)
    clicked_at: datetime = Field(
        default_factory=utcnow, sa_column=utc_column(index=True, nullable=False)
    )
    referrer: str | None = None
    user_agent: str | None = None

    link: Link | None = Relationship(back_populates="clicks")
