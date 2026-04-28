# 4-Agent Lite AI Webnovel Platform Implementation Plan v0.2.3

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first implementation-ready version of the 4-agent AI webnovel platform, aligned with PRD v0.2, including explicit agent contracts, a local rewrite fast-track, chapter state machine, retrieval rules, commit preview safety, event semantics, optimistic concurrency protection, model capability routing, anti-AI-tone soft scoring, hook debt visibility, projection freshness signals, and a minimum regression harness.

**Architecture:** Use a greenfield monorepo with a Vue web app, FastAPI backend, SQLite canonical state store, and a lightweight agent package for Planner, Writer, Reviewer, and Committer. Keep `Story State Core` as the only source of truth, generate Truth Files as projection views, and add a semantic event log instead of full event sourcing. Split the system into two paths: the main chapter flow and a dedicated local rewrite fast-track. Add a lightweight orchestration layer, not a fifth agent, to validate state transitions, aggregate warnings, and propagate correlation metadata across the run.

**Tech Stack:** Vue 3, TypeScript, Element Plus, FastAPI, Python 3.11, SQLite, SQLModel, LiteLLM, local vector store, BM25, pytest, Playwright, Vitest, Jinja, pnpm workspace

**Execution Gate:** The first implementation PR must not merge until the three hard safety guards are in place end-to-end: commit preview hash validation against dirty drafts, optimistic concurrency checks for state writes, and explicit warning propagation plus frontend handling for unresolved `@DSL` references.

---

### Task 0: Bootstrap Monorepo Structure

**Files:**
- Create: `pnpm-workspace.yaml`
- Create: `package.json`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `apps/web/package.json`
- Create: `services/api/pyproject.toml`
- Create: `packages/agents/pyproject.toml`
- Create: `packages/contracts/package.json`
- Create: `tests/conftest.py`
- Create: `apps/web/vitest.config.ts`

**Step 1: Write the failing test**

```python
from pathlib import Path

def test_workspace_directories_exist():
    root = Path(__file__).resolve().parents[2]
    for pkg in ["apps/web", "services/api", "packages/agents", "packages/contracts"]:
        assert (root / pkg).is_dir(), f"Missing workspace directory: {pkg}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests -k workspace_directories_exist -v`
Expected: FAIL because monorepo structure and fixtures do not exist.

**Step 3: Write minimal implementation**

- Initialize the workspace layout for `apps/web`, `services/api`, `packages/agents`, `packages/contracts`, `evals`, and `tests`.
- Add base pnpm workspace config and Python package config.
- Add `tests/conftest.py` with `fake_state`, `fake_project`, `client`, and `session` fixtures.
- Add Vitest config and placeholder package manifests so frontend and backend tests can collect cleanly.
- Keep the bootstrap assertion free of custom helper dependencies so a fresh clone fails with clear path errors, not `NameError`.
- Verify `pytest --collect-only` and frontend test discovery can run without directory ambiguity.

**Step 4: Run test to verify it passes**

Run: `pytest tests -k workspace_directories_exist -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pnpm-workspace.yaml package.json pyproject.toml .gitignore apps/web services/api packages/agents packages/contracts tests/conftest.py
git commit -m "feat: bootstrap monorepo structure"
```

### Task 1: Define Contracts, Chapter State Machine, and Prompt Versions

**Files:**
- Create: `packages/contracts/story_state.schema.json`
- Create: `packages/contracts/agent_io/planner_output.schema.json`
- Create: `packages/contracts/agent_io/writer_output.schema.json`
- Create: `packages/contracts/agent_io/reviewer_output.schema.json`
- Create: `packages/contracts/agent_io/committer_output.schema.json`
- Create: `packages/contracts/chapter_state.schema.json`
- Create: `packages/contracts/prompt_version.schema.json`
- Test: `tests/contracts/test_agent_contracts.py`

**Step 1: Write the failing test**

```python
from jsonschema import validate

def test_reviewer_contract_requires_actionable_suggestions():
    schema = load_schema("packages/contracts/agent_io/reviewer_output.schema.json")
    payload = {
        "consistency_issues": [],
        "style_issues": [],
        "readability_score": 82,
        "hook_strength_score": 68,
        "actionable_suggestions": [{"type": "hook", "message": "add stronger chapter-end hook"}],
        "risk_level": "medium"
    }
    validate(payload, schema)

def test_all_schemas_declare_version():
    for schema_path in get_all_schema_paths():
        schema = load_schema(schema_path)
        assert "$schema" in schema
        assert "x-schema-version" in schema
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/contracts/test_agent_contracts.py -v`
Expected: FAIL because contract files do not exist.

