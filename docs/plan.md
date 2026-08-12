# Project Plan — Book Illustration Studio

## Status

Phase 0 complete. DECISION 1 (Stack) complete. DECISION 2 pending.

## Architectural Decisions

| #   | Decision                          | Status                                |
| --- | --------------------------------- | ------------------------------------- |
| 1   | Stack                             | ✅ Python FastAPI + React TypeScript  |
| 2   | Storage                           | ✅ SQLite (raw sqlite3, no ORM)        |
| 3   | Pipeline State Model              | ✅ status + step_state, Gemini IDs persisted |
| 4   | Duplicate Execution / Concurrency | ✅ SQLite transaction atomic check-and-set |
| 5   | Gemini Integration                | ✅ SDK + chain + steps loop + TTL fallback |
| 6   | Testing Strategy                  | — (covered in TESTING.md)            |

## Verified Pipeline Mechanics (from notebook)

### Book upload

- `client.files.upload(file="book.txt")` → returns `book.uri`
- URI used in first interaction as `{"type": "document", "uri": book.uri}`
- Book text is NOT re-sent on subsequent steps

### Context chaining

- Each interaction returns an `.id`
- Subsequent interactions pass `previous_interaction_id=<prior_id>`
- Two separate chains: text chain and image chain

### Structured output

- `response_format={"type": "text", "mime_type": "application/json", "schema": {"type": "array", "items": Prompt.model_json_schema()}}`
- `Prompt` schema: `{name: str, prompt: str}`
- Output parsed via `json.loads(interaction.output_text)`

### Image generation

- Same `client.interactions.create` API, different model
- Images extracted from `interaction.steps` — find `step.type == "model_output"`, then `content.type == "image"`, then `content.data` (base64) + `content.mime_type`
- Portrait reuse for illustrations: continue image chain from last portrait interaction, prompt model to "refer to previous illustrations"

### Caps

- Characters capped at `characters[:max_character_images]` — we set max to 2
- Chapters capped at `chapters[:max_chapter_images]` — we set max to 1
- Enforced server-side in the pipeline runner

## Key Risks

1. **Duplicate execution**: server-side locking required (DECISION 4)
2. **Stuck steps**: stale threshold must be > 30s (real Gemini call duration) + SDK retry time (up to 5 × 60s = 5 min in worst case)
3. **Book File API TTL**: unknown how long uploaded files persist — need to verify
4. **Image model rate limits**: verify the selected free-tier image model before integration

## Unknowns Still Open

- REST endpoint shape for Interactions API (needed if SDK gaps found)
- File API TTL (affects whether we need to re-upload the book if it expires)
- Free-tier limits for the selected image model

## Implementation Order (planned, subject to approval)

After all decisions are approved:

1. Backend scaffolding (FastAPI, routes, models)
2. Identity flow (sign in / sign up / session)
3. Project persistence (create, list, fetch)
4. Pipeline state tracking (step transitions, stuck-step detection)
5. Duplicate call prevention (server-side lock)
6. Gemini integration — style step
7. Gemini integration — characters step
8. Gemini integration — portraits step (with per-image progress)
9. Gemini integration — chapters step
10. Gemini integration — illustrations step
11. Frontend scaffolding and design system
12. Identity screen
13. Project list screen
14. New project screen
15. Project detail screen (stepper, cards, action button)
16. Error and stuck-step states
17. Integration tests (mocked Gemini)
18. Final audit and polish

## Assessment Deliverables Checklist

- [ ] README.md (one-command start, one-command test, prerequisites, env vars, architecture)
- [ ] DECISIONS.md (4–6 decisions, ≥3 AI overrides, one-more-day answer)
- [ ] TESTING.md (strategy + real test report)
- [ ] CLAUDE.md (this file's companion)
- [ ] AGENTS.md
- [ ] docs/plan.md (this file)
- [ ] docs/architecture.md (after DECISION 6)
- [ ] start.sh
- [ ] test.sh
- [ ] .env.example
- [ ] Git history (small, meaningful commits)
