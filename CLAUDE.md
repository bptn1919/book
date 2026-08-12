# CLAUDE.md — Project Context

## What This Is

Book Illustration Studio — a Gradion take-home assessment.

A web app that turns a book's text into character portraits and a chapter illustration using the Gemini API. Five sequential, user-driven steps: Style → Characters → Portraits → Chapters → Illustrations.

## Stack (Decided — DECISION 1)

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Gemini SDK | `google-genai >= 2.10.0` (Python) |
| Frontend | React 18 + Vite + TypeScript |
| Backend tests | pytest + httpx |
| Frontend tests | Vitest + @testing-library/react |

## Hard Constraints (Non-Negotiable)

- Maximum 2 adult characters — enforced SERVER-SIDE
- Maximum 1 chapter — enforced SERVER-SIDE
- Book content uploaded to Gemini File API ONCE; referenced by URI across all steps via interaction chaining
- No duplicate Gemini calls — server-side guard (not just frontend button disable)
- Never auto-retry Gemini calls — user-triggered retries only
- Steps run in order; each requires explicit user action
- Completed results must survive refresh, logout, and server restart
- No S3, no blob storage, no CDN — local filesystem only
- Never commit API key — `.env.example` only

## Gemini Pipeline (Verified from Notebook)

Two independent interaction chains:

**Text chain** (GEMINI_MODEL_ID = `gemini-3.6-flash`):
```
book_interaction [File API upload → book.uri]
  └── style_interaction [generates/acknowledges art style]
        └── characters_prompts_interaction [JSON: [{name, prompt}]]
              └── chapters_prompts_interaction [JSON: [{name, prompt}]]
```

**Image chain** (IMAGE_MODEL_ID = `gemini-3.1-flash-lite-image`):
```
image_context_interaction [style + system instructions]
  └── portrait_interaction_1 [character[0]]
        └── portrait_interaction_2 [character[1]]
              └── chapter_bridge_interaction [transition message]
                    └── illustration_interaction_1 [chapter[0]]
```

Portrait reuse for illustrations: the image chain is continued from the last portrait interaction. The model references its own history for character consistency.

## Pipeline State (to be finalized in DECISION 3)

Status values: `CREATED → STYLE_SET → CHARACTERS_GENERATED → PORTRAITS_GENERATED → CHAPTERS_GENERATED → DONE`

Each project also has a `step_state` field (separate from `status`): `IDLE | RUNNING | FAILED`
And a `step_started_at` timestamp for stuck-step detection.

## Out of Scope

- Veo (video), Lyria (music), TTS, media mixing, audiobook
- OAuth, passwords
- S3/CDN
- Real-time push (SSE/WebSocket) — polling is fine
- Docker-compose (not needed for disk-based storage)

## Development Approach

- Incremental: one architectural decision, then one implementation task at a time
- Each task has defined acceptance criteria before implementation starts
- Tests are run after each task; results reported as-is, not summarized
- No unrelated refactoring or speculative abstractions during a task
- Git commits are small and meaningful, made after each verified task

## Key Files (to be created)

```
backend/
  app/
    main.py          # FastAPI app, routes
    models.py        # Pydantic data models
    pipeline.py      # Gemini pipeline logic
    storage.py       # Filesystem persistence
    auth.py          # Session handling
  tests/
frontend/
  src/
    components/
    pages/
    api.ts           # API client
start.sh
test.sh
.env.example
DECISIONS.md
TESTING.md
README.md
```
