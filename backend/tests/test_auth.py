from fastapi.testclient import TestClient

from app.main import app


def test_register_creates_user_and_sets_session():
    with TestClient(app) as client:
        r = client.post("/api/auth/register", json={"name": "Alice"})
        assert r.status_code == 201
        assert r.json()["name"] == "Alice"
        assert "id" in r.json()
        me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == "Alice"


def test_register_duplicate_name_returns_409():
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Alice"})
        r = client.post("/api/auth/register", json={"name": "Alice"})
    assert r.status_code == 409


def test_login_finds_existing_user():
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Bob"})
        client.post("/api/auth/logout")
        r = client.post("/api/auth/login", json={"name": "Bob"})
        assert r.status_code == 200
        assert r.json()["name"] == "Bob"
        me = client.get("/api/auth/me")
    assert me.status_code == 200


def test_login_unknown_name_returns_404():
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"name": "Ghost"})
    assert r.status_code == 404


def test_logout_invalidates_session():
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"name": "Carol"})
        client.post("/api/auth/logout")
        r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_without_session_returns_401():
    with TestClient(app) as client:
        r = client.get("/api/auth/me")
    assert r.status_code == 401
