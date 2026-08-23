# T00 Implementation Handoff — Attempt a01

**Phase:** T00 — Baseline Freeze and Transition Safety Net
**Attempt:** 01
**Implementer context:** fresh/isolated
**Status recommendation:** IMPLEMENTED

## Inputs read from disk

| Input | Used for |
|---|---|
| `docs/transition/transition.md` §6, §18, §24.3, §25, §19, TP-003 | phase spec, capability matrix, implementer duties, durable statuses |
| `docs/transition/phases/T00-plan.md` (whole file) | required document shape, completeness rules, failure modes F1–F9, acceptance criteria A1–A14 |
| `docs/transition/phases/T00-blocker.md` §8, §9 | carried-forward findings; RESOLVED guard fix, not revisited |
| `docs/transition/progress.md` | current T00 row, baseline SHA |
| `CLAUDE.md` | product invariants and cross-file sync rules |
| `scripts/sdle.py`, `.claude/skills/sdle/SKILL.md`, `.claude/skills/sdle/templates/state.json`, `.claude/settings.json`, `.claude/hooks/hooks.py`, `tests/`, `.gitignore`, `tools/transition/agent_guard.py` | primary evidence for the inventory |
| `git show HEAD:.github/workflows/ci.yml` | CI Python pin and OS matrix (Read tool cannot open `.github/`) |

## Changes made

Evidence-only. Four new files, one edited row. **No product file was created,
modified or deleted.**

| Path | Action | Content |
|---|---|---|
| `docs/transition/baseline.md` | CREATE | The T00 deliverable: 7 top-level sections in plan order — identity, environment, verification results, 14-part capability inventory (183 rows), 47-row regression matrix, 4 known baseline conditions, 5 explicit-preserve decrees |
| `docs/transition/phases/T00-checkpoint-a01-01.md` | CREATE | Milestone: verification results recorded |
| `docs/transition/phases/T00-checkpoint-a01-02.md` | CREATE | Milestone: capability inventory complete |
| `docs/transition/phases/T00-checkpoint-a01-03.md` | CREATE | Milestone: baseline.md complete + self-check results |
| `docs/transition/phases/T00-handoff-a01.md` | CREATE | This file |
| `docs/transition/progress.md` | MODIFY | T00 row only: `PLANNED`→`IMPLEMENTED`, Attempt `0`→`1`, Handoff, Commit `UNCOMMITTED`, Tests, Notes |

## Deliberate behavior changes

**None.** T00 is evidence-only by contract §6 ("No product behavior changes")
and by the plan's Behavioral delta section ("This is not an approximation").
`git status --porcelain` shows zero lines beginning with `M` or `D`.

## Preserved behavior / invariants

Everything, without exception. Specifically re-confirmed by observation this
attempt:

- the 18-phase sequence and 8 approval gates (unchanged in `SKILL.md`; lint-skill green);
- the repository-global `.workflow/` runtime location and lock behavior;
- current Spec Kit feature behavior and `current_feature_id` as workflow identity;
- deterministic Python core, JSON stdout envelope, exit codes 0/1/2/3;
- atomic writes, audit hash chain, artifact SHA fingerprints, drift detection;
- rate limits, checkpoint/idempotency, retry and remediation caps;
- dirty-tree guard, untrusted-content scan, secrets scan, test evidence, `implementation_base_ref`;
- cross-platform launchers `scripts/sdle.sh` and `scripts/sdle.ps1`;
- the five `CLAUDE.md` non-negotiables;
- all 230 collected tests, unweakened, and lint-skill at 22 PASS checks.

## Test changes and TP-003 classification

| Test | Category | Rationale |
|---|---|---|
| *(none)* | N/A | Zero tests added, deleted, modified or skipped. T00 changes no behavior, so no existing test can legitimately fail because of it, and there is nothing a new test could assert — see plan sections "Existing tests affected" and "New tests required". TP-003's three categories therefore have no applicable member; this is not a fourth category, it is an empty set. |

