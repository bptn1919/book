# Architecture — Book Illustration Studio

Produced after all architectural decisions were approved. Single authoritative reference for implementation.

---

## System Overview

A web application that turns a book's text into character portraits and a chapter illustration using the Gemini API. Five sequential, user-driven steps: **Style → Characters → Portraits → Chapters → Illustrations**. Each step requires an explicit user action; nothing runs automatically.

---

## Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Notebook is Python; FastAPI's ASGI model handles concurrent long-running Gemini calls without blocking |
| Database | SQLite via `sqlite3` stdlib | Transactional, no extra service, no ORM dep; WAL mode for concurrent reads |
| Gemini SDK | `google-genai >= 2.10.0` | Reference implementation; Interactions API verified from notebook |
| Frontend | React 18 + Vite + TypeScript | Type safety for five pipeline states and API contracts; Vite provides a lightweight frontend setup |
| Backend tests | pytest + httpx | Async-compatible HTTP client for FastAPI |
| Frontend tests | Vitest + @testing-library/react | Co-located with Vite config |

---

## Project Structure

```
project_book/
  backend/
    app/
      main.py          # FastAPI app, CORS, lifespan
      models.py        # Pydantic models + SQLite schema
      pipeline.py      # Gemini pipeline runner
      storage.py       # File I/O (images to disk)
      auth.py          # Session handling (cookie-based)
    tests/
      test_pipeline.py
      test_api.py
  frontend/
    src/
      api.ts           # Typed API client
      components/
      pages/
  start.sh
  test.sh
  .env.example
  CLAUDE.md
  AGENTS.md
  DECISIONS.md
  TESTING.md
  README.md
  docs/
    plan.md
    architecture.md    # this file
```

---

## Data Model (SQLite)

```sql
CREATE TABLE users (
  id         TEXT PRIMARY KEY,   -- uuid4
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE projects (
  id               TEXT PRIMARY KEY,
  user_id          TEXT NOT NULL REFERENCES users(id),
  title            TEXT NOT NULL,
  book_uri         TEXT,          -- Gemini File API URI, persisted after upload
  art_style        TEXT,
  status           TEXT NOT NULL DEFAULT 'CREATED',
  step_state       TEXT NOT NULL DEFAULT 'IDLE',
  step_started_at  TEXT,          -- ISO timestamp; NULL when IDLE
  text_chain_last_id  TEXT,       -- last interaction ID in the text chain
  image_chain_last_id TEXT,       -- last interaction ID in the image chain
  created_at       TEXT NOT NULL
);

CREATE TABLE characters (
  id            TEXT PRIMARY KEY,
  project_id    TEXT NOT NULL REFERENCES projects(id),
  name          TEXT NOT NULL,
  prompt        TEXT NOT NULL,
  portrait_path TEXT            -- relative path under backend/storage/
);

CREATE TABLE chapters (
  id                 TEXT PRIMARY KEY,
  project_id         TEXT NOT NULL REFERENCES projects(id),
  name               TEXT NOT NULL,
  prompt             TEXT NOT NULL,
  illustration_path  TEXT
);
```

**Status progression** (forward only — only advances on success):
```
CREATED → STYLE_SET → CHARACTERS_GENERATED → PORTRAITS_GENERATED → CHAPTERS_GENERATED → DONE
```

**step_state** (resettable on retry):
```
IDLE → RUNNING → IDLE (success) | FAILED (error)
```

When a step fails, `status` stays at the last successfully completed state and `step_state` becomes `FAILED`. Retry resets `step_state` to `RUNNING` without changing `status`. This is the reason for the two-field split — a single enum cannot represent "step N done, step N+1 failed" without combinatorial explosion.

---

## Duplicate Call Prevention (DECISION 4)

Every pipeline step does this before launching a Gemini call:

```python
cur.execute(
    "UPDATE projects SET step_state='RUNNING', step_started_at=? "
    "WHERE id=? AND step_state != 'RUNNING'",
    (now_iso(), project_id)
)
if cur.rowcount == 0:
    raise HTTPException(409, "Step already running")
conn.commit()
# Gemini call runs here — no lock held during the 10–30s API call
```

The database lock is held only for the UPDATE (milliseconds), not during the Gemini call. A losing request gets a 409; the frontend shows "step in progress."

---

## Stuck-Step Recovery

