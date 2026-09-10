# SDLE-DEFECT-STABILIZATION-01 — Execution Record

The iteration-local record the stabilization plan's §7 requires. It states what
was actually run and what actually happened. Nothing here is inferred from an
earlier count, and nothing is presented as passing without the command that
passed.

**Resume instruction.** Read the plan and this record, inspect the working tree
and the last commit in the task table, then continue the first task whose status
is not PASS. Re-validate an assumption only where the checkout or its inputs
changed since it was recorded.

## Identity

| Item | Value |
|---|---|
| Plan | `sdle-defect-stabilization-plan.md`, supplied by the maintainer; deliberately not committed on this branch |
| Branch | `fix/defect-stabilization` |
| Starting commit | `e14c4024a8aa459a9acf389f765e29471c706d06` (`main`). Newer than the plan's reviewed commit `17adae4`: transcripts 10–13 and `tests/test_integration_10_to_13.py` already existed |
| Verified final commit | _recorded at T07_ |
| Local OS | Windows 10 Home 10.0.19045 |
| Local Python | 3.13.0. CI pins 3.11; no 3.11 interpreter is installed locally (`py -3.11` → "No suitable Python runtime found") |
| SpecKit exercised | **v1.0.6**, fetched with `uvx --from git+https://github.com/github/spec-kit.git@v1.0.6` into disposable projects. The machine's installed `specify-cli 0.15.0` was never modified |
| CI matrix | `.github/workflows/ci.yml`: `ubuntu-latest` and `windows-latest`, Python 3.11, `lint-skill`, `pytest -q`, then `sh scripts/sdle.sh lint-skill` (POSIX) / `./scripts/sdle.ps1 lint-skill` (PowerShell) |

## Decisions taken before implementation

Each was a question the checkout could not answer. They were put to the
maintainer and answered before any code changed.

| # | Question | Decision |
|---|---|---|
| Q1 | The fixes must touch files the repository freezes: `tests/test_integration_01/02_to_05/06_to_09` are byte-pinned to the T10 rollback point, two of their tests assert the defects themselves (`--skip-tests` approving Gate 7; the `HEAD~1` fallback), transcripts 01–09 are byte-pinned, and `sdle.py`'s write-primitive counts are pinned | **Declared, quantified deltas** in the T11 style. Frozen test files move to a definition-level comparison with a named exception list; the write-primitive delta is declared per needle; transcripts 01–09 move from byte pins to claim pins, with the replacement guarantee named |
| Q2 | What Gate 7 requires when no real passing test run exists. The code states the intent ("an implementation whose tests never ran does not reach a human decision"), and no exception path exists | **Strict refusal**, plus `manifest build --test-command` so a project whose runner is not auto-detected can still produce real evidence. It waives nothing |
| Q3 | Which SpecKit version to support | **v1.0.6**, pinned in the documented command |
| Q4 | Pushing the fix branch so CI runs | Approved for `fix/defect-stabilization` only |

## Task status

| Task | Status | Commit | Notes |
|---|---|---|---|
| T00 Baseline | PASS | `9b00bc4` | Baseline suite and lint green; D01–D04 reproduced |
| T01 D04 execution identity | PASS | `2da5394` | Affected modules 545 passed; full suite at T02 (below) |
| T02 D01 artifact preconditions | PASS | `e778c2e` | Full suite 1800 passed (includes T01) |
| T03 D02 verification enforcement | PASS (focused) | `c6a4f77` | Focused 137 passed; full suite at this commit: see T03 |
| T04 D03 change selection | PASS (focused) | `cc072d9` | Focused 216 passed; full suite pending |
| T05 D05 SpecKit and instructions | PASS (focused) | the T05 commit | Runtime verified for v1.0.6; instructions corrected; two further position/order defects found and fixed |
| T06 D06 dry runs | NOT STARTED | | |
| T07 Delivery | NOT STARTED | | |

"PASS (focused)" means the task's own and directly affected tests passed at
that commit. The full suite is run per commit in a detached verification
worktree, because one run takes about 33 minutes here, and its result is
recorded in the task's section once it finishes. No task is PASS without it.

## T00 — Baseline

### Commands and results

