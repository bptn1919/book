# Book Illustration Studio

A web app that turns a book's text into character portraits and a chapter illustration using the Gemini API. Built as a Gradion intern assessment.

Five sequential, user-driven steps: **Style → Characters → Portraits → Chapters → Illustrations.**

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- A Gemini API key (free tier works; note image-model rate limits)

---

## One-command start

```bash
cp .env.example .env          # add your GEMINI_API_KEY
./start.sh
```

Opens:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

The script loads `.env`, starts the FastAPI backend with `--reload`, and starts the Vite dev server. `Ctrl+C` stops both.

---

## One-command test

```bash
./test.sh
```

Runs 51 backend tests (pytest) and 14 frontend tests (Vitest). No Gemini API key needed — all Gemini calls are mocked.

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Your Gemini API key |
| `APP_HOST` | No | `0.0.0.0` | Backend bind host |
| `APP_PORT` | No | `8000` | Backend port |
| `DB_PATH` | No | `data/app.db` | SQLite database path |
| `STORAGE_DIR` | No | `storage` | Directory for book files and images |

---

## Architecture

```
frontend/          React 18 + Vite + TypeScript
  src/
    api.ts         Typed fetch client for all backend endpoints
    pages/         IdentityPage, ProjectListPage, NewProjectPage, ProjectDetailPage
    components/    Nav, Stepper, StepPanel, EntityCard

backend/
  app/
    main.py        FastAPI app, lifespan (init_db + crash cleanup)
    models.py      SQLite schema, init_db(), get_db() context manager
    auth.py        Cookie-based name-only session auth
    pipeline.py    Gemini integration: claim_step, run_*, _run_*_sync
    projects.py    REST router: CRUD + pipeline step routes + image serving
    storage.py     Local filesystem: book files, base64-decoded images
  tests/           51 pytest tests, all Gemini calls mocked

data/              SQLite database (created on first start)
storage/           Book text and generated images, per project
```

**Gemini pipelines**

Two interaction chains that the server maintains across steps:

- *Text chain*: `book upload → style → characters → chapters` (model: `gemini-3.6-flash`)
- *Image chain*: `style context → portrait 1 → portrait 2 → bridge → illustration` (model: `gemini-3.1-flash-lite-image`)

The book is uploaded to the Gemini File API once and referenced by URI in every subsequent text-chain interaction. The image chain is continued from the last portrait interaction so the model has character consistency context when generating chapter illustrations.

**Duplicate-call prevention**

Every pipeline step is claimed with a conditional `UPDATE ... WHERE step_state != 'RUNNING'`. The Gemini call starts only after the claim commits. A concurrent request that races for the same step will see rowcount = 0 and return 409 without touching Gemini. Steps stranded in RUNNING for more than 3 minutes are automatically overridden by the next user action.

**Persistence**

All results (Gemini interaction IDs, art style, character prompts, image filenames) are written to SQLite before the HTTP response returns. A refresh, logout, or server restart re-reads the same state from the database.

---

## No Docker needed

Storage is local filesystem only. No external services. `./start.sh` is the only command required to bring up the full stack.