**Step 3: Write minimal implementation**

- Add JSON schemas for all four agents.
- Add chapter state enum: `not_started -> planning -> drafting -> reviewing -> pending_confirmation -> committed -> published`.
- Add prompt version schema for Planner, Writer, Reviewer, and Prompt Assembler.
- Add `$schema` and `x-schema-version` to every schema file.
- Require explicit version bumps whenever a breaking schema change is introduced.

**Step 4: Run test to verify it passes**

Run: `pytest tests/contracts/test_agent_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/contracts tests/contracts/test_agent_contracts.py
git commit -m "feat: add versioned agent contracts and chapter state schemas"
```

### Task 2: Build Canonical State Core, Semantic Event Log, and Commit Preview Model

**Files:**
- Create: `services/api/app/models/story_state.py`
- Create: `services/api/app/models/chapter_state.py`
- Create: `services/api/app/models/commit_preview.py`
- Create: `services/api/app/models/event_log.py`
- Create: `services/api/app/repositories/story_state_repository.py`
- Create: `services/api/app/repositories/event_log_repository.py`
- Test: `tests/api/test_commit_preview_repository.py`
- Test: `tests/api/test_commit_hash_validation.py`
- Test: `tests/api/test_event_log_semantics.py`
- Test: `tests/api/test_state_version_guard.py`

**Step 1: Write the failing test**

```python
def test_commit_preview_is_idempotent_for_same_confirmed_draft(session):
    repo = StoryStateRepository(session)
    preview_a = repo.create_commit_preview("project-1", "chapter-20", draft_hash="abc123")
    preview_b = repo.create_commit_preview("project-1", "chapter-20", draft_hash="abc123")
    assert preview_a.id == preview_b.id

def test_commit_preview_invalidated_when_draft_mutated_after_preview(session):
    repo = StoryStateRepository(session)
    repo.create_commit_preview("project-1", "chapter-20", draft_hash="abc123")
    result = repo.confirm_commit("project-1", "chapter-20", current_hash="xyz999")
    assert result.status == "hash_mismatch"
    assert result.requires_reconfirmation is True

def test_event_log_records_semantic_metadata(session):
    repo = EventLogRepository(session)
    event = repo.append(
        event_type="preview_created",
        actor_type="agent",
        correlation_id="run-123",
        causation_id="review-122"
    )
    assert event.event_type == "preview_created"
    assert event.actor_type == "agent"
    assert event.correlation_id == "run-123"
    assert event.causation_id == "review-122"

def test_state_write_rejects_stale_version(session):
    repo = StoryStateRepository(session)
    repo.save_chapter_state("project-1", "chapter-20", {"state": "drafting"}, version=3)
    stale_write = repo.save_chapter_state("project-1", "chapter-20", {"state": "reviewing"}, version=2)
    assert stale_write.status == "version_conflict"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_commit_preview_repository.py tests/api/test_commit_hash_validation.py tests/api/test_event_log_semantics.py tests/api/test_state_version_guard.py -v`
Expected: FAIL because preview repository and models are missing.

**Step 3: Write minimal implementation**

- Define canonical story state tables.
- Define chapter state and semantic event log with `event_type`, `actor_type`, `correlation_id`, and `causation_id`.
- Add commit preview model with draft hash, diff payload, and warnings.
- Make commit preview creation idempotent.
- Reject confirmation when the current draft hash no longer matches the preview hash.
- Require preview regeneration and explicit reconfirmation after hash mismatch.
- Add `version` or equivalent optimistic concurrency field on chapter-level writable state.
- Record semantic route and lifecycle events so runs can be audited and replayed at the event-summary level.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_commit_preview_repository.py tests/api/test_commit_hash_validation.py tests/api/test_event_log_semantics.py tests/api/test_state_version_guard.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/models services/api/app/repositories tests/api/test_commit_preview_repository.py tests/api/test_commit_hash_validation.py tests/api/test_event_log_semantics.py tests/api/test_state_version_guard.py
git commit -m "feat: add semantic event log and state core safety"
```

### Task 3: Implement Retrieval Rules, DSL Safety, and Prompt Assembler Policy

**Files:**
- Create: `services/api/app/services/retrieval_service.py`
- Create: `services/api/app/services/dsl_resolver.py`
- Create: `services/api/app/services/prompt_assembler.py`
- Create: `services/api/app/config/retrieval_policy.py`
- Test: `tests/api/test_prompt_assembler_policy.py`

**Step 1: Write the failing test**

```python
def test_prompt_assembler_prioritizes_explicit_dsl_refs_over_general_recall(fake_state):
    result = assemble_prompt(
        text="use @[character:LiMing] to rewrite this section",
        state=fake_state,
        retrieval_results=make_retrieval_results()
    )
    assert result.blocks[0].source_type == "dsl"

