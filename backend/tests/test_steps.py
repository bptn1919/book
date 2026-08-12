from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import models
from app.main import app

BOOK = ("book.txt", b"Once upon a time...", "text/plain")

FAKE_STYLE = {
    "book_uri": "gs://fake/book.txt",
    "text_chain_last_id": "interaction-style-1",
    "art_style": "watercolor, soft pastels",
}


def _setup(client: TestClient, name: str = "Alice") -> str:
    client.post("/api/auth/register", json={"name": name, "email": f"{name.lower()}@example.com"})
    return client.post(
        "/api/projects", data={"title": "Book"}, files={"book": BOOK}
    ).json()["id"]


# ── Style step ─────────────────────────────────────────────────────────────────

def test_style_step_sets_style_set_status():
    with patch("app.pipeline._run_style_sync", return_value=FAKE_STYLE):
        with TestClient(app) as client:
            pid = _setup(client)
            r = client.post(f"/api/projects/{pid}/style", json={"art_style": "watercolor"})
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "STYLE_SET"
    assert project["step_state"] == "IDLE"
    assert project["art_style"] == "watercolor, soft pastels"


def test_style_step_stores_chain_id_and_book_uri():
    with patch("app.pipeline._run_style_sync", return_value=FAKE_STYLE):
        with TestClient(app) as client:
            pid = _setup(client)
            client.post(f"/api/projects/{pid}/style", json={"art_style": "watercolor"})
    with models.get_db() as conn:
        row = conn.execute(
            "SELECT book_uri, text_chain_last_id FROM projects WHERE id=?", (pid,)
        ).fetchone()
    assert row["book_uri"] == "gs://fake/book.txt"
    assert row["text_chain_last_id"] == "interaction-style-1"


def test_style_step_empty_style_uses_gemini_generated():
    generated = {**FAKE_STYLE, "art_style": "pen and ink, cross-hatching"}
    with patch("app.pipeline._run_style_sync", return_value=generated):
        with TestClient(app) as client:
            pid = _setup(client)
            r = client.post(f"/api/projects/{pid}/style", json={"art_style": ""})
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["art_style"] == "pen and ink, cross-hatching"


def test_style_step_fails_on_gemini_error():
    with patch("app.pipeline._run_style_sync", side_effect=RuntimeError("quota exceeded")):
        with TestClient(app, raise_server_exceptions=False) as client:
            pid = _setup(client)
            r = client.post(f"/api/projects/{pid}/style", json={"art_style": "watercolor"})
            assert r.status_code == 500
            project = client.get(f"/api/projects/{pid}").json()
    assert project["step_state"] == "FAILED"
    assert project["status"] == "CREATED"


def test_style_step_409_when_already_running():
    with TestClient(app) as client:
        pid = _setup(client)
        recent = datetime.now(timezone.utc).isoformat()
        with models.get_db() as conn:
            conn.execute(
                "UPDATE projects SET step_state='RUNNING', step_started_at=? WHERE id=?",
                (recent, pid),
            )
        r = client.post(f"/api/projects/{pid}/style", json={"art_style": "watercolor"})
    assert r.status_code == 409


def test_style_step_409_wrong_status():
    with patch("app.pipeline._run_style_sync", return_value=FAKE_STYLE):
        with TestClient(app) as client:
            pid = _setup(client)
            # Advance status past CREATED
            with models.get_db() as conn:
                conn.execute("UPDATE projects SET status='STYLE_SET' WHERE id=?", (pid,))
            r = client.post(f"/api/projects/{pid}/style", json={"art_style": "watercolor"})
    assert r.status_code == 409


# ── Characters step ────────────────────────────────────────────────────────────

FAKE_CHARACTERS = {
    "characters": [
        {"name": "Mole", "prompt": "A small, velvety black mole with tiny pink hands..."},
        {"name": "Rat", "prompt": "A water rat with sleek brown fur and bright eyes..."},
        {"name": "Extra", "prompt": "Should be dropped — cap is 2"},
    ],
    "text_chain_last_id": "interaction-chars-1",
}


def _advance_to_style_set(client: TestClient, pid: str) -> None:
    with models.get_db() as conn:
        conn.execute(
            "UPDATE projects SET status='STYLE_SET', text_chain_last_id='chain-1' WHERE id=?",
            (pid,),
        )


def test_characters_step_stores_up_to_two_characters():
    with patch("app.pipeline._run_characters_sync", return_value=FAKE_CHARACTERS):
        with TestClient(app) as client:
            pid = _setup(client)
            _advance_to_style_set(client, pid)
            r = client.post(f"/api/projects/{pid}/characters")
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "CHARACTERS_GENERATED"
    assert len(project["characters"]) == 2
    assert project["characters"][0]["name"] == "Mole"


