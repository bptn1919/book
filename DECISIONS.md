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

## If you had one more day, what would you build next and why?

_To be answered after core implementation is complete._