Nothing under `tests/` differs from HEAD. Collected count is still **230**.

The one failing existing test is dispositioned under plan failure mode **F1** as
`ENVIRONMENT_FLAKE`, which is a *plan* failure-mode classification, not a TP-003
category. Per the plan, TP-003 categories do not apply to T00; the plan's own
two-branch rule does, and branch 1 (environment-induced, non-deterministic)
applies. See baseline §6.1.

## Commands actually run

Every row below was executed in this implementer context and its output
observed. `NOT_RUN` means exactly that.

| Command | Result | Evidence/summary |
|---|---|---|
| `git rev-parse HEAD` | exit 0 | `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` — MATCH vs contract baseline |
| `git rev-parse --abbrev-ref HEAD` | exit 0 | `transition/workitem-v1` |
| `git status --porcelain` | exit 0 | 7 lines, all `??`; no `M`, no `D` |
| `git branch -a --contains HEAD` | exit 0 | `transition/workitem-v1`, `remotes/origin/wave-a-deterministic-core` |
| `python --version` | exit 0 | `Python 3.14.6` |
| `python -m pytest --version` | exit 0 | `pytest 9.1.1` |
| `python -c "import platform; print(platform.platform())"` | exit 0 | `Windows-11-10.0.26200-SP0` |
| `git show HEAD:.github/workflows/ci.yml` | exit 0 | pin `python-version: "3.11"`; matrix `[ubuntu-latest, windows-latest]`; steps lint-skill, pytest, both launchers |
| `python scripts/sdle.py lint-skill` | **exit 0** | 22 checks, 22 PASS, `"ok": true`, `"failed": []`; full output quoted in baseline §3.1 |
| `python -m pytest -q --collect-only` | exit 0 | `230 tests collected in 0.09s` |
| `python -m pytest -q --tb=line -rf` | **exit 1** | `1 failed, 229 passed in 340.51s (0:05:40)`; failing node id `tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript`; `PermissionError: [WinError 5]` at `scripts/sdle.py:463` |
| `python -m pytest -q --tb=line -rf tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript` (F1 re-run 1) | exit 0 | `1 passed in 9.45s` |
| same node id (F1 re-run 2) | exit 0 | `1 passed in 9.77s` |
| same node id (F1 re-run 3) | exit 0 | `1 passed in 35.96s` |
| `python tools/transition/validate.py` | **exit 0** | `TRANSITION_VALID: complete=0/12 next=T00` (run before and after the `progress.md` edit) |
| `python scripts/sdle.py constants` | exit 0 | 13-row `version_chain`, `1.0→1.1` … `1.12→1.13` |
| Linux CI (`ubuntu-latest`) | **NOT_RUN** | Branch `transition/workitem-v1` is local-only; no CI run for this SHA on this branch is observable from this context. Contract §6 item 2 says *if available*. No outcome predicted. |
| Windows CI (`windows-latest`) | **NOT_RUN** | Same reason. No outcome predicted. |

**Targeted tests during development (§24.3 item 5):** the three F1 re-runs above
are the targeted runs for this phase. No other targeted run was needed, because
T00 modifies no code that any test exercises.

**Local-vs-CI evidential weight:** local is CPython 3.14.6 / pytest 9.1.1 on
Windows 11; CI pins CPython 3.11 on `[ubuntu-latest, windows-latest]`. The local
results are valid evidence **for this environment only** and say nothing about
either CI platform. Baseline §2 states this explicitly.

## Git evidence

- **HEAD:** `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` (unchanged; equals the contract baseline SHA)
- **Working tree:** 7 untracked entries, all `??`. Zero tracked files modified or deleted. Nothing staged.
- **Diff scope:** empty. `git diff` against HEAD is empty for every tracked path, including every file listed in `docs/transition/control-plane.sha256` — the validator raises no `control-plane hash mismatch` (exit 0).
- **Commit:** none. `progress.md` Commit column records `UNCOMMITTED` per contract §25 rule 7. No SHA was invented.
- **Top-level directories:** `docs/ requirements/ scripts/ tests/ tools/`. No new top-level directory. `workitems/` and `.sdle/` are absent (`ls` reports "No such file or directory" for both).

