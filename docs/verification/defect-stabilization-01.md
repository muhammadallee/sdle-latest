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
| Verified final commit | `7561a68` — all behaviour; later commits are record-only |
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
| T01 D04 execution identity | PASS | `2da5394` | Affected modules 545 passed; full suite at `e778c2e` |
| T02 D01 artifact preconditions | PASS | `e778c2e` | Full suite 1800 passed (includes T01) |
| T03 D02 verification enforcement | PASS | `c6a4f77`, `9c10186` | Full suite at `c6a4f77` found one pin broken by the refactor; fixed in `9c10186` |
| T04 D03 change selection | PASS | `cc072d9` | Full suite at `9c10186`: only the two record self-quotes failed, fixed in T06 |
| T05 D05 SpecKit and instructions | PASS | `65b2850` | Runtime verified for v1.0.6 (Git Bash + PowerShell); native Linux Bash NOT RUN |
| T06 D06 dry runs | PASS | `7561a68` | Full suite R1 at `7561a68`: 2246 passed |
| T07 Delivery | PASS | this record | R1 local, R2 ubuntu-latest and R3 windows-latest all PASS at `7561a68` |

**Verified behavioural commit: `7561a68`.** The commits after it change only
this record and the verification matrix. They change no engine, prompt, test
or transcript, and so do not invalidate the runs recorded against `7561a68`.

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

## T06 — D06 dry runs

| | |
|---|---|
| Starting condition | At `e14c402`, `docs/dry-runs/` already held transcripts 10–13, one per non-GREENFIELD flow, pinned by claims. 01–09 were byte-pinned and stale: `.specify/specs/` paths, uppercase fingerprints, no WorkItem or governance bootstrap, preflight before identity, a Gate 7 with no test requirement. 10 cited `tests/test_integration_10_brownfield_discovery.py`, which does not exist |
| Changes | 01–09 rewritten against the engine; 10–13 given the missing parts; 11 now continues from 10 (brownfield discovery → iterative reuse, `baseline_present`, invalid vs stale baselines); 13 shows urgency refused at Gate 7; 14–16 added (D01/D02, D03, D04) quoting captured engine output; index and `verification-matrix.md` rewritten |
| Existing equivalents reused | `11-iterative.md` kept its name as the plan's `11-iterative-baseline-reuse`. Brownfield → iterative was already driven end-to-end by `tests/test_units_baseline.py::test_n24_the_second_workitem_does_not_rediscover_the_repository`; the new `tests/test_integration_10_to_13.py::test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it` adds what it did not assert (baseline, discovery record and constitution byte-identical after reuse) |
| Pin decision | Byte pins on 01–09 released (Q1) and replaced by `tests/test_dry_run_contracts.py`: required parts and labels, every `SDLE_STATE` / status header / gate prompt recomputed from the bound flow, every `Refused:` reason checked against the engine, every cited test node checked to exist, lowercase fingerprints, no retired `.workflow/` literal. `test_n20_…` and `test_n27_…_declared_substitution` keep their count guard (13 → 16) and the no-regression half, with the release recorded in their docstrings |
| Harness | Engine output for 14–16 and 11 was captured by a temporary pytest file driving the real CLI through the suite's fixtures; the file was deleted, never committed |
| Green | Doc-sensitive modules (`test_lint_skill`, `capabilities`, `gate_policy`, `documented_commands`, `dry_run_contracts`, `10_to_13`): 1033 passed. Contract tests alone: 416 passed |
| Full suite at `9c10186` (T04+T05) | 2066 passed, 2 failed — both `test_no_documented_invocation_puts_a_global_option_after_its_command` on this record's own quotations of the wrong forms. Fixed in T06 by excluding the verification record from that scan, as the transition record already was |

## T07 — Final regression and delivery

### Full-suite runs, in order

Each run is the whole suite (`python -m pytest -q`) at one commit, in a
detached verification worktree so that the development tree could keep
moving. Nothing was re-run to turn a result green; every failure below was
fixed in a later commit and the fix is named.

