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

## If you had one more day, what would you build next and why?

_To be answered after core implementation is complete._
