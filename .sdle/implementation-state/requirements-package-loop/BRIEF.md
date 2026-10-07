# SDLE enhancement brief: requirements package, SA handoff, traceability and bounded implementation loop

## Mode

MODE: PLAN_ONLY

**PLAN_ONLY.** Re-verify §0, resolve everything this brief leaves to discovery, and produce the plan with its Codex review (§7). Do not modify product code. The plan must be executable without repeating discovery. State plainly that implementation has not started.

**PLAN_AND_IMPLEMENT.** Do the same, then execute release by release (§1) without asking for routine permission. Do not merge, publish or deploy. Work on branch `enh/requirements-package-loop`, cut from the pinned baseline, and preserve any existing user changes.

## Role

You are a senior architect and implementation agent for a deterministic workflow engine that wraps GitHub Spec Kit. Prefer small changes, explicit contracts and executed evidence. Separate facts from assumptions, and challenge unnecessary complexity, including this brief's.

## Mission

SDLE starts from supplied requirements. Make it able to:

1. **Turn a source requirements document (for example an SRS) into a uniform, validated requirements package.** A Solution Architect (SA) approves the package at an exact revision. A developer then starts from it without re-reading or re-interpreting the source.
2. **Keep every approved obligation traceable** from the package to the specification, tasks and verification evidence, so that no obligation can disappear silently.
3. **Run a bounded, evidence-checked implementation loop inside the existing `implement` phase.** The loop is implement → verify → review → converge → repair. It stops at the existing human gate.

