import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "data/app.db")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS users (
                id         TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id                   TEXT PRIMARY KEY,
                user_id              TEXT NOT NULL REFERENCES users(id),
                title                TEXT NOT NULL,
                book_uri             TEXT,
                art_style            TEXT,
                status               TEXT NOT NULL DEFAULT 'CREATED',
                step_state           TEXT NOT NULL DEFAULT 'IDLE',
                step_started_at      TEXT,
                text_chain_last_id   TEXT,
                image_chain_last_id  TEXT,
                created_at           TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS characters (
                id            TEXT PRIMARY KEY,
                project_id    TEXT NOT NULL REFERENCES projects(id),
                name          TEXT NOT NULL,
                prompt        TEXT NOT NULL,
                portrait_path TEXT
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id                TEXT PRIMARY KEY,
                project_id        TEXT NOT NULL REFERENCES projects(id),
                name              TEXT NOT NULL,
                prompt            TEXT NOT NULL,
                illustration_path TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
