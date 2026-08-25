# T05 Implementation Handoff — Attempt a01

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary (contract §11)
**Attempt:** 01
**Implementer context:** fresh/isolated
**Status recommendation:** IMPLEMENTED

Precondition HEAD: **`bf4ba5e`** on `transition/workitem-v1`.
Rollback point: **`7b054ee`**. Product baseline: `f8fdaa0`.

> **A green suite is necessary evidence for T05 and nowhere near sufficient.**
> Inert scaffolding that nothing reads would also leave it green. The positive
> proofs are A10/A11/A12/A13/A20 and the N1/N4/N7/N8/N10/N11 tests; the negative
> proofs are A5/A7/A9/A17/A18/A19/A21. Please weigh them separately.

---

## Inputs read from disk

- `docs/transition/transition.md` §11 (lines 1031–1090, read in full), plus TP-002, TP-003, §19, §22, §27 as cited by the plan.
- `docs/transition/phases/T05-plan.md` — read in full (460 lines).
- `docs/transition/RESUME.md`, `docs/transition/progress.md` (the T05 row), `docs/transition/phases/README.md`, `docs/transition/templates/phase-handoff.md` and `…/phase-checkpoint.md`.
- `CLAUDE.md`, `README.md`, `docs/SDLE-Reference-Guide.md`, `docs/architecture/ADR-001-deterministic-core.md`.
- `scripts/sdle.py` (`Paths`, `PROJECT_ROOT_MARKERS`, `discover_project_root`, `resolve_paths`, `write_atomic`, `emit`, error classes, `RUNTIME_FREE_COMMANDS`, `_finding`, `_validate_runtime_state`, `collect_validation_findings`, `cmd_validate`, `cmd_implement_preflight`, `build_parser`, `main`, the lint checks `_check_version_consistency`, `_check_no_hardcoded_progress`, `_check_doc_phase_tables`).
- `tests/conftest.py` in full; `tests/test_units_workitem_resolution.py` (the four closed-set assertions, the marker tests, `sha_map`, the local helpers); `tests/test_integration_01_happy_path.py` (`EXPECTED_TRAVERSAL`, `run_happy_path`).
- `tools/transition/agent_guard.py` (to establish which shell shapes are permitted to an implementer).

---

## Changes made

### Engine — `scripts/sdle.py` (+436 added lines, **0 deleted lines**)

| Change | Anchor |
|---|---|
| **D1** Seven read-only properties on `@dataclass class Paths`: `config_root`, `config_root_relative`, `config_file`, `policies_dir`, `shared_templates_dir`, `baseline_file`, `implementation_state_dir` | immediately after `def speckit_specs_relative`, under the comment `# -- repository configuration boundary (contract §11)` |
| **D2** `(".sdle", "config.json")` appended as the **last** entry of `PROJECT_ROOT_MARKERS` | `PROJECT_ROOT_MARKERS = (` |
| **D3** `REPO_CONFIG_DEFAULTS`, `SUPPORTED_CONFIG_VERSIONS`, `SUPPORTED_POLICY_FORMATS`, `read_repo_config` | new section `# Repository configuration boundary — contract §11`, placed immediately before `def _escape_detail` |
| **D4** `repo_config_findings` (the single soundness predicate), `workitem_runtime_member_names`, `_refuse_config_findings` | same section |
| **D4** validate blocks **8** (`findings.extend(repo_config_findings(paths))`) and **9** (the bidirectional leak detector) | inside `collect_validation_findings`, after check 7 and before the resolution-outcome warning |
| **D5** `cmd_config_init`, `cmd_config_show` | new section `# config — the repository configuration boundary's two commands`, immediately after `cmd_validate` |
| **D5** the `config` parser group with `init` and `show` | in `build_parser`, immediately before `workitem_p = subparsers.add_parser("workitem", …)` |
| **D6** `"config"` added to `RUNTIME_FREE_COMMANDS` | `RUNTIME_FREE_COMMANDS = frozenset({` |

### Repository configuration instance (new, versioned) — **D7**

Produced by running `python scripts/sdle.py config init` at this repository root:

