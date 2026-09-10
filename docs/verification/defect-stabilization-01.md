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
| T00 Baseline | PASS | this commit | Baseline suite and lint green; D01–D04 reproduced |
| T01 D04 execution identity | NOT STARTED | | |
| T02 D01 artifact preconditions | NOT STARTED | | |
| T03 D02 verification enforcement | NOT STARTED | | |
| T04 D03 change selection | NOT STARTED | | |
| T05 D05 SpecKit and instructions | IN PROGRESS | | Runtime checks run early (they write nothing to the repository); documentation not yet changed |
| T06 D06 dry runs | NOT STARTED | | |
| T07 Delivery | NOT STARTED | | |

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
