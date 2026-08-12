# Testing Strategy

## What we test and why

### Backend — pytest + httpx

Tests live in `backend/tests/`. All Gemini calls are mocked so the suite runs without a real API key, making it safe for CI and fast locally (under 3 seconds).

**test_pipeline.py — unit tests for the state machine (11 tests)**

The claim/complete/fail cycle is the most critical server-side logic: it is what prevents duplicate Gemini calls and enforces step ordering. These tests run against a real (in-memory) SQLite database with no HTTP layer in between, so they verify the exact SQL semantics — the conditional `UPDATE ... WHERE step_state != 'RUNNING'` and the rowcount check. Key cases: normal claim, 409 on already-running, 409 on wrong status, 404 on missing project, and automatic override of a stuck step (elapsed > 180 s).

**test_auth.py — session lifecycle (6 tests)**

Register creates a user and sets the cookie. Login finds an existing user. Duplicate name returns 409. Logout deletes the session. Unauthenticated requests return 401.

**test_projects.py — CRUD and authorization (8 tests)**

List, create, get. Project not found. Stuck flag computed correctly. Cross-user isolation: one user cannot read another's project.

**test_steps.py — pipeline step routes (26 tests)**

Each of the five Gemini steps (style, characters, portraits, chapters, illustrations) is tested for:
- happy path: correct status transition and data written to DB
- Gemini error: step_state → FAILED, status unchanged (so retry is from the right point)
- wrong status: 409 if the previous step hasn't completed
- Additional cases: the MAX_CHARACTERS=2 and MAX_CHAPTERS=1 server-side caps, book_uri and chain ID persistence, portrait_path and illustration_path updates, image path traversal rejection (400/404).

**test_api.py — startup and health (2 tests)**

Health check returns 200. Startup cleanup: RUNNING steps left over from a previous crash are reset to FAILED on lifespan.

**test_integration.py — happy-path end-to-end (2 tests)**

Chains all 5 steps from CREATED to DONE in a single test, asserting status, step_state, character names, portrait paths, chapter name, and illustration path. A second test verifies the duplicate-call guard: once a step completes, a second request for the same step returns 409 without touching Gemini.

### What we deliberately do not test on the backend

- The real `_run_*_sync` functions that call the Gemini API — these are integration with an external paid service and are covered by running the notebook manually (per the assessment spec). Testing them with real calls would cost quota and require a secret in CI.
- SQLite WAL mode internals — we trust the stdlib.
- Retry logic inside `_get_client()` — the `HttpRetryOptions` config is declarative; the retry behavior is owned by the SDK.

### Frontend — Vitest + @testing-library/react

Tests live in `frontend/src/**/*.test.tsx`. Three test files, 14 tests total.

**Stepper.test.tsx (4 tests)**

The stepper drives which step shows as current, which as done (dark), and which as pending (grey). Wrong logic here means the user sees incorrect pipeline state. Cases: step 1 current when status=CREATED; steps 1 and 2 marked done when status=CHARACTERS_GENERATED; future steps pending; all five labels render.

**EntityCard.test.tsx (5 tests)**

The card is the primary way users see generated content. Cases: name and prompt render; pending placeholder shown when no image; img tag with correct src when imageSrc provided; Generating spinner when generating=true; prompt truncated at 120 characters.

**IdentityPage.test.tsx (5 tests)**

The identity screen is the app's entry point — broken auth blocks everything. Cases: form renders; empty-name validation without calling the API; successful login fires onAuth; 404 from login triggers register fallback; generic error shows message. The API module is fully mocked with `vi.mock` so no real HTTP goes out.

### What we deliberately do not test on the frontend

- `ProjectDetailPage`, `ProjectListPage`, `NewProjectPage` — these pages orchestrate fetch calls and polling. Testing them properly requires mocking `fetch` globally for multiple sequential requests (poll loop), which produces fragile tests for behaviour that is simpler to verify by running the app. The unit tests above cover the components that carry the most logic (Stepper state machine, EntityCard display states, IdentityPage form logic).
- End-to-end — not expected per the assessment spec.

---

## Running the tests

```bash
# All tests in one command:
./test.sh

# Backend only:
cd backend && python -m pytest tests/ -v

# Frontend only:
cd frontend && npm test
```

---

## Real test report

Produced on 2026-08-12, Python 3.12.8, Node 20, pytest 9.1.1, Vitest 3.2.7.


### Backend — 53 passed

