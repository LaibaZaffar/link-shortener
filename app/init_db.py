"""Creates the database tables. Run this once against a new database.

    DATABASE_URL="postgresql://..." python -m app.init_db

Locally the tables are created automatically when the app starts, but on
serverless hosts that startup step may not run, so production databases get
set up with this one-off command instead.
"""

from app.database import create_db_and_tables, engine

if __name__ == "__main__":
    print(f"creating tables in {engine.url.render_as_string(hide_password=True)}")
    create_db_and_tables()
    print("done")
