# T11 Implementation Handoff — Attempt a01

**Phase:** T11 — Production Hardening, Cleanup and V1 Convergence
**Attempt:** 01
**Implementer context:** fresh/isolated (this context finished the phase; M1–M8 were
implemented across several interrupted contexts of the *same* attempt — see §1.2)
**Status recommendation:** **IMPLEMENTED**

> **T11 is the final phase of the migration. There is no T12.** A finding
> dropped here is dropped permanently. §11 of this handoff therefore gives every
> inherited finding exactly one disposition, and §12 states, explicitly, the
> things the plan asked for that were **not** done and why.

---

## 1. Inputs read from disk

### 1.1 What was read

| Input | Use |
|---|---|
| `docs/transition/transition.md` §§1.4, 17, 18, 19, 20, 24.3, 26, 27, 28 | The contract. §17's Remove / Preserve / Hardening / Documentation lists were parsed programmatically, not read off prose |
| `docs/transition/phases/T11-plan.md` (immutable) | The plan: E1–E36, R1–R7, P1–P9, D1–D16, B1–B12, X1–X12, N1–N25, A1–A22, TR1–TR26, F1–F14 |
| `docs/transition/phases/T11-blocker.md` | The blocker raised at M7 — **now resolved**, see §2 |
| `T11-checkpoint-a01-01` … `-07` | Milestone boundaries M1–M8. `-07` carried the resume state |
| `docs/transition/progress.md`, `RESUME.md` | Control state |
| `CLAUDE.md`, `README.md`, `docs/SDLE-Reference-Guide.md`, ADR-001…ADR-007 | The documentation the phase had to converge |
| `scripts/sdle.py`, `.claude/hooks/hooks.py`, `.claude/skills/sdle/**`, `tests/**` | The actual source. Every claim below was checked against it |
| Git: `git log`, `git status --porcelain`, `git diff --stat 4b1aa71`, `git show <commit>:<path>` | Independent repository evidence |

### 1.2 Two facts about this attempt that the verifier needs up front

**This is still attempt 01.** There has been no verification FAIL. The attempt
spanned several contexts because it was interrupted repeatedly by API session
limits (§24.6 interruption, which does not increment the attempt). Each
interruption was crossed at a milestone boundary using
`TNN-checkpoint-a01-XX.md`, exactly as §24.3 provides for.

**M1–M4 are committed; M5–M8 are not.** HEAD is `42c7d5b`. The M5–M8 work,
including the whole documentation set, ADR-008, `tests/test_units_hardening.py`
and the write-fence correction, is **live in the working tree**. It is real, it
is green, and it must not be redone.

```
42c7d5b  T11 M4: governance downgrade evidence (D11, D12, N12)
90e52d0  T11 M3: Spec Kit tier ambiguity fails closed (D10, X8, N21)
17f7ea2  T11 M2: guard consistency (D5-D9, X4, X5, X9, N18-N20)
a25c930  T11 M1: remove the legacy runtime binding (D1-D4, R1-R5)
97100e2  Plan T11 production hardening and V1 convergence
4b1aa71  T10 verified PASS; phase COMPLETE          <- byte-identity baseline
11363d9  T10 implementation                          <- rollback point
f8fdaa0  product baseline
```

### 1.3 Where the plan disagreed with the repository

The plan was verified against current evidence (§24.3 step 2). Three of its
recorded figures are wrong, and the corrected values are the observed ones.
Plans are immutable, so the corrections live here.

| Plan | Says | Observed | Consequence |
|---|---|---|---|
| **E20** | 18 stale `.workflow/` lines in `docs/dry-runs/` | **17 lines carrying 20 occurrences** — three lines carry two each | `DRY_RUN_SUBSTITUTIONS` has 17 pairs, not 18 |
| **§9 totals** | reads as 20 FIXED / 3 DEFERRED / 2 NOT-A-DEFECT / 1 verify-then-record | **20 FIXED / 4 DEFERRED / 2 NOT-A-DEFECT = 26.** TR20 resolved to DEFERRED in M5 | ADR-008 §7 states 20/4/2. Any prose saying "19 FIXED" is wrong — count the table |
| **§10 / E35** | "Windows / Python 3.14" | **CPython 3.13.0** on win32 | Recorded as observed. Python 3.11 stays `NOT_RUN`, CI stays `UNKNOWN` |

**E31 was checked and is correct:** §17's mandatory hardening list has **16**
bullets, not 17. This was re-derived by parsing the section, not counted by eye.

Two further plan defects were found during implementation and are recorded as
plan deviations, not absorbed: **PD-B** (plan E15 says two tests pin `.sdle/`
as absent; there are three, and the third is in a file §7.2 lists as "Not
affected") and **PD-D** (D10 names `feature bind` as its escape hatch;
`feature bind` cannot name a feature id and is not one). See §10.

---

## 2. The blocker — raised, escalated, decided by the user, resolved

`T11-blocker.md` is retained on disk **unmodified**. It records a real defect in
a shipped guardrail, found at M7 while writing documentation, and it is part of
this phase's evidence. `progress.md` records that it was resolved rather than
deleting the history of it.

**What was blocked.** Contract §17 mandates a documentation directory at
`docs/workitems/`. The shipped write-fence hook denied every write to it. The
minimal correction to `.claude/hooks/hooks.py` was then denied by the auto-mode
permission classifier. Two walls: one the product's, one the permission
system's. The implementer refused to create the file with a different tool,
because routing around a guardrail refusal — in the phase whose entire subject
is guardrail integrity — would have been the worst available precedent.

**The user approved the fix (Option A in the blocker) and it was applied.** It
is recorded in §5.3 below as a **user-approved product change made outside the
plan**, not folded into a D-item that does not fit it.

---

## 3. Changes made — by milestone

### M1 — Remove the legacy runtime binding (`a25c930`)

The only milestone with a red window, taken first. Its correctness argument is
**nothing else moved**: integration 01, the three integration files,
`.claude/settings.json`, `.gitignore` and all nine transcripts stayed
byte-identical throughout, and GREENFIELD's traversal is unchanged.

- **D1** rung 6 deleted from `resolve_decision`. With zero registered WorkItems
  the ladder returns `reason="none"` whether or not `.workflow/state.json`
  exists. `Resolution.rung` can no longer be `"legacy"`.
- **D2** the `if decision.rung == "legacy": return paths` arm deleted from
  `bind_workitem`. A successful bind now **always** returns a bound `Paths`.
- **D3** the `workitem_required` refusal widened: when `legacy_state_present`,
  the message names `workitem create` then `migrate-workflow --workitem <id>`
  **in that order**, and `data` carries `legacy_state`. Same reason string, same
  exit code — no CLI-contract break. Closes TR22.
- **D4** **11** unreachable `paths.workitem is None` carve-outs deleted (the
  plan's E12 lists 12 *sites*; the 12th, `collect_validation_findings`, is
  explicitly kept by D4 itself — P5). Two reason strings became unreachable and
  went with their branches: `governance_workitem_required`,
  `discovery_workitem_required`.
- **R7** the legacy-runtime paragraphs in `SKILL.md` and
  `.claude/commands/sdle-start.md`.

**A3 verified by AST, not grep:** exactly two `X.workitem is None` comparisons
remain in `sdle.py` — `Paths.workitem_root` (the dataclass describing its own
shape) and `collect_validation_findings` (P5). Pinned by
`test_n25_no_unbound_runtime_carve_out_survives_in_the_engine`.

**Preserved and re-verified after the patch, not assumed:** `PROJECT_ROOT_MARKERS`
still contains `(".workflow", "state.json")` (P1); `Paths.legacy_workflow` (P2);
`cmd_migrate_workflow` in full (P3); `legacy_state_present` (P4); the
`runtime_state_outside_workitem` finding (P5); `.workflow` in `FENCED` and in
`SDLE_OWNED_PREFIXES` (P6); `.workflow/` in `.gitignore` (P7).

