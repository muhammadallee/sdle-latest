# T06 Implementation Handoff — Attempt a01

**Phase:** T06 — Deterministic governance inputs and a governed artifact review the gate enforces (contract §12, TP-011)
**Attempt:** 01 (this context resumed the attempt after an API-session interruption under §24.6; that is an interruption, **not** a verification FAIL, so the attempt number is unchanged)
**Implementer context:** fresh/isolated, resumed mid-M6
**Status recommendation:** IMPLEMENTED

Precondition HEAD: **`4a35a1c`** on `transition/workitem-v1`. Nothing is committed this phase; all work is in the working tree.
Rollback point: **`475795a`** (`abee131` and `4a35a1c` are control-plane only).

> **Read the two halves separately.** T06's positive claim is that two stated MUSTs are now *enforced by the core* — A10, A12, A13, A19 and the N10–N12 / N24–N35 tests. Its negative claim is that **nothing else moved** — A5, A6, A9, A17, A18, A20, A22. A green suite is necessary for both and sufficient for neither, so both sets were driven independently, including outside pytest.

---

## What this context inherited, and what it did

The engine half of M6 was already applied by the interrupted context (`review_key`, `read_reviews`, `review_status`, `review_precondition`, `cmd_artifact_review`, `cmd_artifact_reviews`, the two `review_precondition` call sites and the two `artifact` subparsers), together with anti-contradiction row 6b's eight `review_for_gate` calls in `run_happy_path`. **The tree was therefore red on arrival — the planned M6 red window.** This context verified that from disk before touching anything, closed it with setup calls only, then completed M7 and M8.

Everything below was re-derived by a command run **in this context**. No figure is copied from a checkpoint.

---

## The red window, derived rather than inherited

`rtk proxy "python -m pytest -q -p no:cacheprovider --tb=no -rf"` (before any edit) → runner raw exit **0**; pytest reported **`65 failed, 717 passed in 1158.11s (0:19:18)`**.

| File | Failures |
|---|---|
| `tests/test_integration_06_to_09.py` | 26 |
| `tests/test_integration_02_to_05.py` | 17 |
| `tests/test_units_workitem_runtime.py` | 12 |
| `tests/test_units_speckit_binding.py` | 4 |
| `tests/test_units_transitions.py` | 4 |
| `tests/test_units_governance.py` | 2 |

Set-compared against the interrupted context's captured run: **identical — 65 = 65, nothing on either side alone.** Every failure was E2 (`review_missing`) reached through a `gate approve` whose artifact had no current `PASS` review. This is neither a flake nor a regression; the F1 `ENVIRONMENT_FLAKE` procedure stays void and `write_atomic` was not touched.

**The two failures in T06's own new file were investigated individually**, since they could have signalled a real interaction rather than missing setup. They did not:

- `test_gate_approve_inherits_the_same_clause` isolates E1 at `gate approve`. `review_precondition` runs **before** `apply_advance` in `cmd_gate_approve`, so E2 now fires first and the case saw `review_missing` instead of `governance_missing`. Satisfying E2 in setup restores the isolation the test was written for.
- `test_the_governance_entry_is_written_once_per_assessment` drives a real `gate approve` incidentally.

Three refusal cases needed **no** insertion, which is itself evidence the enforcement is ordered correctly: `drift_pending` fires before `review_precondition` in `_approve_drift`; `manifest_incomplete` and `feature_outside_workitem` fire before it in `cmd_gate_approve`. Each failed only because its *fixture* approved an earlier gate.

---

## TP-003 — every deliberate test change, with its category

**There is no fourth category.** Every change below is **category 2** (genuinely superseded behaviour). **No assertion was relaxed, removed, weakened, skipped, xfailed or deleted, and no test file was deleted or renamed.**

### The seven itemised edits from the plan's anti-contradiction clause

