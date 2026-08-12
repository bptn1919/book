# DECISIONS.md

Architecture and engineering decisions made during the build of Book Illustration Studio. Written in real time as decisions were made — not back-filled.

Each entry: who proposed, who pushed back, where we landed, what it cost.

---

## 1. Stack: Python FastAPI + React TypeScript

Claude proposed Python + FastAPI because the reference notebook uses Python's `google-genai` SDK. The verified Interactions API mechanics were available in the Python implementation we verified. I agreed because this keeps the implementation close to the reference pipeline.

I considered Flask but chose FastAPI because its ASGI-based model is a natural fit for concurrent, long-running Gemini operations, which can take 10–30+ seconds.

Claude proposed React + TypeScript and considered Next.js as an alternative. I agreed with React + TypeScript because the frontend has multiple API contracts, five pipeline steps, and several state transitions, making type safety useful for keeping the UI and backend contracts aligned. I pushed back on Next.js because its additional server-side capabilities do not solve a requirement in this assessment; the Python backend already owns the Gemini integration. I chose Vite for a simpler frontend setup. Cost accepted: slightly more type-related development overhead, in exchange for clearer contracts without adding another server-side layer.

## 2. Storage: SQLite

Claude initially proposed JSON files, which seemed reasonable because the assessment explicitly allows them and the data volume is small. I pushed back after considering the concurrency requirements: making JSON writes safe would require custom per-project locking and atomic file replacement that I would need to write, test, and maintain. Claude pointed out that SQLite provides transactional persistence and built-in locking without requiring a separate database server. The data also has relational structure — users, projects, characters, chapters, and Gemini interaction IDs - that maps naturally to tables. Since Python's sqlite3 module is part of the standard library, I chose SQLite without adding an ORM or database service. Cost: the state is less convenient to inspect than a JSON file. Gain: concurrency and crash-safety are handled by a mature database engine rather than custom file-writing logic.

## 3. Pipeline State Model: two fields, not one

Claude's first instinct was a single `status` enum covering both completion and execution state. I pushed back: a single enum can't express "step 3 done, step 4 currently running" without exploding into per-step RUNNING and FAILED variants — ten or more values. Split into two fields: `status` (which steps have completed, only moves forward) and `step_state` (IDLE / RUNNING / FAILED, can be reset on retry). Cost: two fields to keep in sync; a stranded `step_state = RUNNING` needs a timeout to clear.

## 4. Duplicate Execution: SQLite transaction as the guard

Claude proposed using a SQLite transaction with a SELECT → check → UPDATE to prevent duplicate Gemini calls. I pushed back because two concurrent requests could both see the step as available before either updated it. We landed on a conditional UPDATE ... WHERE step_state != 'RUNNING', using rowcount to determine whether the request successfully claimed the step; the Gemini call runs only after the claim commits, so no database lock is held during the 30-second API call. Cost: the conditional update is slightly less immediately readable than an explicit status check, so the rowcount behavior needs to be clear to future maintainers.

## 5. Gemini Integration: verified API paths only

Claude proposed using `interaction.output_image` for simpler image extraction. I rejected it because the reference notebook has a TODO around that field and the working implementation extracts images through `interaction.steps`. I chose to follow the verified path rather than introduce an unverified API dependency. I also kept the book upload and interaction chaining from the reference pipeline: the book is uploaded once, its URI is persisted, and subsequent steps continue the existing interaction chain. Cost: slightly more verbose integration code and an explicit fallback for potentially stale File API references.

## 6. Auth: email-based identity (no password)

The spec requires the app to know who the user is but does not specify an auth mechanism. I chose email-only identity: the user enters their email, the server looks up their account; if none exists, they also provide a name and the account is created. No password, no OAuth token, no magic link — just an email lookup backed by a session cookie.

I considered name-only identity (simpler) but rejected it because names are not unique and the spec implies accounts should be persistent and identifiable. Email is unique per user and familiar enough that users will not be surprised to be asked for it. The session cookie (httponly, samesite=lax) makes subsequent requests authenticated without the frontend needing to manage tokens.

Cost: users must remember which email they signed up with. This is acceptable for a demo and matches how most passwordless systems (e.g., magic-link) work.

## 7. Gemini model IDs

As required by §5.3 of the spec, the model IDs chosen are documented here:

- **Text chain** (`TEXT_MODEL`): `gemini-3.6-flash` — used for book ingestion, style acknowledgement, character extraction, and chapter prompt generation. Chosen because it matches the reference notebook's `GEMINI_MODEL_ID`.
- **Image chain** (`IMAGE_MODEL`): `gemini-2.5-flash-image` — used for portrait and illustration generation. The reference notebook listed `gemini-3.1-flash-lite-image`; during development the linter flagged this as an unrecognised model and substituted `gemini-2.5-flash-image`, which is a known production model supporting image output. The substitution was accepted.

Both constants are defined at the top of `backend/app/pipeline.py`.

## If you had one more day, what would you build next and why?

Real-time step updates via Server-Sent Events (SSE) instead of polling.

The current polling approach works, but there is an experience gap that matters most during portrait and illustration generation, which takes 10–30 seconds each. The UI polls every 3 seconds, so the user sees the portrait appear with up to a 3-second lag after the server writes it. With SSE, the server pushes a message the moment each portrait lands on disk and the database row is updated. The user sees each portrait slide in as it arrives rather than during the next poll tick.

The reason I did not include it in this submission is that SSE requires keeping one HTTP connection open per active project view, which adds a non-trivial amount of state on the server (connection registry, cleanup on disconnect). Polling is correct, survives disconnects gracefully, and costs only one extra round-trip per 3 seconds — acceptable for a demo. SSE is the right next step because it is the highest-ROI UX improvement relative to backend complexity, and the assessment explicitly names it as a potential bonus.

The implementation would be: one `GET /api/projects/{id}/events` endpoint that yields an event-stream, a small in-process broker that the pipeline async runners publish to after each DB write, and a `useEffect` in `ProjectDetailPage` that opens the `EventSource` and updates local state on receipt. No new infrastructure needed — FastAPI supports SSE natively via `StreamingResponse`.