## Plan divergence found (§24.3 item 2)

The plan was re-verified against repository evidence rather than trusted. One
ledger row does not match observation; it is reported, not silently absorbed,
and the plan was **not** edited.

| Plan ledger claim | Observed this context | Handling |
|---|---|---|
| "The CLI exposes 21 top-level subcommands, several with nested subcommands" | **33** `subparsers.add_parser(` registrations and **32** nested registrations. Of the 33, 16 are groups requiring a nested subcommand, so 49 command paths are directly invocable. `21` matches neither count. | Followed the plan's *operative* completeness rule ("every `add_parser` name in `scripts/sdle.py`, including nested subcommands, each as its own row"), which is unambiguous regardless of the ledger number. §4.1 has 65 rows: 33 + 32. |
| Failing node id is `tests/test_integration_02_to_05.py::test_04_unapproved_gates_are_never_drift_checked` | This context observed `tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript` — a **different** node id, same signature (`WinError 5`, `os.replace`, `scripts/sdle.py:463`) | Strengthens rather than contradicts the plan's INFERRED environmental classification: the victim moves between unrelated tests. F1 was applied to the node id actually observed. Recorded in baseline §6.1. |

All other ledger rows were re-verified and hold: HEAD SHA, branch, remote
containment, clean tracked tree, lint-skill 22 PASS / exit 0, 230 collected,
`1 failed / 229 passed`, exit-code constants at `scripts/sdle.py:37-40`, 25
top-level state fields with 8 `approvals` keys, 4 wired hooks, 13 migration rows,
validator exit 0, CI pin and matrix, control-plane manifest exclusions.

## Resolution of the three named findings

1. **Baseline suite not deterministically green.** Reproduced (`exit 1`,
   `1 failed, 229 passed`). Plan F1 followed exactly: only the failing node id
   re-run, 3 times, all passed ⇒ **`ENVIRONMENT_FLAKE`**; both the failing and
   the passing outputs are recorded verbatim in baseline §6.1; the suite is
   treated as green **with the caveat recorded**, and the raw exit code 1 is
   reported unaltered. `write_atomic` was **not** touched (plan F2). No blocker
   was warranted, because the 3× deterministic-fail branch did not occur.
2. **lint-skill "19 phases" vs denominator 18.** **RESOLVED, not smoothed over.**
   Both numbers appear in baseline §6.2 with the quoted tables. 19 = PHASE_SEQUENCE
   row count including the terminal pseudo-phase `` `complete` ``
   (`SKILL.md:110-111`); 18 = `Constants.phase_count`, which excludes it by
   construction (`scripts/sdle.py:322-325`) and is exactly what the denominator
   check compares against (`scripts/sdle.py:3144-3155`). `complete` is terminal,
   not a workflow phase (`NEXT_PHASE` → *(terminal)*; `scripts/sdle.py:2338`
   comment "`complete` is not restartable"). Plan unknown **U3 is closed**.
   There is no defect and nothing to fix.
3. **CI is NOT_RUN.** Recorded as `NOT_RUN` with the reason in baseline §3.4 and
   §3.5 and in the command table above. Non-blocking under contract §6 item 2
   ("if available") and plan failure mode F8. Baseline §2 states that local
   results (Python 3.14.6 / pytest 9.1.1, Windows) are valid for this environment
   only while CI pins 3.11 across two platforms. No CI outcome is predicted
   anywhere, per contract §1 item 15.

## Known limitations / risks

- The suite is not deterministically green on this machine. Any future phase
  running it here should expect an occasional `WinError 5` from
  `write_atomic` and apply F1 rather than reading it as a regression. Root cause
  remains `UNKNOWN`; fixing it is a separate human decision, not phase work.