Requirements refinement (PR #7) is merged and stabilized. This work extends its outputs and handoff; it does not redesign its algorithm.

---

## 0. Verified grounding

These facts were read at `muhammadallee/sdle-latest` commit `1c557d1` (2026-10-03).

**V** means verified by reading the code or by running it. **I** means inferred from the code but not executed.

Re-verify every row against the pinned baseline before relying on it. If a row no longer holds, record the mismatch in the ledger, adjust the plan items that depend on it, and continue.

| # | Fact | Where | St |
|---|---|---|---|
| G01 | `main` is at `1c557d1`, which merges PR #7 (requirements refinement). The state schema is `CURRENT_VERSION = "1.18"`. | `git log`; `scripts/sdle.py` | V |
| G02 | Spec Kit is pinned to v1.0.6 (`SPECKIT_SUPPORTED_VERSION`). v1.0.6 ships the commands `analyze`, `converge`, `implement`, `taskstoissues` and others. SDLE invokes constitution, specify, clarify, plan, checklist, tasks, analyze and implement. It **never invokes `converge`**. | `sdle.py`; `SKILL.md` "SpecKit Invocation"; `github/spec-kit@v1.0.6 templates/commands/` | V |
| G03 | The v1.0.6 `converge` command treats spec.md, plan.md and tasks.md (plus the constitution) as the **sole source of intent**. Its only write is appending a `## Phase N: Convergence` section to tasks.md. It leaves tasks.md byte-identical when converged, does not use git, and must run after `implement`. Extension hooks (`before_/after_converge` in `.specify/extensions.yml`) do not change what counts as intent. | `converge.md` v1.0.6 | V |
| G04 | The v1.0.6 `analyze` command is strictly read-only. Even so, `phase-execution.md` Phase 13 runs `drift rebaseline --gate gate_tasks` unconditionally, on the grounds that analyze "may have refined" tasks.md. The result is that an edit to tasks.md between `gate_tasks` approval and analyze is re-baselined without a drift re-approval or a diff. | `analyze.md` v1.0.6; `modules/phase-execution.md` | I |
| G05 | `analyze` (registry position 15) runs **before** `design_generation` (17). The design is therefore never cross-checked against spec, plan and tasks before implementation. | `SKILL.md` PHASE_SEQUENCE | V |
| G06 | tasks.md is the governed artifact of **both** `gate_tasks` and `gate_analyze`, and the drift check runs before every phase. v1.0.6 `implement` marks tasks `[X]`, and `converge` appends tasks. Both are therefore expected to trigger drift and halt for re-approval. Tests never invoke Spec Kit, so this has never been observed. | `ARTIFACT_OWNERSHIP`; `phase-execution.md` Step 0; `implement.md` v1.0.6 | I |
| G07 | `review_precondition` requires that the newest review of the artifact's **current** content is PASS. It does **not** check that the review type or actor type fits the gate: a PASS `design-review` would satisfy `gate_implement`. | `sdle.py` `review_precondition`, `REVIEW_ACTOR_TYPES` | V |
| G08 | Implementation evidence binds the WorkItem, `manifestSha256`, `baseRef` and exit code 0. The manifest lists paths and git status letters, **not file contents**. Editing an already-changed file after `manifest build` therefore leaves the evidence acceptable. | `implementation_evidence_precondition`; `cmd_manifest_build` | V (read) / I (not executed) |
| G09 | The design, code and security review modules and their agents receive spec, plan and tasks. **None of them receives the bound requirement documents.** Source fidelity is lost after the specification. | `modules/*-review.md`; `.claude/agents/sdle-*-review.md` | V |
| G10 | A review record is an artifact-level PASS or FAIL with comments and an evidence pointer. There are no finding-level records. The review types used today are `architecture-placement`, `code-review`, `design-review` and `impact-analysis`. | `cmd_artifact_review`; module text | V |
| G11 | A human-driven repair loop already exists: a rejection is followed by `remediate begin`, which is bounded by `rate_limits.max_remediation_attempts` (3) in `state.json`. | `sdle.py` remediation; `gate-protocol.md` Step 7 | V |
| G12 | `requirements/` and `guidance/` are write-fenced, and `requirements/` is also scanned as untrusted input. `refinement apply` is the only path that edits a bound document. **A model cannot write a package into `requirements/` with its file tools.** | `.claude/hooks/hooks.py` `FENCED`, `SCANNED` | V |
| G13 | The requirements binding (ADR-012), `governance_stale` and the shared-source rules (ADR-015, `refinement_shared_source`) already mark a WorkItem stale when any document it binds changes, including a shared one. | ADR-012, ADR-015; `requirements-change.md` | V |
| G14 | Refinement is WorkItem-scoped and runs before `init`. It is refused after `init` (`refinement_post_init`). | `modules/requirements-refinement.md` | V |
| G15 | Adding any field to `state.json`, including a new key under `rate_limits`, requires bumping `CURRENT_VERSION`. Under ADR-010 a state of an older schema is refused, never migrated. Commit `19e904e` prepared the repository for a first outside user. | `CLAUDE.md`; ADR-010; `git log` | V |
| G16 | The baseline in a clean Linux clone (Python 3.12.3, pytest 9.1.1) is **3,822 passed and 24 skipped in 410 s**, and `lint-skill` passes. Tests never invoke Spec Kit. There are 22 dry runs, pinned by `SCENARIO_COUNT = 22`. | `tests/test_dry_run_contracts.py`; a run of the suite | V |
| G17 | The maintenance convention for an enhancement is `.sdle/implementation-state/<name>/` holding BRIEF, PLAN, LEDGER, REPORT, `runctl.py` and `runs/`. The Codex harness is `requirements-refinement/stage2/codexrun_*.py`, with `review.schema.json` and `dispositions.schema.json`. Rejected review findings go to **`claude-review-rejections.md`**. The next ADR number is ADR-016. Known deferred gaps are in `docs/enhancements/requirements-refinement/FUTURE.md`. | repository tree | V |

---

## 1. Scope

The work ships as three releases. Each is independently mergeable, and each gets its own implementation review. The order is dependency order: R2 needs R1's identifiers, and R3 needs R2's completion predicate.

| Release | Delivers | Value if work stops after it |
|---|---|---|
| **R1** | The package contract; import and validation; SA approval; WorkItem intake per package work item; the handoff check at `init` | A uniform, SA-approved, identifiable handoff |
| **R2** | Trace coverage checks; verification dispositions; review-type enforcement; source requirements given to the reviewers; a design consistency check; evidence bound to the tested tree | An obligation cannot vanish, and a stale pass cannot carry a gate |
| **R3** | The bounded implementation loop, using the pinned `converge` | Autonomous repair up to the human gate |

**Out of scope. Do not build any of the following:**

- a new lifecycle phase or gate, or a `state.json` schema change (see D07);
- a scheduler, parallel agents, a daemon, or any generic orchestration layer;
- a finding lifecycle across rounds beyond what R3's no-progress rule needs;
- per-test result mapping for any format other than JUnit XML;
- validated links to code locations (file paths in tasks.md stay informative only);
- QA, Jira or issue-tracker integration, a walking skeleton, sprint or release management, or multi-repository work;
- Git hosting API integration to verify approver identity;
- visibility across branches or worktrees (FUTURE.md §3 stands);
- any Spec Kit upgrade, fork or template override.

---

## 2. Owner decisions (settled)

These are settled unless the owner overrides one in this section before execution. Do not reopen them. If evidence shows a decision cannot work, stop and escalate with that evidence.

**D01: one package work item is one WorkItem.**
- Intake creates one SDLE WorkItem per package work item (`WI-nnn`). Each WorkItem binds its work item's `requirements.md` (as the primary document) plus the shared package files that file cites.
- A full SRS never authorizes implementation in a single WorkItem.
- In the documentation, write "package work item (`WI-nnn`)" for the requirement unit and "WorkItem" only for the SDLE runtime unit.

**D02: package format.** Adopt the normalized package shape the owner already uses (the owner's reference SRS package).
- Before PLAN_AND_IMPLEMENT, the owner places one reference package and its "Downstream Consumer Context" document in `docs/enhancements/requirements-package/reference/`.
- **Core files** are always present: the overview, traceability, open issues, and one `work-items/WI-nnn-<slug>/requirements.md` per work item, each carrying a readiness verdict.
- **Supporting files** (system context, shared requirements, access control, business rules, notifications, integrations, data, NFRs) are generated only when the source or an approved clarification warrants them. The overview names each absent supporting file and gives the reason. Never generate an empty file.
- If the reference is not in the repository, PLAN_ONLY proposes a contract and marks it an owner decision that blocks R1.

**D03: identifiers.**
- The ID grammar (the prefixes) is declared once, in the package manifest.
- An ID is immutable once approved and is never reused.
- If a requirement is split, merged, or moved to another work item, its ID is retired and the replacement records `supersedes:`. This is required because the reference format encodes the work item in some IDs.
- The engine extracts IDs by the declared grammar only, never by matching wording.

**D04: location and writer.**
- Source documents stay where they are and are never modified.
- The package lives at `requirements/packages/<package-id>/`, which is already write-fenced and scanned.
- The orchestrator drafts the package in an unfenced staging directory. `package import` then validates it, copies it into place and records its digest.
- The fence is never weakened.

**D05: SA approval.**
- **Mechanism.** Approval is a repository-level, engine-written, append-only ledger bound to the package digest. Each record holds the package id, digest, approver name, role, timestamp, approval wording and the hash of the previous record.
- **Not a lifecycle gate.** The SA is not in the developer's session, and no existing gate approves requirements: the first gates approve the constitution and the architecture placement.
- **Identity.** The engine records the approver's name; it cannot verify who typed `approve`. This is the same boundary as every gate, and it is documented as such.
- **Recommendation, in documentation only.** Protect the package and the ledger with CODEOWNERS and branch protection, so that the Git host supplies real identity.
- **What is displayed.** The approval display shows the overview, every work item's `requirements.md`, the open issues and the readiness verdicts. A re-approval also shows the diff since the last approved revision. Supporting files are listed with their digests and shown on request. ADR-016 records this as a deliberate, scoped relaxation of invariant 4.

**D06: handoff check.**
- `init` refuses `package_approval_missing` or `package_approval_stale` when a WorkItem's bound package files do not match an approved revision.
- `init` refuses `package_workitem_not_ready` for a work item marked NOT READY.
- A package change after `init` is already caught by `governance_stale` and routed through `requirements-change.md`.
- Refinement of an approved package file is allowed. It makes the approval stale, and the report says so.

**D07: no state schema change.**
- Every new record is an engine-written file beside `state.json` (the precedent is `requirements.json` and the refinement record), or a repository-level file.
- The loop's iteration limit lives in the loop record, not in `state.rate_limits`. Adding a key there bumps the schema and strands in-flight WorkItems (G15).
- If a schema change proves unavoidable, stop and escalate.

**D08: convergence.**
- Invoke the pinned `converge` command to compare spec, plan and tasks against the code.
- Do not try to make converge read the package: its contract fixes spec, plan and tasks as the sole intent, and hooks do not change that.
- Source fidelity is enforced by the engine's trace coverage check (R2).
- **tasks.md mutation policy.** During `implement`, the engine accepts exactly two kinds of change to tasks.md: checkbox ticks on existing tasks, and appended `## Phase N: Convergence` sections. It verifies this structurally, audits it, and re-baselines the drift of `gate_tasks` and `gate_analyze`. Any other change is drift and goes to a human.

**D09: loop limits.**
- By default the loop may run 3 iterations per `loop begin`. The default is configurable in `.sdle/config.json`.
- The loop stops for no progress the first time a progress digest repeats.
- The same rules apply in every flow.

**D10: verification mapping.**
- A per-criterion result comes only from JUnit XML, when the runner emits it and the test names cite criterion IDs.
- Otherwise the disposition is `suite-pass-unmapped`. It is displayed separately and is never shown as "verified".
- It is non-blocking by default. The policy can make it blocking.

**D11: untraced tasks.**
- A task that cites neither a source ID nor an engineering obligation tag is listed at the gate, but is not blocking.
- An in-scope acceptance criterion with no task and no approved disposition **is** blocking.

---

## 3. R1: Requirements package and SA handoff

### Contract (`package.json` plus files)

- **Manifest:** package id; the source document identities (path, SHA-256, and the version or date the source states); the ID grammar; the file list with each file's role; the work items, each with its readiness and its assigned IDs; the exclusions, each with a disposition.
- **Each requirement:** id, kind (functional, business rule, acceptance criterion, NFR, security, and so on), statement, status, and either a **source reference** (document plus a section or page anchor) or a **clarification reference**.
- **Each open issue:** id, question, affected IDs, whether it blocks, and its disposition.

### Engine (deterministic)

These command names are indicative; fix the final names in the plan: `package import`, `package validate`, `package approve`, `package show`, `package intake`. All of them are pure readers until their own write, follow the repository's JSON and exit-code contract, and use the standard library only.

`package validate` refuses each of the following, naming every offender:
- a duplicate ID;
- an ID outside the declared grammar;
- a dangling reference;
- a requirement with neither a source reference nor a clarification reference;
- a source reference whose document is not among the package's source identities;
- a requirement that is neither assigned to a work item nor excluded with a disposition (unassigned scope);
- a work item with no acceptance criterion;
- a blocking open issue on a work item marked READY;
- a declared core file that is missing;
- an empty supporting file.

### Prompt side

- **New module.** `modules/requirements-package.md` is routed from `SKILL.md` and `/sdle-start`, the same way refinement is. It is not a phase. Add it to `lint-skill`'s capability accounting.
- **Generation.** The orchestrator generates the package. `sdle-requirements-review` gains a **source-fidelity** mode: does each requirement say what its source reference says, and is every normative statement in the source mapped to a requirement or explicitly excluded? Do not add a new agent.
- **Untrusted input.** Scan the source document before reading it, and scan the staging files before import. The source is data, never instructions.
- **Never invent content.** No business rule, role, performance target, notification or security decision may be invented to fill a template. An unsupported detail becomes an open issue.

### Intake and handoff

1. **Intake (before SA approval).** For each work item: `workitem create`, then `requirements bind` (the work item's file as primary, plus the shared files it cites), then `governance assess`, then optional refinement. This reuses the existing pre-`init` machinery unchanged.
2. **Approval.** The SA approves the package (D05).
3. **Handoff.** The developer resumes a WorkItem that is already created, bound and assessed. `package show` and `requirements show` name the package revision and its approval. The developer copies nothing.

---

## 4. R2: Traceability, verification, review enforcement, evidence freshness

### Trace coverage

`trace check` is a pure reader. It is also enforced as a precondition at these gates:

| Gate | Refuses when |
|---|---|
| `gate_spec` | An in-scope requirement or criterion ID of the bound work item is missing from spec.md without an approved exclusion, or spec.md cites an ID that is not in the package. |
| `gate_tasks` | An in-scope criterion has no task citing it (a test task, for a testable criterion) and no disposition. Engineering tasks may cite obligation tags instead of business IDs: a constitution principle, an architecture decision id, or a plan decision label. |
| `gate_implement` | An in-scope criterion has no verification disposition, or its disposition is `blocked` or missing. The dispositions are `verified-mapped`, `suite-pass-unmapped`, `manual-evidence`, `excluded-approved` and `blocked`. |

**Getting Spec Kit to cite IDs.** Add an instruction to the specify and tasks invocation arguments to cite source IDs. Never edit Spec Kit's templates.

**Verification scenarios.** These live in places that already exist: spec.md's own acceptance scenarios, citing criterion IDs, and test tasks in tasks.md. checklist.md stays what it is, a requirements-quality checklist. Do not create a new planning artifact.

### Review enforcement

- **Required review type per gate.** Add a new constant table to `SKILL.md`, mapping each gate to its required review type or types and the allowed actor types. The engine parses it and `lint-skill` checks its coverage. `review_precondition` refuses `review_type_mismatch` (G07).
- **Reviewers get the source.** The code, design and security modules and agents receive the bound package files and the trace report. Their findings cite obligation IDs.
- **Structured findings.** `artifact review` accepts `--findings <json>` (id, severity, location, obligation references, disposition) and stores it in the review's evidence. A PASS is refused while any blocking finding is open.

### Design consistency

The analyze phase runs before design (G05), so the design review at `gate_design` checks the design against the package, spec, plan, tasks and the approved placement. A conflict with an approved architecture decision is a blocking finding. Do not add a new phase.

After reproducing G04, remove the unconditional `gate_tasks` re-baseline after analyze.

### Evidence freshness

- **Tree digest.** `manifest build` records a `treeDigest`: the tree hash of the working tree, including untracked files that are not ignored, computed through a temporary index (`GIT_INDEX_FILE`, then `git add -A`, then `git write-tree`). It is taken before and after the test run. If the two differ, the evidence status is `invalid_changed_during_run`.
- **Other bindings.** The evidence also records the test command, the runner, the package digest and the bound-requirements digest.
- **At the gate.** The gate recomputes the digest. A mismatch refuses `test_evidence_stale` with `mismatch: treeDigest`.
- **Without git.** Fall back to a hash over the files the manifest lists, and say so in the manifest.
- **History.** Historical evidence is never deleted.

---

## 5. R3: Bounded implementation loop

### Placement and record

- The loop runs **inside the existing `implement` phase**, after `implement preflight` and before advancing to `gate_implement`.
- `loop begin` creates `workitems/<id>/.sdle/implementation-loop.json`. Only the engine writes it, and it is refused if it is not a file the engine wrote, the same rule as `requirements.json`.
- The record holds the limit, the package revision, the base ref, the iterations, each iteration's step state, the progress digests and the stop reason.

### Steps per iteration

The engine enforces this order, so that no step can run twice without the one before it.

1. **Implement.** Run `implement`: on the first iteration over the tasks, afterwards over the open tasks the loop appended.
2. **Reconcile tasks.** `tasks reconcile` applies the D08 mutation policy.
3. **Build the manifest.** `manifest build` produces fresh, tree-bound evidence (R2).
4. **Independent review.** Hand the review to `sdle-code-review` in a fresh context. Give it the diff, the package files, spec, plan, tasks and the **raw** test evidence, never the implementer's summary. Record the result with `artifact review --type code-review --findings …`.
5. **Converge.** Run `converge`. It may append tasks, which go through `tasks reconcile` again.
6. **Trace.** Run `trace check`.
7. **Record.** `loop record` evaluates the completion predicate and the progress digest, then returns `continue` or a stop reason.

### One completion predicate

Factor the `gate_implement` preconditions into a single pure function, for example `implementation_ready(paths, state) -> list[unmet]`. `gate approve` and `loop record` both call it. The conditions are:

- the evidence is fresh and the tests passed;
- the newest review is a current PASS of the required type;
- trace coverage is complete;
- no blocking finding is open;
- the last converge left tasks.md unchanged.

### Stop reasons

The loop stops for one of these reasons, recorded with the next action:

| Stop reason | When |
|---|---|
| `ready_for_gate` | The completion predicate passes |
| `limit_exhausted` | The iteration limit is reached |
| `no_progress` | The progress digest repeats. The digest covers the set of failing tests, the open blocking finding fingerprints and the uncovered IDs. Appending tasks is not progress. |
| `environment_blocker` | The runner is missing or unavailable, or a dependency is down. This is never a pass. |
| `ambiguity` | A finding classified as requirement ambiguity routes to the requirements-change process. |
| `test_expectation_change` | A test file is deleted, the set of JUnit test cases shrinks, or an ACC-tagged test is removed or its assertion is changed. A human decides. |
| `tasks_drift` | A tasks.md change falls outside the mutation policy. |
| `interrupted` | The run stopped before the iteration completed. |

Each failure is classified as an implementation defect, a test defect, a requirement ambiguity or an environment blocker. The model proposes the class; the engine records it. A repair to test code that keeps the expected behavior proceeds within scope. Anything that changes expected behavior or weakens required coverage stops the loop for a human.

### Resume

- On resume, `loop show` names the last completed step. The step state machine prevents duplicate evidence and duplicate convergence tasks.
- A snapshot whose `treeDigest` no longer matches the tree is stale and is re-run, never reused.

### Before the gate

Show the following, then hand over to the existing gate protocol:

- scope coverage, from the trace report;
- the tree digest and the base ref;
- the test result;
- resolved and open findings;
- the unverified and unmapped criteria;
- the stop reason.

A loop that ends `ready_for_gate` means ready for human review. The loop never approves, omits or skips a gate.

---

## 6. Engineering rules (all releases)

- **Preserve the invariants.** All eight invariants in `CLAUDE.md` hold, as do the exit-code contract (0 success, 1 refused, 2 usage, 3 integrity), JSON on stdout, the single writer, refuse-don't-warn, and a standard-library-only, cross-platform engine.
- **Every new refusal** has a stable reason code, a message naming the way out, and an entry in `docs/troubleshooting/`.
- **Deterministic first.** Structural facts (IDs, digests, coverage, step order, task deltas) belong to the engine. Semantic adequacy belongs to a review. A valid link proves nothing about satisfaction, and the documentation must say so.
- **New constants** go in `SKILL.md` tables or `sdle.py`, exactly once, with `lint-skill` rules for any cross-file sync they create.
- **Repository-level records** (the package approval ledger) follow ADR-013's precedent: derived from `project_root`, engine-written, added to `FENCED` and to the dirty-tree guard's `SDLE_OWNED_PREFIXES`, and versioned.
- **ADR-016** records the package and handoff decisions. **ADR-017** records trace, evidence and the loop. State the enforcement split explicitly, as ADR-007 §3 does: what the engine guarantees, what the Claude Code runtime guarantees, and what is convention only (approver identity, delegation, `--actor-name`, the assessor not seeing earlier verdicts).

---

## 7. Execution protocol

### Order

1. **Baseline.** Pin the commit. Re-verify §0. Run the full suite and `lint-skill` in the foreground through the existing `runctl.py` pattern, and record the results in `.sdle/implementation-state/requirements-package-loop/`.
2. **Reproduce the inferred rows (G04, G06, G08)** with throwaway tests. Each outcome either confirms the plan item or changes it, and the ledger records which.
3. **Plan.** Write `PLAN.md`. For each release, give the exact files and functions, the behavior reused, the changes, the refusals (code and exit status), the tests, the regression risks, the documentation affected, and the commit boundaries.
4. **Codex plan review.** Two rounds over the **whole** plan. Do not run a separate debate per milestone.
5. **PLAN_ONLY stops here.**
6. **Each release:** implement, run targeted tests, run the full suite and `lint-skill`, run two rounds of Codex implementation review over the actual diff and test evidence, record dispositions, then commit. A material change after the final review gets a review of the changed scope.
7. **End-to-end run (AS-30).**
8. **Final report.**

### Codex

- **Reuse the harness** in `requirements-refinement/stage2/` (`codex exec --sandbox read-only --ephemeral --json` with the review and dispositions schemas). Copy it into this enhancement's directory; do not move it into product code.
- **Before starting:** check `codex login status` and record the Codex version.
- **Never simulate a Codex review** and never substitute a Claude agent for one. If Codex is unavailable, preserve the review package, continue any work that does not cross a review boundary, and report exactly which boundary is blocked.
- **Rejected findings** go in a new section of `claude-review-rejections.md`, with the rationale. Do not create a second rejections file, and do not reject a valid finding to meet a round limit.

### Tests

- Run the full suite in the foreground at the baseline and at the final handoff. If a local full run is interrupted, a CI run on the branch counts **only** when it is recorded with the run URL and the commit.
- Never skip or weaken a failing test.
- Tests never invoke Spec Kit (simulated generation, fixtures built at runtime), as today. Any claim about real Spec Kit behavior needs AS-30's evidence and must be labelled that way.
- New dry runs (at least one for the package and handoff, one for the loop) update `SCENARIO_COUNT` and `docs/dry-runs/verification-matrix.md`.

### Documentation

- Getting Started gets a package-and-handoff section and a loop section.
- Write the ADRs, the troubleshooting entries, and the `docs/lifecycle/` text for the loop.
- Update `requirements-change.md` for an approval that has become stale.
- Correct any existing statement the shipped behavior makes false. Wider tutorial and reference rewrites are out of scope; list them as open items.

### Autonomy

- **Decide alone:** naming; file layout within §2; refactors local to the change; test design; ordering within a release.
- **Escalate:** anything contradicting §2; a state schema change; weakening any fence, refusal or test; a new phase, gate or agent; any change to Spec Kit; added scope; an unresolved material disagreement with Codex.
- **How to escalate:** state the context, the options, a recommendation and the impact. Continue unrelated safe work while blocked.

### Ledger

Keep `LEDGER.md` short, in fixed sections: Current status · Decisions · Defects · Review dispositions · Test runs · Next action. Commit the run records. Commit raw logs only for failing runs and final runs.

---

## 8. Acceptance scenarios

Each scenario needs a test, or for AS-30 a recorded transcript, that is cited in the final report. Adapt the tests to the actual implementation; do not mirror internal code.

**R1: package and handoff**

- **AS-01** `package validate` refuses duplicate IDs, an ID outside the grammar, dangling references, and a requirement with no source or clarification reference.
- **AS-02** A requirement that is neither assigned nor excluded is refused and named.
- **AS-03** An unwarranted supporting file is absent, the overview gives the reason, and no empty file exists.
- **AS-04** An NFR with no source or clarification reference is refused by the engine. An unsupported claim that does cite a source is caught by the fidelity review.
- **AS-05** A file is edited after approval: `init` refuses `package_approval_stale`, and the approval history is intact.
- **AS-06** `init` of a work item marked NOT READY refuses.
- **AS-07** Refinement on an approved package file applies, makes the approval stale, and says so.
- **AS-08** The developer resumes with nothing copied: `package show` names the revision and the approval.
- **AS-09** The source document's bytes are unchanged throughout.

**R2: trace, review, evidence**

- **AS-10** A source requirement is omitted from spec.md: `gate_spec` refuses.
- **AS-11** spec.md or tasks.md cites an unknown ID: refused.
- **AS-12** A legitimate engineering task cites an obligation tag: accepted. An untraced task is listed but does not block.
- **AS-13** The wrong review type is on the manifest: `review_type_mismatch`.
- **AS-14** A source file is edited after a passing test run: `test_evidence_stale` with `treeDigest`.
- **AS-15** An uncommitted change and an untracked new file change the digest. An ignored file does not.
- **AS-16** The tree changes during the test run: the evidence is `invalid_changed_during_run`.
- **AS-17** The design conflicts with an approved architecture decision: a blocking finding at `gate_design`.
- **AS-18** An in-scope criterion has no test task and no disposition: `gate_tasks` refuses.
- **AS-19** `suite-pass-unmapped` is shown separately and never as verified.

**R3: loop**

- **AS-20** The loop exits `ready_for_gate` only through the same predicate `gate approve` uses.
- **AS-21** A second converge without an implement step in between is refused, and no duplicate tasks result.
- **AS-22** A tasks.md change outside the mutation policy stops the loop with `tasks_drift`.
- **AS-23** A repeated progress digest stops the loop with `no_progress`.
- **AS-24** The iteration limit stops the loop with `limit_exhausted`, a reason and a next action.
- **AS-25** Interrupting after `manifest build` and before `loop record`, then resuming, produces no duplicate evidence and no duplicate tasks, and the stale snapshot is detected.
- **AS-26** An unavailable runner stops the loop with `environment_blocker`, never with a pass.
- **AS-27** Deleting a test or removing an ACC-tagged test stops the loop with `test_expectation_change`.
- **AS-28** A human rejection at `gate_implement` follows the existing remediation path, with its own counter.
- **AS-29** The loop never calls `gate approve`. After `ready_for_gate`, the status is awaiting approval.

**End to end**

- **AS-30** One real run in a scratch repository with Spec Kit v1.0.6: a small SRS becomes a package, the SA approves it, and one work item goes through the loop to `gate_implement`. Record it as a new dry run. **Known limit:** Claude Code loads project hooks only from its launch directory, so record whether the scratch repository's hooks were active. Never present a run without hooks as one with hooks.

---

## 9. Deliverables

**PLAN_ONLY:**
- the re-verified §0, with mismatches;
- the outcomes of reproducing G04, G06 and G08;
- the artifact and authority map (requirements define behavior; the constitution constrains engineering; placement decisions constrain ownership; downstream artifacts elaborate, and a conflict is resolved, never silently overwritten);
- `PLAN.md` per release;
- the Codex plan-review ledger and dispositions;
- the compatibility and test strategy;
- any open owner decisions;
- the statement that implementation has not started.

**PLAN_AND_IMPLEMENT:** all of the above, plus:
- the code, templates and docs per release;
- the executed test evidence (the baseline and final full suites, `lint-skill`, and the AS-01 to AS-30 mapping);
- AS-30's transcript;
- the review dispositions;
- a final report of what changed, what is enforced by the engine, what by the runtime and what is convention only, and the limitations and remaining human decisions.

Do not claim guaranteed correctness, authenticated identity, or convergence beyond what the evidence shows.
