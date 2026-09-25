"""Creates the database tables. Run this once against a new database.

    DATABASE_URL="postgresql://..." .venv/bin/python -m app.init_db

Locally the tables are created automatically when the app starts, but on
serverless hosts that startup step may not run, so production databases get
set up with this one-off command instead.
"""

import sys

from app.config import DATABASE_URL

if __name__ == "__main__":
    # Checked before importing app.database, because that module builds the
    # engine as soon as it is imported and would fail with a less helpful error.
    if not DATABASE_URL.startswith(("postgresql://", "postgres://", "sqlite:")):
        sys.exit(
            "DATABASE_URL does not look like a database address.\n"
            f"  got: {DATABASE_URL!r}\n\n"
            "Paste the real connection string from your Neon project, e.g.\n"
            '  DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require" \\\n'
            "      .venv/bin/python -m app.init_db"
        )

    from app.database import create_db_and_tables, engine

    print(f"creating tables in {engine.url.render_as_string(hide_password=True)}")
    create_db_and_tables()

    from sqlmodel import SQLModel

    print("tables:", ", ".join(sorted(SQLModel.metadata.tables)))
    print("done")
