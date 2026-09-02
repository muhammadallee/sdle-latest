# T09 Implementation Handoff — Attempt a01

**Phase:** T09 — Risk-Adaptive Gate Policy (contract §15)
**Attempt:** 01
**Implementer context:** fresh/isolated (this attempt was **resumed** twice; the
final resume followed an API session limit that killed the previous implementer
mid-M5 — a §24.6 interruption, not a verification FAIL, so the attempt number is
unchanged)
**Status recommendation:** IMPLEMENTED

---

## Inputs read from disk

- `docs/transition/transition.md` §15 (goal, per-level default intent, the nine
  hard risk floors, the "preserve Wave A guardrails" list, the gate-evidence
  clause and the exit criterion), §12's closing line, TP-001, TP-003, TP-011,
  §24.3 and §24.6.
- `docs/transition/phases/T09-plan.md` (932 lines, authoritative and immutable):
  E1–E40, I1–I7, D1–D17, the X table and its anti-contradiction clause, N1–N31,
  the five-milestone sequence, F1–F13, and acceptance criteria A1–A25.
- `docs/transition/phases/T09-checkpoint-a01-01.md` … `-04.md`, treated as
  claims to verify rather than as fact. Everything they assert about the
  repository was re-checked here.
- `docs/transition/progress.md` (the T09 row), `CLAUDE.md`, `scripts/sdle.py`,
  the prompt layer, `README.md`, `docs/SDLE-Reference-Guide.md`, and the
  affected test files.
- Git: HEAD `ad08d4b5a4dc1303a9c48a9dc8af0ad76f8c55a8`, rollback point
  `e1cf341`, product baseline `f8fdaa0`.

---

## Changes made

### `scripts/sdle.py` (+677 / −52 against `e1cf341`)

**M1 — policy data.** `GOVERNANCE_POLICY_BUILTIN` gains five risk signals
(12 → 17), the `authentication_or_authorization` hard floor is edited in place
from MEDIUM to **HIGH**, six hard-floor rules are appended (6 → 12 rules, the
original six keeping their positions so `hard_floors[0]` indexing stays valid),
and `required_gates_by_risk["MEDIUM"]` gains `gate_design`. `risk_thresholds`,
`required_gates_always`, `required_gates_by_type` and `policyVersion` are
unchanged. Every edit is a tightening.

**M2 — the requirement model, read-only.** `GATE_DISPOSITIONS`,
`GATE_OMITTED_DECISION`, `BASELINED_GATE_DECISIONS`; `gate_requirements()` and
`gate_requirements_for_state()`; `terminal_gate_key()`; `required_gate_set`
retained as the policy half. `governance gates` and `gate show` report
dispositions; the record's `wouldBeRequiredGates` becomes `requiredGates` +
`omittableGates`; `GOVERNANCE_RECORD_VERSION` becomes `"2"` with
`GOVERNANCE_RECORD_VERSIONS = ("1", "2")` and a reader that refuses anything
else at exit 3.

**M3 — enforcement.** `cmd_gate_omit` and its `gate omit --gate <key>` parser
entry; `apply_advance` accepts `omitted_by_policy` only after re-deriving that
the gate is still omittable; a second revalidation of every earlier omission at
the bound flow's terminal gate; `compute_drift` and `cmd_repo_staleness` moved
onto `BASELINED_GATE_DECISIONS`; `write_completion_summary`'s
`all_gates_approved` becomes derived; the `governance_recorded` ledger message
gains a disposition summary **appended at the end**.

**M4 — inherited findings.** `read_repo_config` is fail-closed (no `Return`
inside any `ExceptHandler`); new lint check
`repo_config_defaults_match_documentation`.

**M5 — one further engine change, described in full below:** the absent-document
branch of that new lint check.

### Prompt layer

- **`.claude/skills/sdle/SKILL.md`** (+9 / −1). The sentence saying the type and
  risk level "route nothing" now says what they do route. A new paragraph tells
  the orchestrator to **ask the engine** (`governance gates`, or `required` /
  `requirement_reasons` from `gate show`) and never to decide or infer a
  requirement itself; names `gate omit` and the two options at an omittable
  gate; states that a required gate has no third option; and states that
  everything else about a gate stays universal. Two refusal reasons added to the
  list. **No policy value, signal id or gate list is restated.**