### M2 — Guard consistency (`17f7ea2`)

- **D5** `".sdle/"` added to `SDLE_OWNED_PREFIXES`.
- **D6** `cmd_manifest_build` gains its sibling's relocation/ownership
  exclusion, so the Gate 7 manifest stops listing SDLE's own bookkeeping as
  implementation changes. Closes TR9/TR11.
- **D7** the candidate path is normalised before `SPECS_CARVE_OUT` matches, so
  `workitems/<id>/specs/../.sdle/state.json` no longer escapes the fence.
  Closes TR12.
- **D8** `cmd_workitem_use` error-hardened (an `OSError` is a refusal, not a
  traceback); its `UsageError` reason renamed `workitem_required` →
  `workitem_flag_required`, and the same rename in `cmd_migrate_workflow`, so
  one reason string no longer spans exit 1 and exit 2. Closes TR17/TR18.
- **D9** `ACTIVE_CONTEXT_SETTERS` made load-bearing: `write_active_context`
  raises on a non-member `set_by`. A dead constant became an enforced one
  rather than being deleted, because the fact it encodes is worth keeping.
  Closes TR16.
- `FENCE_REASONS[".workflow"]` reworded from "transitional" to "archival".

**The §28 argument for D5, stated precisely** (and narrower than the plan's TR9
wording, which is corrected here): the dirty-tree guard exists to make the
Gate 7 implementation diff meaningful, and `.sdle/` is never implementation.
Its evidence trail is **Git** (`.sdle/` is versioned, §19) plus, for the
baseline, the `baseline_established` audit event. The plan said "both already
produce their own audited records"; `config init` is `RUNTIME_FREE` and appends
to no ledger, so Git — not the audit — carries `.sdle/config.json`. Nothing that
was evidence stops being evidence. Without D5, one WorkItem completing could
trip a *different* WorkItem's `implement preflight` on a change the engine
itself made — cross-WorkItem coupling §8/§9 forbid.

### M3 — Spec Kit tier ambiguity fails closed (`90e52d0`)

- **D10** `cmd_feature_resolve` applies §9's own 0/1/>1 rule inside the chosen
  tier: **more than one candidate refuses `feature_ambiguous`** and lists them.
  The newest-mtime comparison is gone; `_feature_candidates` now sorts by name.
  The refusal's `data` gains `workitem` and `remedy_tier`.

The defect closed (TR10) is concrete: tier 2 is the repository-global `specs/`,
where Spec Kit hardcodes feature *creation*. Two WorkItems standing at the
specification phase stage into one shared directory, and newest-mtime hands
whichever runs second the other's specification — silently, with no refusal and
no audit entry saying a choice was made. **Recency is not evidence of
ownership.**

### M4 — Governance downgrade evidence (`42c7d5b`)

- **D11** `governance_downgrade(previous, risk)` — a pure comparison returning
  both levels, both signal sets and the deltas, or `None`. `cmd_governance_assess`
  reads the record it is about to replace **before** overwriting it and stores
  `record["downgrade"]` (always present, `null` when nothing was lowered).
  `governance show` promotes it. A distinct `governance_downgraded` audit event
  is appended with its own de-duplication marker, and `cmd_gate_omit` carries
  the block into the approvals entry, the payload and the `gate_omitted`
  message. Closes TR7.
- **D12** one paragraph in `modules/gate-protocol.md` Step 6b and one in
  `SKILL.md`: re-assessment is not a gate-clearing device; re-assess only when
  scope actually changed; a downgrade is recorded and never invisible.

**It audits; it does not refuse.** A genuine re-scope legitimately lowers risk.
Refusing would invent a floor no contract section states and would push a
correct user toward hand-editing the record — a dead end, not a guardrail.
**B3 is intact: no policy floor value moved** (`test_n9_no_built_in_floor_was_lowered_or_removed`).

### M5 — Schema, version, branch-guard fail-open (working tree)

- **D13** `pending_branch_ack` (null by default). Written when the first step of
  a two-step command acknowledges a branch; required to match at the second.
  Switching branch between the two steps now produces an audited
  `branch_mismatch` instead of an unaudited action. Closes TR15.
- **D14** version `1.16` → `1.17`; `VERSION_MIGRATION` row `1.16 → 1.17`;
  `_mig_1_16` and the `("1.16","1.17")` `MIGRATIONS` row; a README v1.17 row.
  Per **F6**, `sdle.py::CURRENT_VERSION` was **added to
  `_check_version_consistency`** rather than hand-edited, so the lint rule stays
  the single authority. `lint-skill` now reports *all 7 locations report v1.17*.
- **X6** `templates/state.json` pulled out of both `FROZEN` tuples and pinned
  instead by `test_t11_the_state_template_changed_only_as_declared`.

**TR20 was verified, not assumed, and the verdict is DEFERRED.** The plan said
"FIXED as a by-product of D13 — verify explicitly; if it does not fall out,
record as DEFERRED". It does not fall out: `branch_guard` runs ahead of the
command body and cannot know whether that body will succeed, so
`branch_mismatch_accepted` still precedes a later unrelated refusal. D13 changes
*which* acknowledgement is honoured, not *when* it is written. The residual is
pinned by `test_tr20_the_acknowledgement_is_still_ledgered_before_a_later_refusal`
so it is visible rather than silent.

### M6 — The 16 mandatory hardening tests (working tree)

**A new file, `tests/test_units_hardening.py` — 31 test functions, 38 collected
cases, 1180 lines.** N12 is not in it: it landed in M4 beside the governance
regime it guards (`test_n12_*` in `test_units_governance.py`), which is where it
belongs. All 16 §17 bullets are covered by named test functions.

**Two product changes, both TP-003 category 3 — a hardening test found a gap.**
M6's scope explicitly permits this.

| Change | Why |
|---|---|
| `cmd_gate_omit` records `governance_sha256` on the approvals entry and in the payload | The omission fingerprinted the *policy* but not the *governance record the level came from*, so "which record said LOW" was unanswerable from the evidence alone. §15 requires an omitted gate to be explainable **later** |
| `baseline_commit(paths)`; `baseline_precondition` and `cmd_baseline_validate` carry `baseline_commit` in refusal `data` | A baseline finding said *what* was wrong without saying which repository state its claims were ever true for. It swallows to `None` on an unreadable file so it can never turn a diagnosed `INVALID` into an exit 3 |

Neither adds a writer, a command, a state field or a gate.

### M7 — Documentation convergence (working tree)

- **Six new documentation directories**, all nine §17 targets now present:
  `docs/workitems/`, `docs/lifecycle/`, `docs/risk-and-gates/`,
  `docs/brownfield/`, `docs/spec-kit-integration/`, `docs/troubleshooting/`.
  Each opens by naming `scripts/sdle.py` as the authority and itself as a
  derived view, so a future divergence is a defect in the document rather than
  an ambiguity.
- **`docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`** — NEW,
  379 lines. See §11.
- **D16** a new `lint-skill` check, `documentation_set_is_present`, over
  `DOCUMENTATION_TARGETS`. **X7** extends `test_n26`'s exact-set equality with
  `T11_CHECKS = ("documentation_set_is_present",)` — 42 → 43, equality kept
  exact.
- `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md` (whose header had
  drifted three revisions behind its own history table; 1.1 → 1.5), ADR-001,
  ADR-007, the four product agent bodies, `sdle-approve.md`, `SKILL.md`,
  `modules/gate-protocol.md`, `modules/phase-execution.md`,
  `modules/code-review.md`, `modules/design-review.md`.
- Closes **TR2, TR3, TR4, TR6, TR13, TR14 (prompt half), TR21, TR26**.

