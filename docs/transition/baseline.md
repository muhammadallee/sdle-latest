# SDLE Transition Baseline — T00 Freeze Record

**Phase:** T00 — Baseline Freeze and Transition Safety Net
**Attempt:** a01
**Produced by:** transition implementer, fresh context
**Authority:** `docs/transition/transition.md` §6; `docs/transition/phases/T00-plan.md`
**Nature:** evidence-only. No product file was created, modified or deleted by T00.

Every command result below was executed and observed in the implementer context
that wrote this file. Nothing is carried over from the planner's ledger without
being labelled as such.

---

## 1. Frozen baseline identity

| Label | Value |
|---|---|
| Baseline commit SHA (`git rev-parse HEAD`) | `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` |
| Working branch (`git rev-parse --abbrev-ref HEAD`) | `transition/workitem-v1` |
| Contract baseline SHA (`transition.md` line 6, `progress.md` line 5) | `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` |
| Verdict | **MATCH** — character-for-character identical |
| Branches containing HEAD (`git branch -a --contains HEAD`) | `transition/workitem-v1` (current), `remotes/origin/wave-a-deterministic-core` |
| SDLE product version | v1.13, reported consistently in all four locations by lint-skill check `version_string_consistent` |

Because HEAD equals the contract baseline SHA exactly, the ancestry requirement
is trivially satisfied: HEAD is an ancestor of itself.

### `git status --porcelain` (verbatim)

```text
?? .claude/agents/
?? .claude/skills/apply-sdle-transition/
?? SDLE-TRANSITION-KICKOFF.md
?? SDLE-TRANSITION-KIT-FILES.txt
?? SDLE-TRANSITION-KIT-README.md
?? docs/transition/
?? tools/
```

All seven lines begin with `??`. **No tracked file is modified (`M`) or deleted
(`D`).** Every dirty path is untracked transition-kit scaffolding introduced by
the migration control plane, not by SDLE product work.

---

## 2. Environment record

| Label | Observed value |
|---|---|
| Operating system | `Windows-11-10.0.26200-SP0` (`python -c "import platform; print(platform.platform())"`) |
| Shell | Git Bash (POSIX `sh`) driving the commands; repository launchers are PowerShell/`sh` |
| Python (`python --version`) | `Python 3.14.6` (tags/v3.14.6:c63aec6, Jun 10 2026, MSC v.1944 64 bit AMD64) |
| pytest (`python -m pytest --version`) | `pytest 9.1.1` |
| CI-pinned Python | `python-version: "3.11"` (`actions/setup-python@v5` step) |
| CI OS matrix | `os: [ubuntu-latest, windows-latest]`, `fail-fast: false` |
| CI steps | `lint-skill`, `python -m pytest -q --tb=line -rf`, `sh scripts/sdle.sh lint-skill` (POSIX), `./scripts/sdle.ps1 lint-skill` (Windows) |

Source for the CI rows: `git show HEAD:.github/workflows/ci.yml`, executed in this
context. The Read tool cannot open `.github/` in this environment (see §6.3), so
`git show` against the HEAD tree is the sanctioned observation path.

### Version-skew statement

The local interpreter is Python **3.14.6**; CI pins Python **3.11**. That is a
three-minor-version skew, and the local run is on Windows only. Consequently:

- the local pytest and lint-skill results recorded in §3 are valid evidence
  **for this environment only** (Windows 11, CPython 3.14.6, pytest 9.1.1);
- they are **not** evidence about `ubuntu-latest`, about `windows-latest`, or
  about CPython 3.11 behaviour at this SHA;
- predicting the CI outcome from the local outcome is forbidden by contract §1
  item 15 and is not done anywhere in this document.

---

## 3. Baseline verification results

### 3.1 `python scripts/sdle.py lint-skill`

**Exit code: 0.** 22 checks, 22 PASS, 0 FAIL. JSON envelope tail:
`"ok": true`, `"failed": []`.

```text
[PASS] tables_wellformed: Parsed 19 phases, 8 gates, 13 migration rows.
[PASS] phase_set_matches_next_phase: identical to PHASE_SEQUENCE
[PASS] phase_set_matches_phase_label_map: identical to PHASE_SEQUENCE
[PASS] phase_set_matches_progress_map: identical to PHASE_SEQUENCE
[PASS] next_phase_chains_sequence: chains PHASE_SEQUENCE in order
[PASS] progress_denominator_matches_phase_count: denominators=['18'] expected={18}
[PASS] gate_registered_gate_constitution: registered everywhere
[PASS] gate_registered_gate_spec: registered everywhere
[PASS] gate_registered_gate_plan: registered everywhere
[PASS] gate_registered_gate_tasks: registered everywhere
[PASS] gate_registered_gate_analyze: registered everywhere
[PASS] gate_registered_gate_design: registered everywhere
[PASS] gate_registered_gate_implement: registered everywhere
[PASS] gate_registered_gate_security: registered everywhere
[PASS] every_phase_has_execution_block: all present
[PASS] single_state_template: templates/state.json is the only host
[PASS] version_string_consistent: all four locations report v1.13
[PASS] migration_covers_every_state_field: every field has a migration row
[PASS] no_powershell_only_cmdlets: none found
[PASS] no_hardcoded_progress_outside_progress_map: none found
[PASS] doc_lists_every_phase_README: all phases present
[PASS] doc_lists_every_phase_SDLE-Reference-Guide: all phases present
```

### 3.2 `python -m pytest -q --tb=line -rf`

**Collected: 230** (`python -m pytest -q --collect-only` → `230 tests collected in 0.09s`).
**Exit code: 1.** Result line: `1 failed, 229 passed in 340.51s (0:05:40)`.

Verbatim failure record:

```text
.............................F.......................................... [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
..............                                                           [100%]
================================== FAILURES ===================================
E   PermissionError: [WinError 5] Access is denied: 'C:\Users\...\pytest-6\test_traversal_matches_the_tra0\target\.workflow\.state.json.ml5kgeot.tmp' -> 'C:\Users\...\pytest-6\test_traversal_matches_the_tra0\target\.workflow\state.json'
C:\workspace\ai\cc\sdle-git-repo\sdle-latest\scripts\sdle.py:463: PermissionError: [WinError 5] Access is denied: ...
=========================== short test summary info ===========================
FAILED tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript
1 failed, 229 passed in 340.51s (0:05:40)
PYTEST_EXIT=1
```

Failing node id, verbatim and complete:

```text
tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript
```

**Disposition: failure mode F1 applied — see §6.1.** Three targeted re-runs of
that exact node id all passed, so the failure is classified `ENVIRONMENT_FLAKE`
and the suite is treated as green with the caveat recorded in §6.1. The raw exit
code above is reported unmodified: it was `1`, not `0`.

### 3.3 `python tools/transition/validate.py`

**Exit code: 0.**

```text
TRANSITION_VALID: complete=0/12 next=T00
```

### 3.4 Linux CI (`ubuntu-latest`)

**NOT_RUN.** Reason: the working branch `transition/workitem-v1` is local-only —
`git branch -a --contains HEAD` shows no remote tracking branch for it, so no CI
run exists for this SHA on this branch that can be observed from this context.
Contract §6 item 2 qualifies this entry with *if available*, so its absence is
not a T00 failure. No CI outcome is predicted.

### 3.5 Windows CI (`windows-latest`)

**NOT_RUN.** Same reason as §3.4. No CI outcome is predicted.

---

## 4. Capability inventory

Fourteen subsections, in the order contract §6 item 3 lists them.

**Disposition vocabulary** (used identically in §5):

- **PRESERVE** — behaviour, interface and evidence remain exactly as observed;
  no transition phase in the contract changes it. Changing phase is `-`.
- **ADAPT** — the capability survives with the same observable contract, but the
  named phase rebinds it to new identity, path or scoping.
- **SUPERSEDE_LATER** — the contract explicitly replaces, removes, demotes or
  reverses this capability at the named phase.

`Evidence` cells are file:line references, test node ids, or named lint-skill
checks, all resolvable without this document.

### 4.1 CLI subcommands

