import sqlite3
from datetime import datetime, timezone

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


def is_stuck(step_state: str, step_started_at: str | None) -> bool:
    if step_state != "RUNNING" or step_started_at is None:
        return False
    started = datetime.fromisoformat(step_started_at)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return elapsed > STUCK_THRESHOLD_SECONDS