**The prompt-layer `.workflow/` residuals were not replaced with a
`workitems/<id>/…` literal where the engine already reports the answer.**
`manifest build` returns `path`, so both manifest mentions now say to take it
from the response; the audit-append instruction dropped its path entirely. Only
the completion summary names a literal, because no command reports that
directory directly — and `cmd_resume`'s payload was read before writing that,
not assumed.

### M8 — Dry-run transcript convergence (working tree)

- **D15** the 17 stale lines (20 occurrences) across six transcripts converged
  to the WorkItem runtime shape.
- **X10** **both** pins converted — **not re-baselined** — to a
  declared-substitution comparison. See §7, which justifies the conversion
  property by property rather than asserting it is better.

One substitution is not a path rewrite: transcript 06's list of prefixes the
dirty-tree guard filters. It gained `.sdle/` and `workitems/` and now matches
`SDLE_OWNED_PREFIXES` **element for element and in the engine's order**, read
off the constant. `.workflow/` still appears exactly once in `docs/dry-runs/`,
in that list, and that mention is **correct** — it is still an owned prefix.

---

## 4. Preserved behaviour / invariants

### 4.1 The §18 Capability Preservation Matrix, row by row (A14)

Every PRESERVE / ADD-ENFORCE row with a **named test that passed in this
context's segmented run**. No row is claimed superseded without citing the
contract section that supersedes it.

| §18 capability | Transition | Named passing test |
|---|---|---|
| Python deterministic core | PRESERVE | `test_units_cli.py::test_success_and_refusal_share_one_envelope_shape` |
| Claude-first UX | PRESERVE | `test_integration_01_happy_path.py::test_traversal_matches_the_transcript` |
| CLI called by Claude | PRESERVE | `test_units_cli.py::test_refusal_exit_code_survives_the_process_boundary` |
| JSON stdout contract | PRESERVE | `test_units_cli.py::test_success_and_refusal_share_one_envelope_shape` |
| Exit codes 0/1/2/3 | PRESERVE | `test_units_cli.py::test_refusal_exit_code_survives_the_process_boundary`, `::test_integrity_exit_code_survives_the_process_boundary`, `::test_unknown_subcommand_is_usage_error_not_traceback` |
| Atomic writes | PRESERVE | `test_units_infra.py::test_write_atomic_replaces_completely`, `::test_write_atomic_leaves_no_partial_file_on_failure`; `test_units_hardening.py::test_t11_n6_a_stray_partial_temp_is_never_authoritative` |
| Idempotent deterministic commands | PRESERVE | `test_units_state.py::test_migrate_is_idempotent`; `test_units_transitions.py::test_n23_the_migration_adds_the_field_and_is_idempotent` |
| Cross-platform launchers | PRESERVE | `test_units_hardening.py::test_t11_n16_both_launchers_agree_on_the_interpreter_contract`; `test_units_infra.py::test_a_real_launcher_run_succeeds_here` |
| Artifact SHA/fingerprints | PRESERVE | `test_units_flow_model.py::test_the_impact_analysis_artifact_is_fingerprinted`; `test_units_artifact_review.py::test_recorded_shas_are_lowercase_hex` |
| Artifact review/validation against exact SHA | ADD / ENFORCE | `test_units_flow_model.py::test_the_impact_analysis_review_is_bound_to_that_exact_sha`; `test_units_artifact_review.py::test_a_one_byte_edit_after_review_blocks_approval_until_re_review` |
| Review evidence + audit linkage | ADD / ENFORCE | `test_units_artifact_review.py::test_the_review_evidence_document_records_the_whole_record`, `::test_the_audit_entry_carries_every_tp011_field` |
| Stale-review invalidation after artifact change | ADD / ENFORCE | `test_units_artifact_review.py::test_a_one_byte_edit_after_review_blocks_approval_until_re_review`, `::test_an_earlier_pass_does_not_survive_a_later_fail` |
| Drift detection | PRESERVE | `test_integration_02_to_05.py::test_04_drift_is_detected_against_the_baseline` |
| Drift diff evidence | PRESERVE | `test_integration_02_to_05.py::test_04_drift_reapproval_walks_the_queue_one_at_a_time`; `test_units_artifact_review.py::test_drift_reapproval_needs_a_review_of_the_drifted_content` |
| Audit integrity / hash chain | PRESERVE | `test_integration_01_happy_path.py::test_audit_chain_survives_the_whole_run`; `test_units_hardening.py::test_t11_n5_a_tampered_chain_is_located_and_writes_nothing` |
| Rate limits | PRESERVE | `test_integration_02_to_05.py::test_02_remediation_limit_halts_without_invoking_anything`, `::test_03_retry_limit_stops_offering_retry` |
| Dirty-tree guard | PRESERVE | `test_hooks.py::test_dirty_tree_asks_when_preflight_has_not_run`, `::test_dirty_tree_resolves_a_workitem_the_same_way_the_engine_does` |
| Untrusted-content scan | PRESERVE | `test_hooks.py::test_untrusted_read_asks_on_flagged_requirements`, `::test_untrusted_read_uses_the_engine_patterns_not_a_copy` |
| Secrets scan | PRESERVE | `test_hooks.py::test_secrets_hook_flags_a_credential`, `::test_secrets_hook_never_reproduces_the_secret` |
| Test evidence | PRESERVE | `test_integration_06_to_09.py::test_06_test_evidence_records_a_real_failing_run` |
| `implementation_base_ref` concept | PRESERVE | `test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref`; `test_units_state.py::test_migrate_adds_implementation_base_ref` |
| Hook guardrails | ADAPT to WorkItem paths | `test_hooks.py::test_dirty_tree_resolves_a_workitem_the_same_way_the_engine_does`; the 21 new fence cases (§5.3); `test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical` |
| Transcript-derived tests | PRESERVE / EVOLVE | `test_units_capabilities.py::test_n20_the_nine_dry_run_transcripts_match_the_declared_substitution`; `test_units_gate_policy.py::test_n27_…`. **EVOLVE** exercised under plan §7.3 — justified property by property in §7 |
| `lint-skill` | PRESERVE initially | `test_units_capabilities.py::test_n26_every_baseline_check_is_still_present_and_passing` — exact-set equality at 43 |
| `.workflow/` repo-global runtime | REPLACE T02 — **completed at T11** | `test_units_gate_policy.py::test_t11_the_legacy_rung_is_gone`; `test_units_workitem_runtime.py::test_n25_no_unbound_runtime_carve_out_survives_in_the_engine` |
| repo-global lock | REMOVE / RESCOPE T02 | `test_units_workitem_runtime.py::test_a_lock_on_one_workitem_never_blocks_another` |
| fixed 18 phases | REPLACE T07 | `test_units_capabilities.py::test_n21_greenfield_is_frozen_and_every_flow_is_element_wise_identical` |
| fixed 8 gates | REPLACE T09 | `test_units_gate_policy.py::test_n9_no_built_in_floor_was_lowered_or_removed`; the gate-policy suite (363 cases) |
| `current_feature_id` as primary identity | DEMOTE T04 | `test_units_speckit_binding.py::test_n8_the_feature_directory_is_derived_from_disk`, `::test_n8_a_state_with_no_speckit_key_is_readable` |
| runtime artifacts gitignored | REVERSE for WorkItem records | `.gitignore` byte-identical to `4b1aa71` (P7); `workitems/` versioned by design, only `workitems/*/.sdle/lock` ignored |
| lifecycle constants in `SKILL.md` | MIGRATE only after T07/T09 stable | **Deliberately not migrated.** §18 gates it on stability, §17 does not order it, and §23 warns against a large refactor here. `lint-skill` continues to parse the tables out of `SKILL.md` — 43 checks, `failed: []` |

### 4.2 The plan's B1–B12