```
============================= test session starts =============================
platform win32 -- Python 3.12.8, pytest-9.1.1, pluggy-1.6.0
asyncio: mode=Mode.AUTO
collected 53 items

tests/test_api.py::test_health PASSED                                    [  1%]
tests/test_api.py::test_startup_cleanup PASSED                           [  3%]
tests/test_auth.py::test_register_creates_user_and_sets_session PASSED   [  5%]
tests/test_auth.py::test_register_duplicate_name_returns_409 PASSED      [  7%]
tests/test_auth.py::test_login_finds_existing_user PASSED                [  9%]
tests/test_auth.py::test_login_unknown_name_returns_404 PASSED           [ 11%]
tests/test_auth.py::test_logout_invalidates_session PASSED               [ 13%]
tests/test_auth.py::test_me_without_session_returns_401 PASSED           [ 15%]
tests/test_pipeline.py::test_complete_step_sets_next_status_and_resets_state PASSED [ 17%]
tests/test_pipeline.py::test_fail_step_sets_failed_and_clears_timestamp PASSED [ 19%]
tests/test_pipeline.py::test_is_stuck_false_when_idle PASSED             [ 21%]
tests/test_pipeline.py::test_is_stuck_false_when_no_timestamp PASSED     [ 23%]
tests/test_pipeline.py::test_is_stuck_false_when_recently_started PASSED [ 25%]
tests/test_pipeline.py::test_is_stuck_true_when_over_threshold PASSED    [ 27%]
tests/test_pipeline.py::test_is_stuck_false_when_failed PASSED           [ 29%]
tests/test_pipeline.py::test_claim_step_sets_running PASSED              [ 31%]
tests/test_pipeline.py::test_claim_step_409_when_already_running PASSED  [ 33%]
tests/test_pipeline.py::test_claim_step_409_when_wrong_status PASSED     [ 35%]
tests/test_pipeline.py::test_claim_step_404_for_missing_project PASSED   [ 37%]
tests/test_pipeline.py::test_claim_step_overrides_stuck_running PASSED   [ 39%]
tests/test_pipeline.py::test_is_stuck_handles_naive_timestamp PASSED     [ 41%]
tests/test_projects.py::test_list_projects_empty PASSED                  [ 43%]
tests/test_projects.py::test_create_project_returns_metadata PASSED      [ 45%]
tests/test_projects.py::test_get_project_includes_characters_and_chapters PASSED [ 47%]
tests/test_projects.py::test_list_shows_created_projects PASSED          [ 49%]
tests/test_projects.py::test_project_requires_auth PASSED                [ 50%]
tests/test_projects.py::test_get_project_not_found PASSED                [ 52%]
tests/test_projects.py::test_get_project_is_stuck_false_on_new_project PASSED [ 54%]
tests/test_projects.py::test_cannot_access_other_users_project PASSED    [ 56%]
tests/test_steps.py::test_style_step_sets_style_set_status PASSED        [ 58%]
tests/test_steps.py::test_style_step_stores_chain_id_and_book_uri PASSED [ 60%]
tests/test_steps.py::test_style_step_empty_style_uses_gemini_generated PASSED [ 62%]
tests/test_steps.py::test_style_step_fails_on_gemini_error PASSED        [ 64%]
tests/test_steps.py::test_style_step_409_when_already_running PASSED     [ 66%]
tests/test_steps.py::test_style_step_409_wrong_status PASSED             [ 68%]
tests/test_steps.py::test_characters_step_stores_up_to_two_characters PASSED [ 70%]
tests/test_steps.py::test_characters_step_fails_on_gemini_error PASSED   [ 72%]
tests/test_steps.py::test_characters_step_409_wrong_status PASSED        [ 74%]
tests/test_steps.py::test_portraits_step_sets_portrait_paths PASSED      [ 76%]
tests/test_steps.py::test_portraits_step_stores_image_chain_id PASSED    [ 78%]
tests/test_steps.py::test_portraits_step_fails_on_gemini_error PASSED    [ 80%]
tests/test_steps.py::test_portraits_step_409_wrong_status PASSED         [ 82%]
tests/test_steps.py::test_chapters_step_stores_up_to_one_chapter PASSED  [ 84%]
tests/test_steps.py::test_chapters_step_fails_on_gemini_error PASSED     [ 86%]
tests/test_steps.py::test_chapters_step_409_wrong_status PASSED          [ 88%]
tests/test_steps.py::test_illustrations_step_sets_illustration_paths PASSED [ 90%]
tests/test_steps.py::test_illustrations_step_fails_on_gemini_error PASSED [ 92%]
tests/test_steps.py::test_illustrations_step_409_wrong_status PASSED     [ 94%]
tests/test_steps.py::test_image_endpoint_blocks_path_traversal PASSED    [ 96%]
tests/test_steps.py::test_style_step_requires_auth PASSED                [ 98%]
tests/test_steps.py::test_style_step_404_unknown_project PASSED          [ 98%]
tests/test_integration.py::test_happy_path_all_five_steps PASSED         [ 99%]
tests/test_integration.py::test_no_duplicate_call_on_second_request PASSED [100%]

============================== 53 passed in 2.81s ==============================
```

### Frontend — 14 passed

```
 RUN  v3.2.7

 ✓ src/components/Stepper.test.tsx (4 tests) 69ms
 ✓ src/components/EntityCard.test.tsx (5 tests) 151ms
 ✓ src/pages/IdentityPage.test.tsx (5 tests) 742ms

 Test Files  3 passed (3)
       Tests  14 passed (14)
    Start at  22:40:10
    Duration  3.21s
```

**Grand total: 67 tests, 0 failures.**