- **`.claude/skills/sdle/modules/gate-protocol.md`** (+32 / −2). A requirement
  lookup inserted as step 5 of the display procedure (with `null` → treat as
  required), a new **Step 6b** for an omittable gate — artifact content is still
  displayed, both options are offered, `gate omit` is run by the engine and a
  `gate_required` refusal is printed rather than worked around — and the
  illustrative completion summary's `all_gates_approved` marked as derived.
- **`.claude/commands/sdle-approve.md`** (+7 / −0). Presentation only: offer the
  omit alternative rather than approving on the user's behalf.

### Documentation

- **`README.md`** (+15 / −2). D16's unqualified clause replaced (M4); the
  `governance gates` row rewritten; a `gate omit` row; a paragraph stating that
  risk decides which gates need a human and nothing else, that the last gate
  before completion is required at every level in every flow, and that an
  override can only make more gates required.
- **`docs/SDLE-Reference-Guide.md`** (+24 / −7). The "all eight gates run
  unconditionally" paragraph replaced by the disposition table, `gate omit` and
  its refusals, the two revalidations, the terminal-gate rule and the
  universality list; the `governance gates` row rewritten and a `gate omit` row
  added; the completion-summary sentence corrected. **Four further statements
  T09 falsified** — the record's gate-set description, the glossary's definition
  of a Gate, §9's "three responses are recognized", and the role table's "sole
  authority … at every gate" — corrected narrowly.
- **`docs/architecture/ADR-006-risk-adaptive-gate-policy.md`** — new, 304 lines.
  D1–D17, the alternatives table, and §3 stating explicitly what the engine
  guarantees about an omission **and what it does not**. It names none of the 22
  policy identifiers.

---

## Deliberate behavior changes

1. `authentication_or_authorization`'s hard floor rises MEDIUM → **HIGH** (a
   live under-enforcement against §15, fixed).
2. Five risk signals and six hard-floor rules added; all nine §15 floors are now
   present at or above the mandated level.
3. `required_gates_by_risk["MEDIUM"]` gains `gate_design`.
4. Each gate of the bound flow is `required` or `omittable`; a policy-named gate
   the flow lacks is reported `not_in_flow` rather than silently dropped.
5. New command `gate omit --gate <key>`; new refusals `gate_required` and
   `gate_omission_invalidated`; new audit event `gate_omitted`; new approval
   decision value `omitted_by_policy`.
6. `apply_advance` accepts `omitted_by_policy` only after re-deriving.
7. The terminal gate's approval revalidates every earlier omission.
8. `compute_drift` and `cmd_repo_staleness` treat an omission as baselined.
9. `governance gates` no longer reports `advisory: true`; `gate show` reports
   `required` and `requirement_reasons`.
10. Record keys renamed; `governanceVersion` becomes `"2"` with a real reader
    that still accepts `"1"`.
11. `governance_recorded` gains an appended disposition summary.
12. `read_repo_config` is fail-closed.
13. New lint check `repo_config_defaults_match_documentation` (33 checks total).
14. Prose in `README.md`, the Reference Guide, `SKILL.md` and
    `gate-protocol.md` that said gates run unconditionally and that risk routes
    nothing is true again; ADR-006 records the decision.

### The one engine change made in M5, and why it is not a relaxation

The single suite failure inherited at the start of this resume was
`tests/test_units_workitem_runtime.py::test_runtime_free_commands_need_no_workitem[lint-skill]`
→ exit 1, reason `lint_failed`, `failed: ['repo_config_defaults_match_documentation']`.

I was told it should clear once M5's documentation edits landed, and to
investigate rather than relax the check if it did not. **It did not clear.** I
reproduced it after the documentation edits and diagnosed it: the cause is not
documentation drift. `bare_project` is a temporary project holding a copied
skill root and nothing else, so `_repo_root()` falls back to the project root,
neither `README.md` nor `docs/SDLE-Reference-Guide.md` exists, the check
examined zero blocks, and it fired **its own non-vacuity guard**. `lint-skill`
is a `RUNTIME_FREE` command and must answer in any project.