| Row | File | State |
|---|---|---|
| 0 | `tests/test_units_workitem_resolution.py` | `"governance"` added to the closed `RUNTIME_FREE_COMMANDS` set. Applied. |
| 1 | `tests/test_units_repo_config.py` | `"governance_policy_file"` added to `CONFIG_MEMBERS`. Applied. |
| 2 | `tests/test_units_repo_config.py` | `"read_governance_policy"` added to `CONFIG_REFERENCE_SITES`. Applied. |
| 3 | `tests/test_units_repo_config.py` | `"governance.json"`, `"reviews.json"` added to the expected runtime-name set. Applied. |
| 4 | `tests/test_units_repo_config.py` | `test_no_lifecycle_command_reads_the_repository_configuration` rewritten. **Applied in this context** — see below. |
| 5 | `tests/conftest.py` | `Project.record_governance()` plus one call in `started`. Applied. |
| 6 | `tests/test_integration_01_happy_path.py` | 6a governance call, 6b eight `review_for_gate` calls, both inside `run_happy_path` only. Applied. |

`tests/conftest.py` gained **nothing** in this context. `grep -c review_for_gate tests/conftest.py` = **0**; `project`, `bare_project`, `git_project`, `started_git` and `isolated_git_identity` keep their bodies, and `started` still carries exactly one `record_governance()` call.

### Row 4 — the honest rewrite, not a rename that dodges the check

The old body filtered by function-NAME PREFIX (`cmd_gate`, `cmd_advance`, `cmd_approve`, `cmd_init`). That was adequate while nothing in the engine read the boundary; it is exactly the wrong shape once the lifecycle genuinely consults policy, because a helper named outside those prefixes could read `.sdle/` and the test would still pass — the guardrail would die while looking alive. The rewrite is **strictly stronger** and keeps the original clause:

- **(a)** `governance_policy_file` has exactly **one** reader in the *whole engine*: `read_governance_policy`. Derived from the AST, not assumed — the reference sets were enumerated from disk before the assertion was written.
- **(b)** the `config_file` reader set is closed over the whole engine (`cmd_config_init`, `cmd_config_show`, `collect_validation_findings`, `read_repo_config`, `repo_config_findings`), and the subset of it that is a `cmd_*` outside the `config` group is asserted **empty**.
- **(c)** the original prefix clause is kept verbatim in effect, so `test_the_lifecycle_command_prefixes_actually_match_something` stays load-bearing instead of being orphaned by the rewrite.

Four removed lines in that file (3 docstring lines + one `for` line) are the whole of row 4's rewrite. **No other test file has a single removed line.**

### The derived set — inserted setup calls only, file by file

Each is one `review_for_gate(<view>, <gate>)` line, plus one `from test_units_artifact_review import review_for_gate` per file — the cross-module pattern the suite already uses for `run_happy_path`, so `conftest.py` does not grow a helper.

| File | Sites | Calls |
|---|---|---|
| `tests/test_integration_02_to_05.py` | `at_gate_spec`; `drifted`; `test_04_reapproval_rebaselines_and_resumes`; `test_04_multiple_drifted_gates_queue_most_upstream_first` (2); `test_04_drift_reapproval_walks_the_queue_one_at_a_time` (2); `test_04_drift_includes_a_git_diff_for_tracked_artifacts` | 8 |
| `tests/test_integration_06_to_09.py` | `at_implement` (the three-gate loop, then `gate_tasks`, `gate_analyze`, `gate_design`); `test_06_gate_seven_accepts_a_built_manifest`; `test_07_staleness_is_scoped_to_recorded_artifact_paths`; `at_gate_plan` (2) | 8 |
| `tests/test_units_speckit_binding.py` | `drive_full_workflow` (8); `test_n3_a_gate_refuses_another_workitems_artifact`; `test_migrated_in_flight_workflow_refuses_its_next_speckit_gate`; `test_feature_resolve_recovers_a_migrated_workflow_without_drift` (2) | 12 |
| `tests/test_units_transitions.py` | `test_gate_approve_records_baseline_and_advances`; `test_gate_approve_stores_comments`; `test_gate_approve_writes_audit_entry_with_decision`; `test_final_gate_completes_the_workflow` | 4 |
| `tests/test_units_workitem_runtime.py` | `legacy_workflow` (the seed run whose runtime becomes `.workflow/`) | 1 |
| `tests/test_units_governance.py` | the two cases named above | 2 |