1. **Startup cleanup**: on server start, any `step_state = 'RUNNING'` is set to `FAILED`. Handles server crashes mid-step.

2. **3-minute threshold**: if `step_state = 'RUNNING'` and `now - step_started_at > 3 minutes`, the step is treated as stuck and the user is shown a Retry option. The threshold is intentionally longer than normal Gemini calls but bounded to avoid an indefinitely spinning UI. Three minutes is the configured default and can be adjusted once SDK retry behavior is verified in practice.

---

## Gemini Integration (DECISION 5)

### Book Upload

```python
book_file = client.files.upload(file="book.txt")
# persist book_file.uri → projects.book_uri
```

Uploaded once. URI stored in the database and reused across all text-chain interactions. If the persisted File API URI is no longer valid, the backend re-uploads the source file and updates `book_uri` before retrying.

### Text Chain

Model: `gemini-3.6-flash`

```
book_interaction            [File API URI → document input]
  └── style_interaction     [acknowledges art style; stored in projects.art_style]
        └── characters_interaction  [JSON: [{name, prompt}] → characters table]
              └── chapters_interaction   [JSON: [{name, prompt}] → chapters table]
```

Each step passes `previous_interaction_id` of the prior step. The returned interaction ID is persisted to `projects.text_chain_last_id`.

Structured output:
```python
response_format={
    "type": "text",
    "mime_type": "application/json",
    "schema": {"type": "array", "items": Prompt.model_json_schema()}
}
# Prompt = {name: str, prompt: str}
output = json.loads(interaction.output_text)
```

### Image Chain

Model: `gemini-3.1-flash-lite-image`

```
image_context_interaction     [art style + system instructions]
  └── portrait_1              [character[0]]
        └── portrait_2        [character[1]]
              └── chapter_bridge           [transition to illustration mode]
                    └── illustration_1     [chapter[0]]
```

Portrait reuse: the image chain is continued from the last portrait interaction. The model references its own history for character consistency.

Image extraction (verified from notebook — `interaction.output_image` has a TODO; use `steps` loop):

```python
for step in interaction.steps:
    if step.type == "model_output":
        for content in step.content:
            if content.type == "image":
                image_bytes = base64.b64decode(content.data)
                mime_type = content.mime_type
```

Images saved to `backend/storage/<project_id>/<filename>`. Paths stored in `characters.portrait_path` / `chapters.illustration_path`.

### Hard Caps (server-side)

```python
characters = characters[:2]   # max 2 adult characters
chapters   = chapters[:1]     # max 1 chapter
```

Applied before the portrait and illustration loops, regardless of what Gemini returned.

### SDK in Async Context

```python
result = await asyncio.get_event_loop().run_in_executor(None, sdk_call)
```

The `google-genai` SDK is synchronous; all SDK calls are dispatched to a thread pool executor.

---

## API Surface

All routes under `/api`.

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout

GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}

POST   /api/projects/{id}/style
POST   /api/projects/{id}/characters
POST   /api/projects/{id}/portraits
POST   /api/projects/{id}/chapters
POST   /api/projects/{id}/illustrations

GET    /api/projects/{id}/images/{filename}
```

Session is cookie-based. Name-based demo identity — users provide only a name, no passwords or OAuth. Login sets a session cookie; the backend validates it on subsequent requests. This is intentionally minimal for assessment scope.

---

## Frontend Structure

Five-step stepper UI matching `app-demo.html`.

```
pages/
  LoginPage.tsx
  ProjectListPage.tsx
  ProjectPage.tsx       # stepper + step content

components/
  Stepper.tsx
  CharacterCard.tsx
  ChapterCard.tsx
  PortraitGrid.tsx
  IllustrationView.tsx
  ErrorState.tsx        # stuck-step retry UI
```

Frontend polls `GET /api/projects/{id}` for status. No WebSocket or SSE.

---

## Security Constraints

- API key in `.env` only — never exposed to frontend, never committed
- All Gemini calls server-side only
- Generated images served via authenticated `/api/projects/{id}/images/{filename}`
- Local filesystem only — no S3, no CDN, no blob storage

---

## Out of Scope

- Veo, Lyria, TTS, media mixing, audiobook
- OAuth, password hashing
- Docker-compose
- Real-time push (SSE / WebSocket)
- Multi-region storage or CDN