def test_dsl_resolver_raises_warning_for_unknown_entity(fake_state):
    result = resolve_dsl("use @[character:Unknown] to rewrite", state=fake_state)
    assert result.warnings[0]["type"] == "unknown_entity"
    assert result.warnings[0]["ref"] == "character:Unknown"
    assert result.warnings[0]["severity"] == "block"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_prompt_assembler_policy.py -v`
Expected: FAIL because assembler policy is missing.

**Step 3: Write minimal implementation**

- Support explicit `@DSL` references for character, location, hook, and card.
- Define separate `Top-K` defaults for chapter generation and local rewrite.
- Enforce truncation order: explicit refs > chapter-local state > recent summaries > distant history.
- Return explicit warnings for unresolved `@DSL` entities instead of silently degrading to general recall.
- Support severity policy by warning type: `unknown_entity -> block`, `ambiguous_ref -> warn`, `deprecated_ref -> info`.
- Pass unresolved reference warnings through the prompt assembler and API layer so the frontend can block or warn.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_prompt_assembler_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/services services/api/app/config/retrieval_policy.py tests/api/test_prompt_assembler_policy.py
git commit -m "feat: add retrieval policy and dsl safety rules"
```

### Task 3.5: Add Retrieval Quality Benchmark

**Files:**
- Create: `evals/retrieval/retrieval_cases.yaml`
- Create: `evals/retrieval/run_retrieval_benchmark.py`
- Create: `evals/retrieval/scorers.py`
- Test: `tests/evals/test_retrieval_benchmark.py`

**Step 1: Write the failing test**

```python
def test_retrieval_benchmark_reports_quality_metrics():
    report = run_retrieval_benchmark("evals/retrieval/retrieval_cases.yaml")
    assert "dsl_resolution_accuracy" in report
    assert "recall_at_k" in report
    assert "retained_key_facts_rate" in report
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/evals/test_retrieval_benchmark.py -v`
Expected: FAIL because retrieval benchmark files are missing.

**Step 3: Write minimal implementation**

- Add fixed retrieval benchmark cases for explicit DSL references and mixed recall scenarios.
- Measure `dsl_resolution_accuracy`, `recall_at_k`, and `retained_key_facts_rate`.
- Make the benchmark runnable offline so retrieval changes can be evaluated before prompt or rerank updates merge.

**Step 4: Run test to verify it passes**

Run: `pytest tests/evals/test_retrieval_benchmark.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add evals/retrieval tests/evals/test_retrieval_benchmark.py
git commit -m "feat: add retrieval quality benchmark"
```

### Task 3.6: Add Model Capability Routing Policy

**Files:**
- Create: `packages/agents/src/model_routing_policy.py`
- Create: `services/api/app/config/model_capability_tiers.py`
- Test: `tests/agents/test_model_routing_policy.py`

**Step 1: Write the failing test**

```python
def test_model_routing_uses_capability_tiers_not_provider_names():
    policy = load_model_routing_policy()
    assert policy["planner"]["tier"] == "high_quality_generation"
    assert policy["reviewer"]["tier"] == "high_consistency_check"
    assert policy["local_rewrite"]["tier"] == "low_latency_rewrite"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_model_routing_policy.py -v`
Expected: FAIL because routing policy files are missing.

**Step 3: Write minimal implementation**