The guard is kept. What changed is the question it asks:

- a document that is **present** and carries no `configVersion` block still
  fails — that is the drift D15 exists to catch, and it is still pinned by
  `test_deleting_the_documented_block_fires_rather_than_passing_vacuously`,
  which deletes the block from a README that remains on disk;
- a document that is **absent** is skipped, because there is then no
  restatement to bind. This is not a new convention: `_check_doc_phase_tables`,
  immediately below it, already does `if not path.is_file(): continue`.

A new test, `test_a_project_with_no_repository_documentation_still_lints`, pins
the second half and asserts the check's message.

---

## Preserved behavior / invariants

Re-derived here, not inherited.

- **A HIGH-risk WorkItem cannot omit design or security.** Driven through the
  real CLI in this context: at HIGH, `gate omit --gate gate_design` → exit 1
  `gate_required` with reasons `['risk:HIGH']`; `advance --to implement` → exit
  1 `gate_not_approved`; `gate omit --gate gate_security` → exit 1
  `gate_required` with reasons `['risk:HIGH', 'terminal_gate']`. At HIGH and
  CRITICAL the omittable set is **empty for every flow and every WorkItem
  type**.
- **A refusal leaves `audit.md` byte-identical.** Reproduced at `gate approve`
  (`review_missing`, `not_at_gate`), at `skip` (`not_failed`) and at `gate omit`
  (`gate_required`), each with a byte comparison of the ledger before and after;
  `audit verify` then exits 0 with `matches: true`. B1/NB-6 intact.
- **Claude cannot lower a deterministic floor.** Enforced in the engine by
  `_refuse_weakening` → `policy_weakens_baseline` at exit 1, never by prompt
  text; the prompt layer restates no policy value at all.
- **`gate omit` refuses `gate_required` unless the policy permits**, and
  `cmd_gate_approve` contains no requirement check whatsoever (AST: its only
  refusals are `artifact_missing` and `not_at_gate`, and it makes no call to
  `gate_requirements*` or `required_gate_set`), so **approving an omittable gate
  is always still allowed**. Driven: `gate approve --gate gate_tasks` at LOW,
  where `governance gates` reports it omittable, exits 0 and records
  `"approved"`.
- **The flow's last gate before `complete` is always required**, by a derived
  positional rule. `gate_security` is terminal in all five flows; the terminal
  gate is `required` with `terminal_gate` among its reasons across the full
  5 flows × 4 levels × 4 types cross product; and being derived, it sits in no
  dictionary an override could reach.
- **Omitted gates still raise drift.** `compute_drift` and `cmd_repo_staleness`
  both filter on `BASELINED_GATE_DECISIONS`, which is
  `("approved", GATE_OMITTED_DECISION)`. Plan F2 / A9.
- **`GREENFIELD_V1_PHASES` is the frozen 19-entry tuple**, still not a
  `FLOW_PHASES` row; every flow's phase list is element-wise identical to
  `e1cf341`.
