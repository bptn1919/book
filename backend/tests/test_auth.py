from fastapi.testclient import TestClient

from app.main import app

REG_ALICE = {"name": "Alice", "email": "alice@example.com"}
REG_BOB = {"name": "Bob", "email": "bob@example.com"}
REG_CAROL = {"name": "Carol", "email": "carol@example.com"}


def test_register_creates_user_and_sets_session():
    with TestClient(app) as client:
        r = client.post("/api/auth/register", json=REG_ALICE)
        assert r.status_code == 201
        assert r.json()["name"] == "Alice"
        assert r.json()["email"] == "alice@example.com"
        assert "id" in r.json()
        me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == "Alice"
    assert me.json()["email"] == "alice@example.com"


def test_register_duplicate_email_returns_409():
    with TestClient(app) as client:
        client.post("/api/auth/register", json=REG_ALICE)
        r = client.post("/api/auth/register", json={"name": "Alice2", "email": "alice@example.com"})
    assert r.status_code == 409


def test_login_finds_existing_user_by_email():
    with TestClient(app) as client:
        client.post("/api/auth/register", json=REG_BOB)
        client.post("/api/auth/logout")
        r = client.post("/api/auth/login", json={"email": "bob@example.com"})
        assert r.status_code == 200
        assert r.json()["name"] == "Bob"
        assert r.json()["email"] == "bob@example.com"
        me = client.get("/api/auth/me")
    assert me.status_code == 200


def test_login_unknown_email_returns_404():
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"email": "ghost@example.com"})
    assert r.status_code == 404


def test_logout_invalidates_session():
    with TestClient(app) as client:
        client.post("/api/auth/register", json=REG_CAROL)
        client.post("/api/auth/logout")
        r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_without_session_returns_401():
    with TestClient(app) as client:
        r = client.get("/api/auth/me")
    assert r.status_code == 401