- Define capability tiers instead of hard-coding provider names into the plan.
- Route Planner and Writer through `high_quality_generation`.
- Route Reviewer through `high_consistency_check`.
- Route local rewrite through `low_latency_rewrite`.
- Resolve concrete providers and fallback chains through environment config.
- Add latency and token budget hints per capability tier.
- Record route decisions and fallback choices into the semantic event log for later diagnosis.

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_model_routing_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/agents/src/model_routing_policy.py services/api/app/config/model_capability_tiers.py tests/agents/test_model_routing_policy.py
git commit -m "feat: add model capability routing policy"
```

### Task 4: Expose Project, Chapter State, and Prompt Version APIs

**Files:**
- Create: `services/api/app/routers/projects.py`
- Create: `services/api/app/routers/chapters.py`
- Create: `services/api/app/routers/prompt_versions.py`
- Modify: `services/api/app/main.py`
- Test: `tests/api/test_chapter_state_routes.py`

**Step 1: Write the failing test**

```python
def test_patch_chapter_state_updates_chapter_status(client):
    response = client.patch(
        "/projects/project-1/chapters/chapter-20/state",
        json={"state": "reviewing", "version": 3}
    )
    assert response.status_code == 200
    assert response.json()["state"] == "reviewing"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_chapter_state_routes.py -v`
Expected: FAIL because routes do not exist.

**Step 3: Write minimal implementation**

- Add project bootstrap route.
- Add chapter state read/write route.
- Add prompt version listing and activation routes.
- Require version compare or `If-Match` equivalent on mutable chapter state writes to prevent lost updates.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_chapter_state_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/routers services/api/app/main.py tests/api/test_chapter_state_routes.py
git commit -m "feat: expose chapter state and prompt version apis"
```

### Task 5: Implement the Main 4-Agent Chapter Flow

**Files:**
- Create: `packages/agents/src/planner.py`
- Create: `packages/agents/src/writer.py`
- Create: `packages/agents/src/reviewer.py`
- Create: `packages/agents/src/committer.py`
- Create: `packages/agents/src/orchestrator.py`
- Create: `packages/agents/src/main_flow.py`
- Create: `services/api/app/routers/agent_runs.py`
- Test: `tests/agents/test_main_chapter_flow.py`

**Step 1: Write the failing test**

```python
def test_main_chapter_flow_returns_review_and_commit_preview(fake_project):
    result = run_main_flow(fake_project, "chapter-20", "make the mentor-apprentice split more painful")
    assert result.plan["beats"]
    assert result.draft["draft_text"]
    assert result.review["actionable_suggestions"] is not None
    assert result.review["patch_plan"] is not None
    assert result.commit_preview["state_diff"] is not None
    assert result.meta["correlation_id"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_main_chapter_flow.py -v`
Expected: FAIL because main flow is missing.

**Step 3: Write minimal implementation**

- Make Planner produce structured chapter plan.
- Make Writer consume plan + context and return structured draft.
- Make Reviewer emit scored issues, actionable suggestions, and a structured `patch_plan`.
- Make Committer emit preview-only diff without mutating state until confirmation.
- Add a lightweight orchestrator layer to validate state transitions, aggregate warnings, and propagate `correlation_id` through the run.
- Read concrete models from the capability routing policy instead of embedding provider names in agent logic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_main_chapter_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/agents services/api/app/routers/agent_runs.py tests/agents/test_main_chapter_flow.py
git commit -m "feat: add main four agent chapter flow"
```

### Task 6: Implement the Local Rewrite Fast-Track

**Files:**
- Create: `packages/agents/src/local_rewrite_flow.py`
- Create: `services/api/app/services/diff_validator.py`
- Create: `services/api/app/routers/local_rewrites.py`
- Test: `tests/agents/test_local_rewrite_flow.py`

**Step 1: Write the failing test**

```python
def test_local_rewrite_flow_returns_field_level_commit_diff(fake_project):
    result = run_local_rewrite_flow(
        fake_project,
        selected_text="The mentor watched his back and said nothing.",
        intent="strengthen the death foreshadowing"
    )
    assert result.rewritten_text
    assert result.validation.scope == "local"
    assert result.commit_preview["state_diff"]

def test_local_rewrite_diff_validator_rejects_out_of_scope_changes(fake_project):
    result = run_local_rewrite_flow(
        fake_project,
        selected_text="The mentor watched his back and said nothing.",
        intent="strengthen the death foreshadowing"
    )
    assert result.validation.out_of_scope_changes == []