def test_characters_step_fails_on_gemini_error():
    with patch("app.pipeline._run_characters_sync", side_effect=RuntimeError("timeout")):
        with TestClient(app, raise_server_exceptions=False) as client:
            pid = _setup(client)
            _advance_to_style_set(client, pid)
            r = client.post(f"/api/projects/{pid}/characters")
            assert r.status_code == 500
            project = client.get(f"/api/projects/{pid}").json()
    assert project["step_state"] == "FAILED"
    assert project["status"] == "STYLE_SET"


def test_characters_step_409_wrong_status():
    with TestClient(app) as client:
        pid = _setup(client)  # status=CREATED, not STYLE_SET
        r = client.post(f"/api/projects/{pid}/characters")
    assert r.status_code == 409


# ── Portraits step ─────────────────────────────────────────────────────────────

def _advance_to_characters_generated(client: TestClient, pid: str) -> tuple[str, str]:
    c1, c2 = "char-aaa", "char-bbb"
    with models.get_db() as conn:
        conn.execute(
            "UPDATE projects SET status='CHARACTERS_GENERATED', art_style='watercolor' WHERE id=?",
            (pid,),
        )
        conn.execute(
            "INSERT INTO characters VALUES (?,?,'Mole','A mole desc',NULL)", (c1, pid)
        )
        conn.execute(
            "INSERT INTO characters VALUES (?,?,'Rat','A rat desc',NULL)", (c2, pid)
        )
    return c1, c2


def test_portraits_step_sets_portrait_paths():
    with TestClient(app) as client:
        pid = _setup(client)
        c1, c2 = _advance_to_characters_generated(client, pid)
        fake = {
            "portraits": [(c1, "portrait_0.png"), (c2, "portrait_1.png")],
            "image_chain_last_id": "img-chain-1",
        }
        with patch("app.pipeline._run_portraits_sync", return_value=fake):
            r = client.post(f"/api/projects/{pid}/portraits")
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "PORTRAITS_GENERATED"
    paths = {c["name"]: c["portrait_path"] for c in project["characters"]}
    assert paths["Mole"] == "portrait_0.png"
    assert paths["Rat"] == "portrait_1.png"


def test_portraits_step_stores_image_chain_id():
    with TestClient(app) as client:
        pid = _setup(client)
        c1, c2 = _advance_to_characters_generated(client, pid)
        fake = {
            "portraits": [(c1, "portrait_0.png"), (c2, "portrait_1.png")],
            "image_chain_last_id": "img-chain-1",
        }
        with patch("app.pipeline._run_portraits_sync", return_value=fake):
            client.post(f"/api/projects/{pid}/portraits")
    with models.get_db() as conn:
        row = conn.execute(
            "SELECT image_chain_last_id FROM projects WHERE id=?", (pid,)
        ).fetchone()
    assert row["image_chain_last_id"] == "img-chain-1"


def test_portraits_step_fails_on_gemini_error():
    with TestClient(app, raise_server_exceptions=False) as client:
        pid = _setup(client)
        _advance_to_characters_generated(client, pid)
        with patch("app.pipeline._run_portraits_sync", side_effect=RuntimeError("error")):
            r = client.post(f"/api/projects/{pid}/portraits")
            assert r.status_code == 500
            project = client.get(f"/api/projects/{pid}").json()
    assert project["step_state"] == "FAILED"
    assert project["status"] == "CHARACTERS_GENERATED"


def test_portraits_step_409_wrong_status():
    with TestClient(app) as client:
        pid = _setup(client)  # status=CREATED, not CHARACTERS_GENERATED
        r = client.post(f"/api/projects/{pid}/portraits")
    assert r.status_code == 409


def test_portraits_step_can_retry_after_failure():
    """Verify that a failed portraits step can be retried successfully."""
    c1, c2 = "char-aaa", "char-bbb"
    fake = {
        "portraits": [(c1, "portrait_0.png"), (c2, "portrait_1.png")],
        "image_chain_last_id": "img-chain-1",
    }
    
    with TestClient(app, raise_server_exceptions=False) as client:
        pid = _setup(client)
        _advance_to_characters_generated(client, pid)
        
        # First attempt: fail
        with patch("app.pipeline._run_portraits_sync", side_effect=RuntimeError("Gemini error")):
            r = client.post(f"/api/projects/{pid}/portraits")
            assert r.status_code == 500
        
        project = client.get(f"/api/projects/{pid}").json()
        assert project["step_state"] == "FAILED"
        assert project["status"] == "CHARACTERS_GENERATED"
        
        # Retry: should succeed
        with patch("app.pipeline._run_portraits_sync", return_value=fake):
            r = client.post(f"/api/projects/{pid}/portraits")
            assert r.status_code == 200, f"Retry failed with: {r.text}"
        
        project = client.get(f"/api/projects/{pid}").json()
        assert project["step_state"] == "IDLE"
        assert project["status"] == "PORTRAITS_GENERATED"


# ── Chapters step ─────────────────────────────────────────────────────────────