Every `add_parser` registration in `scripts/sdle.py` gets its own row: 33
top-level parsers and 32 nested subcommands, 65 rows. Of the 33 top-level
parsers, 16 are groups that require a nested subcommand, so 17 + 32 = 49 command
paths are directly invocable.

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| `lint-skill` | Runs 22 cross-file sync checks over `SKILL.md` and docs; exits 0 only when all pass. | `scripts/sdle.py:3459`, `:3087`; `tests/test_lint_skill.py::test_the_repo_passes_every_check` | PRESERVE | - |
| `init` | Creates `.workflow/`, writes the v1.13 state template, advances to `requirements_check`. | `scripts/sdle.py:3462`, `:1065`; `tests/test_units_state.py::test_init_creates_state_and_advances_to_first_generation_phase` | ADAPT | T02 |
| `header` | Renders the two-line status assertion header from state. | `scripts/sdle.py:3466`, `:1239`; `tests/test_units_state.py::test_header_renders_both_lines` | ADAPT | T02 |
| `migrate` | Walks the 13-row version chain, upgrading an older `state.json` in place. | `scripts/sdle.py:3469`, `:1017`; `tests/test_units_state.py::test_migrate_walks_the_whole_chain_from_1_0` | ADAPT | T02 |
| `state` (group) | Namespace for state reads and orchestrator-owned writes. | `scripts/sdle.py:3472` | ADAPT | T02 |
| `state get` | Returns full state or one named field; unknown field refuses, corrupt JSON is an integrity failure. | `scripts/sdle.py:3474`, `:1140`; `tests/test_units_state.py::test_state_get_unknown_field_refuses` | ADAPT | T02 |
| `state dump` | Renders the full human status dump including every gate. | `scripts/sdle.py:3477`, `:1257`; `tests/test_units_state.py::test_state_dump_lists_every_gate` | ADAPT | T02 |
| `state set` | Writes only orchestrator-owned fields; engine-owned fields are refused; every write is audited. | `scripts/sdle.py:3479`, `:1183`; `tests/test_units_infra.py::test_state_set_refuses_engine_owned_fields` | ADAPT | T02 |
| `retry` | Guarded retry that refuses while drift re-approval is pending. | `scripts/sdle.py:3486`, `:1206`; `tests/test_units_infra.py::test_retry_refuses_while_drift_reapproval_is_pending` | ADAPT | T02 |
| `audit` (group) | Namespace for the append-only audit ledger. | `scripts/sdle.py:3490` | ADAPT | T02 |
| `audit append` | Appends a `prev_sha`-chained entry and rebaselines `audit_sha`. | `scripts/sdle.py:3492`, `:722`; `tests/test_units_state.py::test_audit_append_chains_entries_and_rebaselines` | ADAPT | T02 |
| `audit verify` | Walks the chain and reports truncation, deletion or a missing file. | `scripts/sdle.py:3499`, `:738`; `tests/test_units_state.py::test_audit_verify_detects_truncation` | ADAPT | T02 |
| `audit rebaseline` | Re-chains and re-signs the ledger; the rebaseline is itself logged. | `scripts/sdle.py:3501`, `:832`; `tests/test_units_state.py::test_audit_rebaseline_is_itself_logged` | ADAPT | T02 |
| `advance` | Moves to `NEXT_PHASE` only; refuses forward jumps, backwards moves, unknown phases, and leaving an unapproved or rejected gate. | `scripts/sdle.py:3506`, `:1460`; `tests/test_units_transitions.py::test_advance_refuses_forward_jumps` | SUPERSEDE_LATER | T07 |
| `gate` (group) | Namespace for the 8 fixed approval gates. | `scripts/sdle.py:3512` | SUPERSEDE_LATER | T09 |
| `gate show` | Reports gate number, label and artifact path, substituting `current_feature_id`. | `scripts/sdle.py:3514`, `:1495`; `tests/test_units_transitions.py::test_gate_show_substitutes_feature_id` | SUPERSEDE_LATER | T09 |
| `gate approve` | Records approval, pins the artifact SHA baseline and advances; refuses when not at that gate or artifact absent. | `scripts/sdle.py:3517`, `:1535`; `tests/test_units_transitions.py::test_gate_approve_refuses_when_artifact_absent` | SUPERSEDE_LATER | T09 |
| `gate reject` | Records feedback and freezes the workflow at the gate. | `scripts/sdle.py:3521`, `:1685`; `tests/test_units_transitions.py::test_gate_reject_records_feedback_and_freezes` | SUPERSEDE_LATER | T09 |
| `drift` (group) | Namespace for artifact drift detection. | `scripts/sdle.py:3526` | PRESERVE | - |
| `drift check` | Compares approved baselines against disk; a missing artifact counts as drifted. | `scripts/sdle.py:3528`, `:1817`; `tests/test_integration_02_to_05.py::test_04_a_missing_artifact_counts_as_drifted` | PRESERVE | - |
| `drift rebaseline` | Moves one gate's baseline to the current SHA. | `scripts/sdle.py:3535`, `:1851`; `tests/test_integration_02_to_05.py::test_04_reapproval_rebaselines_and_resumes` | PRESERVE | - |
| `feature` (group) | Namespace for Spec Kit feature-directory resolution. | `scripts/sdle.py:3539` | SUPERSEDE_LATER | T04 |
| `feature resolve` | Identifies `current_feature_id` from the Spec Kit output; refuses when nothing was produced. | `scripts/sdle.py:3541`, `:1891`; `tests/test_integration_06_to_09.py::test_09_feature_resolution_refuses_when_nothing_was_produced` | SUPERSEDE_LATER | T04 |
| `security-review` (group) | Namespace for Phase 17 support. | `scripts/sdle.py:3544` | ADAPT | T02 |
| `security-review begin` | Pins the review filename into state. | `scripts/sdle.py:3546`, `:1931` | ADAPT | T02 |
| `security-review evidence` | Diffs against `implementation_base_ref`, not `HEAD~1`; falls back when no ref pinned. | `scripts/sdle.py:3548`, `:2924`; `tests/test_integration_06_to_09.py::test_06_security_review_diffs_against_the_pinned_ref` | PRESERVE | - |
| `artifact` (group) | Namespace for artifact bookkeeping. | `scripts/sdle.py:3553` | ADAPT | T02 |
| `artifact path` | Resolves a gate's artifact path from ARTIFACT_OWNERSHIP. | `scripts/sdle.py:3555`, `:1355`; lint-skill `gate_registered_*` | ADAPT | T04 |
| `artifact record` | Records the artifact SHA fingerprint for the current phase. | `scripts/sdle.py:3558`, `:2008` | PRESERVE | - |
| `limit` (group) | Namespace for rate limits and counters. | `scripts/sdle.py:3567` | PRESERVE | - |
| `limit set` | Changes a configured maximum; the change is audited, not hand-edited. | `scripts/sdle.py:3569`, `:2082`; `tests/test_integration_02_to_05.py::test_02_raising_the_limit_is_audited_not_hand_edited` | PRESERVE | - |
| `limit reset` | Zeroes one phase's counters. | `scripts/sdle.py:3573`, `:2107`; `tests/test_integration_02_to_05.py::test_02_remediation_counters_never_auto_reset` | PRESERVE | - |
| `checkpoint` (group) | Namespace for in-phase crash recovery. | `scripts/sdle.py:3579` | ADAPT | T02 |
| `checkpoint set` | Stores `phase_checkpoint` in state. | `scripts/sdle.py:3581`, `:2135` | ADAPT | T02 |
| `checkpoint get` | Reads the stored checkpoint. | `scripts/sdle.py:3584`, `:2135` | ADAPT | T02 |
| `checkpoint clear` | Clears the stored checkpoint. | `scripts/sdle.py:3585`, `:2135` | ADAPT | T02 |
| `confirm` (group) | Namespace for two-step confirmations. | `scripts/sdle.py:3587` | PRESERVE | - |
| `confirm set` | Arms a pending two-step action in `pending_confirm_action`. | `scripts/sdle.py:3589`, `:2158`; `tests/test_integration_02_to_05.py::test_03_skip_is_two_step` | PRESERVE | - |
| `confirm check` | Verifies the pending action matches before executing it. | `scripts/sdle.py:3592`, `:2158`; `tests/test_integration_06_to_09.py::test_08_confirm_reset_without_a_pending_one_is_refused` | PRESERVE | - |
| `confirm clear` | Stale-confirmation guard: cancels anything pending. | `scripts/sdle.py:3595`, `:2158`; `tests/test_integration_02_to_05.py::test_03_stale_confirmation_guard_cancels_a_pending_skip` | PRESERVE | - |
| `remediate` (group) | Namespace for post-rejection re-runs. | `scripts/sdle.py:3599` | PRESERVE | - |
| `remediate begin` | Checks `max_remediation_attempts` and writes the feedback file from canonical state. | `scripts/sdle.py:3601`, `:2199`; `tests/test_integration_02_to_05.py::test_02_remediation_limit_halts_without_invoking_anything` | PRESERVE | - |
| `remediate finish` | Archives the feedback file and removes it. | `scripts/sdle.py:3604`, `:2258`; `tests/test_integration_02_to_05.py::test_02_remediation_finish_archives_and_removes_feedback` | PRESERVE | - |
| `skip` | Advances without a verified artifact; requires failed status, is two-step, and is permanently logged. | `scripts/sdle.py:3608`, `:2288`; `tests/test_integration_02_to_05.py::test_03_skip_is_permanently_logged` | SUPERSEDE_LATER | T07 |
| `restart` | Rolls back to an earlier phase; two-step, clears only downstream approvals, trims `phase_history`, refuses gate phases and out-of-range targets. | `scripts/sdle.py:3612`, `:2335`; `tests/test_integration_06_to_09.py::test_08_restart_clears_only_downstream_approvals` | SUPERSEDE_LATER | T07 |
| `reset` | Deletes all workflow state; two-step, preserves generated artifacts. | `scripts/sdle.py:3617`, `:2419`; `tests/test_integration_06_to_09.py::test_08_reset_is_two_step_and_preserves_artifacts` | ADAPT | T02 |
| `doctor` | Recovery consistency check: detects hand-edited forward jumps and backwards state, tolerates a gap of two. | `scripts/sdle.py:3621`, `:2448`; `tests/test_integration_06_to_09.py::test_08_doctor_detects_a_hand_edited_forward_jump` | ADAPT | T07 |
| `accept-state` | Acknowledges a detected state jump and logs it. | `scripts/sdle.py:3623`, `:2500`; `tests/test_integration_06_to_09.py::test_08_accept_state_acknowledges_and_logs` | PRESERVE | - |
| `accept-content` | Acknowledges flagged untrusted content; refuses when nothing is flagged. | `scripts/sdle.py:3626`, `:2625`; `tests/test_integration_02_to_05.py::test_05_accept_content_refuses_when_nothing_flagged` | PRESERVE | - |
| `repo-staleness` | Reports commits newer than the newest approval, scoped to recorded artifact paths; silent without approvals. | `scripts/sdle.py:3629`, `:2522`; `tests/test_integration_06_to_09.py::test_07_staleness_is_scoped_to_recorded_artifact_paths` | PRESERVE | - |
| `preflight` | Bootstrap prerequisites: halts on missing Spec Kit, missing/empty `requirements/`, undiscoverable skills; lists guidance files. | `scripts/sdle.py:3632`, `:2963`; `tests/test_integration_06_to_09.py::test_09_healthy_project_passes_preflight` | ADAPT | T03 |
| `scan` | Untrusted-content scan of one path against 11 injection patterns; refuses (exit 1) and arms a pending acknowledgement when flagged. | `scripts/sdle.py:3637`, `:2595`; `tests/test_integration_02_to_05.py::test_05_every_injection_pattern_fires` | PRESERVE | - |
| `clarify` (group) | Namespace for clarification responses. | `scripts/sdle.py:3641` | ADAPT | T02 |
| `clarify save` | Scans and saves a clarification response; a flagged response is still saved but marked. | `scripts/sdle.py:3643`, `:2645`; `tests/test_integration_02_to_05.py::test_05_a_flagged_clarification_is_still_saved_but_marked` | ADAPT | T02 |
| `guidance` (group) | Namespace for per-phase steering files. | `scripts/sdle.py:3648` | SUPERSEDE_LATER | T07 |
| `guidance path` | Resolves the Guidance File Map entry for a phase from `modules/phase-execution.md`. | `scripts/sdle.py:3650`, `:2666`; `tests/test_integration_06_to_09.py::test_09_guidance_map_resolves_from_the_skill_file` | SUPERSEDE_LATER | T07 |
| `implement` (group) | Namespace for Phase 15 support. | `scripts/sdle.py:3654` | SUPERSEDE_LATER | T07 |
| `implement preflight` | Dirty-tree guard; pins `implementation_base_ref` to HEAD; SDLE-owned paths are not dirt; `--bypass` proceeds and is logged. | `scripts/sdle.py:3656`, `:2693`; `tests/test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref` | PRESERVE | - |
| `manifest` (group) | Namespace for the Gate 7 artifact. | `scripts/sdle.py:3663` | SUPERSEDE_LATER | T09 |
| `manifest build` | Builds the file list, runs the secrets scan and the detected test runner; a manifest without scan or tests is refused at Gate 7. | `scripts/sdle.py:3665`, `:2826`; `tests/test_integration_06_to_09.py::test_06_gate_seven_refuses_a_manifest_without_scan_or_tests` | PRESERVE | - |
| `lock` (group) | Namespace for the repository-global session lock. | `scripts/sdle.py:3671` | SUPERSEDE_LATER | T02 |
| `lock acquire` | Writes `.workflow/.lock` with timestamp + session; reports a fresh foreign lock, ignores a stale one, requires a session. | `scripts/sdle.py:3673`, `:614`; `tests/test_units_state.py::test_lock_acquire_ignores_a_stale_foreign_lock` | SUPERSEDE_LATER | T02 |
| `lock release` | Removes the lock file. | `scripts/sdle.py:3675`, `:656`; `tests/test_units_state.py::test_lock_release_removes_the_file` | SUPERSEDE_LATER | T02 |
| `sha` | Prints the lowercase-hex SHA-256 of a file; refuses a missing file. | `scripts/sdle.py:3678`, `:3405`; `tests/test_units_state.py::test_sha_is_lowercase_hex` | PRESERVE | - |
| `constants` | Dumps every parsed constant table from `SKILL.md` as JSON. | `scripts/sdle.py:3682`, `:3417` | SUPERSEDE_LATER | T07 |