def test_diff_validator_detects_out_of_scope_changes_when_model_overwrites_context(fake_project):
    result = run_local_rewrite_flow(
        fake_project,
        selected_text="The mentor watched his back and said nothing.",
        intent="strengthen the death foreshadowing",
        mock_writer_output="[rewrote previous paragraph] The mentor watched his back and said nothing."
    )
    assert len(result.validation.out_of_scope_changes) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_local_rewrite_flow.py -v`
Expected: FAIL because local rewrite flow is missing.

**Step 3: Write minimal implementation**

- Build dedicated fast-track path: Context Assembler -> Writer local mode -> Diff Validator -> Commit Preview.
- Restrict validation scope to impacted region and linked state.
- Return field-level diff only.
- Detect `out_of_scope_changes` when the model modifies text outside the selected range.
- Cover both directions in tests: normal local rewrites must stay in scope, and deliberately overflowing rewrites must be detected.
- Allow local rewrite to consume `patch_plan` output when review-triggered rewrites are launched from the main flow.
- Route the fast-track through the low-latency capability tier so local rewrite stays responsive.

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_local_rewrite_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/agents/src/local_rewrite_flow.py services/api/app/services/diff_validator.py services/api/app/routers/local_rewrites.py tests/agents/test_local_rewrite_flow.py
git commit -m "feat: add local rewrite guardrails"
```

### Task 7: Add Reviewer Threshold Logic and Truth File Projections

**Files:**
- Create: `services/api/app/services/reviewer_policy.py`
- Create: `services/api/app/services/truth_file_projector.py`
- Create: `services/api/app/templates/truth_files/characters.md.j2`
- Create: `services/api/app/templates/truth_files/hooks.md.j2`
- Test: `tests/api/test_reviewer_policy.py`
- Test: `tests/api/test_truth_file_projector.py`

**Step 1: Write the failing test**

```python
def test_reviewer_policy_escalates_when_hook_strength_below_threshold():
    result = evaluate_reviewer_policy({"hook_strength_score": 55, "actionable_suggestions": []})
    assert result["requires_strong_prompt"] is True
    assert result["recommended_card_type"] == "hook"

def test_truth_projection_declares_source_version_and_projection_time():
    projection = build_truth_projection({"state_version": 8})
    assert projection["source_state_version"] == 8
    assert projection["projection_time"] is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_reviewer_policy.py tests/api/test_truth_file_projector.py -v`
Expected: FAIL because reviewer policy and projector are missing.

**Step 3: Write minimal implementation**