| Command | Result | Evidence |
|---|---|---|
| `python scripts/sdle.py lint-skill` | **PASS** — exit 0, 45 checks, `failed: []` | local run at `e14c402` |
| `python -m pytest -q -p no:cacheprovider --tb=line -rfE` | **PASS** — `1773 passed in 1950.49s (0:32:30)`; 0 failed, 0 errors, 0 skipped | local run at `e14c402`, Windows, Python 3.13.0 |

Run once. Nothing was re-run to obtain a green result.

### Reproductions

Driven through the suite's own `conftest.Project` fixtures against the
unmodified engine, from a temporary file that was removed afterwards and never
committed. Each assertion encoded the **defective** behaviour, so "passed"
means "reproduced". Result: `5 passed in 28.24s`.

| Defect | Scenario | Observed at `e14c402` |
|---|---|---|
| D01 | `ITERATIVE`, spec written, `feature resolve` never run, `advance --to gate_spec`, `gate approve --gate gate_spec` | exit 0; `{"sha": null, "next_phase": "plan_draft"}`; `approvals.gate_spec.decision == "approved"`; `artifact_shas.gate_spec` absent |
| D02 | `manifest build --skip-tests` (tests status `skipped by caller`), PASS review, `gate approve --gate gate_implement` | exit 0; `next_phase: security_review` |
| D02 | a real failing pytest suite (`status: FAILED`), PASS review of the manifest, approve | exit 0; `next_phase: security_review` |
| D03 | `implement preflight`, then `src/feature.py` containing a fake AWS key committed, then `manifest build` | `files: ["design/app/app-design.md", "design/db/db-design.md"]` — the committed source is absent, `secrets: []` |
| D04 | `now_iso` frozen at `2026-09-10T12:00:00Z`, two `governance assess` calls with different risk signals | both returned `workitems/fixture-workitem/.sdle/evidence/governance-usr-20260910T120000Z.json`; the file held only the second assessment |

The first D04 attempt failed on a **fixture error**, not an assertion: the
fixture named a risk signal (`authentication`) the policy does not define, and
the engine correctly refused `unknown_risk_signal`. Corrected to
`authentication_or_authorization` and re-run.

### Existing contracts identified

| Surface | Contract at `e14c402` |
|---|---|
| Artifact resolution | `resolve_artifact_path` returns `(None, reason)` for an unset `{speckit_feature_directory}` / `{security_review_artifact}`; `cmd_gate_approve`, `_approve_drift` and `cmd_gate_omit` treat `None` as "nothing to check" |
| Test evidence | Six prose statuses (`passed`, `FAILED`, `no runner detected`, `runner not installed`, `timed out after Ns`, `skipped by caller`); nothing structured persisted; Gate 7 checks three headings only; **no exception path exists** |
| Change selection | `git status --short -uall` ∪ `git diff --name-only HEAD`; `implementation_base_ref` unused by the manifest; the security-review evidence falls back to `HEAD~1` |
| Execution identity | `<prefix>-<UTC second>`; evidence files named after it and written with `write_atomic` (replace); governance audit de-duplication keyed on it |
| Freeze pins | `tests/test_units_capabilities.py` (`FROZEN`, `BASELINE=adbdc5e`, write-primitive counts, transcript count 13), `tests/test_units_gate_policy.py` (`FROZEN_FILES`, `ROLLBACK=e1cf341`, transcript pin), `tests/test_units_repo_config.py` (`CONFIG_REFERENCE_SITES`), `tests/test_units_flow_model.py` (AST checks on `cmd_manifest_build`) |
| Dry runs | 01–09 `GREENFIELD` (byte-pinned); 10–13 the other four flows (claim-pinned by `tests/test_integration_10_to_13.py`); the reusable all-flow CLI driver is `drive()` / `bind()` / `prepare()` in `tests/test_units_flow_model.py` |

## T05 — SpecKit runtime checks (run early; no repository writes)

All in disposable `git init` projects under the session scratch directory.
"Bash" below is **Git Bash on Windows**. Native Linux Bash was not exercised
locally: **NOT RUN**.

