# Phase A Gap Closeout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining Phase A gaps so the novel system can move from a CLI-only validation loop to a minimal HTTP-usable workflow with explicit API entry points, regression checks, and a clean closeout path.

**Architecture:** Keep the current `Story State Core + 4-agent + local rewrite` implementation as-is, and add the thinnest possible outer layer around it. First expose the existing repository and agent flows through FastAPI routes, then add a small regression harness for confidence, then verify the HTTP path end-to-end. A Vue workspace shell can be added later as an optional consumer once the closeout is complete. Do not pull retrieval/DSL/model-routing into this pass beyond what is required to avoid blocking the closeout.

**Tech Stack:** FastAPI, SQLModel, pytest, PyYAML, optional Vue 3/Vite/Vitest shell

**Execution Notes:**
- The current repo already imports correctly with Python namespace packages. Do not add extra `services/api/__init__.py` or `services/api/app/__init__.py` files unless a real import failure appears during execution.
- Before Task 1, run `python -c "import fastapi, sqlmodel"` inside the project root. If it fails, sync the environment with `pip install -e .` before writing route tests.
- Route tests for `main_flow` and `local_rewrite` must enable the built-in mock path from `packages/agents/src/base.py`; API tests must never hit live Ollama / Anthropic endpoints.

---

### Task 1: Expose Project and Chapter State APIs

**Files:**
- Create: `services/api/app/main.py`
- Create: `services/api/app/routers/__init__.py`
- Create: `services/api/app/routers/projects.py`
- Create: `services/api/app/routers/chapters.py`
- Create: `tests/api/test_chapter_state_routes.py`
- Modify: `tests/conftest.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_patch_chapter_state_updates_chapter_status(client):
    response = client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "reviewing", "version": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chapter_id"] == "ch-1"
    assert body["state"] == "reviewing"
    assert body["version"] == 1


def test_patch_chapter_state_rejects_stale_version(client):
    client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "reviewing", "version": 0},
    )
    response = client.patch(
        "/projects/proj-1/chapters/ch-1/state",
        json={"state": "committed", "version": 0},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "version_conflict"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_chapter_state_routes.py -v`
Expected: FAIL because the FastAPI app, client fixture, and routes do not exist.

**Step 3: Write minimal implementation**

```python
# services/api/app/main.py
from fastapi import FastAPI

from services.api.app.routers import chapters, projects


def create_app() -> FastAPI:
    app = FastAPI(title="Novel Gen API")
    app.include_router(projects.router)
    app.include_router(chapters.router)
    return app


app = create_app()
```

