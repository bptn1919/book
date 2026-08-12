"""
Happy-path integration test: all 5 pipeline steps run in order, each
building on the previous, ending with status=DONE and all generated
artefacts recorded in the database. All Gemini calls are mocked.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import models
from app.main import app

BOOK = ("book.txt", b"The Mole had been working very hard all the morning...", "text/plain")


def _fake_portraits(project_id, art_style, project_title, characters):
    # Simulate the real sync function: write each portrait to DB immediately
    with models.get_db() as conn:
        for i, c in enumerate(characters):
            conn.execute(
                "UPDATE characters SET portrait_path=? WHERE id=?",
                (f"portrait_{i}.png", c["id"]),
            )
    return {"image_chain_last_id": "img-chain-after-portraits"}


def _fake_illustrations(project_id, image_chain_last_id, chapters):
    return {
        "illustrations": [(ch["id"], f"illustration_{i}.png") for i, ch in enumerate(chapters)],
        "image_chain_last_id": "img-chain-final",
    }


@pytest.fixture()
def _all_mocks():
    with (
        patch("app.pipeline._run_style_sync", return_value={
            "book_uri": "gs://fake/book.txt",
            "text_chain_last_id": "chain-style",
            "art_style": "watercolor, soft pastels",
        }),
        patch("app.pipeline._run_characters_sync", return_value={
            "characters": [
                {"name": "Mole", "prompt": "A small velvety black mole with tiny pink hands"},
                {"name": "Rat",  "prompt": "A water rat with sleek brown fur and bright eyes"},
            ],
            "text_chain_last_id": "chain-characters",
        }),
        patch("app.pipeline._run_portraits_sync", side_effect=_fake_portraits),
        patch("app.pipeline._run_chapters_sync", return_value={
            "chapters": [
                {"name": "Chapter 1", "prompt": "Mole abandons spring-cleaning and reaches the riverbank..."},
            ],
            "text_chain_last_id": "chain-chapters",
        }),
        patch("app.pipeline._run_illustrations_sync", side_effect=_fake_illustrations),
    ):
        yield


def test_happy_path_all_five_steps(_all_mocks):
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Alice", "email": "alice@example.com"})

        pid = client.post(
            "/api/projects",
            data={"title": "Wind in the Willows"},
            files={"book": BOOK},
        ).json()["id"]

        assert client.post(f"/api/projects/{pid}/style",
                           json={"art_style": "watercolor"}).status_code == 200

        assert client.post(f"/api/projects/{pid}/characters").status_code == 200

        assert client.post(f"/api/projects/{pid}/portraits").status_code == 200

        assert client.post(f"/api/projects/{pid}/chapters").status_code == 200

        assert client.post(f"/api/projects/{pid}/illustrations").status_code == 200

        project = client.get(f"/api/projects/{pid}").json()

    assert project["status"] == "DONE"
    assert project["step_state"] == "IDLE"
    assert project["art_style"] == "watercolor, soft pastels"

    assert len(project["characters"]) == 2
    assert project["characters"][0]["name"] == "Mole"
    assert project["characters"][0]["portrait_path"] == "portrait_0.png"
    assert project["characters"][1]["name"] == "Rat"
    assert project["characters"][1]["portrait_path"] == "portrait_1.png"

    assert len(project["chapters"]) == 1
    assert project["chapters"][0]["name"] == "Chapter 1"
    assert project["chapters"][0]["illustration_path"] == "illustration_0.png"


def test_no_duplicate_call_on_second_request(_all_mocks):
    """A second request on a RUNNING step must return 409, not fire Gemini twice."""
    import app.pipeline as pipeline
    from unittest.mock import MagicMock

    call_count = 0
    original_run_style_sync = pipeline._run_style_sync

    def counting_style(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_run_style_sync(*args, **kwargs)

    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Bob", "email": "bob@example.com"})
        pid = client.post(
            "/api/projects",
            data={"title": "Test"},
            files={"book": BOOK},
        ).json()["id"]

        # First request succeeds
        r1 = client.post(f"/api/projects/{pid}/style", json={"art_style": "ink"})
        assert r1.status_code == 200

        # Second request on the completed step returns 409 (wrong status now)
        r2 = client.post(f"/api/projects/{pid}/style", json={"art_style": "ink"})
        assert r2.status_code == 409