| Check | Bash (Git Bash, `--script sh`) | PowerShell 7 (`--script ps`) |
|---|---|---|
| Old documented command `specify init . --skills --here` | **FAIL (as expected)** — exit 2, `No such option: --skills` | not repeated; the option parser is shared |
| `--integration claude --integration-options=--skills` | **FAIL (as expected)** — exit 1, `Unknown integration option '--skills'` | not repeated |
| `specify init --here --force --non-interactive --integration claude --script <sh\|ps>` | **PASS** — exit 0 | **PASS** — exit 0 |
| Installed skill names | `speckit-analyze`, `-checklist`, `-clarify`, `-constitution`, `-converge`, `-implement`, `-plan`, `-specify`, `-tasks`, `-taskstoissues` under `.claude/skills/` (`init-options.json`: `"ai_skills": true`) | identical |
| `create-new-feature` run from **outside** the project with `SPECIFY_INIT_DIR=<project>` | **PASS** — created `<project>/specs/001-todo-api/` | **PASS** — same |
| `setup-plan` with `SPECIFY_FEATURE_DIRECTORY=workitems/todo-api/specs/001-todo-api` | **PASS** — `plan.md` written into the WorkItem directory; nothing under root `specs/` | **PASS** — same |
| `sdle.py preflight` straight after install | **REFUSED** `workitem_required` — preflight needs a registered WorkItem. The README's order (install → preflight) is wrong | same |
| `workitem create --name "Todo API"`, then `preflight` | **PASS** — `ok: true`, `skill_prefix: speckit-`, `problems: []`, both capabilities supported | **PASS** — same |
| `feature bind` → real `create-new-feature` → `feature resolve` | **PASS** — adopted `specs/001-todo-api` → `workitems/todo-api/specs/001-todo-api`, recorded in `specKit.featureDirectory` | **PASS** — same |
| Two fresh candidates in root `specs/`, then `feature resolve` | **PASS (refusal)** — exit 1 `feature_ambiguous`, lists both, `featureDirectory` stays null | **PASS (refusal)** — same |

Two harness faults surfaced and were fixed. Neither was a product finding:
Python resolved `bash` to the WSL stub, and one ambiguity probe ran after the
WorkItem already owned a feature directory, so tier 1 correctly answered first.

## T01 — D04 execution identity

| | |
|---|---|
| Reproduction | T00, above: two same-second `governance assess` calls shared `governance-usr-20260910T120000Z.json` |
| Affected paths | `scripts/sdle.py` — `execution_identity`, and the four evidence writers `cmd_governance_assess`, `cmd_artifact_review`, `cmd_discovery_assess`, `cmd_migrate_workflow`; governance audit de-duplication (`governance_audit_marker`) |
| Root cause | The id was `<prefix>-<UTC second>` and is used as a key: it names each evidence file (written with a replacing atomic write) and is the ledger's de-duplication marker |
| Correction | `execution_identity` appends 32 random bits (`execution_suffix`). `reserve_evidence` claims each evidence file with an exclusive create before anything is written, retries with a fresh id up to 3 times, then refuses `execution_id_collision` (exit 3) having recorded nothing. Governance and discovery claim evidence before writing their record |
| Compatibility | Historical ids are read unchanged — nothing parses an id. A pre-D04 record's marker still de-duplicates (test below). The contract's `<prefix>-<UTC>` format is deliberately widened; the divergence is recorded in ADR-009 |
| Regression tests | `tests/test_units_execution_identity.py` — all 8 (frozen clock via `now_iso`, forced collision via `execution_suffix`, no sleeps) |
| Red before fix | 6 failed / 2 passed at `9b00bc4`. The behavioural three failed on assertions (one evidence file; one ledger entry); the collision three on the missing `execution_suffix` hook. The two that passed are guards: review evidence names already carried a ledger-wide counter, and historical readability is a property to preserve. The ledger test was also re-run against the stashed pre-fix engine: 1 failed |
| Green | 8 passed; affected modules (`execution_identity`, `governance`, `hardening`, `workitem_runtime`, `artifact_review`, `discovery`, `capabilities`) 545 passed |
| Also changed | The second-boundary wait loop in `test_units_governance.py::test_the_governance_entry_is_written_once_per_assessment` is gone; `test_units_hardening.py` now asserts distinct ids across worktrees; both id regexes require the suffix; `STABILIZATION_01_WRITE_DELTA` declares `.mkdir(` +1, and a named pin holds the one exclusive-create writer to `reserve_evidence` |

