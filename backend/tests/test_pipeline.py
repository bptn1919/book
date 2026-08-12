from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app import models
from app.pipeline import (
    STUCK_THRESHOLD_SECONDS,
    claim_step,
    complete_step,
    fail_step,
    is_stuck,
)


def test_complete_step_sets_next_status_and_resets_state():
    conn = MagicMock()
    complete_step(conn, "p1", "STYLE_SET")
    sql, params = conn.execute.call_args[0]
    assert params[0] == "STYLE_SET"
    assert "IDLE" in sql
    assert "step_started_at=NULL" in sql


def test_fail_step_sets_failed_and_clears_timestamp():
    conn = MagicMock()
    fail_step(conn, "p1")
    sql, params = conn.execute.call_args[0]
    assert "FAILED" in sql
    assert "step_started_at=NULL" in sql
    assert params[0] == "p1"


def test_is_stuck_false_when_idle():
    assert not is_stuck("IDLE", None)


def test_is_stuck_false_when_no_timestamp():
    assert not is_stuck("RUNNING", None)


def test_is_stuck_false_when_recently_started():
    recent = datetime.now(timezone.utc).isoformat()
    assert not is_stuck("RUNNING", recent)


def test_is_stuck_true_when_over_threshold():
    old = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_THRESHOLD_SECONDS + 1)
    ).isoformat()
    assert is_stuck("RUNNING", old)


def test_is_stuck_false_when_failed():
    old = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_THRESHOLD_SECONDS + 1)
    ).isoformat()
    assert not is_stuck("FAILED", old)


def _seed(status: str = "CREATED", step_state: str = "IDLE", step_started_at: str | None = None) -> None:
    models.init_db()
    with models.get_db() as conn:
        conn.execute("INSERT INTO users VALUES ('u1','Test','test@example.com','2026-01-01')")
        conn.execute(
            "INSERT INTO projects (id,user_id,title,status,step_state,step_started_at,created_at) "
            "VALUES ('p1','u1','Book',?,?,?,'2026-01-01')",
            (status, step_state, step_started_at),
        )


def test_claim_step_sets_running():
    _seed(status="CREATED")
    claim_step("p1", "CREATED")
    with models.get_db() as conn:
        row = conn.execute("SELECT step_state FROM projects WHERE id='p1'").fetchone()
    assert row["step_state"] == "RUNNING"


def test_claim_step_409_when_already_running():
    recent = datetime.now(timezone.utc).isoformat()
    _seed(status="CREATED", step_state="RUNNING", step_started_at=recent)
    with pytest.raises(HTTPException) as exc:
        claim_step("p1", "CREATED")
    assert exc.value.status_code == 409
    assert "already running" in exc.value.detail


def test_claim_step_409_when_wrong_status():
    _seed(status="CREATED")
    with pytest.raises(HTTPException) as exc:
        claim_step("p1", "STYLE_SET")
    assert exc.value.status_code == 409
    assert "CREATED" in exc.value.detail


def test_claim_step_404_for_missing_project():
    models.init_db()
    with pytest.raises(HTTPException) as exc:
        claim_step("no-such-id", "CREATED")
    assert exc.value.status_code == 404


def test_claim_step_overrides_stuck_running():
    stuck_at = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_THRESHOLD_SECONDS + 1)
    ).isoformat()
    _seed(status="CREATED", step_state="RUNNING", step_started_at=stuck_at)
    claim_step("p1", "CREATED")  # should not raise
    with models.get_db() as conn:
        row = conn.execute("SELECT step_state FROM projects WHERE id='p1'").fetchone()
    assert row["step_state"] == "RUNNING"


def test_is_stuck_handles_naive_timestamp():
    old = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_THRESHOLD_SECONDS + 1)
    ).replace(tzinfo=None).isoformat()
    assert is_stuck("RUNNING", old)