**35 calls plus 6 imports, across 6 files.** Earlier milestones inserted 13 further `record_governance()` setup calls for E1, in `tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py`, `tests/test_units_speckit_binding.py`, `tests/test_units_workitem_runtime.py`, `tests/test_units_workitem_resolution.py`, `tests/test_units_repo_config.py` and `tests/test_units_workitem.py`; all are category 2 and all were re-inspected here.

### Declared divergences from the plan's *enumeration* (not from its rule)

1. **`tests/test_units_workitem.py` and `tests/test_units_repo_config.py` are in the derived setup-call set**, though the plan bounded the set by "the 49 `"approve"` literals across 8 files" and did not list them. E1 sits at **`advance`**, not at `approve`, so the true bound is phase-*movement* sites. `tests/test_units_workitem.py` is additionally on the plan's "byte-unchanged and passing" list; it gained **two `record_governance()` calls in one test** (`test_a_workitem_does_not_change_what_init_and_advance_produce`), which is exactly what makes that test's comparison meaningful — both sides of it now carry a record. **No assertion in that file moved.**
2. **`tests/test_units_workitem_resolution.py` gained one setup call** beyond row 0's literal, although the plan says row 0 is "the only edit permitted anywhere in that file" — `test_skip_on_a_mismatched_branch_needs_both_acknowledgements` drives a `skip`, and `skip` moves a phase. Inserted call, no assertion touched.
3. **`tests/test_units_transitions.py`** is named in the plan's "existing tests affected" table but not in the anti-contradiction clause's enumeration; four inserted calls.

All three are recorded here under the clause's own escape hatch ("record it as a declared divergence with the reason and the category"). Category 2 in every case.

### The `skip \| xfail` grep, quoted rather than asserted empty

Run in this context: `grep -rn "xfail" tests/` matches **nothing** — zero lines, including in the two new files. `grep -rn "skipif" tests/` and `grep -rn "pytest.mark.skip" tests/` each match exactly **one** source line, the pre-existing `tests/test_units_infra.py:49: @pytest.mark.skipif(SH is None, reason="POSIX sh not available")` (plus two stale `__pycache__` binaries of that same file). Every other `skip` in the tree is the SDLE `skip` subcommand or the `--skip-tests` CLI flag. **T06 added no `skip`, no `xfail` and no `skipif`.** `-rsxX` on the final run produced **no** short-summary section, which is the mechanical form of the same claim.

---

## New tests written in this context (M7)

Appended to `tests/test_units_governance.py`:

1. **`test_governance_changes_no_lifecycle_behaviour`** — A17 + N13's differential half + N20(d), written after the engine was complete so it pins what shipped. Four scratch repositories, cloned **before** any run so they genuinely start identical, differing only in the governance record: baseline (`LOW`/enhancement/ITERATIVE), classification-only (`defect`/DEFECT_FIX), risk-only (`CRITICAL`), and both (`hotfix`/HOTFIX/`CRITICAL`). It asserts:
   - clause 0, the anti-vacuity guard: `finalLevel` is `LOW`/`LOW`/`CRITICAL`/`CRITICAL` and three distinct classification types are recorded, so the variants demonstrably took effect;
   - all four traversals equal `EXPECTED_TRAVERSAL`;
   - identical ordered lifecycle audit events, modulo the two event kinds T06 itself adds;
   - identical approvals (8 gates, all `approved`), identical `artifact_shas` key sets (8), identical `progress`;
   - clause 3: the would-be required gate set **does** differ across risk (`baseline ⊂ risk_only`) and across classification, so the identity above is not true for an uninteresting reason (A18).

   The variant is injected by overriding the **fixture** method's default document for the duration of the run. **No engine function is patched**; every command still goes through the real CLI.