| # | Held? | Evidence |
|---|---|---|
| **B1** core refuses, never warns | Yes | Every new failure path (D3, D10, D13) is a refusal with reason, message and structured `data` |
| **B2** a refusal leaves `audit.md` byte-identical | Yes, **with one declared exception** | D10 is a pure reader ahead of the first `append_audit`. **D13 is not** — see §10 PD-F and ADR-008 §5.2 |
| **B3** Claude cannot lower a deterministic floor | Yes | D11 adds evidence, never permission. `test_n9_no_built_in_floor_was_lowered_or_removed` |
| **B4** the ladder never guesses | Yes | D1 removes a rung and adds no tie-break. D10 extends no-guessing into Spec Kit discovery |
| **B5** exit codes keep their meanings | Yes | D8 moves one reason string between two already-distinct codes |
| **B6** JSON on stdout, human text on stderr | Yes | `lint-skill` and `constants` still nest under `data` |
| **B7** the whole guardrail set | Yes | §4.1, row by row |
| **B8** cross-platform launchers | Yes | `no_powershell_only_cmdlets` passes; N16 |
| **B9** `migrate-workflow` never mutates `.workflow/` | Yes | `test_t11_n7_an_interruption_at_any_write_point_is_recoverable`, over all **nine** write points |
| **B10** CLAUDE.md invariants 1–8 | Yes | No T11 change delegates a gate or adds a second writer. `append_audit` gained call sites, not competitors — a new call site is not a new writer |
| **B11** GREENFIELD frozen | Yes | A1: the three integration files byte-identical to `4b1aa71` |
| **B12** transcripts remain pinned | Yes | §7 |

---

## 5. Deliberate behaviour changes

### 5.1 The plan's D-items

| # | Landed | Milestone |
|---|---|---|
| D1 · D2 · D3 · D4 | Yes | M1 |
| D5 · D6 · D7 · D8 · D9 | Yes | M2 |
| D10 | Yes, with **PD-D** (the named escape hatch did not exist) | M3 |
| D11 · D12 | Yes | M4 |
| D13 · D14 | Yes, D13 with a declared B2 deviation (**PD-F**) | M5 |
| D15 · D16 | Yes | M8 / M7 |

**All sixteen landed. None was dropped.** M5 and M8 were both severable by the
plan and neither was severed.

### 5.2 Three product changes made outside the D-items

All three are recorded here and in ADR-008 §5 rather than folded into a D-item
that does not fit them. None adds a writer, a command, a state field or a gate.

| Change | Found by | Authority |
|---|---|---|
| `cmd_gate_omit` records `governance_sha256` | M6 hardening (N13) | Plan M6 scope: "if a hardening test finds a defect, fix it inside M6 and record it" |
| `baseline_commit` in baseline refusal `data` | M6 hardening (N11) | Same |
| `hooks.py::fenced_target`; `write_fence` uses it | M7 documentation | **User approval** — see §5.3 |

### 5.3 The write-fence correction — a user-approved change made outside the plan

**This is not a D-item, not an X row, and not an X-GEN re-valuation.** It is a
product change to a shipped guardrail, made outside the plan, approved by the
user after being escalated as a blocker. It is recorded as exactly that.

**The defect.** `in_dir(path, name)` matched `/{name}/` **anywhere** in a path.
`SDLE_OWNED_PREFIXES` — the ownership the fence exists to protect — is entirely
repository-root-relative. The hook was therefore **strictly broader than the
ownership behind it**: it denied `docs/workitems/`, a documentation path the
engine does not own, never writes, and has **no choke-point refusal for**.

**Why that is a defect and not a conservative default.** CLAUDE.md's own
position is that where a hook and the script overlap, *the script's refusal at
the choke point is the guarantee* and the hook is a tripwire. A tripwire that
fires where the engine would not refuse is the one failure mode a tripwire must
not have: it teaches the reader that the fence is noise, and a fence people
learn to route around has stopped being a fence.

**The fix.** `fenced_target(path, name)` anchors the match at the start of the
repository-relative path, mirroring `SDLE_OWNED_PREFIXES`, and `write_fence`
calls it. Two shapes count as repository-relative and both anchor: a path under
`PROJECT_DIR` (which `relative` strips), and a path that is not absolute at all
(relative to the project directory by definition — this is how the fence has
always read `.workflow/state.json`). Only an **absolute path outside the
repository** falls through to `in_dir`'s loose match, as defence in depth.
Absoluteness is tested *after* backslash normalisation, so `C:/other/...`
counts as absolute; `posixpath.isabs` would call it relative and wrongly anchor
another tree's path against this root.

**Replacement safety property (§28).** Inside the repository the fence becomes
*exactly* `SDLE_OWNED_PREFIXES` — no broader, no narrower. Outside it, the loose
match is kept. What is lost is only the accidental coverage of unrelated
directories that merely share a name, which was never a guarantee. `FENCED` is
unchanged, so P6 holds: `.workflow/` is still fenced.

**`in_dir` was kept, character for character.** It is the out-of-repository
fallback, and the `SCANNED` / `untrusted_read` call site **still uses it,
unchanged** — there a deliberately broad warn-and-acknowledge scan is the
intent, not an ownership claim.

**Does it supersede T10's NB-6? No.** NB-6 (= TR6) is about the prompt layer
stating the fence's *effect* without ADR-007 §3's caveat that a registered hook
firing at all is Claude Code's guarantee, not SDLE's; that was fixed separately
in M7. **NB-6 concerns whether the fence runs; this concerns which paths it
denies when it does.** ADR-008 §5.3 says so explicitly so a later reader does
not collapse them. `SKILL.md`'s write-fence sentence was re-checked against the
corrected behaviour and needed no edit.

**Evidence — 21 new cases in `tests/test_hooks.py`**, driving the registered
command as a subprocess: 6 owned paths asserted denied in **both** the
repo-relative and absolute forms (the first cut anchored only the absolute form
and left the repo-relative form still denied — this is the pin for that);
9 unowned paths asserted permitted in both forms, including
`workitems-archive/` (a name that merely *begins* with a fenced name);
4 foreign absolute paths still denied; `FENCED` read out of the source by AST
and every name asserted anchored; and `FENCED ⊆ SDLE_OWNED_PREFIXES` asserted
against the engine constant, with strictness asserted and the reason recorded.
6 + 9 + 4 + 1 + 1 = **21**, exactly the collection delta 1710 → 1731.

---

## 6. Test changes and TP-003 classification

**Three categories. There is no fourth.** `ENVIRONMENT_FLAKE` is **VOID** for
this phase and was never invoked; no failure was re-run in the hope of a
different answer.

**No test was deleted in any milestone.** One was *retired and replaced*
(`test_n31_no_t11_leakage` → `test_t11_the_legacy_rung_is_gone`), which the
plan's X3 explicitly directs, and the replacement asserts the removal
positively where the original asserted the pre-removal state. Every other change
is an inversion, a strengthening, or an X-GEN re-valuation of a mechanically
forced closed set.