- Add threshold behavior for `>=80`, `60-79`, `<60`.
- Generate Markdown Truth File projections from canonical state after commit confirmation.
- Include `source_state_version`, `projection_time`, and stale-view messaging metadata in projection payloads.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_reviewer_policy.py tests/api/test_truth_file_projector.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/api/app/services services/api/app/templates tests/api/test_reviewer_policy.py tests/api/test_truth_file_projector.py
git commit -m "feat: add reviewer threshold policy and truth projections"
```

### Task 8: Add Minimum Evaluation Harness and Prompt Regression

**Files:**
- Create: `evals/cases/minimum_set.yaml`
- Create: `evals/run_minimum_regression.py`
- Create: `evals/scorers/story_constraints.py`
- Create: `evals/scorers/ai_tone_detector.py`
- Test: `tests/evals/test_minimum_regression.py`

**Step 1: Write the failing test**

```python
def test_minimum_regression_suite_contains_required_story_checks():
    suite = load_suite("evals/cases/minimum_set.yaml")
    assert len(suite["cases"]) >= 10
    assert "constraint_schema" in suite["cases"][0]["checks"]
    assert "hook_presence" in suite["cases"][0]["checks"]
    assert "ai_tone_soft_score" in suite["cases"][0]["checks"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/evals/test_minimum_regression.py -v`
Expected: FAIL because regression suite files are missing.

**Step 3: Write minimal implementation**

- Add 10 to 20 fixed cases with setting, character sheet, chapter goal, and style constraints.
- Add local regression runner.
- Add basic checks for schema, forbidden words, conflicts, and hook presence.
- Add anti-AI-tone soft scoring based on fatigue word density, repeated sentence patterns, and paragraph rhythm.
- Keep anti-AI-tone as a weighted score and warning channel, not a single hard blocklist gate.
- Leave genre-specific tolerance calibration as a follow-up optimization after the minimum suite stabilizes.
- Reserve 3 to 5 golden chapter snapshots as the next-stage regression gate after the minimum suite is stable.

**Step 4: Run test to verify it passes**

Run: `pytest tests/evals/test_minimum_regression.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add evals tests/evals/test_minimum_regression.py
git commit -m "feat: add prompt regression and anti-ai-tone scoring"
```

### Task 9: Wire End-to-End Workspace and Confirmation UX

**Files:**
- Create: `apps/web/src/views/ChapterWorkspaceView.vue`
- Create: `apps/web/src/components/StateSidebar.vue`
- Create: `apps/web/src/components/ReviewPanel.vue`
- Create: `apps/web/src/components/CommitPreviewPanel.vue`
- Create: `apps/web/src/components/HookDebtPanel.vue`
- Create: `apps/web/src/components/DslWarningPanel.vue`
- Create: `apps/web/src/components/ProjectionFreshnessBadge.vue`
- Create: `apps/web/src/components/ChapterStateBadge.vue`
- Test: `apps/web/src/views/__tests__/ChapterWorkspaceView.test.ts`
- Test: `tests/e2e/chapter-workspace.spec.ts`

**Step 1: Write the failing test**

```ts
import { render, screen } from "@testing-library/vue";
import ChapterWorkspaceView from "../ChapterWorkspaceView.vue";

test("renders chapter state, commit preview, hook debt, dsl warnings, and projection freshness", async () => {
  render(ChapterWorkspaceView);
  expect(screen.getByText("Current chapter state")).toBeInTheDocument();
  expect(screen.getByText("Commit preview")).toBeInTheDocument();
  expect(screen.getByText("Open hook debt")).toBeInTheDocument();
  expect(screen.getByText("Reference warnings")).toBeInTheDocument();
  expect(screen.getByText("Projection freshness")).toBeInTheDocument();
});

test("user can override dsl warning and continue generation", async () => {
  render(ChapterWorkspaceView);
  expect(screen.getByText("Reference warnings")).toBeInTheDocument();
  expect(screen.getByText("Continue anyway")).toBeInTheDocument();
});
```

Also add an E2E scenario in `tests/e2e/chapter-workspace.spec.ts` that verifies the full override path:

```ts
test("user can override DSL warning and force generation", async ({ page }) => {
  await page.fill('[data-testid="editor"]', 'use @[character:Unknown] to rewrite');
  await page.click('[data-testid="generate-btn"]');
  await expect(page.getByText("Unresolved reference warnings")).toBeVisible();
  await page.click('[data-testid="confirm-override-btn"]');
  await expect(page.getByText("Generating")).toBeVisible();
});
```

**Step 2: Run test to verify it fails**

Run: `pnpm --filter web test ChapterWorkspaceView`
Expected: FAIL because the updated workspace view is missing.

**Step 3: Write minimal implementation**

- Show chapter state badge, reviewer suggestions, and commit preview.
- Show pending hook debt from Truth File projections, including source chapter and expected closure window.
- Add buttons for local rewrite, full draft, confirm, and reject state diff.
- Show projection refresh success after confirmed commit.
- Show projection freshness metadata so users can see `projection_time`, `source_state_version`, and stale-view warnings.
- Highlight when the current chapter touches an open hook.
- Surface unresolved `@DSL` warnings in a dedicated panel.
- Inline-highlight invalid `@DSL` references in the editor.
- Block generation by default when unresolved `@DSL` warnings exist, or require explicit user confirmation to continue.
- Add an E2E override path so users can acknowledge the warning and force generation when they intentionally want to proceed.

**Step 4: Run test to verify it passes**

Run: `pnpm --filter web test ChapterWorkspaceView`
Expected: PASS

Run: `pnpm --filter web test tests/e2e/chapter-workspace.spec.ts`
Expected: PASS, including the warning override flow.

**Step 5: Commit**

```bash
git add apps/web/src/views apps/web/src/components apps/web/src/views/__tests__/ChapterWorkspaceView.test.ts tests/e2e/chapter-workspace.spec.ts
git commit -m "feat: add workspace guardrails and hook debt ui"
```

Plan complete and saved to `docs/plans/2026-04-09-ai-webnovel-platform-4-agent-lite-implementation-plan-v0.2.3.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
