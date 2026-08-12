from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_cleanup(monkeypatch):
    from app import models

    # Tables must exist before seeding — init_db() creates them
    models.init_db()

    with models.get_db() as conn:
        conn.execute(
            "INSERT INTO users VALUES ('u1','Test','2026-01-01')"
        )
        conn.execute(
            "INSERT INTO projects"
            " (id,user_id,title,status,step_state,step_started_at,created_at)"
            " VALUES ('p1','u1','Book','STYLE_SET','RUNNING','2026-01-01T00:00:00','2026-01-01')"
        )

    with TestClient(app):  # lifespan runs here → cleanup fires
        pass

    with models.get_db() as conn:
        row = conn.execute(
            "SELECT step_state, step_started_at FROM projects WHERE id='p1'"
        ).fetchone()
    assert row["step_state"] == "FAILED"
    assert row["step_started_at"] is None