## T02 — D01 artifact preconditions

| | |
|---|---|
| Reproduction | T00: `ITERATIVE`, `gate approve --gate gate_spec` with `featureDirectory` null → exit 0, `sha: null` |
| Affected paths | `cmd_gate_approve`, `_approve_drift`, `cmd_gate_omit`, `gate_precondition_hook` (Gate 7 manifest read) |
| Root cause | `resolve_artifact_path` returns `(None, reason)` for an unset binding and every caller treated `None` as "no artifact to check"; `sha256_file` errors escaped as tracebacks |
| Correction | `required_gate_artifact` resolves, finds and hashes the artifact or refuses `artifact_unresolved` (naming the binding and recovery), `feature_ambiguous` (listing candidates via the shared `feature_candidate_tier`), `artifact_missing` or `artifact_unreadable`; a pure reader ahead of every write. A `(none)` template remains the only artifact-free gate |
| Regression tests | `tests/test_units_gate_artifacts.py` — 19: null feature reference ×5 flows, unresolved security artifact ×5 flows, ambiguity, deleted file, unhashable (approve and omit), FAIL/stale review, drift re-approval of a deleted artifact, valid approval, and `ITERATIVE` needing no constitution |
| Red before fix | 13 failed at `2da5394`, plus 2 added later that were also red: the omit case, and the drift case once its setup used `drift check --queue`. Most striking: an unresolved `security_review_artifact` let **every flow run to `complete`**, writing a completion summary |
| Green | 19 passed; full suite at `e778c2e`: **1800 passed** in 33m15s |

## T03 — D02 verification enforcement

| | |
|---|---|
| Reproduction | T00: `--skip-tests` and a real failing pytest suite each approved Gate 7 under a PASS review |
| Existing contract (recorded before coding) | Six prose statuses; nothing structured persisted; Gate 7 checked three headings; **no exception path exists** — no waiver, accepted-risk record or policy switch, and `gate omit` cannot reach the implementation gate |
| Affected paths | `run_tests`, `cmd_manifest_build`, `gate_precondition_hook`; prompt layer `phase-execution.md`, `/sdle-approve` |
| Root cause | The reader never read the result the producer wrote, and nothing bound a result to the manifest it described |
| Correction | `manifest build` writes `evidence/implementation-<id>.json` (runner, command, exit code, status, manifest SHA, base, WorkItem) and names it on an `Evidence:` line. `implementation_evidence_precondition` refuses `test_evidence_missing`, `test_evidence_malformed`, `test_evidence_stale` (`manifestSha256`, `baseRef`, `workitem`, `location`) and `tests_not_passed`. `--test-command` supplies a project's real command (run without a shell; evidence, not a waiver) |
| Compatibility | A manifest built before D02 has no `Evidence:` line and is refused `test_evidence_missing` with an explicit "this format cannot establish success" and the rebuild command — the plan's required behaviour for an insufficient existing format |
| Regression tests | `tests/test_units_implementation_evidence.py` — 18, covering plan cases 1–8 (case 7 pins the *absence* of an exception path via the parser) |
| Red before fix | 17 failed / 1 passed at `e778c2e` — the real-pytest-passes case is the positive control |
| Green | 18 passed; happy path, 06–09, 10–13, every flow traversal and Spec Kit binding: 137 passed |
| Freeze deltas | `tests/conftest.py` `STABILIZATION_01_TEST_EDITS` / `_ADDITIONS` / `_REMOVALS`: `run_happy_path` gains `--test-command`; `test_06_gate_seven_accepts_a_built_manifest` builds with a passing command; `test_06_gate_seven_refuses_a_manifest_whose_tests_were_skipped` added. Both freeze pins compare the Python files unit by unit against those declarations; `write_atomic` +1 declared |

## T04 — D03 change selection

