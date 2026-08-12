import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .models import get_db

STUCK_THRESHOLD_SECONDS = 180  # 3 minutes

STATUS_SEQUENCE = [
    "CREATED",
    "STYLE_SET",
    "CHARACTERS_GENERATED",
    "PORTRAITS_GENERATED",
    "CHAPTERS_GENERATED",
    "DONE",
]


def complete_step(conn: sqlite3.Connection, project_id: str, next_status: str) -> None:
    conn.execute(
        "UPDATE projects SET status=?, step_state='IDLE', step_started_at=NULL WHERE id=?",
        (next_status, project_id),
    )


def fail_step(conn: sqlite3.Connection, project_id: str) -> None:
    conn.execute(
        "UPDATE projects SET step_state='FAILED', step_started_at=NULL WHERE id=?",
        (project_id,),
    )


def claim_step(project_id: str, required_status: str) -> None:
    """Atomically claim a pipeline step. Raises HTTPException on conflict."""
    now = datetime.now(timezone.utc)
    stuck_cutoff = (now - timedelta(seconds=STUCK_THRESHOLD_SECONDS)).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE projects SET step_state='RUNNING', step_started_at=? "
            "WHERE id=? AND status=? "
            "AND (step_state != 'RUNNING' OR step_started_at <= ?)",
            (now.isoformat(), project_id, required_status, stuck_cutoff),
        )
        if cur.rowcount == 0:
            row = conn.execute(
                "SELECT status, step_state FROM projects WHERE id=?",
                (project_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Project not found")
            if row["step_state"] == "RUNNING":
                raise HTTPException(409, "Step already running")
            raise HTTPException(
                409,
                f"Step requires status {required_status!r}, got {row['status']!r}",
            )


def is_stuck(step_state: str, step_started_at: str | None) -> bool:
    if step_state != "RUNNING" or step_started_at is None:
        return False
    started = datetime.fromisoformat(step_started_at)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return elapsed > STUCK_THRESHOLD_SECONDS