2. **`test_a_corrupt_governance_record_is_an_integrity_failure`** (3 parametrised cases) — pins the phase's **one declared new exit-3 path**. `EXIT_INTEGRITY = 3` was added to the file's exit-code constants.

N20(b)(c), N28 and N30 already existed from earlier milestones and were re-checked by name rather than rewritten: `test_no_phase_movement_function_consults_the_would_be_gate_set`, `test_the_phase_movement_prefixes_actually_match_something`, `test_no_stored_freshness_flag_exists_in_a_record`, `test_a_hand_planted_freshness_flag_changes_nothing`, `test_the_approval_baseline_and_the_review_ledger_never_mix`, `test_the_artifact_shas_writer_set_is_unchanged`.

---

## M8 — the prompt and documentation layer

`lint-skill` was re-run after **each** document edit: **eleven** runs, every one raw exit **0**, **22 PASS / 0 FAIL**.

- **`.claude/skills/sdle/SKILL.md`** — Step 1 gains one "Governance comes before planning" block between `workitem create` and `init`, naming the three E1 refusals. **10 insertions, 0 deletions; no constant table touched** (see A6 below). SKILL.md is CRLF in this working copy and the patch preserved that; writing LF would have turned the diff into the whole file.
- **`modules/phase-execution.md`** — a **Governed Artifact Review (MANDATORY — before every gate)** block beside Post-SpecKit Verification, plus one item in the pre-gate self-check. 21 insertions, 0 deletions.
- **`modules/gate-protocol.md`** — a review-status step in the "before displaying any gate prompt" list and a `Review:` line in the prompt format. The artifact-content display steps are untouched, so the review status is **added to** the gate prompt, not substituted for content (A21).
- **`.claude/commands/sdle-start.md`**, **`.claude/commands/sdle-approve.md`** — the two invocation lines, with the surrounding steps renumbered. Invocation and presentation only; no constant, no header format, no business logic.
- **`README.md`** — a "Governance inputs and artifact review" section (63 insertions, 0 deletions).
- **`docs/SDLE-Reference-Guide.md`** — §12.4, three §14 compliance rows and an Appendix C command table (24 insertions, 0 deletions). **No Document Revision History row**, following T05's precedent: there is no engine version change.
- **`docs/architecture/ADR-003-governance-inputs-and-artifact-review.md`** — new, 245 lines, recording all ten decisions, the ten alternatives rejected, and the consequences (including the pre-T06 WorkItem that will refuse at its next `advance`, and the legacy-binding carve-out).

**Invariant 7 was checked mechanically before writing, not after.** N23's needle set (12 risk-signal ids plus the 5 underscored check ids) was derived from `GOVERNANCE_POLICY_BUILTIN` by AST and searched against every M8 draft: **zero hits** in ADR-003, README and the Reference Guide. `test_no_policy_default_value_is_restated_outside_sdle_py` searches `docs/architecture/` too, and it passes.

---

## Acceptance criteria A1–A24 — evidence, quoted