| | |
|---|---|
| Reproduction | T00: a source file with a fake key committed after `implement preflight` was absent from `files` and `secrets` |
| Affected paths | `cmd_manifest_build`, `cmd_security_review_evidence`, `git()` |
| Root cause | The manifest compared against current `HEAD`; the review evidence had its own exclusions and a `HEAD~1` fallback |
| Correction | `implementation_changes` diffs the pinned base against the working tree with `-z` (committed + staged + unstaged), adds untracked files, marks R/D/binary, and filters through `implementation_exclusions`, the one list both consumers read. A missing or invalid base refuses `implementation_base_missing` / `implementation_base_invalid`. Deletions and binary files are listed, never read; the review evidence lists `untracked` files for direct reading |
| Additional defect found | `git()` stripped leading whitespace from its whole output, so the first `git status --short` line lost its leading space and `line[3:]` cut the first character of the path. The manifest listed `orkitems/…/state.json`, and the **dirty-tree guard** reported a false `dirty_tree` for an SDLE-owned file sorting first. Not in the plan's D-list; fixed at the root (`rstrip()` only) with a regression test |
| Regression tests | `tests/test_units_manifest_changes.py` — 9 (post-base commit reaching both consumers and the scanner, staged/unstaged/untracked, rename, delete, binary PNG, exclusions, missing and invalid base, determinism, first-status-entry parse) |
| Red before fix | 7 failed / 1 passed at `c6a4f77` (the exclusion case passed — existing behaviour to preserve); the parse test failed with the false `dirty_tree` |
| Green | 9 passed; with 06–09, `workitem_runtime`, hooks and the dirty-tree tests: 216 passed |
| Freeze deltas | Three frozen 06 manifest tests gain a declared `implement preflight` line; `test_06_security_review_falls_back_when_no_ref_pinned` is replaced, as declared, by `test_06_security_review_refuses_when_no_ref_pinned`. `CONFIG_REFERENCE_SITES` and the flow-model AST pin retarget `cmd_manifest_build` → `implementation_exclusions`, old and new values recorded |

## T05 — D05 SpecKit and instructions

The runtime results are in the table above. These are the changes, including the defects
found while checking the instructions against the real parser:

| Finding | Where | Correction |
|---|---|---|
| `specify init . --skills --here` rejected by v1.0.6 | README, `SPECKIT_MISSING_MESSAGE`, the skills-missing message, transcript 09 | One engine constant `SPECKIT_INIT_COMMAND` (pinned `@v1.0.6`), stated verbatim in README for both script flavours; transcript 09 via a declared `DRY_RUN_SUBSTITUTIONS` pair held equal to the constant |
| Newest-mtime feature selection described | `phase-execution.md` Phase 4 (and "most recently updated `tasks.md`" at `gate_analyze`) | States the engine's rule: one candidate adopted, more than one refuses `feature_ambiguous`, never recency |
| `preflight` documented before WorkItem creation | README step 2, SKILL.md Step 1, `/sdle-start` step 1 | `preflight` resolves a WorkItem, so in a fresh repository it refuses `workitem_required` first. The order is now identity → `sdle.sh --workitem <id> preflight` → scan → governance → `init` |
| `sdle.sh lock acquire --session <token>` | SKILL.md Step 1 | A usage error (exit 2): `--session` is global. Now `sdle.sh --session <token> lock acquire` |
| `sdle.sh --workitem <id> init --session <token>` | `/sdle-start` step 5 | Same defect. Now `sdle.sh --workitem <id> --session <token> init` |

Regression tests are in `tests/test_units_documented_commands.py`:
- The real parser checks every documented `sdle.sh` invocation in the prompt layer, README and docs for a global option placed after the subcommand. The check is proven able to fail on both forms above.
- The README and the engine state the same install command.
- No document still teaches the rejected `--skills` flag.
- The spec-phase instruction states the engine's selection rule.
- A real two-candidate `feature resolve` is refused.
- In a fresh repository, preflight asks for a WorkItem first.

| Environment | Result |
|---|---|
| Git Bash on Windows (`--script sh`) | **PASS** — install, skills, preflight, feature bind → create → resolve, ambiguity refusal |
| PowerShell 7 on Windows (`--script ps`) | **PASS** — same checks |
| Native Linux Bash | **NOT RUN** — no local Linux; CI runs the suite and launchers on ubuntu-latest but does not install SpecKit |
