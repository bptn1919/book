import asyncio
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from . import storage
from .models import get_db

STUCK_THRESHOLD_SECONDS = 180  # 3 minutes

TEXT_MODEL = "gemini-3.6-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"

SYSTEM_INSTRUCTIONS = (
    "There must be no text on the image, it should not look like a cover page. "
    "It should be a full illustration with no borders, titles, nor description. "
    "Unless asked otherwise, stay family-friendly with uplifting colors. "
    "Each produced image should be a simple image, no panels."
)

STATUS_SEQUENCE = [
    "CREATED",
    "STYLE_SET",
    "CHARACTERS_GENERATED",
    "PORTRAITS_GENERATED",
    "CHAPTERS_GENERATED",
    "DONE",
]


# ── State utilities ────────────────────────────────────────────────────────────

def complete_step(conn: sqlite3.Connection, project_id: str, next_status: str) -> None:
    conn.execute(
        "UPDATE projects SET status=?, step_state='IDLE', step_started_at=NULL WHERE id=?",
        (next_status, project_id),
    )


def fail_step(conn: sqlite3.Connection, project_id: str) -> None:
    conn.execute(
        "UPDATE projects SET step_state='FAILED', step_started_at=NULL WHERE id=?",
        (project_id,),
    )


def claim_step(project_id: str, required_status: str) -> None:
    """Atomically claim a pipeline step. Raises HTTPException on conflict."""
    now = datetime.now(timezone.utc)
    stuck_cutoff = (now - timedelta(seconds=STUCK_THRESHOLD_SECONDS)).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE projects SET step_state='RUNNING', step_started_at=? "
            "WHERE id=? AND status=? "
            "AND (step_state != 'RUNNING' OR step_started_at <= ?)",
            (now.isoformat(), project_id, required_status, stuck_cutoff),
        )
        if cur.rowcount == 0:
            row = conn.execute(
                "SELECT status, step_state FROM projects WHERE id=?",
                (project_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Project not found")
            if row["step_state"] == "RUNNING":
                raise HTTPException(409, "Step already running")
            raise HTTPException(
                409,
                f"Step requires status {required_status!r}, got {row['status']!r}",
            )


def is_stuck(step_state: str, step_started_at: str | None) -> bool:
    if step_state != "RUNNING" or step_started_at is None:
        return False
    started = datetime.fromisoformat(step_started_at)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return elapsed > STUCK_THRESHOLD_SECONDS


# ── Gemini client ──────────────────────────────────────────────────────────────

def _get_client():
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=60.0,
                http_status_codes=[429, 500, 502, 503, 504],
            )
        ),
    )


# ── Style step ─────────────────────────────────────────────────────────────────

async def run_style(project_id: str, art_style: str, existing_book_uri: str | None) -> None:
    claim_step(project_id, "CREATED")
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _run_style_sync, project_id, art_style, existing_book_uri
        )
    except Exception:
        with get_db() as conn:
            fail_step(conn, project_id)
        raise
    with get_db() as conn:
        conn.execute(
            "UPDATE projects SET book_uri=?, text_chain_last_id=?, art_style=? WHERE id=?",
            (result["book_uri"], result["text_chain_last_id"], result["art_style"], project_id),
        )
        complete_step(conn, project_id, "STYLE_SET")


def _run_style_sync(project_id: str, art_style: str, existing_book_uri: str | None) -> dict:
    client = _get_client()

    book_uri = existing_book_uri or client.files.upload(
        file=str(storage.book_path(project_id))
    ).uri

    book_interaction = client.interactions.create(
        model=TEXT_MODEL,
        input=[
            {
                "type": "text",
                "text": "Here's a book, to illustrate using Nano Banana. Don't say anything for now, instructions will follow.",
            },
            {"type": "document", "uri": book_uri},
        ],
    )

    if art_style.strip():
        style_interaction = client.interactions.create(
            model=TEXT_MODEL,
            input=f'The art style will be: "{art_style}". Keep that in mind when generating future prompts. Keep quiet for now, instructions will follow.',
            previous_interaction_id=book_interaction.id,
        )
        final_style = art_style.strip()
    else:
        style_interaction = client.interactions.create(
            model=TEXT_MODEL,
            input="Can you define an art style that would fit the story? Just give us the prompt for the art style that will be added to future prompts.",
            previous_interaction_id=book_interaction.id,
        )
        final_style = style_interaction.output_text

    return {
        "book_uri": book_uri,
        "text_chain_last_id": style_interaction.id,
        "art_style": final_style,
    }