- `docs/transition/progress.md` is untracked, so it has no Git safety net. Its
  only integrity gate is `python tools/transition/validate.py`, which was run
  immediately after the edit and exited 0.
- The three `ADD / ENFORCE` rows of contract §18 are `NO_ANCHOR` in baseline §5
  because the capabilities are **absent at this baseline**. That is a real
  finding, not padding: T06 has no regression net to inherit for them.
- Two further `NO_ANCHOR` rows exist and are deliberate: `.gitignore` content
  has no test, and `checkpoint set/get/clear` has no dedicated test.
- The residual noted in blocker §9.5 stands: the planner/verifier Bash filter
  does not stop interpreter-mediated writes. This attempt did not rely on that
  gap — every file above was written with the `Write`/`Edit` tool, so
  `agent_guard.py` evaluated each write and allowed it. No sanctioned write was
  refused.

## Claims for verifier to independently check

Re-run these rather than trusting the table above.

1. `git status --porcelain` — every line `??`; no `M`, no `D`. (A4)
2. `git diff HEAD --stat` on tracked paths — empty; nothing under `scripts/`, `tests/`, `.claude/`, `.github/` differs from HEAD. (A4, A13)
3. `python tools/transition/validate.py` — exit 0, `TRANSITION_VALID`, no `control-plane hash mismatch`. (A11, A13)
4. `python scripts/sdle.py lint-skill` — exit 0, 22 PASS, `"failed": []`. (A3)
5. `python -m pytest -q --collect-only` — 230. (A14)
6. `python -m pytest -q --tb=line -rf` — expect green **or** a `WinError 5` flake at `scripts/sdle.py:463`; if the latter, F1 applies, and note the victim node id will likely differ again. (A3)
7. `grep -n "^## " docs/transition/baseline.md` — exactly 7 sections in plan order. (A1)
8. `grep -c "^### 4\." docs/transition/baseline.md` — 14, headings matching contract §6 item 3 order. (A2)
9. Parse baseline §4 tables — 183 rows, every row 5 cells, **no blank cell**. (A2)
10. Parse baseline §5 column 2 against contract §18 — all 31 labels present **exactly once**, verbatim, none invented; 16 additional `NOT_IN_S18` rows; 47 total. (A5, A6)
11. Baseline §5's declared vocabulary-mapping rule — check the three `ADD / ENFORCE` rows map to ADAPT/T06 with `NO_ANCHOR`, and that no §18 label was reworded. (A5)
12. Baseline §1 — observed HEAD SHA plus an explicit MATCH verdict. (A7)
13. Baseline §3.4/§3.5 — both CI rows `NOT_RUN` with a reason; no predicted CI result anywhere in `baseline.md` or this handoff. (A8)
14. Baseline §6 — all four required known conditions present. (A9)
15. Baseline §7 — all five contract §6 explicit-preserve items, each paired with the permitted phase. (A10)
16. `ls -d */` — `docs/ requirements/ scripts/ tests/ tools/`; `workitems/` and `.sdle/` absent. (A12)
17. Scope-exclusion sweep — no T01–T11 artefact anywhere in the diff: no `workitem` CLI subcommand, no `RepositoryContext`/`WorkItemContext`, no `.sdle/` config, no flow-model change, no `.gitignore` edit.
18. `progress.md` T00 row — 9 columns, `Plan` = `docs/transition/phases/T00-plan.md`, `Handoff` = this file (which exists), `Commit` = `UNCOMMITTED`, no pipe character in any cell. (A11)

## Blocker

**None.** No material decision is required. The `agent_guard.py` blocker is
`RESOLVED` (blocker §9) and was not revisited by this attempt. The `write_atomic`
flake is a recorded baseline condition owned by the human as separate product
work, not a T00 blocker: plan F1's blocker branch requires three deterministic
failures, and all three re-runs passed.