### 4.2 Exit codes

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| `EXIT_OK = 0` | Successful command; envelope carries `"ok": true`. | `scripts/sdle.py:37`; `tests/test_units_cli.py::test_help_exits_zero` | PRESERVE | - |
| `EXIT_REFUSED = 1` | Deterministic refusal with a `reason` code; survives the process boundary. | `scripts/sdle.py:38`; `tests/test_units_cli.py::test_refusal_exit_code_survives_the_process_boundary` | PRESERVE | - |
| `EXIT_USAGE = 2` | Argument/usage error, never a traceback. | `scripts/sdle.py:39`; `tests/test_units_cli.py::test_unknown_subcommand_is_usage_error_not_traceback` | PRESERVE | - |
| `EXIT_INTEGRITY = 3` | State/audit integrity failure such as missing or corrupt `state.json`. | `scripts/sdle.py:40`; `tests/test_units_cli.py::test_integrity_exit_code_survives_the_process_boundary` | PRESERVE | - |

### 4.3 State fields

All 25 top-level keys of `.claude/skills/sdle/templates/state.json` plus the 8
`approvals` gate keys. lint-skill `migration_covers_every_state_field` proves
every one of these has a migration row.

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| `workflow_version` | `"1.13"` at the template; drives the migration chain. | `templates/state.json:2`; lint-skill `version_string_consistent` | ADAPT | T02 |
| `project_name` | `null` until `init` infers it from the first requirements heading or takes `--project-name`. | `templates/state.json:3`; `tests/test_units_state.py::test_init_infers_project_name_from_first_heading` | ADAPT | T01 |
| `current_phase` | `"requirements_check"` at template; always one of PHASE_SEQUENCE. | `templates/state.json:4`; `scripts/sdle.py:1460` | SUPERSEDE_LATER | T07 |
| `status` | `"pending"` at template; mapped to display text by the header renderer. | `templates/state.json:5`; `tests/test_units_state.py::test_header_maps_every_status_to_its_display_text` | PRESERVE | - |
| `progress` | `"1/18"` at template; every value comes from PROGRESS_MAP only. | `templates/state.json:6`; lint-skill `no_hardcoded_progress_outside_progress_map` | SUPERSEDE_LATER | T07 |
| `last_updated` | `null` until the first save; ISO timestamp thereafter. | `templates/state.json:7`; `scripts/sdle.py:597` | PRESERVE | - |
| `current_artifact` | Path of the artifact under review at the current phase. | `templates/state.json:8`; `scripts/sdle.py:2008` | ADAPT | T04 |
| `current_artifact_sha` | SHA-256 fingerprint of `current_artifact`; migration normalises uppercase PowerShell digests. | `templates/state.json:9`; `tests/test_units_state.py::test_migrate_normalizes_uppercase_shas_from_powershell` | PRESERVE | - |
| `current_feature_id` | Spec Kit feature directory id; substituted into artifact path templates. | `templates/state.json:10`; `tests/test_units_transitions.py::test_gate_show_substitutes_feature_id` | SUPERSEDE_LATER | T04 |
| `security_review_artifact` | Filename pinned by `security-review begin` for Phase 17. | `templates/state.json:11`; `scripts/sdle.py:1931` | ADAPT | T02 |
| `implementation_base_ref` | Git ref pinned by `implement preflight`; security-review evidence diffs against it. | `templates/state.json:12`; `tests/test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref` | PRESERVE | - |
| `phase_checkpoint` | In-phase crash-recovery marker set by `checkpoint set`. | `templates/state.json:13`; `scripts/sdle.py:2135` | PRESERVE | - |
| `pending_confirm_action` | Arms two-step confirmations and the untrusted-content acknowledgement; any other command cancels it. | `templates/state.json:14`; `tests/test_integration_06_to_09.py::test_08_a_pending_reset_is_cancelled_by_any_other_command` | PRESERVE | - |
| `speckit_initialized` | `true` at template; preflight halts when Spec Kit is missing. | `templates/state.json:15`; `tests/test_integration_06_to_09.py::test_09_missing_speckit_halts_first` | ADAPT | T04 |
| `speckit_skill_prefix` | Discovered Spec Kit skill prefix, persisted by preflight. | `templates/state.json:16`; `tests/test_units_infra.py::test_preflight_persists_the_discovered_prefix` | ADAPT | T04 |
| `verbose` | Boolean; `state set` rejects a non-boolean. | `templates/state.json:17`; `tests/test_units_infra.py::test_state_set_rejects_a_non_boolean_for_verbose` | PRESERVE | - |
| `clarification_phase` | Records the phase a clarification round belongs to. | `templates/state.json:18`; `scripts/sdle.py:2645` | ADAPT | T02 |
| `rate_limits` | `{"max_remediation_attempts": 3, "max_retry_attempts": 3}`; read via `limit()`. | `templates/state.json:19-22`; `scripts/sdle.py:1999` | PRESERVE | - |
| `attempt_counts` | Per-phase counters; never auto-reset. | `templates/state.json:23`; `tests/test_integration_02_to_05.py::test_02_remediation_counters_never_auto_reset` | PRESERVE | - |
| `approvals` | Object with exactly the 8 gate keys, all `null` at template. | `templates/state.json:24-33`; lint-skill `gate_registered_*` (8 checks) | SUPERSEDE_LATER | T09 |
| `approvals.gate_constitution` | Gate 1 approval record; `null` until approved. | `templates/state.json:25`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_spec` | Gate 2 approval record. | `templates/state.json:26`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_plan` | Gate 3 approval record. | `templates/state.json:27`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_tasks` | Gate 4 approval record. | `templates/state.json:28`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_analyze` | Gate 5 approval record. | `templates/state.json:29`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_design` | Gate 6 approval record. | `templates/state.json:30`; `scripts/sdle.py:1535` | SUPERSEDE_LATER | T09 |
| `approvals.gate_implement` | Gate 7 approval record; requires a built manifest. | `templates/state.json:31`; `tests/test_integration_06_to_09.py::test_06_gate_seven_accepts_a_built_manifest` | SUPERSEDE_LATER | T09 |
| `approvals.gate_security` | Gate 8 approval record; the final gate completes the workflow. | `templates/state.json:32`; `tests/test_units_transitions.py::test_final_gate_completes_the_workflow` | SUPERSEDE_LATER | T09 |
| `artifact_shas` | Per-gate approved SHA baselines; the input to drift detection. | `templates/state.json:34`; `tests/test_integration_01_happy_path.py::test_all_eight_gates_approved_with_baselines` | PRESERVE | - |
| `audit_sha` | Whole-file SHA-256 of `audit.md`, rebaselined on every append. | `templates/state.json:35`; `scripts/sdle.py:718` | ADAPT | T02 |
| `drift_queue` | Ordered list of drifted gates awaiting re-approval, most upstream first. | `templates/state.json:36`; `tests/test_integration_02_to_05.py::test_04_multiple_drifted_gates_queue_most_upstream_first` | PRESERVE | - |
| `pending_phase` | Remembers the phase interrupted by drift queueing so it can resume. | `templates/state.json:37`; `tests/test_integration_02_to_05.py::test_04_queueing_halts_the_workflow_and_remembers_what_was_interrupted` | PRESERVE | - |
| `phase_history` | Append-only ordered record of every phase entered; trimmed by `restart`. | `templates/state.json:38`; `tests/test_integration_01_happy_path.py::test_phase_history_records_every_phase_in_order` | SUPERSEDE_LATER | T07 |

### 4.4 Audit behavior

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Append-only ledger | `.workflow/audit.md` is only ever appended to by `audit append`. | `scripts/sdle.py:665-734`; `tests/test_integration_01_happy_path.py::test_audit_chain_survives_the_whole_run` | ADAPT | T02 |
| Per-entry `prev_sha` chain | Each entry digests the previous block, so any edit breaks the chain. | `scripts/sdle.py:672` `_entry_digest`; `tests/test_units_state.py::test_audit_verify_detects_a_deleted_middle_entry` | PRESERVE | - |
| Whole-file `audit_sha` | `audit append` rebaselines `state["audit_sha"] = sha256_file(audit.md)`. | `scripts/sdle.py:718`; `tests/test_units_state.py::test_audit_append_chains_entries_and_rebaselines` | PRESERVE | - |
| Tamper halt | An edited ledger halts the workflow until explicitly rebaselined. | `scripts/sdle.py:738`; `tests/test_integration_06_to_09.py::test_07_edited_audit_halts_until_rebaselined` | PRESERVE | - |
| Mismatch persistence | The mismatch survives until acknowledged; it is not cleared by an unrelated command. | `tests/test_integration_06_to_09.py::test_07_the_mismatch_persists_until_acknowledged` | PRESERVE | - |
| Rebaseline is logged | `audit rebaseline` writes its own audit entry. | `scripts/sdle.py:832-846`; `tests/test_units_state.py::test_audit_rebaseline_is_itself_logged` | PRESERVE | - |
| Missing-file / truncation detection | Verify reports a missing ledger and detects truncation; skips when no baseline exists. | `tests/test_units_state.py::test_audit_verify_reports_missing_file`, `::test_audit_verify_detects_truncation`, `::test_audit_verify_skips_when_no_baseline` | PRESERVE | - |
| Audit ledger location | Ledger lives at the repository-global `.workflow/audit.md`. | `scripts/sdle.py` `Paths.audit_file`; contract §18 `.workflow/` repo-global runtime | SUPERSEDE_LATER | T02 |

### 4.5 Lock behavior

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Repository-global lock file | One `.workflow/.lock` for the whole repository, holding `"<iso-timestamp> <session>"`. | `scripts/sdle.py:597-612`; `tests/test_units_state.py::test_init_writes_lock_when_session_given` | SUPERSEDE_LATER | T02 |
| Freshness window | `LOCK_FRESH_SECONDS = 600`; a foreign lock younger than that is "fresh". | `scripts/sdle.py:594`, `:633` | SUPERSEDE_LATER | T02 |
| Fresh foreign lock warns, never halts | A fresh foreign lock is reported but does not block the workflow. | `tests/test_integration_06_to_09.py::test_07_foreign_fresh_lock_warns_but_never_halts`; `tests/test_units_state.py::test_lock_acquire_reports_a_fresh_foreign_lock` | SUPERSEDE_LATER | T02 |
| Stale foreign lock ignored | A lock older than the freshness window is ignored. | `tests/test_units_state.py::test_lock_acquire_ignores_a_stale_foreign_lock` | SUPERSEDE_LATER | T02 |
| Own lock is not foreign | Re-acquiring your own session's lock is a no-op, not a conflict. | `tests/test_units_state.py::test_lock_acquire_on_own_lock_is_not_foreign` | SUPERSEDE_LATER | T02 |
| Session is mandatory | `lock acquire` refuses without a session identifier. | `tests/test_units_state.py::test_lock_acquire_requires_a_session` | SUPERSEDE_LATER | T02 |
| Refresh on every save | `touch_lock` refreshes the lock timestamp on every state save. | `scripts/sdle.py:597`; `tests/test_integration_01_happy_path.py::test_lock_is_refreshed_on_every_save` | SUPERSEDE_LATER | T02 |

### 4.6 Rate limits

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| `max_remediation_attempts` | Default 3; `remediate begin` halts at the cap without invoking anything. | `scripts/sdle.py:884`, `:2218`; `tests/test_integration_02_to_05.py::test_02_remediation_limit_halts_without_invoking_anything` | PRESERVE | - |
| `max_retry_attempts` | Default 3; `retry` stops being offered at the cap. | `scripts/sdle.py:884`, `:2050`; `tests/test_integration_02_to_05.py::test_03_retry_limit_stops_offering_retry` | PRESERVE | - |
| `limit()` accessor | Reads `state["rate_limits"][name]`, defaulting to 3 when absent. | `scripts/sdle.py:1999-2000` | PRESERVE | - |
| Counters never auto-reset | `attempt_counts` are only cleared by an explicit `limit reset`. | `tests/test_integration_02_to_05.py::test_02_remediation_counters_never_auto_reset` | PRESERVE | - |
| Successful verification resets retries | A passing verification zeroes the retry counter for that phase. | `tests/test_integration_02_to_05.py::test_03_successful_verification_resets_the_retry_counter` | PRESERVE | - |
| Raising a limit is audited | `limit set` writes an audit entry; hand-editing state is not the supported path. | `tests/test_integration_02_to_05.py::test_02_raising_the_limit_is_audited_not_hand_edited` | PRESERVE | - |

### 4.7 Drift behavior

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Baseline comparison | `compute_drift` compares each approved gate's recorded SHA against the file on disk. | `scripts/sdle.py:1778`; `tests/test_integration_02_to_05.py::test_04_drift_is_detected_against_the_baseline` | PRESERVE | - |
| Missing artifact counts as drift | A deleted approved artifact is drift, not a silent pass. | `tests/test_integration_02_to_05.py::test_04_a_missing_artifact_counts_as_drifted` | PRESERVE | - |
| Unapproved gates are never checked | Drift is scoped strictly to gates that hold an approval. | `tests/test_integration_02_to_05.py::test_04_unapproved_gates_are_never_drift_checked` | PRESERVE | - |
| Queue halts and remembers | Drift queues the affected gates, halts the workflow and stores `pending_phase`. | `tests/test_integration_02_to_05.py::test_04_queueing_halts_the_workflow_and_remembers_what_was_interrupted` | PRESERVE | - |
| Most-upstream-first ordering | Multiple drifted gates queue in PHASE_SEQUENCE order, upstream first. | `tests/test_integration_02_to_05.py::test_04_multiple_drifted_gates_queue_most_upstream_first` | PRESERVE | - |
| One-at-a-time walk, order enforced | Re-approval walks the queue singly; approving out of order is refused. | `tests/test_integration_02_to_05.py::test_04_drift_reapproval_walks_the_queue_one_at_a_time`, `::test_04_approving_out_of_queue_order_is_refused` | PRESERVE | - |
| Re-approval rebaselines and resumes | Approving a queued gate moves its baseline and resumes `pending_phase`. | `tests/test_integration_02_to_05.py::test_04_reapproval_rebaselines_and_resumes` | PRESERVE | - |
| Rejection clears the queue | Rejecting a drifted gate clears the queue and does not resume. | `tests/test_integration_02_to_05.py::test_04_rejection_clears_the_queue_and_does_not_resume` | PRESERVE | - |
| Git diff evidence | Drift output includes a git diff for tracked artifacts. | `tests/test_integration_02_to_05.py::test_04_drift_includes_a_git_diff_for_tracked_artifacts` | PRESERVE | - |
| Retry is blocked while drift pending | `retry` refuses while drift re-approval is outstanding. | `tests/test_units_infra.py::test_retry_refuses_while_drift_reapproval_is_pending` | PRESERVE | - |

### 4.8 Hooks

All four wired entries in `.claude/settings.json`, each dispatching
`python .claude/hooks/hooks.py <name>`.

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| PreToolUse `write-fence` (matcher `Write` / `Edit` / `MultiEdit`) | Denies model writes to governance files; the engine is their single writer. | `.claude/settings.json` PreToolUse[0]; `.claude/hooks/hooks.py:129`; `tests/test_hooks.py::test_write_fence_denies_governance_files` | ADAPT | T02 |
| PreToolUse `untrusted-read` (matcher `Read`) | Warn-and-acknowledge on flagged `requirements/`, `guidance/`, `clarifications/` reads; silent on clean or unrelated files. | `.claude/settings.json` PreToolUse[1]; `.claude/hooks/hooks.py:141`; `tests/test_hooks.py::test_untrusted_read_asks_on_flagged_requirements` | ADAPT | T02 |
| PreToolUse `dirty-tree` (matcher `Bash`) | Asks during the implement phase when preflight has not run; silent outside that phase, once the base ref is pinned, on an acknowledged bypass, and with no workflow. | `.claude/settings.json` PreToolUse[2]; `.claude/hooks/hooks.py:173`; `tests/test_hooks.py::test_dirty_tree_asks_when_preflight_has_not_run` | ADAPT | T02 |
| PostToolUse `secrets-scan` (matcher `Write` / `Edit`) | Flags credentials in written content without ever reproducing the secret; silent on clean code. | `.claude/settings.json` PostToolUse[0]; `.claude/hooks/hooks.py:201`; `tests/test_hooks.py::test_secrets_hook_never_reproduces_the_secret` | ADAPT | T02 |
| Single pattern source | Both scanning hooks import the engine's pattern lists rather than copying them. | `.claude/hooks/hooks.py:219`; `tests/test_hooks.py::test_secrets_hook_uses_the_engine_patterns_not_a_copy`, `::test_untrusted_read_uses_the_engine_patterns_not_a_copy` | PRESERVE | - |
| Registration completeness | Every guard the test suite knows about is registered in settings. | `tests/test_hooks.py::test_every_guard_is_registered` | ADAPT | T02 |
| Malformed-payload safety | A malformed hook payload never breaks the tool call. | `tests/test_hooks.py::test_a_malformed_payload_never_breaks_the_tool_call` | PRESERVE | - |
| Interpreter resolution | The registered `python` interpreter resolves on this machine. | `tests/test_hooks.py::test_the_registered_interpreter_resolves_on_this_machine` | PRESERVE | - |

### 4.9 Dirty-tree behavior

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Implement halts on a dirty tree | Uncommitted changes stop Phase 15 before implementation starts. | `scripts/sdle.py:2693`; `tests/test_integration_06_to_09.py::test_06_dirty_tree_halts_implement` | PRESERVE | - |
| SDLE-owned paths are not dirt | `.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/` are excluded. | `scripts/sdle.py:2688` `SDLE_OWNED_PREFIXES`; `tests/test_integration_06_to_09.py::test_06_sdle_owned_paths_are_not_dirt` | ADAPT | T02 |
| Explicit bypass, always logged | `--bypass` proceeds and writes the bypass into the audit ledger. | `scripts/sdle.py:2749`; `tests/test_integration_06_to_09.py::test_06_bypass_proceeds_and_is_logged` | PRESERVE | - |
| Hook-side echo of the guard | The `dirty-tree` Bash hook mirrors the same rule and respects an acknowledged bypass. | `.claude/hooks/hooks.py:173`; `tests/test_hooks.py::test_dirty_tree_respects_an_acknowledged_bypass` | ADAPT | T02 |

### 4.10 Untrusted-content scan

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| 11 injection patterns | `INJECTION_PATTERNS` covers ignore-previous-instructions, disregard-rules, you-are-now, act-as-orchestrator, new-persona, approve-gate, skip-gate, advance-phase, mark-approved, set-status, edit-state. | `scripts/sdle.py:2569-2582`; `tests/test_integration_02_to_05.py::test_05_every_injection_pattern_fires` | PRESERVE | - |
| Line-scoped, first-match-per-line | `scan_text` reports line number, stripped text and pattern name, one hit per line. | `scripts/sdle.py:2584-2593` | PRESERVE | - |
| Clean content passes silently | No matches means exit 0 and no prompt. | `tests/test_integration_02_to_05.py::test_05_clean_content_passes_silently` | PRESERVE | - |
| Flag arms an acknowledgement | A hit sets `pending_confirm_action = accept_content:<path>` and refuses with exit 1. | `scripts/sdle.py:2607-2622`; `tests/test_integration_02_to_05.py::test_05_flag_sets_a_pending_acknowledgement` | PRESERVE | - |
| Acknowledge clears and logs | `accept-content` clears the flag and writes an audit entry; refuses when nothing is flagged. | `scripts/sdle.py:2625`; `tests/test_integration_02_to_05.py::test_05_accept_content_clears_and_logs` | PRESERVE | - |
| Editing the file clears the finding | Removing the offending lines makes the scan pass. | `tests/test_integration_02_to_05.py::test_05_editing_the_file_makes_the_scan_pass` | PRESERVE | - |
| Clarifications are scanned too | Clarification responses go through the same scan and are saved-but-marked when flagged. | `scripts/sdle.py:2645`; `tests/test_integration_02_to_05.py::test_05_a_flagged_clarification_is_still_saved_but_marked` | ADAPT | T02 |
| Data-not-instructions framing | The refusal message states SDLE treats the file as data and will not act on the lines. | `scripts/sdle.py:2616-2621` | PRESERVE | - |

### 4.11 Secrets scan

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| 6 credential patterns | AWS access key, private key material, GitHub token, secret API key (`sk-` incl. `sk-proj-`), hardcoded credential assignment, bearer token. | `scripts/sdle.py:2753-2763`; `tests/test_hooks.py::test_secrets_hook_flags_a_credential` | PRESERVE | - |
| Scan scoped to text suffixes | `TEXT_SUFFIXES` limits scanning to 28 source/config/text extensions. | `scripts/sdle.py:2765-2769` | PRESERVE | - |
| Masked reporting | Findings are reported without reproducing the secret value. | `scripts/sdle.py:2862`; `tests/test_integration_06_to_09.py::test_06_manifest_flags_a_hardcoded_key_masked`; `tests/test_hooks.py::test_secrets_hook_never_reproduces_the_secret` | PRESERVE | - |
| Runs inside `manifest build` | The Gate 7 manifest carries the scan result as a mandatory section. | `scripts/sdle.py:2826`; `tests/test_integration_06_to_09.py::test_06_manifest_always_has_the_mandatory_sections` | PRESERVE | - |
| Silent on clean code | No finding means no prompt. | `tests/test_hooks.py::test_secrets_hook_is_silent_on_clean_code` | PRESERVE | - |

### 4.12 Test evidence

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Runner auto-detection | `detect_test_runner` resolves npm / pytest / cargo / maven / gradle from repository markers, else `None`. | `scripts/sdle.py:2772-2796` | PRESERVE | - |
| Bounded execution | `run_tests` runs with a timeout and captures stdout+stderr, keeping the last 40 lines. | `scripts/sdle.py:2799-2824` | PRESERVE | - |
| Honest status reporting | Status is `passed` / `FAILED` / `no runner detected` / `runner not installed` / `timed out after Ns`; a real failing run is recorded as failing. | `scripts/sdle.py:2812-2824`; `tests/test_integration_06_to_09.py::test_06_test_evidence_records_a_real_failing_run` | PRESERVE | - |
| Gate 7 enforcement | A manifest without a scan or test section is refused at Gate 7. | `tests/test_integration_06_to_09.py::test_06_gate_seven_refuses_a_manifest_without_scan_or_tests` | SUPERSEDE_LATER | T09 |
| Built manifest accepted | A complete manifest satisfies Gate 7. | `tests/test_integration_06_to_09.py::test_06_gate_seven_accepts_a_built_manifest` | SUPERSEDE_LATER | T09 |

### 4.13 Implementation-base-ref behavior

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| Pinned by `implement preflight` | Sets `state["implementation_base_ref"]` to the current HEAD, or `None` when unavailable. | `scripts/sdle.py:2697`, `:2706`; `tests/test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref` | PRESERVE | - |
| Security review diffs against it | Phase 17 evidence diffs against the pinned ref rather than `HEAD~1`. | `scripts/sdle.py:2926`, `:3549`; `tests/test_integration_06_to_09.py::test_06_security_review_diffs_against_the_pinned_ref` | PRESERVE | - |
| Documented fallback | With no ref pinned the review falls back to a defined alternative instead of failing. | `tests/test_integration_06_to_09.py::test_06_security_review_falls_back_when_no_ref_pinned` | PRESERVE | - |
| Surfaced in the status dump | The dump prints `Implementation base ref: <value or 'none'>`. | `scripts/sdle.py:1296` | PRESERVE | - |
| Silences the dirty-tree hook | Once the base ref is pinned the hook stops asking. | `.claude/hooks/hooks.py:173`; `tests/test_hooks.py::test_dirty_tree_is_silent_once_the_base_ref_is_pinned` | PRESERVE | - |

### 4.14 Migrations

13 migration rows, exactly as lint-skill parses them
(`tables_wellformed: Parsed 19 phases, 8 gates, 13 migration rows`) and as
`python scripts/sdle.py constants` reports in `version_chain`. lint-skill
`migration_covers_every_state_field` proves every state field is covered.

| Item | Observed behavior | Evidence | Disposition | Changing phase |
|---|---|---|---|---|
| `1.0 -> 1.1` | Chain step applied by `migrate_state`. | `scripts/sdle.py:980`; `constants.version_chain[0]` | ADAPT | T02 |
| `1.1 -> 1.2` | Chain step applied by `migrate_state`. | `constants.version_chain[1]` | ADAPT | T02 |
| `1.2 -> 1.3` | Chain step applied by `migrate_state`. | `constants.version_chain[2]` | ADAPT | T02 |
| `1.3 -> 1.4` | Chain step applied by `migrate_state`. | `constants.version_chain[3]` | ADAPT | T02 |
| `1.4 -> 1.5` | Chain step applied by `migrate_state`. | `constants.version_chain[4]` | ADAPT | T02 |
| `1.5 -> 1.6` | Chain step applied by `migrate_state`. | `constants.version_chain[5]` | ADAPT | T02 |
| `1.6 -> 1.7` | Chain step applied by `migrate_state`. | `constants.version_chain[6]` | ADAPT | T02 |
| `1.7 -> 1.8` | Chain step applied by `migrate_state`. | `constants.version_chain[7]` | ADAPT | T02 |
| `1.8 -> 1.9` | Warns about reordered phases and recomputes `progress`. | `constants.version_chain[8]`; `tests/test_units_state.py::test_migrate_1_8_warns_about_reordered_phases`, `::test_migrate_1_8_recomputes_progress` | ADAPT | T02 |
| `1.9 -> 1.10` | Chain step applied by `migrate_state`. | `constants.version_chain[9]` | ADAPT | T02 |
| `1.10 -> 1.11` | Chain step applied by `migrate_state`. | `constants.version_chain[10]` | ADAPT | T02 |
| `1.11 -> 1.12` | Chain step applied by `migrate_state`. | `constants.version_chain[11]` | ADAPT | T02 |
| `1.12 -> 1.13` | Terminal step; adds `implementation_base_ref` and normalises uppercase SHAs. | `scripts/sdle.py:944`, `:952`; `tests/test_units_state.py::test_migrate_adds_implementation_base_ref` | ADAPT | T02 |
| Idempotence | Re-running `migrate` on an already-current state is a no-op. | `tests/test_units_state.py::test_migrate_is_idempotent` | PRESERVE | - |
| Unknown version refused | An unrecognised `workflow_version` is refused, not guessed. | `tests/test_units_state.py::test_migrate_refuses_unknown_version` | PRESERVE | - |

---

## 5. Transition regression matrix

Every capability of contract §18 appears exactly once (31 rows), followed by
capabilities T00 discovered that §18 does not enumerate, marked `NOT_IN_S18`.
Together they cover every Item in §4.

### Vocabulary mapping rule (declared, not improvised per row)

Contract §18 uses its own labels. This table keeps the §18 label verbatim in its
own column and maps it into the three-value disposition vocabulary by a fixed
rule:

| §18 label family | Mapped disposition |
|---|---|
| `PRESERVE`, `PRESERVE unless deliberately versioned`, `PRESERVE/EVOLVE`, `PRESERVE initially; ...` | PRESERVE |
| `ADAPT to WorkItem paths` | ADAPT |
| `REPLACE`, `REMOVE/RESCOPE`, `DEMOTE`, `REVERSE`, `MIGRATE` | SUPERSEDE_LATER |
| `ADD / ENFORCE` | ADAPT — the capability is **absent at this baseline** and is added by the named phase, so there is nothing to preserve and nothing to supersede |

`Regression anchor` names what will actually detect a regression. `NO_ANCHOR` is
recorded honestly where none exists; it is never padded with an unrelated test.

### §4 → §5 mapping rule (so completeness is checkable, not arguable)

Every Item in §4 maps to exactly one row below, by this rule: a nested
subcommand maps through its family row (e.g. `audit append` → "`prev_sha` entry
chain plus whole-file `audit_sha`"; `drift check` → "Drift detection"; `limit
set` → "`max_remediation_attempts` / `max_retry_attempts` caps"). The two Items
whose family row is not obvious are named here so no sweep has to guess, and in
both cases the disposition of the Item and of its row agree:

- `security-review begin` (§4.1, ADAPT T02) → the "`state.json` schema, 25
  top-level fields" row (ADAPT T02); it only pins `security_review_artifact`
  into state. `security-review evidence` maps instead to the
  `implementation_base_ref` row.
- `accept-state` (§4.1, PRESERVE) → the "Restart / reset / doctor recovery
  commands" row; it is the acknowledgement half of the `doctor` state-jump
  detection.

| Capability | Contract §18 row | Disposition | Changing phase | Regression anchor | Evidence |
|---|---|---|---|---|---|
| Deterministic Python core | Python deterministic core | PRESERVE | - | whole `tests/` suite, 230 collected | `scripts/sdle.py`; §3.2 |
| Claude-first UX (header, status dump, gate content in conversation) | Claude-first UX | PRESERVE | - | `tests/test_units_state.py::test_header_renders_both_lines`, `::test_state_dump_lists_every_gate` | `scripts/sdle.py:1239`, `:1257`; §4.1 |
| CLI invoked by Claude via the launchers | CLI called by Claude | PRESERVE | - | `tests/test_units_cli.py::test_help_exits_zero` | `scripts/sdle.py:3459-3682`; §4.1 |
| Pure-JSON stdout envelope, prose to stderr | JSON stdout contract | PRESERVE | - | `tests/test_units_cli.py::test_stdout_is_pure_json_and_prose_goes_to_stderr`, `::test_success_and_refusal_share_one_envelope_shape` | `scripts/sdle.py:3040-3047`; §4.1 |
| Four-value exit-code contract | Exit codes 0/1/2/3 | PRESERVE | - | `tests/test_units_cli.py::test_refusal_exit_code_survives_the_process_boundary`, `::test_integrity_exit_code_survives_the_process_boundary` | `scripts/sdle.py:37-40`; §4.2 |
| `write_atomic` temp-file + `os.replace` | Atomic writes | PRESERVE | - | `tests/test_units_infra.py::test_write_atomic_leaves_no_partial_file_on_failure`, `::test_write_atomic_replaces_completely` | `scripts/sdle.py:446-469`; §6.1 |
| Idempotent deterministic commands | Idempotent deterministic commands | PRESERVE | - | `tests/test_units_state.py::test_migrate_is_idempotent`, `tests/test_units_infra.py::test_state_writes_survive_repeated_saves` | `scripts/sdle.py:980`; §4.14 |
| `scripts/sdle.sh` and `scripts/sdle.ps1` | Cross-platform launchers | PRESERVE | - | lint-skill `no_powershell_only_cmdlets`; CI launcher steps (NOT_RUN here, see §3.4/§3.5) | `scripts/sdle.sh`, `scripts/sdle.ps1`; `.github/workflows/ci.yml` |
| Artifact SHA fingerprints recorded per gate | Artifact SHA/fingerprints | PRESERVE | - | `tests/test_integration_01_happy_path.py::test_all_eight_gates_approved_with_baselines`; `tests/test_units_state.py::test_sha_is_lowercase_hex` | `scripts/sdle.py:436-444`, `:2008`; §4.3 `artifact_shas` |
| Review/validation bound to the exact artifact SHA | Artifact review/validation against exact SHA | ADAPT | T06 | NO_ANCHOR — capability absent at this baseline | contract §12 T06 "Governed artifact review/validation"; TP-011 |
| Review evidence linked into the audit ledger | Review evidence + audit linkage | ADAPT | T06 | NO_ANCHOR — capability absent at this baseline | contract §12 T06; TP-011 |
| Reviews invalidated when the artifact changes after review | Stale-review invalidation after artifact change | ADAPT | T06 | NO_ANCHOR — capability absent at this baseline. Nearest baseline relative is drift re-approval, which is a different mechanism | contract §12 T06; TP-011; cf. §4.7 |
| Drift detection against approved baselines | Drift detection | PRESERVE | - | `tests/test_integration_02_to_05.py::test_04_drift_is_detected_against_the_baseline`, `::test_04_unapproved_gates_are_never_drift_checked` | `scripts/sdle.py:1778`; §4.7 |
| Git diff shown as drift evidence | Drift diff evidence | PRESERVE | - | `tests/test_integration_02_to_05.py::test_04_drift_includes_a_git_diff_for_tracked_artifacts` | `scripts/sdle.py:1817`; §4.7 |
| `prev_sha` entry chain plus whole-file `audit_sha` | Audit integrity/hash chain | PRESERVE | - | `tests/test_units_state.py::test_audit_verify_detects_truncation`, `::test_audit_verify_detects_a_deleted_middle_entry`; `tests/test_integration_06_to_09.py::test_07_edited_audit_halts_until_rebaselined` | `scripts/sdle.py:665-734`; §4.4 |
| `max_remediation_attempts` / `max_retry_attempts` caps | Rate limits | PRESERVE | - | `tests/test_integration_02_to_05.py::test_02_remediation_limit_halts_without_invoking_anything`, `::test_03_retry_limit_stops_offering_retry` | `scripts/sdle.py:1999`, `:884`; §4.6 |
| Dirty-tree guard on the implement phase | Dirty-tree guard | PRESERVE | - | `tests/test_integration_06_to_09.py::test_06_dirty_tree_halts_implement`, `::test_06_bypass_proceeds_and_is_logged` | `scripts/sdle.py:2693`; §4.9 |
| 11-pattern prompt-injection scan on untrusted files | Untrusted-content scan | PRESERVE | - | `tests/test_integration_02_to_05.py::test_05_every_injection_pattern_fires` | `scripts/sdle.py:2569-2593`; §4.10 |
| 6-pattern masked credential scan | Secrets scan | PRESERVE | - | `tests/test_hooks.py::test_secrets_hook_flags_a_credential`, `::test_secrets_hook_never_reproduces_the_secret` | `scripts/sdle.py:2753-2763`; §4.11 |
| Detected-runner test execution recorded in the manifest | Test evidence | PRESERVE | - | `tests/test_integration_06_to_09.py::test_06_test_evidence_records_a_real_failing_run` | `scripts/sdle.py:2772-2824`; §4.12 |
| `implementation_base_ref` pinned at preflight, used by the security review | `implementation_base_ref` concept | PRESERVE | - | `tests/test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref`, `::test_06_security_review_diffs_against_the_pinned_ref` | `scripts/sdle.py:2706`, `:2926`; §4.13 |
| Four wired Claude hooks (write-fence, untrusted-read, dirty-tree, secrets-scan) | Hook guardrails | ADAPT | T02 | `tests/test_hooks.py::test_every_guard_is_registered` plus the 19 other `test_hooks.py` cases | `.claude/settings.json`; `.claude/hooks/hooks.py`; §4.8 |
| Tests derived from recorded dry-run transcripts | Transcript-derived tests | PRESERVE | - | `tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript` | `docs/dry-runs/`; §6.1 records this node id's flake |
| 22-check cross-file sync linter | `lint-skill` | PRESERVE | - | `tests/test_lint_skill.py::test_the_repo_passes_every_check` plus 16 negative cases | `scripts/sdle.py:3087`; §3.1 |
| Repository-global `.workflow/` runtime directory | `.workflow/` repo-global runtime | SUPERSEDE_LATER | T02 | `tests/test_units_state.py::test_init_creates_state_and_advances_to_first_generation_phase` | `.gitignore:1`; `scripts/sdle.py:1065`; §4.3, §4.4 |
| Single repository-wide session lock | repo-global lock | SUPERSEDE_LATER | T02 | `tests/test_units_state.py::test_lock_acquire_reports_a_fresh_foreign_lock`; `tests/test_integration_01_happy_path.py::test_lock_is_refreshed_on_every_save` | `scripts/sdle.py:590-670`; §4.5 |
| Hard-coded 18-phase sequence | fixed 18 phases | SUPERSEDE_LATER | T07 | lint-skill `next_phase_chains_sequence`, `progress_denominator_matches_phase_count`; `tests/test_units_transitions.py::test_advance_follows_next_phase` | `.claude/skills/sdle/SKILL.md:89-111`; §6.2 |
| Hard-coded 8 approval gates | fixed 8 gates | SUPERSEDE_LATER | T09 | lint-skill `gate_registered_*` (8 checks); `tests/test_integration_01_happy_path.py::test_all_eight_gates_approved_with_baselines` | `.claude/skills/sdle/SKILL.md:136-145`; §4.3 |
| `current_feature_id` as the primary workflow identity | `current_feature_id` as primary identity | SUPERSEDE_LATER | T04 | `tests/test_units_transitions.py::test_gate_show_substitutes_feature_id`, `::test_gate_show_reports_unresolved_feature_id` | `templates/state.json:10`; `scripts/sdle.py:1891`; §4.1 `feature resolve` |
| Runtime artifacts excluded from version control | runtime artifacts gitignored | SUPERSEDE_LATER | T01 first, T11 completes | NO_ANCHOR — `.gitignore` content has no test | `.gitignore` lines 1-5 (`.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`); contract §19 |
| Lifecycle constants parsed out of `SKILL.md` | lifecycle constants in `SKILL.md` | SUPERSEDE_LATER | after T07/T09 stable | lint-skill `tables_wellformed`, `single_state_template`; `tests/test_lint_skill.py::test_a_renamed_constant_heading_fails_loudly` | `.claude/skills/sdle/SKILL.md`; `scripts/sdle.py:3417` `constants` |
| Version migration chain, 13 rows | NOT_IN_S18 | ADAPT | T02 | lint-skill `migration_covers_every_state_field`; `tests/test_units_state.py::test_migrate_walks_the_whole_chain_from_1_0` | §4.14 |
| `state.json` schema, 25 top-level fields | NOT_IN_S18 | ADAPT | T02 | lint-skill `single_state_template`, `migration_covers_every_state_field` | §4.3 |
| Two-step confirmation protocol and stale-confirmation guard | NOT_IN_S18 | PRESERVE | - | `tests/test_integration_02_to_05.py::test_03_skip_is_two_step`, `::test_03_stale_confirmation_guard_cancels_a_pending_skip` | §4.1 `confirm *` |
| In-phase checkpoint / crash recovery | NOT_IN_S18 | ADAPT | T02 | NO_ANCHOR — no dedicated test for `checkpoint set/get/clear` | `scripts/sdle.py:2135`; §4.1 |
| Post-rejection remediation loop | NOT_IN_S18 | PRESERVE | - | `tests/test_integration_02_to_05.py::test_02_remediation_writes_feedback_from_canonical_state`, `::test_02_remediation_finish_archives_and_removes_feedback` | §4.1 `remediate *` |
| Restart / reset / doctor recovery commands | NOT_IN_S18 | SUPERSEDE_LATER | T07 | `tests/test_integration_06_to_09.py::test_08_restart_is_two_step_and_rolls_back`, `::test_08_doctor_detects_a_hand_edited_forward_jump`, `::test_08_reset_is_two_step_and_preserves_artifacts` | §4.1 |
| `phase_history` append-only phase ledger | NOT_IN_S18 | SUPERSEDE_LATER | T07 | `tests/test_integration_01_happy_path.py::test_phase_history_records_every_phase_in_order`; `tests/test_integration_06_to_09.py::test_08_restart_trims_phase_history_and_clears_drift` | §4.3 |
| Spec Kit preflight, skill discovery and feature binding | NOT_IN_S18 | SUPERSEDE_LATER | T04 | `tests/test_integration_06_to_09.py::test_09_missing_speckit_halts_first`, `::test_09_healthy_project_passes_preflight`; `tests/test_units_infra.py::test_preflight_persists_the_discovered_prefix` | §4.1 `preflight`, §4.3 `speckit_*` |
| Per-phase guidance files | NOT_IN_S18 | SUPERSEDE_LATER | T07 | `tests/test_integration_06_to_09.py::test_09_guidance_map_resolves_from_the_skill_file`, `::test_09_preflight_lists_guidance_files` | §4.1 `guidance path` |
| Clarification capture, scanned and saved | NOT_IN_S18 | ADAPT | T02 | `tests/test_integration_02_to_05.py::test_05_clarification_responses_are_scanned_and_saved` | §4.1 `clarify save`, §4.3 `clarification_phase` |
| Repository staleness reporting against approvals | NOT_IN_S18 | PRESERVE | - | `tests/test_integration_06_to_09.py::test_07_staleness_is_scoped_to_recorded_artifact_paths`, `::test_07_staleness_is_silent_without_approvals` | §4.1 `repo-staleness` |
| ARTIFACT_OWNERSHIP artifact-path resolution | NOT_IN_S18 | ADAPT | T04 | lint-skill `gate_registered_*`; `tests/test_units_transitions.py::test_gate_show_reports_number_label_and_path` | §4.1 `artifact path` |
| `skip` — advance without a verified artifact | NOT_IN_S18 | SUPERSEDE_LATER | T07 | `tests/test_integration_02_to_05.py::test_03_skip_requires_a_failed_status`, `::test_03_skip_is_permanently_logged` | §4.1 `skip` |
| State-write ownership fence (`state set` refuses engine-owned fields) | NOT_IN_S18 | PRESERVE | - | `tests/test_units_infra.py::test_state_set_refuses_engine_owned_fields`, `::test_state_set_is_audited` | §4.1 `state set` |
| UTF-8 output regardless of platform encoding | NOT_IN_S18 | PRESERVE | - | `tests/test_units_cli.py::test_output_is_utf8_regardless_of_platform_encoding` | §4.1 |
| Relocatable skill root (`--skill-root`) | NOT_IN_S18 | ADAPT | T05 | `tests/test_units_cli.py::test_skill_root_can_be_pointed_elsewhere` | §4.1 `constants` |

---

## 6. Known baseline conditions

Findings observed at the baseline. **None is a T00 defect and none may be fixed
in T00.** Each records the observation, its evidence classification, and who
owns it next.

### 6.1 Non-deterministic Windows `PermissionError` in `write_atomic`

**Classification:** `INFERRED` environmental. Root cause `UNKNOWN`.
**Owner next:** the human, as a separate product decision. Not owned by any
transition phase; the plan's failure mode F2 explicitly rejects patching it
inside T00.

The full-suite run in §3.2 produced `1 failed, 229 passed`, exit code 1. The
failure was:

```text
FAILED tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript
C:\workspace\ai\cc\sdle-git-repo\sdle-latest\scripts\sdle.py:463: PermissionError: [WinError 5] Access is denied:
  '...\pytest-6\test_traversal_matches_the_tra0\target\.workflow\.state.json.ml5kgeot.tmp'
  -> '...\pytest-6\test_traversal_matches_the_tra0\target\.workflow\state.json'