| Commit | Contains | Platform | Result | Follow-up |
|---|---|---|---|---|
| `e14c402` | starting point | Windows 10, Python 3.13.0 | **PASS** — 1773 passed | — |
| `e778c2e` | T01 + T02 | Windows 10, Python 3.13.0 | **PASS** — 1800 passed | — |
| `c6a4f77` | + T03 | Windows 10, Python 3.13.0 | **FAIL** — 1819 passed, 1 failed: `test_units_artifact_review.py::test_the_engine_invokes_no_agent` (the `--test-command` refactor moved the test spawn into a helper; the pin allows only `git` and `run_tests`) | Fixed in `9c10186` |
| `9c10186` | + T04, T05, the spawn fix | Windows 10, Python 3.13.0 | **FAIL** — 2066 passed, 2 failed: the new position check flagged this record's own quotations of the wrong CLI forms | Fixed in `7561a68` (the record is excluded, as the transition record is) |
| `7561a68` | + T06 | Windows 10, Python 3.13.0 (R1) | **PASS** — 2246 passed, 0 failed, 0 errors, 0 skipped, in 38m56s | — |
| `7561a68` | + T06 | GitHub Actions `ubuntu-latest`, Python 3.11 (R2) | **PASS** — lint, test suite and POSIX launcher steps all `success` ([run 34526996629](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629), [job](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629/job/103038213266)) | — |
| `7561a68` | + T06 | GitHub Actions `windows-latest`, Python 3.11 (R3) | **PASS** — lint, test suite and PowerShell launcher steps all `success` ([run 34526996629](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629), [job](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629/job/103038213547)) | — |

Job logs, and with them the exact CI test counts, are not readable without a
token. The CI results above are the step conclusions from the public jobs API.

### Other checks

| Check | Result |
|---|---|
| `python scripts/sdle.py lint-skill` at `7561a68` | **PASS** — 45 checks, none failed |
| `sh scripts/sdle.sh lint-skill` (Git Bash, Windows) | **PASS** — exit 0 |
| `pwsh ./scripts/sdle.ps1 lint-skill` (Windows) | **PASS** — exit 0 |
| POSIX launcher on Linux | **PASS** in CI (R2) |
| Local Python 3.11 | **NOT RUN** — no 3.11 interpreter installed; covered by CI R2/R3 |
| Native Linux Bash with a real SpecKit install | **NOT RUN** — CI does not install SpecKit |
| Diff review, `e14c402..7561a68` | Every removed engine line maps to a D0x change; no consumer parses the manifest's file rows (the new `A path` form changes no machine reader) |

## Release notes — SDLE-DEFECT-STABILIZATION-01

No state-schema change and no version bump: SDLE stays at v1.17. Every fix
below is a refusal that did not exist before, or a document that now matches
the runtime.

**D01 — gates approve specific content or nothing.** `gate approve`, drift
re-approval and `gate omit` refuse an artifact that cannot be resolved
(`artifact_unresolved`, naming the binding and its recovery), is ambiguous
(`feature_ambiguous`), is missing (`artifact_missing`), or cannot be read
(`artifact_unreadable`). Previously the first case approved with `sha: null`.
An unnamed security review let every flow run to `complete`.

**D02 — Gate 7 enforces the test result.** `manifest build` writes a
structured evidence record bound to the manifest's SHA-256, the pinned base
and the WorkItem. Gate 7 refuses anything but a run that exited 0:
`tests_not_passed`, `test_evidence_missing`, `test_evidence_stale`,
`test_evidence_malformed`. There is no exception path. The new
`--test-command` lets a project whose runner is not auto-detected supply its
real command.
*Compatibility:* a manifest built by an earlier SDLE has no evidence record
and must be rebuilt before Gate 7. `--skip-tests` still builds, but that
manifest can no longer be approved.

**D03 — the implementation change set is measured from the pinned base.**
The manifest, the secrets scan and the security-review evidence all read one
selection:
- committed, staged, unstaged and untracked changes since
  `implement preflight`;
