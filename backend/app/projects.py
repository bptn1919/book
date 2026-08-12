import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .auth import CurrentUser
from .models import get_db
from . import pipeline
from .pipeline import is_stuck
from .storage import save_book

router = APIRouter(prefix="/api/projects", tags=["projects"])


class StyleIn(BaseModel):
    art_style: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def list_projects(user: CurrentUser):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, status, step_state, created_at "
            "FROM projects WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
async def create_project(
    user: CurrentUser,
    title: str = Form(...),
    book: UploadFile = File(...),
):
    project_id = str(uuid.uuid4())
    content = await book.read()
    save_book(project_id, content)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id,user_id,title,status,step_state,created_at) "
            "VALUES (?,?,?,'CREATED','IDLE',?)",
            (project_id, user["id"], title, _now()),
        )
    return {"id": project_id, "title": title, "status": "CREATED", "step_state": "IDLE"}


@router.get("/{project_id}")
def get_project(project_id: str, user: CurrentUser):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, status, step_state, step_started_at, art_style, created_at "
            "FROM projects WHERE id=? AND user_id=?",
            (project_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        characters = conn.execute(
            "SELECT id, name, prompt, portrait_path FROM characters WHERE project_id=?",
            (project_id,),
        ).fetchall()
        chapters = conn.execute(
            "SELECT id, name, prompt, illustration_path FROM chapters WHERE project_id=?",
            (project_id,),
        ).fetchall()
    project = dict(row)
    return {
        **project,
        "is_stuck": is_stuck(project["step_state"], project["step_started_at"]),
        "characters": [dict(c) for c in characters],
        "chapters": [dict(c) for c in chapters],
    }


@router.post("/{project_id}/style")
async def run_style_step(project_id: str, body: StyleIn, user: CurrentUser):
    with get_db() as conn:
        row = conn.execute(
            "SELECT book_uri FROM projects WHERE id=? AND user_id=?",
            (project_id, user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    await pipeline.run_style(project_id, body.art_style, row["book_uri"])
    return {"ok": True}