| # | Test(s) | Cat. | Action and rationale |
|---|---|---|---|
| **X1** | `test_rung3_legacy_state_stays_readable_when_no_workitem_exists`; `test_the_legacy_dual_read_rung_still_binds` | 2 | **Inverted, not deleted** — each now asserts the ladder returns `none` and the refusal names the migration path. Strictly more assertion than before |
| **X2** | `test_e1_is_skipped_under_the_legacy_binding_and_only_there`; `test_e2_stands_aside_under_the_legacy_binding_and_only_there`; `test_n18_the_legacy_runtime_can_never_omit_a_gate`; `test_n7_…`; `test_n9_…` and the `plant_legacy_workflow` dependents | 2 | Rewritten as "the precondition now applies unconditionally". The "and only there" half became "always" |
| **X3** | `test_n22_the_legacy_rung_and_migrate_workflow_are_untouched`; `test_n31_…`; `test_n31_no_t11_leakage` | 2 | Split: the **`migrate-workflow` leaves `.workflow/` byte-identical** half kept verbatim (B9); the legacy-rung half replaced by its inverse. `test_n31_no_t11_leakage` retired → `test_t11_the_legacy_rung_is_gone` |
| **X4** | `test_the_two_guard_surfaces_are_unchanged` | 2 (X-GEN) | Tuple gains `".sdle/"`; the `cmd_manifest_build` AST assertions invert to require the exclusion. Exhaustive set kept exhaustive |
| **X5** | `ACTIVE_CONTEXT_SETTERS` pin | 1 | Kept; **plus** a new assertion that a non-member `set_by` raises |
| **X6** | The `templates/state.json` entry in both `FROZEN` tuples | 2 | That **one entry** pulled out and replaced by `test_t11_the_state_template_changed_only_as_declared`. The other entries keep their baselines untouched |
| **X7** | `test_n26_every_baseline_check_is_still_present_and_passing` | 2 (X-GEN) | `T11_CHECKS = ("documentation_set_is_present",)`; 42 → 43. Equality stays **exact** |
| **X8** | Newest-mtime selection tests | 3 | Defect (TR10) fixed by D10. Two candidates now refuse. Single- and zero-candidate cases keep their assertions verbatim |
| **X9** | `test_n28_the_hooks_are_byte_identical` | 2 | `_hooks_top_level` extended to capture `ast.Import`/`ImportFrom` and the module docstring (T10 NB-1's own written remedy); hooks pin re-baselined to `4b1aa71`; every existing definition-name / guard-registry assertion kept. **Net coverage strictly increases** |
| **X10** | Both dry-run transcript pins | 2 | Converted to declared-substitution comparisons. See §7 |
| **X11** | Every `1.16` / 16-row pin | 2 (X-GEN) | Re-valued to `1.17` / 17. Files: `test_units_flow_model.py` ×2, `test_units_capabilities.py`, `test_units_state.py`, `test_units_repo_config.py`, `test_lint_skill.py`, `test_units_gate_policy.py` |
| **X12** | The rung-enum assertion | 1 | **Tightened** — `"legacy"` dropped from the permitted set |
| **PD-A** | `test_n27_the_four_existing_hook_guards_and_their_tests_are_unmodified` | 2 | A *second* `hooks.py` byte pin the plan's X9 did not name. `write_fence` declared as the one T11-edited definition and pinned by a property **not weaker** than the bytes: every non-blank baseline line must still be present and the definition must have grown, so only a pure insertion passes |
| **PD-B** | `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` → `…_is_treated_as_sdle_owned_from_t11` | 2 | Forced by D5. In a file §7.2 lists as "Not affected" — raised as a deviation (§10). The half that could genuinely regress (an uncommitted **source** change must still fail closed) is kept in the same test |
| **PD-C** | `test_the_repository_configuration_members_have_a_closed_reference_set` | 2 (X-GEN) | D6 makes `cmd_manifest_build` name `config_root_relative`; the closed set grows by one |
| **PD-1** | `test_governance_refuses_under_the_legacy_binding`; `test_bind_workitem_writes_nothing_and_prints_nothing`; `test_migrating_a_state_at_the_legacy_location_leaves_workitem_null` | 2 | In X2's *class* but not named in the table. Each rewritten so **net coverage increases** — e.g. the third's rule (1.13→1.14 leaves `workitem` null off-WorkItem) is now asserted against `migrate_state` directly **and** end-to-end through `migrate-workflow` |
| **M4 ×2** | `test_only_evaluate_risk_produces_a_final_level`; `test_n24_a18_the_engine_gained_no_writer_and_no_state_field` | 2 (X-GEN) | Reader set gains `governance_downgrade` (**producer** set unchanged at `{evaluate_risk}`, and the test now additionally asserts `governance_downgrade` is *not* a producer). Write primitives moved to `before + T11_WRITE_DELTA`, a declared **signed delta map** — stronger than re-baselining, because the permitted movement is named and quantified and any other movement in any primitive still fails |
| **M6 ×3** | `test_n9_…pending` keys; `T11_WRITE_DELTA`; `test_n28_…version_chain` | 2 (X-GEN) | M5 fallout: `pending_branch_ack` (D13); `{"append_audit": 2, "save_state": 1}`; 16 → 17 |
| **M5** | N22/N23 as first written | 3 (defect **in the new test**, not the product) | Six failed. `skip` has no `--reason` flag so 11 invocations were argparse usage errors that never reached the branch guard; `execution.json["branch"]` is really `["git"]["branch"]`; `BRANCH_TWO_STEP` was declared and unused — it became the parametrisation of a **new** test covering all four commands N22 names, where only `skip` had been covered |
| **M4** | de-duplication count test | 3 (defect in the new test) | Counted the event *name*, which `gate_omitted` deliberately mentions; now counts the de-duplication **marker** |
| **New** | `tests/test_units_hardening.py` (38), `test_hooks.py` (+21), N17–N25, N12 ×8, TR19/TR20/TR23 pins | — | Additive |

**Files §7.2 declared "Not affected" that nevertheless changed:**
`test_units_repo_config.py` (PD-B, forced by D5), `test_units_state.py` (X11),
`test_lint_skill.py` (X11 and D16's `documented_repo` fixture), `test_hooks.py`
(the fence correction), `test_units_transitions.py` (N22/N23),
`test_units_infra.py` (**unchanged**), `test_units_discovery.py`
(**unchanged**), `test_units_workitem.py` (**unchanged**),
`test_units_baseline.py` (**unchanged**), `test_units_cli.py` (**unchanged**).
The three integration files are **byte-identical** (A1). Each departure is
listed above with its authorising item.

**`tests/conftest.py`** changed only within §7.1's clause: `Project.runtime`'s
`workitem is None → .workflow` branch dropped once no fixture used it; fixtures
added for N1/N7/N14/N15; `DRY_RUN_SUBSTITUTIONS` and
`apply_dry_run_substitutions` added. **No existing fixture changed what it
produces for an existing test.**

---

## 7. The transcript-pin conversion, justified property by property (A20, B12, F7)

The plan (§7.3) authorises converting both byte-identity pins into
declared-substitution comparisons. That conversion is only legitimate if it
still catches everything the byte pin caught. Asserting "it is stronger" is not
enough, so each property is taken in turn.

The old pin: `at_baseline(f) == here(f)` for every file in `docs/dry-runs/`.
The new pin: `apply_dry_run_substitutions(at_baseline(f)) == here(f)`.

| # | Property the byte pin had | Still caught? | Why |
|---|---|---|---|
| 1 | **Any change to a transcript fails** | **Yes, in full** | `apply_dry_run_substitutions(at_baseline(f))` is a *fixed, deterministic string*. The comparison to `here(f)` is still exact equality against one target. There is **no relaxation on the current-file side at all** — only the target string moved once, by a declared amount |
| 2 | A transcript deleted or renamed fails | Yes | `assert len(numbered) == 9` is kept, and the whole `*.md` glob is compared |
| 3 | A transcript **added** fails | Yes | Every file in the directory is compared and `at_baseline(relative)` must be non-`None`; a new file has no baseline |
| 4 | The README cannot drift | Yes | The loop iterates every `*.md`, not just the nine |
| 5 | Non-vacuity if `git show` fails | Yes | `test_the_baseline_is_reachable` names `docs/dry-runs/01-happy-path.md` explicitly, so `None == None` cannot pass silently |
| 6 | A wildcard cannot absorb a real edit (F7) | Yes | `DRY_RUN_SUBSTITUTIONS` is **17 pairs of exact literals** in `conftest.py`. There is no regex, no pattern, no computed rewrite |
| 7 | — (**new**) A pair cannot decay into a no-op | New property | `assert used == {old for old, _ in DRY_RUN_SUBSTITUTIONS}` — every declared pair must match at least once, so a stale pair fails loudly instead of quietly widening the permitted set |
| 8 | — (**new**) The two pins cannot drift apart | New property | Both consume the **same** list from `conftest.py`, and each must independently produce the *identical* current bytes from a **different** baseline commit (`adbdc5e` and `e1cf341`). That joint constraint is stronger than either pin alone |

**The one thing that changed, stated plainly:** a single, enumerated, one-time
relaxation of *which* string the transcripts are compared against. That is the
whole of the cost, and it is exactly what §7.3 authorises.

**Proven, not argued (A20).** `docs/dry-runs/01-happy-path.md` was appended with
a line **not** in the substitution set; both pins **failed**; the file was
restored from a byte-for-byte copy and the SHA-256 verified identical to the
original (`e7a918ca…474c` before and after; mutated `69d2d2f4…a71b`).

---

## 8. Commands actually run — in this context, no figure inherited

**The Bash tool caps a foreground command at 600 s and this suite takes ~26
minutes, so a single foreground full-suite run is impossible in this
environment.** Backgrounded runs have truncated repeatedly (four consecutive
failures were reported by the orchestrating context, at 16 %, 83 %, 29 % and
16 %, each signalling completion while output stopped short). The suite was
therefore run in **six foreground segments**, and the segments were then
**proved exhaustive** against the collection rather than assumed to be.

| Command | Result | Evidence / summary |
|---|---|---|
| `rtk proxy "python -m pytest --collect-only -q"` | **1731 collected in 0.49s** | Baseline for the exhaustiveness proof |
| `rtk proxy "python -m pytest <3 integration files> -q --junitxml=seg1.xml"` | **88 passed in 208.50s** | |
| `… test_units_workitem, _resolution, _runtime, _state, _transitions, _cli, _infra … seg2.xml` | **320 passed in 350.43s** | |
| `… test_units_speckit_binding, _repo_config, _discovery, _baseline, test_lint_skill … seg3.xml` | **304 passed in 286.75s** | |
| `… test_units_governance, _artifact_review … seg4.xml` | **235 passed in 173.35s** | |
| `… test_units_gate_policy, _flow_model … seg5.xml` | **470 passed in 285.46s** | |
| `… test_hooks, test_units_capabilities, test_units_hardening … seg6.xml` | **314 passed in 283.77s** | |
| **Aggregate, parsed from the six junit XMLs** | **`tests=1731 failures=0 errors=0 skipped=0`** | **1731 passed, zero failures** |
| Exhaustiveness cross-check | **1731 unique testcase ids; collected set == run set** | Compared element-wise. Six entries differ only in pytest's `::` vs `.` class separator in the junit `classname` (`test_units_infra.py::TestLauncherResolution`) — the same six tests |
| `python scripts/sdle.py lint-skill > file 2>/dev/null; echo $?` | **exit 0** | Raw exit, **no pipe** |
| The same output parsed | **43 checks, `failed: []`** | `data.checks` = 43, `data.failed` = `[]` |
| `python tools/transition/validate.py; echo $?` | **exit 0** | `TRANSITION_VALID: complete=11/12 next=T11` |
| `python scripts/sdle.py constants` | `phase_sequence` **21**, `flows` **5**, `gate_phases` **8**, `version_chain` **17** | A11, A15 |
| `grep -n 'CURRENT_VERSION =' scripts/sdle.py` | `CURRENT_VERSION = "1.17"` | A11 |
| `git diff --stat 4b1aa71 -- <3 integration files> .claude/settings.json .gitignore` | **empty** | A1 |
| `grep '"legacy"' scripts/sdle.py` | **no match (exit 1)** | A2 |
| `PROJECT_ROOT_MARKERS` / `FENCED` / `.gitignore` read | `(".workflow", "state.json")` present; `FENCED = (".workflow", "workitems", "requirements", "guidance")`; `.workflow/` line 1 of `.gitignore` | A7 |
| A20 mutation probe (§7) | **both pins failed, then restored byte-identical** | SHA-256 recorded |
| `git status --porcelain -- docs/transition/ tools/transition/ .claude/agents/` | Only `RESUME.md`, `progress.md`, four **product** agents, and new `T11-*` files | A21 |
| **Python 3.11** | **NOT_RUN** | No 3.11 interpreter on this host. Observed interpreter: **CPython 3.13.0**, win32 |
| **CI (`ubuntu-latest` / `windows-latest`)** | **UNKNOWN** | CI has **never executed** at any point in this migration |
| **A single-process full-suite run** | **NOT_RUN in this context** | See §12.1 |

**Limitation of the segmented evidence, stated rather than glossed:** six
segments are not identical to one process. Cross-file ordering effects that only
a single process would surface are not covered. The partial mitigation is an
**inherited, not re-observed** figure: a single full-process run was recorded at
the blocked state in `T11-blocker.md` §5 and `T11-checkpoint-a01-07.md` §8 —
`tests=1710 failures=2 errors=10 skipped=0` from that run's junit XML, all
twelve non-passing outcomes traced to the one missing directory — and
1710 + 21 new fence cases = **1731**, which is the number observed here. The
arithmetic corroborates; it does not substitute. **The verifier should attempt a
single full-process run and should treat that as the outstanding evidence gap.**

---

## 9. Acceptance criteria

| # | Status | Evidence |
|---|---|---|
| **A1** | **MET** | `git diff --stat 4b1aa71 -- …` empty for all five paths |
| **A2** | **MET** | No `"legacy"` rung literal in `sdle.py`; `bind_workitem`'s only non-raising return is a bound `Paths` |
| **A3** | **MET** | AST test `test_n25_no_unbound_runtime_carve_out_survives_in_the_engine`: exactly two `X.workitem is None` sites remain — `Paths.workitem_root` and `collect_validation_findings` |
| **A4** | **MET** | `test_t11_n7_a_legacy_only_repository_recovers_in_exactly_two_commands`, driven through `run_cli` |
| **A5** | **MET** | `test_t11_n8_zero_workitems_with_legacy_state_names_both_steps_in_order` |
| **A6** | **MET** | `test_t11_n7_an_interruption_at_any_write_point_is_recoverable` over **nine** write points, plus `test_t11_n7_the_migration_write_sequence_is_exactly_this` so a new write point fails loudly |
| **A7** | **MET** | Read directly, this context |
| **A8** | **MET** | All 16 exist as named functions and pass. N12 lives in `test_units_governance.py`; the other 15 in `test_units_hardening.py` |
| **A9** | **MET, with one declared exception** | D3, D10 and D11's refusals leave the ledger byte-identical. **D13 does not** — §10 PD-F |
| **A10** | **MET** | `lint-skill` **43** checks, `failed: []`, exit 0; `test_n26`'s exact-set equality holds at `BASELINE_CHECKS + T10_CHECKS + T11_CHECKS` |
| **A11** | **MET** | `all 7 locations report v1.17` (seven, not the plan's five — `sdle.py::CURRENT_VERSION` was added to the checker per F6, and the Reference Guide header is the seventh); `version_chain` = **17** |
| **A12** | **MET** | All nine targets exist and are non-empty. The six new directories are named in §3 M7 |
| **A13** | **MET** | `test_n9_no_built_in_floor_was_lowered_or_removed`; `test_n9_the_first_six_floor_rules_keep_their_positions` |
| **A14** | **MET** | §4.1, row by row |
| **A15** | **MET** | 21 registry phases, 5 flows, 8 gate phases; `test_n21_greenfield_is_frozen_and_every_flow_is_element_wise_identical` |
| **A16** | **MET** | Every new refusal exits 1, every new usage error 2, every new integrity failure 3 — asserted per test |
| **A17** | **MET** | `no_powershell_only_cmdlets` passes; `test_t11_n16_both_launchers_agree_on_the_interpreter_contract` |
| **A18** | **MET** | `product_agents_are_read_only`, `product_agents_declare_the_fence`, `product_agents_declare_the_non_approval_clause` all pass inside the 43 |
| **A19** | **MET** | ADR-008 §7 carries **all 26** TR rows; totals **20 FIXED / 4 DEFERRED / 2 NOT-A-DEFECT** |
| **A20** | **MET, proven by mutation** | §7 |
| **A21** | **MET** | Only `progress.md`, `RESUME.md` and new `T11-*` artifacts. The four modified `.claude/agents/sdle-*` are **product** agents (TR4), authorised by plan §6.1 |
| **A22** | **MET, with the limitation in §8 stated** | `1731 collected` == `1731 run` == `1731 passed`; `failures=0 errors=0 skipped=0` from six junit XMLs |

---

## 10. Plan deviations — every one declared, none absorbed

| # | Deviation | Disposition |
|---|---|---|
| **PD-1** | Three tests in X2's *class* but not named in the X-table | Recorded individually; each rewritten so net coverage increases. §7.1's remedy is "raise as a plan deviation in the handoff", not "stop" |
| **PD-2** | — | No file on §7.2's "Not affected" list changed **in M1** |
| **PD-3** | Process: a full suite was not run at every milestone boundary | Declared. M1 — the only milestone with a red window — got its own full run (**1621 passed, raw exit 0**, recorded in `T11-checkpoint-a01-01.md`; **inherited, not observed in this context**). Later milestones were grouped; every milestone got targeted runs, `lint-skill`, and the A-criteria it could affect; the phase ends on a full green collection observed here |
| **PD-A** | A **second** `hooks.py` byte-identity pin exists that X9 did not name | `write_fence` declared as the one T11-edited definition, pinned by a property not weaker than the bytes (every non-blank baseline line present, definition grew) |
| **PD-B** | Plan **E15 is wrong** — three tests pin `.sdle/` as absent, not two, and the third is in a file §7.2 calls "Not affected" | Weighed against writing a blocker and **rejected**: the change is forced by D5, an authorised delta whose disposition the plan already fixed; the defect is *observational*, not a material architecture/contract/baseline decision. §28 argument recorded in §3 M2 |
| **PD-C** | The closed configuration-reference set grows by one | X-GEN |
| **PD-D** | **D10 names an escape hatch that does not exist.** `feature bind` takes one flag (`--require-feature`), emits the already-recorded environment, and cannot name a feature id | Rejected adding `--feature-id` (a new override flag is precisely what §9 warns against — it makes "SDLE will not guess" negotiable). Instead the refusal names the remedy that already works: tier 1 (`workitems/<id>/specs/`) takes precedence, so moving the directory this WorkItem owns resolves the ambiguity **by precedence**, with SDLE still choosing nothing. `test_n21_the_named_remedy_is_a_real_one` **performs** the remedy end to end rather than describing it — because a fail-closed refusal is only honest if the way out actually works |
| **PD-E** | An M1 residual closed in M3: `cmd_feature_resolve` carried a `legacy = specs_root is None` branch not in D4's list, because E11/E12 enumerated *textual* `paths.workitem is None` sites | Removed with its `.specify/specs`-only tier list; `Paths.speckit_specs_root`'s docstring corrected (`None` means *unbound*, not *legacy-bound*) |
| **PD-F** | **D13 deviates from B2**: the stale-acknowledgement path appends `branch_ack_stale`, re-arms `pending_branch_ack`, saves state, **then** refuses | Declared, not discovered. It is `branch_guard`'s **pre-existing** shape (it already appended `branch_mismatch_guard` before refusing, pinned by a baseline test); the branch guard is the engine's one *auditing* guard, per §9; T03-1's defect was an **unaudited** action, so a silent refusal would reproduce it; and without the state write the user is dead-ended forever on the current branch. B2's guarantee reads precisely: **a refusal writes nothing except where the refusal itself is the auditable event**, and this is the only such place. ADR-008 §5.2 |
| **Out of plan** | The write-fence correction | §5.3. **User-approved**, escalated first via `T11-blocker.md` |
| **Plan figures** | E20 (18 → **17** lines / 20 occurrences); §9 totals (**20/4/2**); §10 interpreter (3.14 → **3.13.0**) | §1.3 |

---

## 11. Inherited findings — all 26 dispositioned

**Recorded in `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`
§7**, which A19 makes the authority. Totals re-derived in this context by
counting the ADR's table, not by copying prose: **20 FIXED · 4 DEFERRED ·
2 NOT-A-DEFECT · 26 rows.**

- **FIXED (20):** TR1, TR2, TR3, TR4 (partially, with the reason recorded),
  TR6 (minimally), TR7 (as evidence, not refusal), TR9, TR10, TR11, TR12, TR13,
  TR14, TR15, TR16, TR17, TR18, TR21, TR22, TR24, TR26.
- **DEFERRED (4):** **TR8** — the single named V1 gap; **TR20**, **TR23**,
  **TR25** — each with a reason and, for TR20 and TR23, a **pinning test** so
  the residual is visible rather than silent.
- **NOT-A-DEFECT (2):** TR5, TR19 — TR19's ordering now pinned by a new
  assertion in N3, so it stops being untested.

**TR7 / T09 NB-2 stays FIXED as evidence, not as refusal**, as instructed. The
floor was never lowered; the *inputs* changed. Refusing a downgrade would block
a legitimate re-scope — a false floor — and would push a correct user toward
hand-editing the record. D11 closes the asymmetry by making the downgrade
auditable in three places at once.

**TR8 / T09 NB-3 stays DEFERRED as the single named V1 gap.** §15's HIGH list
names a documentation review no gate implements; seven of its eight items map
onto existing gates. Adding a ninth gate is a **lifecycle** change owned by
T07/T09, not a §17 removal-and-hardening change: it would move all four phase
tables, `phase-execution.md`, every `PROGRESS_MAP` denominator, the state
template's `approvals`, integration 01's `EXPECTED_TRAVERSAL` and `GATES`, and
all nine transcripts — i.e. change what a GREENFIELD run looks like, at the last
milestone of the last phase, for something §17 does not ask for and §26 does not
list. §15 itself calls the list a *default intent*. **ADR-008 §8 gives it a
two-step proposed shape so the deferral is actionable rather than decorative.**

### 11.1 Four declared scenario divergences (ADR-008 §5.1)

Each is a §17 hardening bullet that could not be implemented exactly as worded.
**None is silently narrowed**; each is stated in its own test docstring and in
ADR-008, with the property that *is* asserted instead.

1. **"Corrupt audit refuses at the choke point."** SDLE's integrity choke point
   is `audit verify` (and `migrate-workflow`). Lifecycle commands do not
   re-verify the whole ledger per invocation, by design. Asserted instead: the
   tamper stays visible, is **located** (`broken_at_entry == 2`), and cannot be
   laundered by continuing to use the tool.
2. **"A partial temp does not survive the next successful write."** It does
   survive — each `write_atomic` renames its own uniquely named temp, and a
   sweep would let one writer delete a concurrent writer's in-flight temp.
   Asserted instead: such a temp is **inert**.
3. **"A stale baseline blocks an ITERATIVE WorkItem."** It does not,
   deliberately — treating change as invalidation would force the third
   WorkItem in any repository back into full rediscovery, which §26 item 22
   forbids. Asserted instead as the two true statements it decomposes into: a
   **materially invalid** baseline blocks ITERATIVE outright, and a **stale**
   one can never be relied on silently.
4. **"Neither ledger contains the other's execution id."** Execution ids are
   **not globally unique by contract** — §"Execution identity" specifies
   `<3-letter-prefix>-<UTC-datetime>` at second resolution and calls it
   *lightweight*. The engine was **not** changed. Asserted instead, and more
   strongly: each execution *record* is a separate file naming its own WorkItem
   and worktree, and the ledger half is asserted against the WorkItem id, which
   **is** unique. Worth recording as a process point: the original assertion
   held only when two `init` calls straddled a second boundary — **a hardening
   test whose outcome turns on the clock is worse than no hardening test**,
   because it launders a false property as a proven one.

---

## 12. Known limitations and risks

### 12.1 What was not run

| Item | Status | Why |
|---|---|---|
| Python 3.11 | **NOT_RUN** | No 3.11 interpreter on this host. T11 introduces no new syntax level and no dependency, but no outcome is predicted |
| CI on `ubuntu-latest` / `windows-latest` | **UNKNOWN** | CI has never executed at any point in this migration |
| A run on Linux | **NOT_RUN** | §17 mandates a Windows/Linux hardening test; only the Windows half is observable here. `test_t11_n16_what_this_host_could_not_observe_is_not_asserted` exists precisely so the gap is recorded in the suite rather than implied to be covered |
| A **single-process** full-suite run in this context | **NOT_RUN** | The tool caps a foreground command at 600 s; the suite takes ~26 min; backgrounded runs truncate. Six foreground segments, proved exhaustive, were used instead. §8 |

**The honest V1 cross-platform statement**, which ADR-008 §6 carries and which
must not be softened: *the engine is written to be cross-platform and is
mechanically checked for platform-only constructs; during this migration it has
been executed only on Windows, on Python 3.13.*

### 12.2 Residual risks

1. **M5–M8 are uncommitted.** A working-tree loss would destroy the hardening
   file, the documentation set, ADR-008 and the fence correction. This is the
   phase's single largest operational risk.
2. **The fence narrowed.** It is now exactly `SDLE_OWNED_PREFIXES` inside the
   repository. Accidental coverage of same-named directories elsewhere is gone
   — deliberately, with 21 tests pinning both halves. A verifier should satisfy
   itself that nothing the engine owns became writable.
3. **Four DEFERRED findings.** TR8 is the only one that is a genuine capability
   gap; TR20, TR23 and TR25 are bounded residuals, and TR20/TR23 have tests.
4. **B2 has one named exception** (PD-F). If a later change adds a second
   auditing guard, the narrower guarantee must be re-stated, not silently
   widened.
5. **Segmented suite evidence** (§8).

### 12.3 Corrections earlier contexts made, kept here on purpose

These are the phase's own evidence discipline working, and they belong in the
record:

- **20 FIXED, not 19.** TR20 resolved to DEFERRED in M5, making four deferrals.
  Count the ADR's table, not any prose summary.
- **17 stale transcript lines / 20 occurrences**, not the plan's E20 figure of
  18 — three lines carry two occurrences each.
- **§17's mandatory hardening list has 16 bullets, not 17** (E31, re-verified
  by parsing).
- **ADR-008 once claimed TR26 FIXED while `RESUME.md` was still stale** — a
  record written ahead of the fact, caught by a later context and repaired.
  `RESUME.md` now genuinely describes the completed state, and it carries the
  lesson: *a document can be a claim ahead of the fact.*
- **The orchestrating context's brief said "nothing about T11 is committed" and
  named HEAD `97100e2`.** Both are wrong: HEAD is `42c7d5b` and M1–M4 are
  committed. Recorded because the difference decides what a rollback discards.

---

## 13. Claims for the verifier to check independently

Treat everything above as claims. The highest-value independent checks:

1. **Attempt a single-process full-suite run.** Confirm the figure by locating
   the `N passed` summary line and by parsing `--junitxml`, not by trusting a
   completion signal. Expect **1731**.
2. **Re-derive ADR-008's ledger** by counting its table: 26 rows, 20/4/2.
   A19 fails if a single TR is missing or carries two dispositions.
3. **Re-run the A20 mutation probe** on a *different* transcript, to confirm the
   pins are non-vacuous in a case this context did not use.
4. **Check the fence in both path forms.** The bug was subtle: an early cut of
   the fix anchored only the absolute form and left the repo-relative form of
   `docs/workitems/README.md` still denied. Verify `docs/workitems/README.md`
   is permitted *and* `workitems/index.md` is denied, both as a bare relative
   path and as an absolute one.
5. **Confirm `in_dir` still guards `SCANNED`.** The untrusted-read scan must
   still be loose; only `write_fence` was anchored.
6. **Verify A3 by AST**, not grep — the plan says so, and a plain `grep` has
   already produced one false negative in this migration.
7. **Confirm no test was weakened.** Every entry in §6 either inverts a
   superseded assertion, strengthens coverage, or re-values a mechanically
   forced closed set. No assertion was relaxed to an `in` / `>=` shape.
8. **Confirm P1.** `PROJECT_ROOT_MARKERS` must still contain
   `(".workflow", "state.json")`. Removing it is the bricking §17's own gate
   forbids, and it is the single most dangerous "cleanup" a later reader could
   make.
9. **Check §26's 41 definition-of-done items** against the shipped engine.
   Item 37 ("test suite is green on supported platforms") is the one this
   handoff cannot fully evidence — see §12.1.
10. **Confirm no future-phase leakage.** There is no future phase; the risk here
    is the inverse — the §1.4 control-plane cleanup leaking *into* T11. It did
    not: `tools/transition/`, `docs/transition/` and
    `.claude/agents/sdle-transition-*` are all intact.

---

## 14. Git evidence

- **HEAD:** `42c7d5b` — "T11 M4: governance downgrade evidence (D11, D12, N12)"
- **Branch:** `transition/workitem-v1`
- **Working tree:** M5–M8 uncommitted. 38 tracked files modified; 12 untracked
  paths (`tests/test_units_hardening.py`, ADR-008, six documentation
  directories, `T11-blocker.md`, `T11-checkpoint-a01-05/-06/-07`, and this
  attempt's `-08` and handoff).
- **Diff scope, whole phase (`97100e2` → working tree):** 46 tracked files
  changed, **3662 insertions, 454 deletions**, plus the untracked additions.
  - `scripts/sdle.py`: +546 / −166 (10 799 → 11 179 lines)
  - `tests/`: 14 files, +2158 / −176, plus `test_units_hardening.py` (1180 new)
  - `.claude/`: 14 files, +123 / −31
  - `docs/`, `README.md`, `CLAUDE.md`: 17 files, +835 / −81, plus 7 new documents
- **Out of scope and untouched:** `.claude/settings.local.json` (dirty
  throughout, deliberately not read or edited).
- **Must-not-change list:** the three integration files, `.claude/settings.json`
  and `.gitignore` are **byte-identical to `4b1aa71`**;
  `docs/transition/transition.md` and every `T00…T10-*.md` artifact are
  untouched.

---

## 15. Blocker

**None outstanding.** `T11-blocker.md` records a blocker that was raised at M7,
escalated as a permission-and-safety-control decision, **decided by the user**
(Option A), and resolved. The file is retained unmodified as evidence that a
guardrail defect was found and escalated rather than routed around.

**No material decision remains open.** Every candidate was examined and resolved
inside the contract: the ninth documentation-review gate is deferred **on the
record** (TR8); a HIGH→LOW re-assessment is audited rather than refused, because
refusing would be a false floor (TR7); and the §20 migration path was **not**
reduced, because §20 permits reducing it only by explicit human decision.

---

## 16. Status

**IMPLEMENTED.** Ready for independent verification by a fresh
`sdle-transition-verifier`.

T11 is the last phase. After a `PASS`, the only remaining work is the
post-transition control-plane cleanup that §1.4 permits — **in a separate
change, after T11 has independently passed, never while the transition is
executing.**