| # | Result | Evidence |
|---|---|---|
| **A1** | **PASS** | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **RAW EXIT 0**, **`786 passed in 858.90s (0:14:18)`**. Captured output is **12 lines**; `grep -c "short test summary"` = **0**, so zero skips, xfails and errors. `--collect-only -q` = **`786 tests collected in 0.84s`**, so collected == passed. |
| **A2** | **PASS** | Baseline re-derived here from a **pristine `git archive 475795a`** extracted to scratch: **`569 tests collected in 2.08s`**. Arithmetic: **569 + 175** (`tests/test_units_governance.py`, new) **+ 40** (`tests/test_units_artifact_review.py`, new) **+ 2** = **786**. The **+2** is the only per-file delta in a modified file and is *not* a new test function: a node-id diff against the pristine baseline shows exactly `test_lifecycle_state_under_the_repository_boundary_is_an_error[governance.json]` and `[reviews.json]` — row 3 added two runtime member names and that leak-detector test is parametrised over them. Every other per-file count is identical to baseline (hooks 44, integration_01 8, 02_to_05 42, 06_to_09 38, lint_skill 17, cli 9, infra 28, speckit_binding 55, state 37, transitions 24, workitem 57, resolution 96, runtime 45); `test_units_repo_config.py` 69 → **71**. |
| **A3** | **PASS** | `python scripts/sdle.py lint-skill` → **raw exit 0**, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15`, `"failed": []`. Re-run after **each** of the eleven document edits, plus a baseline run before the first. |
| **A4** | **PASS** | `python tools/transition/validate.py` → **raw exit 0**, `TRANSITION_VALID: complete=6/12 next=T06`. |
| **A5** | **PASS** | `git diff --exit-code 475795a -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .claude/skills/sdle/modules/security-review.md .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ ADR-001 ADR-002 .sdle/ tools/` → **raw exit 0**, run again after the M8 edits. |
| **A6** | **PASS** | All **175** markdown table rows in `SKILL.md` are byte-identical to `475795a` (compared programmatically, reading `git show` as bytes to avoid a console-encoding artefact). `templates/state.json` byte-identical via A5. `CURRENT_VERSION` is `"1.15"`; `lint-skill` reports **15 migration rows** and v1.15 in all four locations. |
| **A7** | **PASS** | `RUNTIME_FREE_COMMANDS` at `475795a` is a 7-member frozenset; at HEAD it is the same seven plus exactly `"governance"` = **8**. Both definitions read side by side; nothing removed. |
| **A8** | **PASS** | `ls -a .sdle/policies/` → **`.gitkeep` only**. `.sdle/` byte-identical via A5, so `config init`/`config show` and `REPO_CONFIG_DEFAULTS` are untouched (A9 confirms the functions). |
| **A9** | **PASS** | AST extract-and-compare against `475795a`: **24/24** named definitions byte-identical — the 19 functions the plan lists plus `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`, `INJECTION_PATTERNS`, `SECRET_PATTERNS`. `cmd_gate_approve` **+1 line / 0 removed**; `_approve_drift` **+1 / 0**; `append_audit` +11 with one line reformatted (`**Prev:**` gained a `+` concatenation prefix and is still the **last** rendered line); `apply_advance` +6 with 4 docstring lines rewritten. |
| **A10** | **PASS** | Driven through the **real CLI as subprocesses in a throwaway project outside pytest**: a fresh WorkItem `init`s (exit 0 — governance is deliberately not an `init` precondition) but its first `advance` refuses **`governance_missing`** with `state.json` byte-identical across the refusal; after `governance assess`, `governance.json` carries `quality`, `classification`, `risk` and `wouldBeRequiredGates`, with `risk` holding `signals`, `score`, `deterministicLevel`, `floorsApplied`, `finalLevel`, `proposedLevel`, `loweringAttempted`, `uncertainty` — all seven §12 evidence items. `governance policy` reports `source: "builtin"` and **12** check ids with no WorkItem bound. |
| **A11** | **PASS** | In the same live run: after a pre-`init` assessment, three review records (one `FAIL`, two `PASS`) and a gate approval, `audit verify` → exit 0, `matches: true`. The ledger holds **3** `**Review:**` lines and **1** `**Gate Decision:** APPROVED`, and **every** entry's last line starts with `**Prev:**`. Also covered across a full 18-phase run by `test_integration_01_happy_path.py` and the M7 differential (four complete runs). |
| **A12** | **PASS** | Live: an input proposing `LOW` against a signal carrying a hard floor produced `deterministicLevel=HIGH`, `proposedLevel=LOW`, **`finalLevel=HIGH`**, **`loweringAttempted=True`**, **exit 0**. N16's cross-product test (`test_claude_can_never_lower_a_deterministic_floor`) is green in the 786. |
| **A13** | **PASS** | Live, one case each: `governance_missing`, `review_missing`, `review_failed`, `review_stale` — every one exit 1, and `current_phase`, `status`, `approvals` and `artifact_shas` compared before and after **all three** review refusals and found unchanged. `review_stale`'s `data` carries `reviewed_sha != current_sha`. The remaining reasons (`governance_blocked`, `governance_stale`, `policy_malformed`, `policy_weakens_baseline`, `unknown_risk_signal`, `classification_invalid`, every `quality_*`) each have a dedicated green test asserting the frozen-state tuple, not just the reason string. |
| **A14** | **PASS, with one declared divergence** | The whole `scripts/sdle.py` + `tests/` diff plus both new files contain exactly **two** added `raise IntegrityError` statements, both in `read_governance_record` (`governance_record_invalid`). Every other new failure is exit 1 or 2. The divergence was declared at checkpoint 02 and is argued below; this context **pinned it with a test** rather than leaving it narrated. |
| **A15** | **PASS** | N23 green. Grep over the 3,915 added lines plus both new files: `PHASE_SEQUENCE` 0, `PROGRESS_MAP` 0, `PHASE_TO_GATE_KEY` 0, `rate_limits` 0; `NEXT_PHASE` **1** and `ARTIFACT_OWNERSHIP` **1**, both docstring prose ("not a target that is not `NEXT_PHASE[current]`", "never restates `ARTIFACT_OWNERSHIP`") — mentions, not copied values. Quoted rather than reported as empty. |
| **A16** | **PASS** | Every named guardrail test passes unmodified in the 786: `test_no_rung_ever_returns_an_unregistered_workitem`, `test_workitem_rebinding_happens_only_at_the_declared_sites`, `test_the_active_context_is_written_only_by_the_declared_setters`, `test_init_still_refuses_a_legacy_workflow_unconditionally`, `test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding`, the whole `migrate-workflow` block (`legacy_digests` byte-compared before and after every migration case), `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned`, `test_the_scrubbed_state_comparison_still_has_teeth`, `test_the_two_boundaries_never_contain_one_another`, `test_the_configuration_commands_never_touch_runtime_state`, and every `test_units_workitem.py`, `test_hooks.py` and `test_lint_skill.py` case. |
| **A17** | **PASS** | `test_governance_changes_no_lifecycle_behaviour` — see above. Green on its first run: **`1 passed, 171 deselected in 46.53s`**, and again inside the 786. |
| **A18** | **PASS** | N20(b)+(c) green. `governance gates` differs across risk (`baseline ⊂ risk_only` in the differential; `test_the_would_be_gate_set_actually_differs_across_risk_levels` asserts `LOW < CRITICAL`) while the traversal is identical. No gate became conditional. |
| **A19** | **PASS** | N26 and N29 green, plus the live one-byte-edit case: PASS review → append one line → `gate approve` refuses `review_stale` → re-review → approval succeeds. The drift path is guarded by the same function. |
| **A20** | **PASS** | Grep over every added line in `scripts/`, `tests/`, `.claude/`, `README.md`, the Reference Guide and ADR-003: `speckit-` **0**, `/speckit.` **0**. `.claude/agents/` byte-identical (A5). `sdle-architect` matched **9** lines, all recorded actor **strings** in T06's own tests plus one descriptive sentence in ADR-003; `subagent` matched **6**, all inside `test_t06_creates_no_subagent`, its docstring, and ADR-003's statement that none is created. Quoted, not asserted empty. |
| **A21** | **PASS** | `modules/gate-protocol.md`'s content-display steps 1–3 are byte-unchanged; the review status is a **new** step 4 and a **new** `Review:` line in the prompt, added alongside the artifact content. |
| **A22** | **PASS** | Over the same corpus: `conditional gate` matched **1** line — the phrase "eight **unconditional** gates" in ADR-003's consequences, a substring match on prose, not a mechanism; `gate_policy` 0, `flow_selection` 0, `flow routing` 0, `baseline.json` 0, `brownfield` 0, `discovery` 0. `.sdle/baseline.json` is still written by nothing; `implementation-state/` is still empty; the `.workflow/` dual-read rung, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal all still present and tested. |
| **A23** | **PASS** | `git diff --name-status 475795a -- tests/` → **10 `M`**, **zero `D`**, **zero `R`**, plus **2 untracked** new files. Removed lines across the whole tracked diff, enumerated: **6 in `scripts/sdle.py`** (the `**Prev:**` line reformatted, `bound.completion_file,` reformatted when two members were appended, 4 rewritten `apply_advance` docstring lines) and **4 in `tests/test_units_repo_config.py`** (row 4's rewrite). **Every other test file: 0 deletions.** The `M` set is the plan's ten named files with `tests/test_units_infra.py` **not** touched and `tests/test_units_workitem.py` touched instead — divergence 1 above. |
| **A24** | **NOT_RUN** | Host is Python **3.13.0**; the branch is local-only. **Python 3.11: NOT_RUN. CI: NOT_RUN / UNKNOWN.** No outcome predicted. T06 is standard-library-only and adds no syntax `sdle.py` did not already use, but that is a design statement, not a result. |

---

## Files changed

`git diff --numstat 475795a` (excluding the out-of-scope `.claude/settings.local.json`):

```
   11    4  .claude/commands/sdle-approve.md
    9    3  .claude/commands/sdle-start.md
   10    0  .claude/skills/sdle/SKILL.md
    3    1  .claude/skills/sdle/modules/gate-protocol.md
   21    0  .claude/skills/sdle/modules/phase-execution.md
   63    0  README.md
   24    0  docs/SDLE-Reference-Guide.md
 1494    6  scripts/sdle.py
   38    0  tests/conftest.py
   16    0  tests/test_integration_01_happy_path.py
   13    0  tests/test_integration_02_to_05.py
   14    0  tests/test_integration_06_to_09.py
   60    4  tests/test_units_repo_config.py
   18    0  tests/test_units_speckit_binding.py
    6    0  tests/test_units_transitions.py
    4    0  tests/test_units_workitem.py
    5    0  tests/test_units_workitem_resolution.py
    3    0  tests/test_units_workitem_runtime.py
