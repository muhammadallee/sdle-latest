# Dry Run 01 — Happy Path (Full End-to-End Success)

| | |
|---|---|
| **Scenario ID** | DR-01 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The complete success flow for a new project: WorkItem identity, preflight, governance, then **18 phases, 8 gates.** through to `complete` and the repository baseline. |
| **Defect IDs** | D02, D03, D05 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6 installed with the README's tested command. Generation is simulated |
| **Starting conditions** | A new git repository with one commit. SpecKit initialised (`.specify/`, `.claude/skills/speckit-*`). `requirements/todo-api.md` present. No WorkItem registered, no `.sdle/baseline.json`. Governance input classifies it `GREENFIELD` at LOW risk. No feature directory bound yet |
| **Guardrails exercised** | Bootstrap order, gate discipline, status headers, TP-011 review before every approval, Gate 7 test evidence bound to the manifest, change set measured from the pinned base, completion summary, baseline establishment |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; no model
> or SpecKit run produced it. Hashes are illustrative and shortened with `…`,
> and artifact bodies are abridged. The engine behaviour it depends on is
> asserted by the tests under *Executable coverage*. Their results — **PASS**,
> **FAIL**, **BLOCKED** or **NOT RUN** — are recorded against the verified
> commit in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable project. Nothing outside the directory is touched.

```bash
mkdir dr01 && cd dr01 && git init -q
uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script sh
# Copy SDLE in: .claude/skills/sdle/, .claude/commands/, .claude/hooks/,
# .claude/agents/sdle-*, scripts/  — and merge .claude/settings.json's hooks.
mkdir requirements && cp <sdle-checkout>/requirements/todo-api.md requirements/
git add -A && git commit -qm "fixture"
```

The executable form of this scenario uses the suite's generated fixture rather
than a real Spec Kit install: `tests/conftest.py::git_project` writes
`requirements/todo-api.md` and a stub skill at runtime, and every generation
step is simulated by writing an artifact over the size floor.

---

## Transcript

**User:**

```
start workflow
```

**SDLE:**

```
No workflow exists in this repository yet. WorkItem name?
```

*(No header: there is no state to assert. `preflight` has not run yet. It
resolves a WorkItem like every runtime command, so in a repository with none it
would refuse `workitem_required` before checking anything. Identity comes
first.)*

---

**User:** `Todo API`

**SDLE:**

```
📋 SDLE Status: Phase 1/18 — Requirements Check [IN PROGRESS]

WorkItem created: todo-api.
Preflight passed: SpecKit found, skills discovered (speckit-), requirements found.

I found requirements/:
  • requirements/todo-api.md (2.4 KB)

Content scan passed. Project name inferred: "Todo List REST API".

Governance: requirements quality PASS; classified as an enhancement on
GREENFIELD — 18 phases, 8 gates; risk LOW. At LOW risk the design gate is
omittable; I will still ask you to approve it, which is always permitted.

I'll now generate the project constitution. Shall I proceed?
```

*(Engine: `sdle.sh workitem create --name "Todo API"` →
`sdle.sh --workitem todo-api preflight` →
`sdle.sh --workitem todo-api scan --path requirements/todo-api.md` →
`sdle.sh --workitem todo-api governance assess --input governance-input.json`.)*

---

**User:** `yes`

**SDLE:**

```
<!-- SDLE_STATE phase=constitution_draft status=in_progress progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Generate Constitution [IN PROGRESS]

Generating constitution...

Constitution generated at .specify/memory/constitution.md (4.1 KB, verified).

---
✋ APPROVAL REQUIRED — Gate 1/8: Constitution Approval

# Todo List REST API — Project Constitution

## Principles
1. All endpoints follow REST semantics and return consistent error envelopes.
2. Input validation at every boundary; no unvalidated user data reaches the ORM.
[... abridged — the full constitution is displayed in a real run ...]

Artifact path: .specify/memory/constitution.md
Fingerprint: 3c9a61b2…f4e7
Review: architecture-review | PASS | agent:sdle-design-review

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

*(Engine: `sdle.sh --workitem todo-api --session 7c1e9a42 init` bound the flow
and advanced to `constitution_draft`. After generation:
`sdle.sh artifact record --phase constitution_draft --path .specify/memory/constitution.md`,
`sdle.sh advance --to gate_constitution`, then the TP-011 review the gate
prompt's `Review:` line reports, `sdle.sh artifact review --path .specify/memory/constitution.md --type architecture-review --result PASS --actor-type agent --actor-name sdle-design-review`.)*

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=4/18 -->
📋 SDLE Status: Phase 4/18 — Generate Specification [IN PROGRESS]

Gate 1 approved. Baseline fingerprint recorded.

Generating specification...

Specification generated at workitems/todo-api/specs/001-todo-api/spec.md (11.8 KB, verified).

Before the approval gate, the generator raised clarification questions:

  1. Should completed todos be excluded from the default list view, or included?
  2. Is there a maximum length for the todo title?

Please answer the above questions — your response will be saved to
clarifications/spec_draft-2026-09-10-1012.clarify. Say `continue` to skip without saving.
```