- renames, deletions and binary files represented explicitly.

A missing or invalid base refuses (`implementation_base_missing`,
`implementation_base_invalid`) instead of falling back to `HEAD` or `HEAD~1`.
Also fixed: a leading-whitespace strip in `git()` that raised false
`dirty_tree` refusals.

**D04 — execution ids are collision-resistant.**
`<prefix>-<UTC second>-<8 hex>`. Every evidence file is claimed with an
exclusive create, and none is ever replaced. An unallocatable id refuses with
exit 3 and nothing recorded.
*Compatibility:* historical ids are read unchanged. The format deliberately
diverges from the transition contract (ADR-009).

**D05 — instructions match the runtime.** The SpecKit install command is the
one actually run against **v1.0.6**, pinned `@v1.0.6`, in README and in both
preflight messages. The bootstrap order is now identity, then preflight.
Global options go before the subcommand, which fixes
`lock acquire --session` and `init --session`, both usage errors. The spec
phase no longer describes newest-mtime selection.

**D06 — dry runs for all five flows.** Sixteen transcripts:
- 01–09 rewritten;
- 10–13 completed, with brownfield → iterative in 11;
- 14–16 added.

Each is pinned by its claims (`tests/test_dry_run_contracts.py`) and mapped
to its tests in `docs/dry-runs/verification-matrix.md`.

## Definition of done (plan §8)

| Criterion | Status | Evidence |
|---|---|---|
| D01 blocks unresolved or invalid required artifacts without partial mutation | **Met** | T02; `tests/test_units_gate_artifacts.py`, including frozen-state assertions |
| D02 blocks failed, missing, malformed, unrelated or unauthorised-skipped verification | **Met** | T03; `tests/test_units_implementation_evidence.py`, plan cases 1–8 |
| D03 includes committed and working-tree changes from the base, consistently across consumers | **Met** | T04; `tests/test_units_manifest_changes.py` |
| D04 keeps distinct evidence and ledger entries under one clock value; a forced collision is safe | **Met** | T01; `tests/test_units_execution_identity.py`, with a frozen clock and no sleeps |
| D05 instructions match the tested runtime | **Met, with one environment NOT RUN** | T05. Git Bash and PowerShell verified against SpecKit v1.0.6; native Linux Bash with a real SpecKit install NOT RUN |
| D06 current dry runs for all five flows | **Met** | T06; 16 transcripts, `tests/test_dry_run_contracts.py` |
| Brownfield → iterative documented and executable-tested | **Met** | DR-11; `test_n24_…`, `test_11_brownfield_then_iterative_…` |
| Focused defect scenarios linked to passing assertions | **Met** | DR-14..16; the verification matrix |
| Existing flow behaviour, guardrails and historical readability intact | **Met** | R1–R3 full suites; frozen files changed only as declared; historical execution ids test |
| Linux/Windows tests and launcher checks pass | **Met** | R2, R3 (CI run 34526996629), local launchers |
| Skill lint and full suite pass | **Met** | R1: 2246 passed; lint 45/45 |
| Record, index, matrix and release notes agree with `7561a68` | **Met** | this record; `docs/dry-runs/README.md`; `docs/dry-runs/verification-matrix.md` |

## Remaining limitations

- **Native Linux Bash with a real SpecKit install: NOT RUN.** The SpecKit
  checks ran on Windows, in Git Bash and in PowerShell 7. CI runs the suite
  and the POSIX launcher on Linux, but it does not install SpecKit.
- **Local Python 3.11: NOT RUN.** It is covered by CI (R2, R3), which pins 3.11.
- **CI test counts** are not readable without a token. The CI result is each
  job's step conclusions, all `success`.
- **An existing SpecKit install older than v1.0.6** is detected, not upgraded.
  Whether it behaves the same is not tested. The documentation says so.
- **A pre-existing cosmetic issue, not fixed** because it is outside the D-list:
  the `baseline_required` message for an INVALID baseline prints a doubled
  period (`…supports '1'.. Complete…`).