```

Line 463 is the `os.replace(handle.name, path)` inside `write_atomic`
(`scripts/sdle.py:446-469`). That function performs the rename with no retry and
no backoff, so any transient Windows sharing violation surfaces as an unhandled
`PermissionError`.

**Failure mode F1 applied.** Only the failing node id was re-run, three times,
in this context:

```text
=== F1 RERUN 1 ===
.                                                                        [100%]
1 passed in 9.45s
RERUN_1_EXIT=0
=== F1 RERUN 2 ===
.                                                                        [100%]
1 passed in 9.77s
RERUN_2_EXIT=0
=== F1 RERUN 3 ===
.                                                                        [100%]
1 passed in 35.96s
RERUN_3_EXIT=0
```

All three passed, so the classification is **`ENVIRONMENT_FLAKE`** and the
suite is treated as green **with this caveat recorded**. The raw suite exit code
remains 1 as reported in §3.2; it is not restated as 0.

Two further observations support the environmental reading rather than a
deterministic product defect:

1. The victim differs between occurrences. The T00 plan's ledger recorded
   `tests/test_integration_02_to_05.py::test_04_unapproved_gates_are_never_drift_checked`
   with victims `audit.md` and `state.json`; this context observed a **different
   node id**, `test_traversal_matches_the_transcript`, with victim `state.json`.
   A deterministic defect would not move between unrelated tests.
2. The wall-clock spread is large and unstable for identical work: 9.45s, 9.77s,
   35.96s for the same single test. That pattern is consistent with an
   on-access scanner or indexer briefly holding the temp file handle.

`scripts/sdle.py` was **not** modified. `git status --porcelain` in §1 confirms
it.

### 6.2 lint-skill parses 19 phases while progress denominators are 18

**Classification:** `OBSERVED` and **RESOLVED** in this context. Plan unknown U3
is closed. **Owner next:** nobody — there is no discrepancy to fix. Both numbers
are recorded below, as U3 requires, and neither was silently discarded.

Both numbers are correct and measure different things:

- **19** is `len(consts.phase_sequence)` — the row count of the PHASE_SEQUENCE
  table, whose 19th row is the terminal pseudo-phase `complete`:

  ```text
  | 18 | `gate_security` |
  | 19 | `complete` |
  ```

  (`.claude/skills/sdle/SKILL.md` lines 110-111.) The message is emitted by
  `check_tables_wellformed` at `scripts/sdle.py:3078`.

- **18** is `Constants.phase_count`, which excludes that terminal entry by
  construction:

  ```python
  @property
  def phase_count(self) -> int:
      """The N in 'N/18' — every phase except the terminal ``complete``."""
      return len([p for p in self.phase_sequence if p != "complete"])
  ```

  (`scripts/sdle.py:322-325`.) The denominator check compares PROGRESS_MAP
  denominators against exactly that value:

  ```python
  expected_denominator = str(consts.phase_count)
  ```

  (`scripts/sdle.py:3144-3155`.)

`complete` is a terminal state, not a workflow phase: NEXT_PHASE maps
`` `complete` `` to *(terminal)* and `restart` computes its range as
`len(consts.phase_sequence) - 1` with the comment "`complete` is not restartable"
(`scripts/sdle.py:2338`). The product's user-facing count of 18 phases is
therefore accurate, and the lint message's 19 is a raw table-row count, not a
competing claim. Both checks pass (§3.1).

### 6.3 `.github/` is not readable with the Read tool in this environment

**Classification:** `OBSERVED` (environment restriction, carried forward from
the planning context and re-confirmed here by using the alternative path).
**Owner next:** nobody — it is an agent-environment permission setting, not a
repository condition.

The CI facts in §2 were obtained with `git show HEAD:.github/workflows/ci.yml`,
which reads the committed tree and succeeded (exit 0). Any later phase needing
`.github/` content should use `git show` rather than concluding the file is
absent.

### 6.4 `agent_guard.py` absolute-path defect — control-plane, human-owned

**Classification:** `OBSERVED`, **RESOLVED before this attempt began**.
**Owner next:** the human, who already exercised that ownership. Explicitly
**not** owned by any transition phase.

`tools/transition/agent_guard.py` matched an absolute `file_path` against
repo-relative anchored patterns, which failed **closed** for the planner and
verifier roles (every sanctioned evidence write denied) and **open** for the
implementer role (control-plane deny-list vacuous, terminal `return True`
reached for every path). The full analysis is
`docs/transition/phases/T00-blocker.md` §2-§5.

Resolution already applied and signed off, per that blocker's §9: the user chose
Option A, the orchestrator normalised the repo root out of the path before
matching, re-signed the `tools/transition/agent_guard.py` line of
`docs/transition/control-plane.sha256`
(`aa57c588…1aa42` → `93afa049…f7f40`), and re-ran a 20-case acceptance matrix in
both path forms with all cases agreeing. `python tools/transition/validate.py`
exits 0 (§3.3).

This attempt did **not** revisit, re-test or re-patch that fix. It is recorded
here only because plan §6 requires the finding to appear in the baseline, and
because the residual noted in blocker §9.5 stands: the planner/verifier Bash
filter still does not stop interpreter-mediated writes, with
`control-plane.sha256` + `validate.py` as the accepted backstop. Every write in
this attempt went through the `Write`/`Edit` tools, so the guard evaluated each
one.

---

## 7. Explicitly preserved by decree

The five items of the contract §6 *Explicitly preserve* list, each paired with
the phase that is permitted to change it later. **A future phase must consult
this list before altering any of these behaviours.** Until the named phase runs
and is verified, changing any of these is a contract violation, not an
optimisation.

| # | Contract §6 explicit-preserve item | Preserved until | Phase permitted to change it | Baseline evidence |
|---|---|---|---|---|
| 1 | 18-phase sequence | T07 is verified COMPLETE | **T07** — declarative flow model (contract §13) | `.claude/skills/sdle/SKILL.md:89-111`; lint-skill `next_phase_chains_sequence`; §5 row "fixed 18 phases" |
| 2 | 8 gates | T09 is verified COMPLETE | **T09** — risk-adaptive gates (contract §15) | `.claude/skills/sdle/SKILL.md:136-145`; lint-skill `gate_registered_*`; §5 row "fixed 8 gates" |
| 3 | current `.workflow/` location | T02 is verified COMPLETE | **T02** — WorkItem-scoped runtime state (contract §8) | `.gitignore:1`; `scripts/sdle.py:1065`; §5 row "`.workflow/` repo-global runtime" |
| 4 | current lock behavior | T02 is verified COMPLETE | **T02** — lock removed or rescoped (contract §8 "Lock behavior") | `scripts/sdle.py:590-670`; §4.5; §5 row "repo-global lock" |
| 5 | current Spec Kit feature behavior | T04 is verified COMPLETE | **T04** — Spec Kit bound to the active WorkItem, `current_feature_id` demoted (contract §10) | `scripts/sdle.py:1891`; `templates/state.json:10`; §5 row "`current_feature_id` as primary identity" |

Contract §6 states these are "intentionally preserved until later phases".
T00 changed none of them: no tracked file differs from
`f8fdaa048b9a9a35d317224eddd191318ccdd7f6`.