FAKE_CHAPTERS = {
    "chapters": [
        {"name": "Chapter 1", "prompt": "Mole abandons his spring-cleaning and escapes to the riverbank..."},
        {"name": "Chapter 2", "prompt": "Should be dropped — cap is 1"},
    ],
    "text_chain_last_id": "interaction-chapters-1",
}


def _advance_to_portraits_generated(client: TestClient, pid: str) -> tuple[str, str]:
    c1, c2 = "char-aaa", "char-bbb"
    with models.get_db() as conn:
        conn.execute(
            "UPDATE projects SET status='PORTRAITS_GENERATED', art_style='watercolor', "
            "image_chain_last_id='img-chain-1', text_chain_last_id='chain-1' WHERE id=?",
            (pid,),
        )
        conn.execute(
            "INSERT INTO characters VALUES (?,?,'Mole','A mole desc','portrait_0.png')", (c1, pid)
        )
        conn.execute(
            "INSERT INTO characters VALUES (?,?,'Rat','A rat desc','portrait_1.png')", (c2, pid)
        )
    return c1, c2


def test_chapters_step_stores_up_to_one_chapter():
    with patch("app.pipeline._run_chapters_sync", return_value=FAKE_CHAPTERS):
        with TestClient(app) as client:
            pid = _setup(client)
            _advance_to_portraits_generated(client, pid)
            r = client.post(f"/api/projects/{pid}/chapters")
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "CHAPTERS_GENERATED"
    assert len(project["chapters"]) == 1
    assert project["chapters"][0]["name"] == "Chapter 1"


def test_chapters_step_fails_on_gemini_error():
    with patch("app.pipeline._run_chapters_sync", side_effect=RuntimeError("timeout")):
        with TestClient(app, raise_server_exceptions=False) as client:
            pid = _setup(client)
            _advance_to_portraits_generated(client, pid)
            r = client.post(f"/api/projects/{pid}/chapters")
            assert r.status_code == 500
            project = client.get(f"/api/projects/{pid}").json()
    assert project["step_state"] == "FAILED"
    assert project["status"] == "PORTRAITS_GENERATED"


def test_chapters_step_409_wrong_status():
    with TestClient(app) as client:
        pid = _setup(client)  # status=CREATED, not PORTRAITS_GENERATED
        r = client.post(f"/api/projects/{pid}/chapters")
    assert r.status_code == 409


# ── Illustrations step ─────────────────────────────────────────────────────────

def _advance_to_chapters_generated(client: TestClient, pid: str) -> str:
    ch1 = "chapter-aaa"
    with models.get_db() as conn:
        conn.execute(
            "UPDATE projects SET status='CHAPTERS_GENERATED', image_chain_last_id='img-chain-1' WHERE id=?",
            (pid,),
        )
        conn.execute(
            "INSERT INTO chapters VALUES (?,?,'Chapter 1','A long prompt...',NULL)", (ch1, pid)
        )
    return ch1


def test_illustrations_step_sets_illustration_paths():
    with TestClient(app) as client:
        pid = _setup(client)
        ch1 = _advance_to_chapters_generated(client, pid)
        fake = {
            "illustrations": [(ch1, "illustration_0.png")],
            "image_chain_last_id": "img-chain-final",
        }
        with patch("app.pipeline._run_illustrations_sync", return_value=fake):
            r = client.post(f"/api/projects/{pid}/illustrations")
            assert r.status_code == 200
            project = client.get(f"/api/projects/{pid}").json()
    assert project["status"] == "DONE"
    assert project["chapters"][0]["illustration_path"] == "illustration_0.png"


def test_illustrations_step_fails_on_gemini_error():
    with TestClient(app, raise_server_exceptions=False) as client:
        pid = _setup(client)
        _advance_to_chapters_generated(client, pid)
        with patch("app.pipeline._run_illustrations_sync", side_effect=RuntimeError("error")):
            r = client.post(f"/api/projects/{pid}/illustrations")
            assert r.status_code == 500
            project = client.get(f"/api/projects/{pid}").json()
    assert project["step_state"] == "FAILED"
    assert project["status"] == "CHAPTERS_GENERATED"


def test_illustrations_step_409_wrong_status():
    with TestClient(app) as client:
        pid = _setup(client)  # status=CREATED, not CHAPTERS_GENERATED
        r = client.post(f"/api/projects/{pid}/illustrations")
    assert r.status_code == 409


def test_image_endpoint_blocks_path_traversal():
    with TestClient(app) as client:
        pid = _setup(client)
        r = client.get(f"/api/projects/{pid}/images/../../etc/passwd")
    assert r.status_code in (400, 404)


def test_style_step_requires_auth():
    with TestClient(app) as client:
        r = client.post("/api/projects/fake/style", json={"art_style": "watercolor"})
    assert r.status_code == 401


def test_style_step_404_unknown_project():
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Alice", "email": "alice@example.com"})
        r = client.post("/api/projects/no-such-id/style", json={"art_style": "watercolor"})
    assert r.status_code == 404
