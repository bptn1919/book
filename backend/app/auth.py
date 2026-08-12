import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from .models import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "session_id"


class RegisterIn(BaseModel):
    name: str
    email: str


class LoginIn(BaseModel):
    email: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_session(user_id: str, response: Response) -> None:
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?)",
            (session_id, user_id, _now()),
        )
    response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    with get_db() as conn:
        row = conn.execute(
            "SELECT u.id, u.name, u.email FROM sessions s "
            "JOIN users u ON u.id = s.user_id "
            "WHERE s.id=?",
            (session_id,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Invalid session")
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.post("/register", status_code=201)
def register(body: RegisterIn, response: Response):
    if not body.name.strip():
        raise HTTPException(422, "Name is required")
    if not body.email.strip() or "@" not in body.email:
        raise HTTPException(422, "Valid email is required")
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (body.email.lower(),)).fetchone():
            raise HTTPException(409, "Email already registered")
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (user_id, body.name.strip(), body.email.lower(), _now()),
        )
    _set_session(user_id, response)
    return {"id": user_id, "name": body.name.strip(), "email": body.email.lower()}


@router.post("/login")
def login(body: LoginIn, response: Response):
    if not body.email.strip():
        raise HTTPException(422, "Email is required")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE email=?", (body.email.lower(),)
        ).fetchone()
    if not row:
        raise HTTPException(404, "No account found for that email")
    _set_session(row["id"], response)
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser):
    return user