```
.sdle/config.json                       {"configVersion": "1", "policyFormat": "json"}
.sdle/policies/.gitkeep                 (0 bytes)
.sdle/templates/.gitkeep                (0 bytes)
.sdle/implementation-state/.gitkeep     (0 bytes)
```

No `baseline.json`. `.gitignore` and `.gitattributes` were **not** edited: `git check-ignore -v` exits **1** for all four files, so §19's "must eventually be versioned" was already satisfied with zero diff.

### Documentation — **D8**

- **New** `docs/architecture/ADR-002-repository-configuration-boundary.md` (ADR-001's shape): context, the two-boundary decision, the JSON policy-format decision with the maintainer's verbatim rationale, four rejected alternatives (YAML + dependency; a home-grown YAML parser; configuration in `state.json`; extending the write fence / `SDLE_OWNED_PREFIXES`), consequences, and the explicit statement that no lifecycle rule moved.
- `README.md` — repository `.sdle/` block added above `workitems/` in "In your target project"; a new `### Repository configuration` subsection carrying the two `config` rows and the `config.json` shape; the project-root-marker sentence now lists `.sdle/config.json`; the runtime-free-command sentence now lists `config`; a paragraph distinguishing the two `.sdle/` directories.
- `docs/SDLE-Reference-Guide.md` §4 — new un-numbered `### Repository configuration boundary` subsection with the two-column ownership table, placed immediately before §4.3, matching the existing `### WorkItem identity` / `### validate` pattern.
- `CLAUDE.md` — one paragraph after the existing "Runtime state is WorkItem-scoped" paragraph.

**No version bump and no version-history row.** All four version locations still report v1.15; `lint-skill` re-run after **each** document edit (five times) reported 22 PASS / 0 FAIL every time.

### Tests

- **New** `tests/test_units_repo_config.py` — **69 collected**, covering N1–N14 plus four anti-vacuity guards.
- `tests/test_units_workitem_resolution.py` — **one** hunk: the literal `"config"` (plus a two-line comment) inside `test_runtime_free_commands_is_a_closed_enumerated_set`.

---

## Deliberate behavior changes

1. **`sdle config init` and `sdle config show` exist**, both runtime-free. New refusal reasons: `config_exists`, `config_malformed`, `config_root_inside_workitem`. No existing reason removed or renamed (`Refused`/`UsageError`/`IntegrityError` literal-reason set: **56 → 57**, added `{"config_exists"}`, removed `{}`; the other two reasons are raised through `_refuse_config_findings` from the finding's `check`, so they do not appear as string literals in a `Refused(` call).
2. **`sdle validate` gained four new checks**: `config_root_inside_workitem`, `config_malformed`, `lifecycle_state_in_repository_config`, `repository_config_in_workitem`. All are silent for any repository with no `.sdle/` and no misplaced artefact — `test_validate_is_clean_in_a_healthy_repository` is unmodified and passing.
3. **`PROJECT_ROOT_MARKERS` gained a fourth entry.** Provably a no-op for every tree with no `.sdle/config.json`, pinned by a control test that runs the four pre-existing marker shapes against both the new tuple and the `7b054ee` tuple and asserts equality.
4. **`RUNTIME_FREE_COMMANDS` gained `"config"`** — 6 → 7 members, nothing removed. This *is* §11's exit criterion in executable form.

### Declared divergence from the plan's literal wording (one)

**N10 clause 2 needs the configured project's `.sdle/` to be committed.** Written exactly as the plan words it, the differential test fails: with `.sdle/` left untracked, `implement preflight` sees an uncommitted `.sdle/config.json` and audits an extra `dirty_tree_bypassed` event, so the audit sequences differ by one entry.

That is **the plan's own Unknowns §4 decision working as designed, not a lifecycle change**: nothing *read* the configuration; an untracked file in the working tree changed what the dirty-tree guard reports, exactly as an untracked `src/foo.py` would. `SDLE_OWNED_PREFIXES` is deliberately not extended, and `.sdle/` is versioned by D7, so "committed" is the realistic state.

Resolution: the differential test commits `.sdle/` before running the workflow, and a **separate new test** — `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` — pins the uncommitted behaviour explicitly (asserting `".sdle/" not in sdle.SDLE_OWNED_PREFIXES` and that preflight refuses `dirty_tree` naming a `.sdle/` entry), so the decision is evidenced rather than hidden. No test was weakened: the differential proof still asserts identical traversals, identical ordered audit events, identical scrubbed state and a byte-identical `.sdle/` across the whole 18-phase run.

**One addition to the plan's run-varying field list.** The plan names `last_updated`, `audit_sha`, `artifact_shas`, `current_artifact_sha`, `security_review_artifact`, `implementation_base_ref` and the `approvals` timestamps. `phase_history[*].completed_at` is the same class of value (a wall-clock stamp written per run) and is scrubbed too. `test_the_scrubbed_state_comparison_still_has_teeth` guards against over-scrubbing by asserting the scrubbed state still carries `current_phase`, `workflow_version`, `workitem`, `progress`, the phase-history phase names, every approval decision and the Spec Kit feature id.

---

## Preserved behavior / invariants

- **The whole prompt/skill layer is untouched.** `git diff --exit-code 7b054ee -- .claude/skills/ .claude/hooks/ .claude/commands/ .claude/settings.json .claude/agents/ .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ docs/architecture/ADR-001-deterministic-core.md tools/` → **exit 0**.
- **No schema change.** `templates/state.json` byte-identical to `7b054ee` (`git diff --exit-code` → 0); `CURRENT_VERSION == "1.15"`; `len(MIGRATIONS) == 15`; `lint-skill` reports `15 migration rows` and `all four locations report v1.15`.
- **The write fence is untouched**; `hooks.py` is byte-identical (A5). Repository `.sdle/` is deliberately **not** fenced — see "Known limitations".
- **`SDLE_OWNED_PREFIXES` is untouched** and byte-identical (A7), deliberately.
- **Extract-and-compare against `7b054ee`** (AST source segments, not eyeballing) shows these **byte-identical**: `write_atomic`, `append_audit`, `save_state`, `read_state`, `touch_lock`, `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, `cmd_migrate_workflow`, `cmd_init`, `cmd_workitem_use`, `cmd_implement_preflight`, `cmd_manifest_build`, `_validate_runtime_state`, `discover_project_root`, and the `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS` and `CONFIRMABLE` definitions. Exactly three named definitions changed: `PROJECT_ROOT_MARKERS`, `RUNTIME_FREE_COMMANDS`, `collect_validation_findings` — the three the plan declares.
- **The resolution ladder never guesses**; the legacy `.workflow/` dual-read rung still binds; `migrate-workflow` never mutates `.workflow/`; `init` still refuses `legacy_workflow_present` unconditionally. Each by its named existing test passing unmodified (see A16).
- **Invariant 6 (single writer).** `config init` is the only new writer, writes **only** inside `config_root`, never `state.json`, never `audit.md`, and appends no audit entry. Proved at source level (N11 clause 2) and at runtime (`test_no_config_command_appends_an_audit_entry`).
- **Invariant 7 (one fact, one home).** No existing fact moved into `.sdle/`. A grep of `.sdle/` for `rate_limits|approvals|project_name|verbose|max_remediation_attempts|PHASE_SEQUENCE|NEXT_PHASE|PROGRESS_MAP|ARTIFACT_OWNERSHIP|PHASE_TO_GATE_KEY` returns **nothing** (grep exit 1); `.sdle/config.json` is 53 bytes and carries two new keys. `repo_config_findings` is the single soundness predicate, and `test_malformed_configuration_fails_closed_in_both_consumers` asserts `config show`'s refusal message and `validate`'s finding `detail` are the **same string** across all eight malformed cases.
- **Invariant 3.** No `speckit-` or `/speckit.` string in anything T05 added (grep over the whole T05 change corpus → exit 1).
- **Invariant 8.** No subagent, no delegation, nothing that holds a gate.
- **T04's Spec Kit binding** untouched: `speckit_specs_root`, `feature bind/resolve/capabilities`, the gate precondition and `specKit` state all unchanged (A5/A7 plus the full suite).

---

## Test changes and TP-003 classification

| Test | Category | Rationale |
|---|---|---|
| `tests/test_units_workitem_resolution.py::test_runtime_free_commands_is_a_closed_enumerated_set` — the literal `"config"` added to the asserted frozenset | **2 — genuinely superseded** | D6 puts `config` in `RUNTIME_FREE_COMMANDS`, which is contract §11's exit criterion in executable form. The assertion remains a *closed* set and is not weakened: it still fails if any other member is added or removed. |

**That is the entire `M` set.** `git diff --name-status 7b054ee -- tests/` = **one `M`**, **zero `D`**, **zero `R`**; one untracked `A` (`tests/test_units_repo_config.py`). `tests/conftest.py` is byte-identical (`git diff --exit-code` → 0). The full diff of the one modified test file is a **single hunk** of three added lines, so the other three closed-set assertions (`sites`, `writers`, `ACTIVE_CONTEXT_SETTERS`) are byte-identical by construction.

**No test was weakened, skipped, xfailed or deleted.** The final run used `-rsxX`; `grep -c "short test summary"` over the captured output = **0**, so the suite has zero skips, zero xfails and zero errors.

*(Note, per the plan's own warning: a naive `grep "skip\|xfail"` over `tests/` is not evidence of anything — it matches the pre-existing `@pytest.mark.skipif(SH is None, …)` in `test_units_infra.py`, the `--skip-tests` CLI flag and the `skip` subcommand's test names. The `-rsxX` short-summary count above is the real evidence.)*

---

## Commands actually run

All pytest runs went through `rtk proxy`, unpiped, with the raw exit read directly (`echo "RAW_EXIT=$?"`), 600000 ms timeout.

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only <scratch>/baseline-bf4ba5e/tests"` | **500 tests collected in 3.08s** | pristine `git archive bf4ba5e` copy |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/baseline-bf4ba5e/tests"` | **`500 passed in 617.01s (0:10:17)`, RAW_EXIT=0** | re-derived baseline; `grep -c "short test summary"` = **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py tests/test_units_workitem_resolution.py"` (M1) | **106 passed in 137.85s, RAW_EXIT=0** | M1 green with zero existing-test edits |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_workitem_resolution.py tests/test_units_workitem.py tests/test_units_cli.py"` (M2) | **162 passed in 161.43s, RAW_EXIT=0** | |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/m2/tests"` (M2) | **`541 passed in 627.24s (0:10:27)`, RAW_EXIT=0** | 500 + 41 |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py"` (M4) | **69 passed in 51.51s, RAW_EXIT=0** | |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/m6/tests"` (final snapshot) | **`569 passed in 715.31s (0:11:55)`, RAW_EXIT=0** | `grep -c "short test summary"` = **0**; a grep for `passed\|failed\|error\|skipped\|xfail` matched exactly one line, the summary |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only <scratch>/m6/tests"` | **569 tests collected in 1.19s** | collected == passed |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` **in the actual repository working tree** (**the primary A1 figure**) | **`569 passed in 656.85s (0:10:56)`, RAW_EXIT=0** | `grep -c "short test summary"` = **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` in the working tree | **569 tests collected in 0.55s** | collected == passed |
| per-file collect-only, `test_units_repo_config.py` | **69** | |
| per-file collect-only, `test_units_workitem_resolution.py`, baseline **and** final | **96** and **96** | the one authorised edit adds no test |
| `rtk proxy "python scripts/sdle.py lint-skill"` (after **each** of the five M5 document edits, and finally) | raw exit **0**, `grep -c PASS` = **22**, `grep -c FAIL` = **0** | `Parsed 19 phases, 8 gates, 15 migration rows`; `all four locations report v1.15` |
| `rtk proxy "python tools/transition/validate.py"` | `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** | also re-verifies `control-plane.sha256` |
| `rtk proxy "git diff --exit-code 7b054ee -- <must-not-change list>"` | **exit 0** | A5 |
| AST extract-and-compare vs `7b054ee` | 19 definitions identical, 3 changed (the declared three) | A7 |
| Real-CLI (subprocess) probes for A9/A10/A11/A14 | see the matrix below | not in-process |
| Python 3.11 | **NOT_RUN** | no 3.11 interpreter on this host (host is **Python 3.13.0**) |
| CI | **NOT_RUN / UNKNOWN** | branch is local-only; CI has never run. **No outcome predicted.** |

**Baseline method — read this before comparing figures.** The first full-suite run was started in the working tree and then **discarded, not quoted**: several tests re-read `scripts/sdle.py` from disk at run time, so an edit landing mid-run contaminates the result. The baseline and the intermediate milestone figures were therefore taken against pristine/snapshot copies under the scratchpad, built by `git archive <rev> | tar -x` plus an overlay of changed and untracked files, which also freed the working tree for editing while a run was in flight. **The final A1 figure was then re-taken in the actual repository working tree, with no edit in flight**, and matched the snapshot run exactly at 569 passed. The snapshot and the working tree were diffed file-by-file: the only differences are `__pycache__` and the line endings of three files I never touched (`tests/conftest.py`, `tests/test_hooks.py`, `tests/test_units_speckit_binding.py` carry pre-existing CRLF working copies; content compares equal after newline normalisation).

**Line endings.** The editing tool rewrote `scripts/sdle.py` as CRLF; it was normalised back to LF (`git ls-files --eol` now reports `i/lf w/lf` for `scripts/sdle.py`, `README.md`, `CLAUDE.md` and `docs/SDLE-Reference-Guide.md`). `git diff` normalises via `.gitattributes` either way, but a CRLF working copy would corrupt byte-level comparison.

**Guard.** The transition agent guard refused **nothing** during this phase. Heredoc appends to test files were used only for content with no backslash escapes; every substantial file was written with the Write tool.

---

## Acceptance criteria — A1…A22

| # | Result | Evidence |
|---|---|---|
| **A1** | **PASS** | In the actual working tree: **`569 passed in 656.85s (0:10:56)`, RAW_EXIT=0**; `--collect-only` = **569**, so collected == passed; `-rsxX` produced **no** short-summary section (`grep -c` = 0). Independently reproduced on the final snapshot copy: `569 passed in 715.31s (0:11:55)`, RAW_EXIT=0 |
| **A2** | **PASS** | 500 (re-derived baseline) + 69 (`test_units_repo_config.py`) = **569**. `test_units_workitem_resolution.py` = **96** at baseline and **96** at final |
| **A3** | **PASS** | `lint-skill` raw exit 0, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15` |
| **A4** | **PASS** | `validate.py` raw exit **0** |
| **A5** | **PASS** | `git diff --exit-code 7b054ee -- …` → **exit 0** |
| **A6** | **PASS** | `templates/state.json` diff exit 0; `CURRENT_VERSION == "1.15"`; `len(MIGRATIONS) == 15`; no `VERSION_MIGRATION` row added (`lint-skill` reports 15); no version string changed |
| **A7** | **PASS** | AST extract-and-compare: all 15 named functions plus `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE` **identical**; only `PROJECT_ROOT_MARKERS`, `RUNTIME_FREE_COMMANDS`, `collect_validation_findings` changed |
| **A8** | **PASS** | `sorted(RUNTIME_FREE_COMMANDS)` = `['config','constants','lint-skill','migrate-workflow','sha','validate','workitem']` — **7 members**, `7b054ee`'s six plus exactly `"config"` |
| **A9** | **PASS** | `.sdle/config.json` parses to exactly `{"configVersion": "1", "policyFormat": "json"}`; `baseline.json` does **not** exist; `policies/`, `templates/` and `implementation-state/` each list exactly `['.gitkeep']`; `git check-ignore -v` exits **1** for all four files |
| **A10** | **PASS** | `config init` into a fresh scratch root produced the identical relative file list (`.sdle/config.json`, `.sdle/implementation-state/.gitkeep`, `.sdle/policies/.gitkeep`, `.sdle/templates/.gitkeep`) and an equal parsed `config.json` |
| **A11** | **PASS** | Real CLI, three scratch repositories: 0 WorkItems → `config show` **0**, `config init` **0**, `state get` **1** `workitem_required`; 1 WorkItem → `config show` **0**, `config init` **0**, `state get` **3** `state_unreadable` (resolution *succeeded*; the runtime is simply not initialised — the contrast still holds); 2 WorkItems → `config show` **0**, `config init` **0**, `state get` **1** `workitem_ambiguous` |
| **A12** | **PASS** | `test_lifecycle_state_under_the_repository_boundary_is_an_error` (7 params, derived from `workitem_runtime_member_names`) and `test_repository_configuration_under_a_workitem_is_an_error` (5 members × `has_state` True/False), both asserting exit **3**, severity `error` and the offending path; plus `test_an_unregistered_workitem_directory_is_scanned_too` |
| **A13** | **PASS** | `test_the_config_commands_are_pure_toward_workitem_runtime` (two WorkItems, one mid-run; everything outside `.sdle/` byte-identical across `config init`/`config show`/`validate`; `.sdle/` itself byte-identical across the two readers) and `test_no_config_command_appends_an_audit_entry` |
| **A14** | **PASS** | Real CLI: second `config init` → **1** `config_exists`; `config init` with root `workitems/` → **1** `config_root_inside_workitem`; `config show` with root `workitems/alpha` → **1** `config_root_inside_workitem`; `policyFormat: "yaml"` → **1** `config_malformed` with the message quoted below. Eight malformed cases covered by `test_malformed_configuration_fails_closed_in_both_consumers` |
| **A15** | **PASS** | `test_validate_stays_clean_with_no_repository_boundary` and `test_validate_stays_clean_after_config_init` — `findings == []`, `errors == 0`, exit 0 in both shapes; and the unmodified `test_validate_is_clean_in_a_healthy_repository` still passes |
| **A16** | **PASS** | All named existing tests pass unmodified in the final run: `test_workitem_rebinding_happens_only_at_the_declared_sites`, `test_the_active_context_is_written_only_by_the_declared_setters`, `test_validate_is_clean_in_a_healthy_repository`, `test_init_still_refuses_a_legacy_workflow_unconditionally`, `test_no_rung_ever_returns_an_unregistered_workitem`, `test_the_legacy_dual_read_rung_still_binds`, `test_the_nearest_marker_ancestor_wins` (+ the other marker tests), every `test_units_workitem.py` case, every `test_hooks.py` case and all nine integration transcripts |
| **A17** | **PASS** | `grep -rn 'rate_limits\|approvals\|project_name\|verbose\|max_remediation_attempts\|PHASE_SEQUENCE\|NEXT_PHASE\|PROGRESS_MAP\|ARTIFACT_OWNERSHIP\|PHASE_TO_GATE_KEY' .sdle/` → **exit 1, no matches**; `REPO_CONFIG_DEFAULTS` holds only the two new keys |
| **A18** | **PASS** | `grep -n 'speckit-\|/speckit\.'` over the combined T05 corpus (the tracked diff vs `7b054ee` for `scripts/ tests/ README.md CLAUDE.md docs/SDLE-Reference-Guide.md`, plus the full text of `tests/test_units_repo_config.py`, `ADR-002…md` and `.sdle/config.json`) → **exit 1, no matches** |
| **A19** | **PASS, with one match declared** | The same grep for `risk_tier\|flow_id\|classification\|quality_gate\|risk evaluate\|gate status\|baseline validate\|discovery` matched **exactly one line**: `tests/test_units_repo_config.py`, the docstring phrase *"discovery returns exactly what it returned at `7b054ee`"* — **project-root** discovery, not T08 brownfield discovery. No other term matched. `.sdle/policies/` contains only `.gitkeep`. No code path writes `baseline.json` (`baseline_file` is referenced only for `.name` in the leak detector and as a reported path in `config show`), and the only thing written under `implementation-state/` is its `.gitkeep`. The `.workflow/` dual-read rung (`legacy_state_present`), `cmd_migrate_workflow` and `init`'s `legacy_workflow_present` refusal are all still present |
| **A20** | **PASS** (with the divergence declared above) | `test_the_configuration_boundary_changes_no_lifecycle_behaviour`: two identical scratch projects; both traversals equal `EXPECTED_TRAVERSAL`; ordered audit `(phase, event)` sequences identical; scrubbed `state.json` identical; the configured project's `.sdle/` **byte-identical before and after** the whole 18-phase run |
| **A21** | **PASS** | `git diff --name-status 7b054ee -- tests/` = **one `M`**, zero `D`, zero `R`; one untracked `A`. `tests/conftest.py` byte-identical. The one `M` is a single three-line hunk, so the other three closed-set assertions are byte-identical |
| **A22** | **RECORDED** | Python 3.11: **NOT_RUN**. CI: **NOT_RUN / UNKNOWN**. No outcome predicted |

The `policyFormat: "yaml"` refusal message, verbatim from the CLI:

```
.sdle/config.json declares policyFormat 'yaml'; this engine supports 'json'.
The deterministic core is standard-library-only, so any other policy format
requires a parser dependency that has been explicitly accepted first — and a
home-grown parser is not an option.
```

---

## Git evidence

- **HEAD:** `bf4ba5e1f52a893c3ef0247c173687268e5c546c` on `transition/workitem-v1`. Nothing committed by this phase; the working tree carries the change.
- **Rollback point:** `7b054ee`. `git reset --hard 7b054ee` plus `rm -rf .sdle/` restores the T04 product tree exactly. T05 has no irreversible data effect: it writes only inside a previously non-existent `.sdle/`, never deletes, never overwrites, and touches no state, audit, evidence or Spec Kit artefact.
- **Working tree** (`git status --porcelain`):

```
 M .claude/settings.local.json                      <- pre-existing, OUT OF SCOPE
 M CLAUDE.md
 M README.md
 M docs/SDLE-Reference-Guide.md
 M scripts/sdle.py
 M tests/test_units_workitem_resolution.py
?? .sdle/
?? docs/architecture/ADR-002-repository-configuration-boundary.md
?? docs/transition/phases/T05-checkpoint-a01-01.md
?? docs/transition/phases/T05-checkpoint-a01-02.md
?? docs/transition/phases/T05-checkpoint-a01-03.md
?? docs/transition/phases/T05-checkpoint-a01-04.md
?? docs/transition/phases/T05-handoff-a01.md
?? tests/test_units_repo_config.py
```

`docs/transition/progress.md` is additionally modified (the T05 row moved to
IMPLEMENTED). The status line above was captured before the handoff and
checkpoint 04 were written and before that row was updated.

**One process note.** The first `progress.md` row edit made `validate.py` exit
**3** with `progress row must have 9 columns`, because the narrative contained
literal `|` characters inside grep alternations. The row was restored with
`git checkout -- docs/transition/progress.md` and rewritten without them;
`validate.py` then exits **0**. Anyone editing that table should keep `|` out of
a cell entirely.

- **Diff scope** (`git diff --name-status 7b054ee`, product files only): `M CLAUDE.md`, `M README.md`, `M docs/SDLE-Reference-Guide.md`, `M scripts/sdle.py`, `M tests/test_units_workitem_resolution.py`. Control-plane rows (`docs/transition/RESUME.md`, `progress.md`, `T05-plan.md`) and `.claude/settings.local.json` are outside T05's product surface; `settings.local.json` was neither staged, reverted nor edited.
- **Deletions across the whole tracked diff: six lines**, all in `README.md`, both being sentences rewritten for accuracy (the project-root marker list and the runtime-free command list). `scripts/sdle.py` has **zero** deleted lines.

---

## Known limitations / risks

1. **`config_root_inside_workitem` is a name-based heuristic.** It fires when `project_root.name == "workitems"` or `project_root.parent.name == "workitems"`. A repository legitimately checked out at `…/workitems/<name>/` would therefore be refused. This is the plan's D4 as written and it fails **closed**, but it is a false-positive surface worth knowing about.
2. **`repo_config_findings` returns early on `config_root_inside_workitem`.** A misplaced root will not also report `config_malformed` in the same run. Intentional — the root is wrong, so nothing below it is worth diagnosing — but it means the two errors never co-occur.
3. **The repository `.sdle/` is deliberately NOT fenced, and this is a recorded hazard for T09** (the first phase that must fence `policies/`). `.claude/hooks/hooks.py::in_dir(path, name)` matches `/{name}/` **anywhere** in the path, so adding `".sdle"` to `FENCED` would also match `workitems/<id>/.sdle/` and shadow the existing `workitems` reason text. A fence for the repository boundary must anchor to the **start** of the repo-relative path.
4. **`SDLE_OWNED_PREFIXES` is deliberately NOT extended**, so an uncommitted `.sdle/` trips the implement-preflight dirty-tree guard. Fails closed and preserves a §18 Wave A guardrail byte-for-byte; pinned by `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned`. The contrast with `workitems/` (added at T02) is intended: `workitems/` holds runtime state SDLE writes mid-run; `.sdle/` does not. A later phase that makes something write there mid-run revisits this.
5. **`implementation-state/` has no defined meaning.** The contract names it in two diagrams and one phrase and defines no schema, producer or consumer. T05 created it as an empty, versioned, documented slot with no writer, per §27. `baseline.json` is named by `Paths.baseline_file` and policed by `validate`, but no code creates it — T08 owns its schema.
6. **CI and Python 3.11 are unobserved.** T05 adds no syntax beyond what `sdle.py` already uses and no dependency, but "green on 3.11" must be treated as UNKNOWN.
7. **Not adopted, deliberately** (plan Unknowns §8, Scope exclusions): T04 N-2, N-3, N-4, N-7; T03-1, T03-4/5/6, T03-7/8, T03-10; T02 NB-2/4/5. None is incidental to any T05 edit, and adopting N-4 or N-7 would break A5/A7's requirement that `SKILL.md` and `cmd_manifest_build` be byte-identical.

---

## Claims for verifier to independently check

1. Re-run the full suite and confirm **569 passed, raw exit 0**, `--collect-only` = 569, and that `-rsxX` produces no short-summary section. Note the baseline-method caveat above: a run started before an edit and finished after it is not a valid figure.
2. Confirm the arithmetic **500 + 69 = 569** and that `test_units_workitem_resolution.py` collects **96** at both `7b054ee`/`bf4ba5e` and now.
3. Re-run A5 and A7 (the AST extract-and-compare script is reproducible: extract `ast.get_source_segment` for the named definitions from `git show 7b054ee:scripts/sdle.py` and from the working file). Exactly three definitions may differ.
4. Confirm `git diff --name-status 7b054ee -- tests/` has one `M`, zero `D`, zero `R`, and that the one `M` is a single three-line hunk inside `test_runtime_free_commands_is_a_closed_enumerated_set`; and that `tests/conftest.py` is byte-identical.
5. **Test the positive proofs, not just the green suite.** Deliberately break the boundary and confirm it is caught: add a property to `Paths.config_root` that reads `self.workitem` (N1 must fail); plant `state.json` under `.sdle/` (`validate` must exit 3 with `lifecycle_state_in_repository_config`); plant `config.json` under a `workitems/<id>/.sdle/` with no state (must exit 3 with `repository_config_in_workitem`); make `cmd_gate_approve` read `paths.config_file` (N11 clause 3 must fail).
6. Confirm the declared N10 divergence is what it claims: re-run the differential test with the `git add`/`git commit` lines removed and check that the **only** difference is one extra `('implement', 'dirty_tree_bypassed')` audit event, caused by an untracked file rather than by anything reading configuration.
7. Confirm the A19 grep really does match only the one `discovery` line quoted, and nothing else.
8. Confirm `config` appends no audit entry and writes nothing outside `config_root` on any path — success, `config_exists`, `config_root_inside_workitem`, or an injected write failure.
9. Confirm no lifecycle rule moved: `.sdle/config.json` is 53 bytes with two keys, and no phase, gate, approval requirement, artifact-ownership row, rate limit or progress-map entry exists anywhere under `.sdle/`.

---

## Blocker (only if material decision is required)

None. No material architecture, contract or baseline decision was required.