*(Engine: `sdle.sh gate approve --gate gate_constitution`. Then, around the
specification step: `sdle.sh feature bind` exported `SPECIFY_INIT_DIR`, Spec Kit
created `specs/001-todo-api/`, and `sdle.sh feature resolve` found exactly one
candidate and **moved** it into the WorkItem:
`workitems/todo-api/specs/001-todo-api`. Had there been two candidates it
would have refused `feature_ambiguous` and listed them.)*

---

**User:**

```
1. Include completed todos by default; the completed=false filter is opt-in.
2. Title max length 200 characters.
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [AWAITING APPROVAL]

✓ Clarification saved to clarifications/spec_draft-2026-09-10-1012.clarify.

---
✋ APPROVAL REQUIRED — Gate 2/8: Specification Approval

# Feature Specification: Todo List REST API

## User Stories
- As a user, I can create a todo with a title (required, ≤200 chars) ...
[... abridged ...]

Artifact path: workitems/todo-api/specs/001-todo-api/spec.md
Fingerprint: 88d204ca…19be
Review: specification-review | PASS | agent:sdle-design-review
---
```

---

**User:** `approve with comments: Add rate limiting to the API constraints in the plan phase.`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=in_progress progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [IN PROGRESS]

Gate 2 approved. Baseline fingerprint recorded. Comments noted.
Generating plan...
```

*(Gate 3, Plan Approval, follows the same prompt structure and the user
approves. Compacted:)*

```
<!-- SDLE_STATE phase=gate_plan status=awaiting_approval progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [AWAITING APPROVAL]
✋ APPROVAL REQUIRED — Gate 3/8: Plan Approval
[workitems/todo-api/specs/001-todo-api/plan.md displayed in full — abridged]
```

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=checklist_draft status=in_progress progress=8/18 -->
📋 SDLE Status: Phase 8/18 — Generate Checklist [IN PROGRESS]

Gate 3 approved. Baseline fingerprint recorded.
Checklist generated (verified). Proceeding directly to Phase 9: Generate Tasks —
no gate between these phases; both are reviewed together at Gate 4.

Tasks generated at workitems/todo-api/specs/001-todo-api/tasks.md (verified).

### Checklist (Phase 8 output — review alongside Tasks)
- [ ] Every endpoint has input validation defined
[... abridged ...]

---
✋ APPROVAL REQUIRED — Gate 4/8: Tasks Approval

# Tasks: Todo List REST API
T001. Scaffold project structure and dependency manifest
[... abridged ...]

Artifact path: workitems/todo-api/specs/001-todo-api/tasks.md
Fingerprint: 5e11f0ad…c773
---
```

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=analyze status=in_progress progress=11/18 -->
📋 SDLE Status: Phase 11/18 — Analyze [IN PROGRESS]

Gate 4 approved. Baseline fingerprint recorded.
Running cross-artifact analysis...
```

*(Analysis refines `tasks.md` in place. The engine re-baselines Gate 4's
fingerprint to match (`sdle.sh drift rebaseline --gate gate_tasks`), so both
gates can reference one file without a false drift alert. Gate 5, Analysis
Approval, shows the refined file. The user approves. Compacted.)*

```
<!-- SDLE_STATE phase=design_generation status=in_progress progress=13/18 -->
📋 SDLE Status: Phase 13/18 — Generate Design [IN PROGRESS]

Gate 5 approved. Generating design/app/app-design.md and design/db/db-design.md...
```

*(Gate 6, Design Approval, displays `design/app/app-design.md`. At LOW risk the
policy does not require it, so SDLE offers both `approve` and `gate omit`, and
the user approves. Compacted.)*

---

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=in_progress progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [IN PROGRESS]

Gate 6 approved. Baseline fingerprint recorded.

Working tree is clean — dirty-tree guard passed. Implementation base pinned:
b9332aab…5ca9.

Implementing against tasks.md, informed by the approved design documents...

Implementation complete. Building the implementation manifest...
Secrets scan: no high-risk patterns found in the changed files.
Test evidence: pytest detected — 28 passed (exit 0). Gate 7 can accept this.

---
✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval

# Implementation Manifest
Generated: 2026-09-10T11:42:09Z
Evidence: workitems/todo-api/.sdle/evidence/implementation-muh-20260910T114209Z-3a554ee0.json
Phase: implement (15/18)

## Changed/Added Files
A design/app/app-design.md
A design/db/db-design.md
A requirements.txt
A src/app.py
A src/models/todo.py
A src/routes/todos.py
A src/validation.py
A tests/test_todos.py

## Potential Secrets Detected
None detected.

## Test Evidence
Runner: pytest
Command: python -m pytest -q
Result: passed (exit 0)

```
28 passed in 3.41s
```

## Summary
Implemented the Todo REST API per tasks.md: CRUD endpoints, filtering,
completion shortcut endpoint, validation layer, and pytest suite.

Artifact path: workitems/todo-api/.sdle/implementation-manifest.md
Fingerprint: b07e33d1…a2c5
Review: code-review | PASS | agent:sdle-code-review
---
```