# ── Characters step ────────────────────────────────────────────────────────────

MAX_CHARACTERS = 2


async def run_characters(project_id: str, text_chain_last_id: str) -> None:
    claim_step(project_id, "STYLE_SET")
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _run_characters_sync, project_id, text_chain_last_id
        )
    except Exception:
        with get_db() as conn:
            fail_step(conn, project_id)
        raise
    with get_db() as conn:
        for char in result["characters"][:MAX_CHARACTERS]:
            import uuid as _uuid
            conn.execute(
                "INSERT INTO characters (id,project_id,name,prompt) VALUES (?,?,?,?)",
                (_uuid.uuid4().hex, project_id, char["name"], char["prompt"]),
            )
        conn.execute(
            "UPDATE projects SET text_chain_last_id=? WHERE id=?",
            (result["text_chain_last_id"], project_id),
        )
        complete_step(conn, project_id, "CHARACTERS_GENERATED")


def _run_characters_sync(project_id: str, text_chain_last_id: str) -> dict:
    import json

    client = _get_client()
    from pydantic import BaseModel

    class Prompt(BaseModel):
        name: str
        prompt: str

    interaction = client.interactions.create(
        model=TEXT_MODEL,
        input="Can you describe the main characters (only the adults) and prepare a prompt describing them with as much details as possible (use the descriptions from the book) so Nano Banana can generate images of them? Each prompt should be at least 50 words.",
        previous_interaction_id=text_chain_last_id,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": {"type": "array", "items": Prompt.model_json_schema()},
        },
    )
    characters = json.loads(interaction.output_text)[:MAX_CHARACTERS]
    return {
        "characters": characters,
        "text_chain_last_id": interaction.id,
    }


# ── Portraits step ─────────────────────────────────────────────────────────────

async def run_portraits(
    project_id: str,
    art_style: str,
    project_title: str,
    characters: list[dict],
) -> None:
    claim_step(project_id, "CHARACTERS_GENERATED")
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _run_portraits_sync, project_id, art_style, project_title, characters
        )
    except Exception:
        with get_db() as conn:
            fail_step(conn, project_id)
        raise
    with get_db() as conn:
        for char_id, filename in result["portraits"]:
            conn.execute(
                "UPDATE characters SET portrait_path=? WHERE id=?",
                (filename, char_id),
            )
        conn.execute(
            "UPDATE projects SET image_chain_last_id=? WHERE id=?",
            (result["image_chain_last_id"], project_id),
        )
        complete_step(conn, project_id, "PORTRAITS_GENERATED")


def _run_portraits_sync(
    project_id: str,
    art_style: str,
    project_title: str,
    characters: list[dict],
) -> dict:
    client = _get_client()
    style_prompt = f'Follow this style: "{art_style}" '

    image_interaction = client.interactions.create(
        model=IMAGE_MODEL,
        input=(
            f"You are going to generate portrait images to illustrate {project_title}. "
            f"The style to follow is: {style_prompt} "
            f"Rules: {SYSTEM_INSTRUCTIONS}"
        ),
    )

    portraits = []
    for i, char in enumerate(characters[:MAX_CHARACTERS]):
        image_interaction = client.interactions.create(
            model=IMAGE_MODEL,
            input=f"Create an illustration for {char['name']} following this description: {char['prompt']}",
            previous_interaction_id=image_interaction.id,
        )
        for step in reversed(image_interaction.steps):
            if step.type == "model_output" and step.content:
                for content in reversed(step.content):
                    if content.type == "image":
                        ext = content.mime_type.split("/")[-1]
                        filename = f"portrait_{i}.{ext}"
                        storage.save_image(project_id, filename, content.data)
                        portraits.append((char["id"], filename))
                        break
                break

    return {
        "portraits": portraits,
        "image_chain_last_id": image_interaction.id,
    }