- **Byte-identical to `e1cf341`:** `tests/test_integration_01_happy_path.py`,
  all ten files under `docs/dry-runs/` (the nine transcripts plus that
  directory's README), `.claude/skills/sdle/templates/state.json`,
  `.claude/hooks/`, `.claude/settings.json`, `.gitignore`, `tests/conftest.py`.
  `git diff --exit-code e1cf341 --` over that set exits **0**.
- **No version bump:** `lint-skill` reports `all four locations report v1.16`;
  the migration chain still has **16** rows; `approvals` still has exactly
  **8** keys.
- **Everything except human approval stays universal** for an omitted gate:
  artifact generation, `artifact record`, the baseline SHA, TP-011 review, the
  drift queue, the secrets scan, test evidence at `implement`, the
  implementation diff baseline, the audit chain, caps and fail-safe
  transitions.
- **Invariant 3** — no `speckit-*` name or `/speckit.*` command in any added
  (`^+`) line of the T09 diff. **Invariant 4** — Step 6b displays artifact
  content before either option. **Invariant 7** — the prompt layer asks the
  engine and restates nothing. **Invariant 8** — nothing holding a gate is
  delegated; no `.claude/agents/` product subagent exists.
- **Legacy `.workflow/` dual-read** still binds with no WorkItem registered;
  `migrate-workflow` still leaves `.workflow/` byte-for-byte untouched;
  `gate omit` refuses `governance_workitem_required` on that rung.
- **No T10/T11 leakage:** the product skill is still the single undivided
  `sdle`; `apply-sdle-transition` and the four `sdle-transition-*` agents are
  migration control plane, named as such by the plan's scope exclusion;
  `current_feature_id`, `legacy_workflow` and `SDLE_OWNED_PREFIXES` (still
  without `.sdle`) all still present.

---

## Test changes and TP-003 classification

**Three categories, no fourth. Zero deletions (`D`) and zero relaxations (`R`)
under `tests/`.** No test is deleted, `skip`ped, `xfail`ed or weakened — an AST
sweep confirms no `@pytest.mark.skip/skipif/xfail`, `pytest.skip(` or
`pytest.xfail(` anywhere in the changed files, and the per-file test-function
counts are preserved (`test_units_baseline.py` 41 → 41,
`test_units_governance.py` 72 → 72) with the two apparent removals being the
authorised **renames** of X1 and X6.

| Test | Category | Rationale |
|---|---|---|
| `test_units_governance.py::test_no_phase_movement_function_consults_the_would_be_gate_set` → `…::test_the_phase_movement_path_consults_the_requirement_model` (**X1**) | 2 | It asserted that no phase-movement function consults the gate set. T09 makes exactly that consultation the mechanism. Inverted in place; renamed because the old name states the opposite of what it now proves; its companion vacuity guard is untouched |
| `test_units_governance.py::test_the_would_be_gate_set_is_always_a_subset_of_the_registered_gates` (**X2**) | 2 | Record/payload key rename; `advisory is True` dropped. Subset and non-emptiness assertions kept |
| `test_units_governance.py::test_the_would_be_gate_set_actually_differs_across_risk_levels` (**X3**) | 2 | Key rename only; `LOW < CRITICAL` still asserted |
| `test_units_governance.py::test_risk_and_type_change_no_lifecycle_behaviour` (**X4**) | 2 | Clause 3 only — key rename, `advisory` dropped. Clauses 0–2, the proof that approving every gate stays risk-independent, are unchanged |
| `test_units_governance.py::test_a_floor_raises_the_level_the_score_alone_would_not_reach` (**X5**) | 2 | Docstring said the auth floor sits at MEDIUM; T09 raises it to HIGH |
| `test_units_baseline.py::test_n34_no_gate_is_conditional_on_risk_or_classification` → `…::test_gate_requirements_are_policy_driven_from_exactly_one_home` (**X6**) | 2 | T08's explicit T09-leakage guard; its subject is now this phase. Inverted, renamed for the same reason as X1 |
| `test_units_baseline.py::test_n34_every_flow_gate_set_is_structural_not_policy_driven` (**X7**) | 2 | Sharpened: flow *membership* is still structural; what is policy-driven is the *requirement* |
| `test_units_baseline.py::test_n15_the_baseline_reader_never_swallows_and_defaults` (**X8**) | 2 | **Anti-contradiction clause.** It asserted `read_repo_config` is fail-open. Only the final block (`swallower`, `swallowed`, that assertion) is replaced by the inverse, with a non-vacuity guard retained; the `read_baseline` half above it is untouched; the docstring is rewritten because it described a contrast that no longer exists |
| `test_units_governance.py::test_the_policy_reader_has_no_handler_that_returns` (**X9**) | 2 | Docstring only — it cited `read_repo_config` as the fail-open example |
| `test_units_governance.py::test_the_classification_flag_no_longer_claims_to_be_advisory` (**X13**) | 2 | Row the plan's X table was short by: the `advisory` field is deliberately removed by D12 |
| `test_units_governance.py::test_only_evaluate_risk_produces_a_final_level` (**X14**) | 2 | Unlisted row: `gate_requirements` reads `final_risk`, widening the set of functions that see a level |
| `test_units_workitem_resolution.py::test_the_invocation_list_covers_every_branch_critical_action` (**X15**) | 2 | Unlisted row: `gate omit` is branch-critical and must be in `CRITICAL_INVOCATIONS` |
| `test_units_governance.py::test_the_clause_has_exactly_one_enforcement_site` (**X16**) | 2 | Unlisted row: the enforcement-site set changes because the requirement model is a new reader |
| `test_units_artifact_review.py::test_the_artifact_shas_writer_set_is_unchanged` (**X17**) | 2 | Unlisted row: `cmd_gate_omit` writes `artifact_shas`, exactly as `cmd_gate_approve` does — that is D1, not a relaxation |
| `tests/test_units_gate_policy.py` — **new file, 1533 lines** | 1 | New coverage for new behaviour: N1–N31 |
| `test_lint_skill.py` — three firing tests for the new rule (**X12**) | 1 | New coverage: the rule must be provably failable |
| `test_lint_skill.py::test_a_project_with_no_repository_documentation_still_lints` | 1 | New coverage: the absent-document half of that rule's non-vacuity guard |
| `test_units_repo_config.py` — three tests (**N26**, D15 binding) | 1 | New coverage for the fail-closed reader and the documented-defaults binding |

The five unlisted X rows (X13, X14, X15, X16, X17) are ordinary consequences of
the plan's own design decisions, each recorded in the checkpoint for the
milestone that hit it; none required a plan change or a human decision.

`tests/conftest.py` is **unchanged** — the anti-contradiction clause permitted a
governance-input helper but `record_governance(**over)` already accepted the
overrides needed, so none was added.

---

## Commands actually run

Every pytest invocation went through `rtk proxy`, was redirected to a file, and
its raw exit code was read with **no pipe** (plain `python -m pytest` under the
`rtk` hook prints "No tests collected" and exits 0 — a false green).

| Command | Result | Evidence/summary |
|---|---|---|
| `git rev-parse HEAD` | `ad08d4b5a4dc1303a9c48a9dc8af0ad76f8c55a8` | Nothing committed this attempt |
| `python scripts/sdle.py lint-skill` (after each document edit, and finally) | exit **0** | **33 checks, `failed: []`**; `all four locations report v1.16`; `repo_config_defaults_match_documentation` → `1 documented configuration block(s) equal REPO_CONFIG_DEFAULTS` |
| `python scripts/sdle.py governance policy` | exit **0** | `source builtin`; **17** signals, **12** floor rules; `required_gates_by_risk` = `{LOW: [], MEDIUM: [gate_tasks, gate_design], HIGH: [gate_tasks, gate_analyze, gate_design, gate_security], CRITICAL: same}`; `required_gates_always`, `required_gates_by_type`, `risk_thresholds` and `policyVersion: 1` unchanged |
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` | exit **0** | **1402 tests collected in 0.77s** |
| `rtk proxy "python -m pytest tests/test_units_gate_policy.py -k 'n27 or …'"` (staged block, first run) | exit **1** | **3 failed, 13 passed** — the three draft defects |
| the same, after fixes | exit **0** | **16 passed** |
| `rtk proxy "python -m pytest tests/test_units_gate_policy.py tests/test_lint_skill.py"` | exit **0** | **401 passed in 160.04s** |
| `rtk proxy "python -m pytest tests/test_units_workitem_runtime.py"` (before the lint fix) | exit **1** | **1 failed, 44 passed** — the inherited failure, reproduced and diagnosed |
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_workitem_runtime.py tests/test_units_repo_config.py"` (after) | exit **0** | **159 passed in 151.40s** |
| **`rtk proxy "python -m pytest -q -p no:cacheprovider --no-header"`** | **RAW_EXIT=0** | **`1402 passed in 1409.25s (0:23:29)`.** Collected (1402) equals passed (1402); the summary names no skip, xfail or error category |
| Live CLI probe (temporary file, deleted after the run) | exit **0** | **4 passed**; printed output quoted in checkpoint 05 |
| `python tools/transition/validate.py` | exit **0** | `TRANSITION_VALID: complete=9/12 next=T09` |
| `git diff --exit-code e1cf341 -- <must-not-change set>` | exit **0** | state template, hooks, `settings.json`, `.gitignore`, happy path, `docs/dry-runs/`, `conftest.py` |
| Python 3.11 | **NOT_RUN** | Only Python 3.13.0 is available in this environment |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN** | Nothing pushed; outcome **UNKNOWN**, not predicted |

### Acceptance matrix

| # | Verdict | Evidence |
|---|---|---|
| A1 | **PASS** | `governance policy` row above — 17 signals, 12 floor rules, the exact `required_gates_by_risk`, everything else unchanged. Pinned by `test_a1_the_built_in_policy_shape_is_what_section_15_requires` |
| A2 | **PASS** | `test_n7_every_section_15_floor_fires_through_the_cli` (parametrised over an explicit nine-row table) and `test_n8_authentication_alone_is_high` |
| A3 | **PASS** | `test_n9_no_built_in_floor_was_lowered_or_removed`, `…_no_built_in_signal_weight_was_lowered_or_removed`, `…_no_threshold_became_harder_to_reach` |
| A4 | **PASS** | `test_n10_an_override_restating_the_old_auth_floor_is_refused` |
| A5 | **PASS** | `test_n11_…` (HIGH, CRITICAL), `test_n13_the_terminal_gate_is_never_omittable_through_the_cli`, `test_n21_every_new_refusal_leaves_the_ledger_byte_identical`; independently reproduced by the live probe |
| A6 | **PASS** | `test_n11_a_high_risk_workitem_cannot_skip_design_or_security`, `test_n12_a_low_risk_workitem_may_omit_design_but_not_security`; independently reproduced by the live probe |
| A7 | **PASS** | `test_n4_hotfix_has_no_omittable_gate_at_any_level` (4 levels × 4 types), `test_hotfix_cannot_omit_any_of_its_three_gates`; re-derived here over the whole cross product |
| A8 | **PASS** | N21 plus N16 and N20 for the fifth and sixth sites; live probe reproduced ledger byte-identity at `gate approve` and `skip` too, with `audit verify` `matches: true` |
| A9 | **PASS** | `test_n19_an_omitted_gate_keeps_drift_protection`, `test_the_implement_gate_evidence_is_unchanged_by_an_omission`, N12, N20; `BASELINED_GATE_DECISIONS` is the single filter both `compute_drift` and `cmd_repo_staleness` use |
| A10 | **PASS** | `git diff --exit-code e1cf341` over the set = 0; `lint-skill` `all four locations report v1.16`; 16 migration rows; 8 `approvals` keys (`test_n28_the_state_schema_did_not_move`) |
| A11 | **PASS** | `test_n27_n28_the_frozen_files_are_byte_identical_to_the_rollback_point`, `test_n27_the_nine_dry_run_transcripts_are_byte_identical` (line endings normalised) |
| A12 | **PASS** | `test_n31_the_legacy_rung_and_migrate_workflow_are_untouched` (SHA map of `.workflow/` before and after), `test_n18_the_legacy_runtime_can_never_omit_a_gate` |
| A13 | **PASS** | `test_n29_the_frozen_greenfield_tuple_and_every_flow_are_unchanged` — the other four flows compared element-wise against `e1cf341`'s own SKILL.md |
| A14 | **PASS** | `test_no_policy_default_value_is_restated_outside_sdle_py` (22 needles: 17 signals + 5 underscored check ids) plus `test_n30_the_policy_needle_count_is_what_this_phase_left_it` and `test_n30_adr_006_exists_and_names_no_policy_identifier` |
| A15 | **PASS** | `git diff e1cf341 \| grep -E '^\+.*(speckit-\|/speckit\.)'` → no match; `test_a15_no_speckit_name_leaked_into_the_prompt_layer`; no product subagent |
| A16 | **PASS** | AST enumeration of the refusals in `cmd_gate_omit` (`drift_pending`, `not_at_gate`, `governance_workitem_required`, `governance_missing`, `gate_required`, `artifact_missing`) and `apply_advance` (`gate_omission_invalidated`) — every new path raises `Refused`; none warns |
| A17 | **PASS** | 33 checks, `failed: []`. The 32 at HEAD all present and passing, plus the new rule with four firing/behaviour tests |
| A18 | **PASS** | `test_n26_the_reader_itself_refuses_rather_than_defaulting`, `test_n26_a_malformed_config_still_refuses_with_the_same_reason` |
| A19 | **PASS** | `test_a19_the_unqualified_readme_clause_is_gone` |
| A20 | **PASS** | `test_n30_adr_006_states_both_halves_of_the_guarantee` — `**Guaranteed.**` / `**Not guaranteed.**`, "could **not** have been chosen for a gate the policy required", "cannot tell whether a human being or the orchestrator issued" |
| A21 | **PASS** | 1402 collected, **1402 passed**, RAW_EXIT **0**. The baseline was re-derived here rather than inherited: `git archive e1cf341` extracted to scratch collects **1025**. The delta is accounted for file by file — `test_units_gate_policy.py` 0→**363**, `test_lint_skill.py` 35→**39**, `test_units_repo_config.py` 72→**75**, `test_units_governance.py` 181→**187**, `test_units_workitem_resolution.py` 96→**97**, `test_units_baseline.py` and `test_units_artifact_review.py` unchanged at 55 and 40. 363+4+3+6+1 = **377**, and 1025 + 377 = **1402** |
| A22 | **PASS** | `validate.py` exit 0; the T09 progress row contains no literal `\|` inside a cell |
| A23 | **PASS** | The table above. Changed test functions are a subset of the X table plus the five unlisted rows recorded in the checkpoints; `conftest.py` unchanged |
| A24 | **PASS** | `test_n31_no_t10_or_t11_leakage` |
| A25 | **PASS** | Python 3.11 and CI recorded **NOT_RUN / UNKNOWN** above; no outcome predicted |

---

## Git evidence

- **HEAD:** `ad08d4b5a4dc1303a9c48a9dc8af0ad76f8c55a8`. **Nothing committed
  this attempt** — all work is in the working tree.
- **Working tree** (`git status --short`, excluding `docs/transition/`):

  ```
   M .claude/commands/sdle-approve.md
   M .claude/settings.local.json      <- already modified at HEAD; OUT OF SCOPE, untouched
   M .claude/skills/sdle/SKILL.md
   M .claude/skills/sdle/modules/gate-protocol.md
   M README.md
   M docs/SDLE-Reference-Guide.md
   M scripts/sdle.py
   M tests/test_lint_skill.py
   M tests/test_units_artifact_review.py
   M tests/test_units_baseline.py
   M tests/test_units_governance.py
   M tests/test_units_repo_config.py
   M tests/test_units_workitem_resolution.py
  ?? docs/architecture/ADR-006-risk-adaptive-gate-policy.md
  ?? tests/test_units_gate_policy.py
  ```

- **Diff scope** — `git diff --numstat e1cf341`:

  | Path | + | − |
  |---|---:|---:|
  | `scripts/sdle.py` | 677 | 52 |
  | `tests/test_units_governance.py` | 98 | 40 |
  | `tests/test_units_baseline.py` | 67 | 25 |
  | `tests/test_lint_skill.py` | 62 | 0 |
  | `tests/test_units_repo_config.py` | 49 | 1 |
  | `.claude/skills/sdle/modules/gate-protocol.md` | 32 | 2 |
  | `docs/SDLE-Reference-Guide.md` | 24 | 7 |
  | `README.md` | 15 | 2 |
  | `tests/test_units_artifact_review.py` | 11 | 2 |
  | `.claude/skills/sdle/SKILL.md` | 9 | 1 |
  | `.claude/commands/sdle-approve.md` | 7 | 0 |
  | `tests/test_units_workitem_resolution.py` | 6 | 1 |

  New files: `tests/test_units_gate_policy.py` (1533 lines),
  `docs/architecture/ADR-006-risk-adaptive-gate-policy.md` (304 lines).

- **Rollback:** `git checkout e1cf341 -- scripts/sdle.py README.md docs/SDLE-Reference-Guide.md .claude/ tests/`
  and delete the two new files. Product baseline `f8fdaa0`.

---

## Known limitations / risks

1. **Python 3.11 and CI are NOT_RUN.** Only Python 3.13.0 is available here and
   nothing was pushed. T09 adds no syntax or stdlib surface beyond what T05–T08
   already use, but the outcome is **UNKNOWN** and is not predicted.
2. **The dry-run transcripts are now mildly stale as documentation.** They show
   runs that approve all eight gates, which remains a valid run at every risk
   level, but is no longer the only shape a run can take. They stay
   byte-identical by design (A11); the staleness joins T04 N-6's documented
   transcript residual for **T11**'s documentation sweep. Plan U6.
3. **The plan's D6 prose contains an off-by-one that ADR-006 inherited.** The
   plan says "Five map onto an existing signal; four do not" while its own table
   and the shipped engine are four and five. The engine is right; **ADR-006 is
   corrected here** to four/five. The plan is immutable and is left alone; this
   note is the record.
4. **`_repo_root()` resolves documentation against the target project.** In a
   downstream project with its own `README.md`, the new lint rule and the
   pre-existing `doc_lists_every_phase_README` both evaluate that README. That
   exposure predates T09 (`_check_doc_phase_tables` shipped with it) and is not
   adopted here; the new rule was made to follow the same convention rather than
   invent a second one.
5. **`gate omit` is unreachable on the legacy `.workflow/` rung**, by design
   (`governance_workitem_required`). A repository that has not migrated keeps
   universally required gates — strictly stricter, but worth knowing.
6. **Everything else on the open-findings list stays open**, explicitly
   including `.sdle/` being in neither `SDLE_OWNED_PREFIXES` nor
   `cmd_manifest_build`'s exclusion (T04 N-7 / T05 NB-7(b)) — still T11's.

---

## Claims for verifier to independently check

1. **Re-run the full suite yourself** through `rtk proxy`, redirected, `$?` read
   unpiped. Expect 1402 collected and 1402 passed, RAW_EXIT 0, ~23 minutes. The
   F1 `ENVIRONMENT_FLAKE` procedure is **VOID**; any failure is a presumed real
   regression.
2. **Drive §15's exit criterion yourself**, not only via the tests: a HIGH-risk
   GREENFIELD WorkItem must be unable to `gate omit` either `gate_design` or
   `gate_security`, and unable to `advance` past them.
3. **Check ledger byte-identity around every refusal**, including at
   `gate approve` and `skip`, and that `audit verify` exits 0 afterwards.
4. **Confirm no floor or weight is below its `e1cf341` value** — the literals
   are in `test_units_gate_policy.py`, so read them against `git show
   e1cf341:scripts/sdle.py` rather than trusting the test.
5. **Confirm the terminal-gate rule is derived, not a policy row**, and that no
   override can remove it (`test_n17_an_override_can_make_every_gate_universal_again`
   shows overrides only tighten).
6. **Confirm ADR-006 names none of the 22 policy identifiers** and that its
   floor arithmetic (four reused signals, five new) matches
   `GOVERNANCE_POLICY_BUILTIN` at HEAD versus `e1cf341`.
7. **Confirm the M5 lint-check change is not a relaxation** — delete the
   `configVersion` block from a README that stays on disk and check the rule
   still fires.
8. **Confirm no T10/T11 leakage**, remembering that `.claude/agents/` and
   `.claude/skills/apply-sdle-transition/` are migration control plane, named as
   such by the plan's scope exclusion, and were present before T09.
9. `git diff --exit-code e1cf341 --` over the must-not-change set must exit 0.
10. Beware the tooling traps recorded in checkpoint 05 — in particular the plain
    `grep -rn` false negative, which recurred in this context on
    `scripts/sdle.py`.

## Blocker (only if material decision is required)

**None.** No `T09-blocker.md` was written. Every problem encountered was an
ordinary implementation or test defect and was fixed.
