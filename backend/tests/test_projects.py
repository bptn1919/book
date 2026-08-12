from fastapi.testclient import TestClient

from app.main import app

BOOK = ("book.txt", b"Once upon a time...", "text/plain")


def _register(client: TestClient, name: str = "Alice") -> None:
    client.post("/api/auth/register", json={"name": name})


def test_list_projects_empty():
    with TestClient(app) as client:
        _register(client)
        r = client.get("/api/projects")
    assert r.status_code == 200
    assert r.json() == []


def test_create_project_returns_metadata():
    with TestClient(app) as client:
        _register(client)
        r = client.post("/api/projects", data={"title": "My Book"}, files={"book": BOOK})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "My Book"
    assert data["status"] == "CREATED"
    assert data["step_state"] == "IDLE"
    assert "id" in data


def test_get_project_includes_characters_and_chapters():
    with TestClient(app) as client:
        _register(client)
        pid = client.post(
            "/api/projects", data={"title": "My Book"}, files={"book": BOOK}
        ).json()["id"]
        r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "My Book"
    assert data["characters"] == []
    assert data["chapters"] == []


def test_list_shows_created_projects():
    with TestClient(app) as client:
        _register(client)
        client.post("/api/projects", data={"title": "Book A"}, files={"book": BOOK})
        client.post("/api/projects", data={"title": "Book B"}, files={"book": BOOK})
        r = client.get("/api/projects")
    assert r.status_code == 200
    titles = [p["title"] for p in r.json()]
    assert "Book A" in titles and "Book B" in titles


def test_project_requires_auth():
    with TestClient(app) as client:
        r = client.get("/api/projects")
    assert r.status_code == 401


def test_get_project_not_found():
    with TestClient(app) as client:
        _register(client)
        r = client.get("/api/projects/no-such-id")
    assert r.status_code == 404


def test_cannot_access_other_users_project():
    with TestClient(app) as client:
        _register(client, "Alice")
        pid = client.post(
            "/api/projects", data={"title": "Alice's Book"}, files={"book": BOOK}
        ).json()["id"]
        client.post("/api/auth/logout")
        _register(client, "Bob")
        r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 404