- Add a `client` fixture in `tests/conftest.py` that creates a `TestClient(create_app())` and injects the temp-db-backed session.
- Add `GET /projects/{project_id}` to bootstrap/read a project.
- Add `GET /projects/{project_id}/chapters/{chapter_id}` to read chapter state.
- Add `PATCH /projects/{project_id}/chapters/{chapter_id}/state` to update chapter state with explicit version compare.
- Reuse `StoryStateRepository.update_chapter_state()` instead of inventing new persistence behavior.
- Return `409` on stale writes instead of silently overwriting state.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_chapter_state_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/main.py services/api/app/routers tests/api/test_chapter_state_routes.py tests/conftest.py
git commit -m "feat: expose project and chapter state routes"
```

### Task 2: Expose Main Flow and Local Rewrite APIs

**Files:**
- Create: `services/api/app/routers/agent_runs.py`
- Create: `services/api/app/routers/local_rewrites.py`
- Create: `tests/api/conftest.py`
- Create: `tests/api/test_agent_run_routes.py`
- Modify: `services/api/app/main.py`

**Step 1: Write the failing test**

```python
def test_agent_run_route_returns_plan_draft_review_and_preview(client, fake_story_state):
    response = client.post(
        "/agent-runs/main-flow",
        json={
            "story_state": fake_story_state,
            "chapter_goal": "生成第1章：主角进入宗门",
            "chapter_id": "ch-1",
            "chapter_num": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["beats"]
    assert body["draft"]["draft_text"]
    assert body["review"]["actionable_suggestions"] is not None
    assert body["commit_preview"]["state_diff"] is not None


def test_local_rewrite_route_returns_diff_lines(client, fake_story_state):
    response = client.post(
        "/local-rewrites",
        json={
            "selected_text": "师父看了他一眼，没有说话。",
            "context_before": "夜雨刚停，山门仍冷。",
            "context_after": "李明低头，不敢再问。",
            "story_state": fake_story_state,
            "rewrite_instructions": "加强压抑感",
            "chapter_id": "ch-1",
        },
    )
    assert response.status_code == 200
    assert "diff_lines" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_agent_run_routes.py -v`
Expected: FAIL because the agent-run and local-rewrite routes do not exist.

**Step 3: Write minimal implementation**

```python
# services/api/app/routers/agent_runs.py
from fastapi import APIRouter

from packages.agents.src.main_flow import run_main_flow

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.post("/main-flow")
def create_main_flow_run(payload: dict) -> dict:
    return run_main_flow(
        story_state=payload["story_state"],
        chapter_goal=payload["chapter_goal"],
        chapter_id=payload.get("chapter_id"),
        chapter_num=payload.get("chapter_num"),
    )
```

- Add `POST /agent-runs/main-flow` as a thin HTTP wrapper around `run_main_flow()`.
- Add `POST /local-rewrites` as a thin HTTP wrapper around `run_local_rewrite()`.
- Keep request/response payloads plain and explicit for now; do not introduce a service layer just to satisfy layering.
- Add `tests/api/conftest.py` with an `autouse=True` fixture that calls `set_mock_responses(MOCK_RESPONSES)` before each API test and `reset_mock()` after it.
- Scope the mock to `tests/api/` only; do not move the mock back to the root `tests/conftest.py`.
- Reuse the current mockable agent runtime so route tests stay local and deterministic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_agent_run_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/main.py services/api/app/routers/agent_runs.py services/api/app/routers/local_rewrites.py tests/api/conftest.py tests/api/test_agent_run_routes.py
git commit -m "feat: expose agent flow and local rewrite routes"
```

### Task 3: Add the Minimum Regression Harness

**Files:**
- Modify: `pyproject.toml`
- Create: `evals/cases/minimum_set.yaml`
- Create: `evals/run_minimum_regression.py`
- Create: `evals/scorers/story_constraints.py`
- Create: `tests/evals/test_minimum_regression.py`

**Step 1: Write the failing test**

```python
from evals.run_minimum_regression import load_suite


def test_minimum_regression_suite_contains_required_checks():
    suite = load_suite("evals/cases/minimum_set.yaml")
    assert len(suite["cases"]) >= 3
    assert "hook_presence" in suite["cases"][0]["checks"]
    assert "min_word_count" in suite["cases"][0]["checks"]


def test_story_constraint_scorer_flags_short_draft():
    from evals.scorers.story_constraints import score_story_constraints

    result = score_story_constraints(
        draft_text="太短了。",
        checks={"min_word_count": 100, "hook_presence": True},
    )
    assert result["passed"] is False
    assert "min_word_count" in result["failures"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/evals/test_minimum_regression.py -v`
Expected: FAIL because the eval suite and scorer files do not exist.

**Step 3: Write minimal implementation**

```python
# evals/scorers/story_constraints.py
def score_story_constraints(draft_text: str, checks: dict) -> dict:
    failures = []
    if len(draft_text) < checks.get("min_word_count", 0):
        failures.append("min_word_count")
    if checks.get("hook_presence") and "？" not in draft_text and "！" not in draft_text:
        failures.append("hook_presence")
    return {"passed": not failures, "failures": failures}
```

- Add `pyyaml>=6.0.2` to `pyproject.toml` so YAML suites load cleanly.
- Create a 3-case minimum suite covering a straight chapter generation case, a hook-strength case, and a local rewrite case.
- Implement `load_suite()` plus a tiny local runner in `evals/run_minimum_regression.py`.
- Keep scoring intentionally narrow: word count, obvious hook presence, and simple forbidden-pattern checks.
- Do not start genre-specific anti-AI-tone calibration in this pass.

**Step 4: Run test to verify it passes**

Run: `pytest tests/evals/test_minimum_regression.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml evals tests/evals/test_minimum_regression.py
git commit -m "feat: add minimum regression harness"
```

### Task 4 (Optional): Add the Workspace Shell After Phase A Closeout

**Why this is optional:**
- The current Phase A acceptance criteria require a stable 4-agent loop, local rewrite, writeback to `Story State Core`, and a minimum regression harness.
- A prop-driven Vue shell that does not yet call the real APIs is useful as a future consumer, but it is not a blocker for this week’s closeout.
- Only execute this task if the required closeout tasks (1-3 and 5) are already complete and there is still time.

**Files:**
- Modify: `apps/web/package.json`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/views/ChapterWorkspaceView.vue`
- Create: `apps/web/src/components/ChapterStateBadge.vue`
- Create: `apps/web/src/components/ReviewPanel.vue`
- Create: `apps/web/src/components/CommitPreviewPanel.vue`
- Create: `apps/web/src/views/__tests__/ChapterWorkspaceView.test.ts`

**Step 1: Write the failing test**

```ts
import { render, screen } from "@testing-library/vue";
import ChapterWorkspaceView from "../ChapterWorkspaceView.vue";

test("renders chapter state, review panel, and commit preview", async () => {
  render(ChapterWorkspaceView, {
    props: {
      chapterState: { chapter_id: "ch-1", state: "reviewing", version: 1 },
      review: { actionable_suggestions: [{ type: "hook", message: "加强章末钩子" }] },
      commitPreview: { state_diff: { add: [] } },
    },
  });

  expect(screen.getByText("Current chapter state")).toBeInTheDocument();
  expect(screen.getByText("Review suggestions")).toBeInTheDocument();
  expect(screen.getByText("Commit preview")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- --run`
Expected: FAIL because the workspace view, components, and testing dependencies do not exist.

**Step 3: Write minimal implementation**

```ts
// apps/web/src/main.ts
import { createApp } from "vue";
import App from "./App.vue";

createApp(App).mount("#app");
```

- Add the minimum frontend testing dependencies needed for Vue component tests: `@testing-library/vue`, `@testing-library/jest-dom`, and `jsdom`.
- Create a single `ChapterWorkspaceView.vue` that renders three regions only: current chapter state, review suggestions, and commit preview.
- Keep data flow prop-driven for now; do not add a global store before the shell proves useful.
- Use static mock props in the first pass instead of wiring real network calls in the same task.

**Step 4: Run test to verify it passes**

Run: `npm --prefix apps/web test -- --run`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/package.json apps/web/src
git commit -m "feat: add phase-a workspace shell"
```

### Task 5: Verify the Closeout Path End-to-End

**Files:**
- Modify: `docs/2026-04-15_W16小说生成系统开发记录.md`
- Modify: `00 专注区/_本周.md`

**Step 1: Write the failing checklist**

```markdown
- [ ] API routes return usable JSON for project, chapter state, main flow, and local rewrite
- [ ] Minimum regression harness can be run locally
- [ ] Route tests remain offline by using the scoped API LLM mock
```

**Step 2: Run the verification commands**

Run: `pytest tests/api/test_chapter_state_routes.py tests/api/test_agent_run_routes.py tests/evals/test_minimum_regression.py -v`
Expected: PASS

**Step 3: Write the minimal closeout documentation**

- Update the daily development log with the exact commands and pass counts.
- Update the weekly board so the current收口项 is explicit: `API routes -> evals -> closeout verification`.
- Record that the workspace shell was intentionally deferred unless Task 4 was explicitly executed after closeout.

**Step 4: Re-run the checks after docs are updated**

Run: `pytest tests/api/test_chapter_state_routes.py tests/api/test_agent_run_routes.py tests/evals/test_minimum_regression.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/2026-04-15_W16小说生成系统开发记录.md ../../00\ 专注区/_本周.md
git commit -m "docs: record phase-a closeout status"
```

**Optional follow-up after closeout:**

If Task 4 is executed later, run:

```bash
npm --prefix apps/web test -- --run
```

Expected: PASS