```

New (untracked): `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md` (245 lines), `tests/test_units_governance.py` (175 tests), `tests/test_units_artifact_review.py` (40 tests), `docs/transition/phases/T06-checkpoint-a01-0{1..6}.md`.

`.claude/settings.local.json` was already modified in the working tree before this phase and is **out of scope** — not staged, not reverted, not edited.

---

## Declared divergences, carried and new

1. **`governance_record_invalid` is exit 3** (A14). Declared at checkpoint 02, argued on the merits: a corrupt record is not the same fact as no record, and returning `None` would let a damaged file read as "never assessed" and then be silently overwritten. Every other unreadable runtime file SDLE itself wrote is an integrity failure (`state_unreadable`, `legacy_state_invalid`, `index_malformed`). **This context pinned it with a 3-case test** so the divergence is judged against behaviour rather than prose. The **policy** reader, by contrast, refuses `policy_malformed` at exit 1 — a human-authored file gets a refusal, a SDLE-written file gets an integrity halt.
2. **The governance ledger entry lands at the first *phase movement***, not at "the first state-writing command" as N17's wording says. `governance assess` cannot write it (it runs before `init`, so there is no `audit_sha`) and `cmd_init` is on A9's byte-identical list. It is emitted from `governance_precondition` after every refusal has had its chance to fire — so a refused advance writes nothing — and de-duplicated by the record's `executionId`.
3. **Three test-file scope divergences** (workitem, workitem_resolution, transitions), described under TP-003 above. All inserted setup calls, no assertion touched.
4. **One closed-set assertion in T06's own new file was extended**, not loosened: `test_only_evaluate_risk_produces_a_final_level` grew by the single name `record_governance_audit`, which legitimately reads `finalLevel` to name it in the ledger. The load-bearing half — `producers == {"evaluate_risk"}` — is untouched and the set stays closed.

---

## Residuals and non-adoptions

- **The E1/E2 legacy-binding carve-out** is a declared, bounded residual: under `paths.workitem is None` both preconditions are skipped, because the transitional `.workflow/` binding has no WorkItem to hold either record. It mirrors the identical tested carve-out in `gate_precondition_hook`, fires only when **zero** WorkItems are registered, and **T11 removes the rung**. `test_e1_is_skipped_under_the_legacy_binding_and_only_there` and `test_e2_stands_aside_under_the_legacy_binding_and_only_there` pin it in both directions.
- **`docs/dry-runs/` is not updated** — recorded documentation debt, owner **T11**, alongside T04 N-6. The nine transcripts stay true but incomplete: none shows a governance assessment or a review before a gate.
- **Unowned hygiene items adopted: none.** T03-1, T03-4/5/6, T03-7/8, T03-10, T04 N-2/N-3/N-4/N-6/N-7, T05 NB-3/NB-4/NB-5/NB-6, T02 NB-2/4/5 all remain open with their existing owners. T05 NB-4 in particular: `read_repo_config` is **byte-identical** and its fail-open swallow was **not** inherited — `read_governance_policy` is a separate, fail-closed reader — and NB-4 stays T09's.
- **`docs/transition/RESUME.md` is stale** (`complete=5/12 next=T05`, contradicted by `validate.py`'s `complete=6/12 next=T06`). Non-authoritative by its own first paragraph; flagged for the orchestrator, not edited here.

---

## Process notes for the verifier

- Every pytest figure came through `rtk proxy "python -m pytest …"` with the output redirected to a file and the raw exit read with no pipe in between. Plain `python -m pytest` under the `rtk` hook prints `Pytest: No tests collected` and exits 0 — a false green.
- **The M6 confirmation run (`782 passed in 1381.25s`, raw exit 0) was launched against the M6 tree, and two test-only edits landed on disk while it executed** — M7's appended cases in `tests/test_units_governance.py` and row 4's body rewrite in `tests/test_units_repo_config.py`. Neither can affect that run: pytest had already imported both modules, no test reads test-file source, and `scripts/sdle.py` was untouched. Both were then verified by their own targeted runs, and the final 786-test run covers the whole tree. Stated rather than glossed. One further edit landed during the *final* run: `.claude/commands/sdle-start.md` was rewrapped to the file's line width. Checked rather than assumed — `grep -rln "sdle-start\|sdle-approve" tests/ scripts/` matches **nothing**, `lint-skill` does not read `.claude/commands/`, and `tests/conftest.py`'s install-layout fixture copies `scripts/`, `.claude/hooks/`, `.claude/settings.json` and the skill folder but **not** `.claude/commands/`. No test can see that file.
- **Do not edit a prompt file while a suite run is in flight.** `tests/test_lint_skill.py` runs `lint-skill` against the repository's own `SKILL.md` on disk, and `tests/test_units_speckit_binding.py` reads `modules/phase-execution.md`. All M8 edits were made after the M6 run finished.
- **`SKILL.md` is CRLF in this working copy; every other prompt file is LF.** A naive read-modify-write normalises it and turns the diff into the whole file. The patch preserved the existing convention; `git diff --numstat` shows **10 / 0**.
- The transition agent guard refused **nothing** this context.

## Checkpoints

`docs/transition/phases/T06-checkpoint-a01-01.md` … `-06.md`. Checkpoint 06 covers M6 and M7 and carries the M6 red-window evidence in full.
