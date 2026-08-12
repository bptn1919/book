from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.pipeline import (
    STUCK_THRESHOLD_SECONDS,
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


def test_is_stuck_handles_naive_timestamp():
    old = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_THRESHOLD_SECONDS + 1)
    ).replace(tzinfo=None).isoformat()
    assert is_stuck("RUNNING", old)