*(Engine: `sdle.sh implement preflight` pinned `implementation_base_ref`, and
`sdle.sh feature bind --require-feature` re-asserted the Spec Kit environment
before generation. Then `sdle.sh manifest build --summary "Implemented the Todo REST API…"`
listed every change **since that base**, whether committed, staged, unstaged
or untracked, each with its git status letter. It wrote the evidence record the
`Evidence:` line names: runner, command, exit code, status, this manifest's
SHA-256, the base and the WorkItem. At approval, Gate 7 reads that record and
requires a run that actually passed, for these exact manifest bytes.)*

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=security_review status=in_progress progress=17/18 -->
📋 SDLE Status: Phase 17/18 — Security Review [IN PROGRESS]

Gate 7 approved. Baseline fingerprint recorded.

Gathering evidence: constitution, spec, plan, tasks, and the implementation diff
from the pinned base (the same change set the manifest listed)...
Review written to reviews/security-review-2026-09-10-1151.md (verified).

---
✋ APPROVAL REQUIRED — Gate 8/8: Security Review Approval

# AI-Assisted Security Review — Todo List REST API
**Disclaimer:** This is an AI-assisted review based on artifacts and a git diff.
It is NOT a substitute for SAST/DAST tools, dependency scanners, or a professional audit.
[... abridged ...]

Artifact path: reviews/security-review-2026-09-10-1151.md
Fingerprint: 4d8fa6e0…77b1
---
```

*(Engine: `sdle.sh security-review begin` named the review file,
`sdle.sh security-review evidence` returned the diff, `changes` and
`untracked` from `implementation_base_ref`, and the review was recorded and
reviewed before the gate.)*

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=18/18 -->
📋 SDLE Status: Phase 18/18 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 8 gates passed. Completion summary: workitems/todo-api/.sdle/completion-summary.json
Repository baseline established: .sdle/baseline.json — later WorkItems in this
repository converge onto ITERATIVE against it.
```

---

## Artifacts, state and audit

- `workitems/index.md` gained one row and `workitems/todo-api/workitem.json`
  was written, both by `workitem create`.
- `workitems/todo-api/.sdle/state.json` traversed
  `requirements_check → constitution_draft → gate_constitution → spec_draft → gate_spec → plan_draft → gate_plan → checklist_draft → tasks_draft → gate_tasks → analyze → gate_analyze → design_generation → gate_design → implement → gate_implement → security_review → gate_security → complete`.
- All 8 `approvals.*` entries hold `decision: "approved"`, and `artifact_shas`
  holds 8 lowercase SHA-256 baselines.
- `specKit.featureDirectory` is `workitems/todo-api/specs/001-todo-api`.
- `evidence/` holds the governance record's evidence, one review evidence file
  per review, and `implementation-<execution-id>.json` for the manifest. Each
  is named by a collision-resistant execution id and was claimed with an
  exclusive create.
- `audit.md` grew with every phase movement, review and gate decision, and
  `audit verify` reports an intact chain.
- `completion-summary.json` and `.sdle/baseline.json` were each written
  exactly once, at the Gate 8 approval.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `approve` at a gate whose artifact has no current PASS review | Refused `review_missing` | Phase, approvals and `audit.md` unchanged |
| `approve` at Gate 7 on a manifest built with `--skip-tests` | Refused `tests_not_passed` | Same — see [DR-14](14-gate-evidence-refusals.md) |
| `manifest build` before `implement preflight` pinned a base | Refused `implementation_base_missing` | Nothing written — see [DR-15](15-committed-change-manifest.md) |

## Cleanup

`rm -rf dr01`. The test fixtures live under pytest's `tmp_path` and are
removed by pytest.

## Executable coverage

| Claim | Test |
|---|---|
| The traversal is exactly the 18 phases above | `tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript` |
| All 8 gates approved with lowercase baselines | `tests/test_integration_01_happy_path.py::test_all_eight_gates_approved_with_baselines` |
| Ends `complete` at `18/18` | `tests/test_integration_01_happy_path.py::test_workflow_ends_complete` |
| The audit chain survives the run | `tests/test_integration_01_happy_path.py::test_audit_chain_survives_the_whole_run` |
| Completion summary written once | `tests/test_integration_01_happy_path.py::test_completion_summary_written_exactly_once` |
| GREENFIELD completion establishes the baseline | `tests/test_units_baseline.py::test_n23_only_the_two_declared_flows_establish_a_baseline` |
| Gate 7 approves a real passing pytest run | `tests/test_units_implementation_evidence.py::test_d02_8_a_real_passing_pytest_suite_approves` |
| An unreviewed artifact cannot be approved | `tests/test_units_artifact_review.py::test_an_unreviewed_artifact_cannot_be_approved` |
| Identity before preflight | `tests/test_units_documented_commands.py::test_preflight_in_a_repository_with_no_workitem_asks_for_one_first` |
