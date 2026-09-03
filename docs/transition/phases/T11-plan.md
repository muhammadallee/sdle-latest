# T11 Plan — Production Hardening, Cleanup and V1 Convergence

**Phase:** T11 (final phase of the migration)
**Planner context:** fresh/isolated
**Contract sections:** §17 (primary), §18, §19, §20, §24.2, §26, §28
**HEAD at planning time:** `4b1aa71`
**Rollback point:** `11363d9` (T10 implementation)
**Product baseline:** `f8fdaa0`
**Status recommendation:** PLANNED

---

## 0. How to read this plan

T11 is the only destructive phase in the migration. Everything below is
organised so that the destructive part happens **first**, in one milestone, with
its correctness proven by *absence of movement everywhere else*, and so that
every later milestone is independently severable.

Three cross-cutting rules govern the whole phase:

1. **No milestone may end with an existing repository unrecoverable.** §17's
   removals are gated on "after all migration tests pass"; the recoverability
   rule is stricter and applies *within* the phase as well as at its end.
2. **Removal and preservation are in tension.** §17 orders removal of the
   repository-global `.workflow/`; §20 mandates a bounded legacy migration path
   and §17 itself mandates an *interrupted legacy migration* hardening test.
   Section 3 draws that boundary explicitly rather than leaving it implicit.
3. **No finding is dropped silently.** There is no T12. Section 9 gives every
   inherited finding exactly one disposition: FIXED, DEFERRED (with reason), or
   NOT-A-DEFECT (with reason).

---

## 1. Objective

Make the WorkItem-based model the **only** normal runtime model, remove the
transitional scaffolding that has kept the pre-v1.14 runtime alive since T02,
close or explicitly defer every finding accumulated across T02–T10, add the
hardening tests §17 names, and bring the shipped documentation into agreement
with the shipped engine — without weakening a single guardrail on the §17
Preserve list or the §18 Capability Preservation Matrix.

Exit criterion (§17): *"Latest WorkItem-based requirements are the only normal
runtime model and all V1 definition-of-done checks pass."*

---

## 2. Repository evidence

Everything in this table was inspected or executed **in this planning context**.
Nothing is carried over from a prior agent's prose.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `4b1aa71`; the only dirty path is `.claude/settings.local.json` | OBSERVED | `git log --oneline -3` and `git status --porcelain` |
| E2 | `validate.py` prints `TRANSITION_VALID: complete=11/12 next=T11`, exit 0 | OBSERVED | `rtk proxy "python tools/transition/validate.py"`; `EXIT=0` |
| E3 | `lint-skill` emits **42** checks, all `[PASS]`, `"failed": []`, and reports `Parsed 21 phases, 8 gates, 16 migration rows` | OBSERVED | `rtk proxy "python scripts/sdle.py lint-skill"`; `grep -c '^\[PASS\]'` = 42 |
| E4 | The product version string is `1.16`, sourced from `templates/state.json::workflow_version` and mirrored in four other locations by `_check_version_consistency` | OBSERVED | `cat .claude/skills/sdle/templates/state.json`; `_check_version_consistency` in `scripts/sdle.py` |
| E5 | `scripts/sdle.py` is 10799 lines | OBSERVED | `wc -l scripts/sdle.py` |
| E6 | `Paths.runtime` returns `Paths.legacy_workflow` (`<root>/.workflow`) exactly when `Paths.workitem is None`; every other runtime path derives from `runtime` | OBSERVED | `Paths` dataclass, properties `legacy_workflow` / `workitem_root` / `runtime` |
| E7 | `resolve_decision` rung 6 binds the legacy runtime when there are **zero** registered WorkItems and `.workflow/state.json` exists; its own docstring says *"TRANSITIONAL, removed at T11"* | OBSERVED | `resolve_decision` docstring and the `if not known:` branch; `bind_workitem`'s `if decision.rung == "legacy": return paths` |
| E8 | `main()` calls `bind_workitem` only when `args.command not in RUNTIME_FREE_COMMANDS`; `workitem` and `migrate-workflow` are both members | OBSERVED | `main()` dispatch; `RUNTIME_FREE_COMMANDS` frozenset |
| E9 | Therefore `workitem create` and `migrate-workflow --workitem <id>` remain invocable in a repository with zero WorkItems and a legacy `.workflow/` **after** rung 6 is removed | INFERRED | From E7 + E8: neither command reaches the ladder, so removing a rung cannot affect them |
| E10 | `PROJECT_ROOT_MARKERS` contains `(".workflow", "state.json")` — the marker that lets a legacy-only repository be *discovered* at all | OBSERVED | `PROJECT_ROOT_MARKERS` tuple |
| E11 | There are 14 textual occurrences of `workitem is None` in `sdle.py`; 12 are runtime carve-outs in named functions | OBSERVED | `grep -c 'workitem is None'` = 14; AST mapping to enclosing `def` |
| E12 | The 12 carve-out sites are `collect_validation_findings`, `gate_requirements_for_state`, `bind_for_governance`, `bind_for_discovery`, `discovery_precondition`, `baseline_precondition`, `establish_baseline`, `review_precondition`, `governance_precondition`, `flow_precondition`, `cmd_gate_omit`, `gate_precondition_hook` | OBSERVED | AST walk mapping each `workitem is None` line to its enclosing function |
| E13 | Several carve-out docstrings name T11 as owner verbatim, e.g. `review_precondition`: *"the same declared, bounded residual as E1, which T11 removes with the rung itself"* | OBSERVED | Docstrings at `review_precondition`, `governance_precondition`, `baseline_precondition` |
| E14 | `SDLE_OWNED_PREFIXES` = `(".workflow/", "workitems/", ".specify/", "design/", "reviews/", "clarifications/", "guidance/", "requirements/")` — `.sdle/` is absent | OBSERVED | `SDLE_OWNED_PREFIXES` literal |
| E15 | Two live tests **pin** `.sdle/` as absent from that tuple and absent from `cmd_manifest_build`, each naming T11 as the owner | OBSERVED | `test_units_flow_model.py::test_the_two_guard_surfaces_are_unchanged`; `test_units_gate_policy.py::test_n31_no_t11_leakage` |
| E16 | `test_n31_no_t11_leakage` asserts `"legacy_workflow" in source` and `"current_feature_id" in source` — i.e. it fails by design once T11 does its job | OBSERVED | Body of `test_n31_no_t11_leakage` |
| E17 | Two separate tests pin the nine dry-run transcripts byte-identical, against **different** commits: `test_units_capabilities.py::test_n20_...` vs `adbdc5e`, `test_units_gate_policy.py::test_n27_...` vs `e1cf341` | OBSERVED | `BASELINE = "adbdc5e"`, `ROLLBACK = "e1cf341"`, both test bodies |
| E18 | `FROZEN` (capabilities) = 3 integration files + `.claude/settings.json` + `templates/state.json` + `.gitignore`; `FROZEN_FILES` (gate_policy) = integration 01 + `templates/state.json` + `.claude/settings.json` + `.gitignore` | OBSERVED | Both tuples |
| E19 | `test_n26_every_baseline_check_is_still_present_and_passing` asserts **exact set equality** against `BASELINE_CHECKS + T10_CHECKS` (33 + 9 = 42) | OBSERVED | Body at `tests/test_units_capabilities.py` |
| E20 | `docs/dry-runs/` carries **18** stale `.workflow/` lines across 6 transcripts | OBSERVED | `rtk proxy "grep -rn '\.workflow' docs/dry-runs/"` — 18 matching lines |
| E21 | `.claude/skills/sdle/modules/phase-execution.md` (5 lines) and `modules/gate-protocol.md` (3 lines) still name `.workflow/` runtime paths | OBSERVED | `grep -rn '\.workflow' .claude/` |
| E22 | `docs/` currently contains only `architecture/`, `dry-runs/`, `transition/` plus `SDLE-Reference-Guide.md`. **Six** of §17's nine documentation targets do not exist: `docs/workitems/`, `docs/lifecycle/`, `docs/risk-and-gates/`, `docs/brownfield/`, `docs/spec-kit-integration/`, `docs/troubleshooting/` | OBSERVED | `ls docs/` |
| E23 | `docs/architecture/` holds ADR-001 … ADR-007; the next number is **ADR-008** | OBSERVED | `ls docs/architecture/` |
| E24 | `ADR-001-deterministic-core.md:50` still reads "Four hooks…"; there are five guards registered | OBSERVED | `grep` on ADR-001; `T09_GUARDS + T10_GUARD_ADDITIONS` = 5 in `test_units_gate_policy.py` |
| E25 | `cmd_feature_resolve` selects **newest mtime** inside the chosen tier and refuses `feature_ambiguous` only when the two newest share a timestamp; tier 2 is the repository-global `<root>/specs/` | OBSERVED | `cmd_feature_resolve` body and docstring |
| E26 | `ACTIVE_CONTEXT_SETTERS = ("init", "use", "migrate-workflow")` is referenced only by its own definition and one test — nothing in production reads it | OBSERVED | `grep -rn 'ACTIVE_CONTEXT_SETTERS'` returns `sdle.py:2644` and `test_units_workitem_resolution.py:1459` only |
| E27 | `hooks.py` fences `(".workflow", "workitems", "requirements", "guidance")` and carves out `SPECS_CARVE_OUT = re.compile(r"(?:^\|/)workitems/[^/]+/specs/")` against an unnormalised path | OBSERVED | `.claude/hooks/hooks.py` `FENCED`, `SPECS_CARVE_OUT` |
| E28 | `hooks.py::_project_dir` treats `.workflow/` as a project-directory marker | OBSERVED | `_project_dir` body |
| E29 | `read_index` rejects any row whose cell count differs from `INDEX_COLUMNS`, raising `index_malformed` (`IntegrityError`, exit 3), and never rewrites the file | OBSERVED | `read_index` / `_index_malformed` |
| E30 | `VERSION_MIGRATION` already contains a precedent no-op row: `1.2 → 1.3  No field change.` | OBSERVED | `SKILL.md` VERSION_MIGRATION table |
| E31 | §17's "Hardening tests / Mandatory" list has **16** bullets, not 17 | OBSERVED | Parsed the section programmatically; printed 16 numbered bullets |
| E32 | `tests/conftest.py::project` registers exactly one WorkItem, and `test_integration_01_happy_path.py` drives that fixture — so GREENFIELD never takes the legacy rung today | OBSERVED | `conftest.py` `bare_project` / `project` fixtures; `run_happy_path(project)` |
| E33 | `current_feature_id` survives **only** inside migration steps `1.0→1.1`, `1.1→1.2`, `1.14→1.15` and their tests; no runtime reader indexes it | OBSERVED | `grep -rn 'current_feature_id'`; `test_units_speckit_binding.py` F1 test asserts no direct reader |
| E34 | Full suite figures (`1616 passed`, ~26 min) were **not** re-run in this planning context | UNKNOWN (to this planner) | Deliberately not executed: the suite takes ~26 minutes and the recorded lesson is that concurrent commands distort it. The last observed figure is the T10 verifier's, recorded in `progress.md` |
| E35 | Python 3.11 behaviour and CI on `ubuntu-latest` / `windows-latest` | UNKNOWN | CI has never executed at any point in this migration; no 3.11 interpreter on this host |
| E36 | `docs/transition/RESUME.md` is stale — it says `complete=6/12 next=T06` | OBSERVED | `cat docs/transition/RESUME.md` vs E2 |

---

## 3. The removal / preservation boundary

§17 says *remove* the repository-global `.workflow/`. §20 says a bounded
migration path may exist, and §17 itself mandates an **interrupted legacy
migration** hardening test. Those are only compatible if "remove" means one
specific thing. This plan fixes that meaning:

> **`.workflow/` ceases to be a *runtime*. It remains a *migration source* and a
> *project-root marker*, and nothing more.**

Concretely:

### 3.1 REMOVED

| # | Removed | Where |
|---|---|---|
| R1 | Resolution rung 6 — the legacy dual-read binding | `resolve_decision`, `bind_workitem` |
| R2 | The possibility that any **bound** `Paths` has `workitem is None` | consequence of R1 |
| R3 | All 12 `workitem is None` runtime carve-outs (E12), which become unreachable | the 12 functions named in E12 |
| R4 | The repository-global runtime lock — there is no repository-global runtime left to lock | consequence of R1; `Paths.lock_file` is already `runtime/lock` |
| R5 | WorkItem-less workflow initialization | already refused by `for_init`; T11 **pins** it and removes the code path that made a non-`init` command tolerate no WorkItem |
| R6 | `ACTIVE_CONTEXT_SETTERS` as a dead constant | either enforced or deleted — see D9 |
| R7 | Prose asserting a legacy runtime binds | `SKILL.md`, `.claude/commands/sdle-start.md`, `CLAUDE.md`, `README.md` |

### 3.2 PRESERVED — and why removing each would be a §28 violation

| # | Preserved | Why |
|---|---|---|
| P1 | `PROJECT_ROOT_MARKERS` entry `(".workflow", "state.json")` | Without it a legacy-only repository cannot be *found*, so `migrate-workflow` could not be pointed at it. Removing it is exactly the bricking §17's gate forbids. |
| P2 | `Paths.legacy_workflow` and the `workitem=None → .workflow/` mapping | `cmd_migrate_workflow` constructs `legacy = dataclass_replace(paths, workitem=None)` as its **source view**. This is no longer a runtime binding; it is a reader. |
| P3 | `cmd_migrate_workflow` in full, including its refusals (`target_exists`, `legacy_state_missing`, `legacy_state_invalid`, broken-chain) and its "never mutate `.workflow/`" property | §20; and §17's mandatory *interrupted legacy migration* test presupposes it |
| P4 | `legacy_state_present()` | Feeds `init`'s `legacy_present` refusal and `validate`'s `runtime_state_outside_workitem` warning |
| P5 | The `validate` finding `runtime_state_outside_workitem` | It is now the *only* automated way a user learns a legacy runtime is still on disk |
| P6 | `.workflow` in `hooks.py::FENCED` and in `SDLE_OWNED_PREFIXES` | A legacy `.workflow/` on disk is still a migration source. Un-fencing it would let Claude hand-edit the exact file `migrate-workflow` validates. This is a safety control whose justification *survives* the removal. |
| P7 | `.workflow/` in `.gitignore` | It is archival, never versioned (§19 versions WorkItem records, not the legacy runtime). Leaving `.gitignore` untouched also keeps two byte-identity pins intact (E18) — a deliberate risk reduction. |
| P8 | `current_feature_id` inside migration steps `1.0→1.1`, `1.1→1.2`, `1.14→1.15` | §17 removes it *as workflow identity* (done at T04, E33). The migration rows are the "every state field has a migration row" invariant and `lint-skill` enforces them. |
| P9 | The whole §17 Preserve list and the §18 matrix | Section 5 (B-list) enumerates each with the proof T11 will carry |

### 3.3 The migration path, stated plainly

After T11, a repository still on the pre-v1.14 runtime recovers with **exactly
two commands**, both of which are `RUNTIME_FREE` and therefore never reach the
resolution ladder (E8, E9):

```text
sdle.sh workitem create --name "<name>"
sdle.sh migrate-workflow --workitem <id>
```

Every other command in such a repository refuses `workitem_required` (exit 1)
and the refusal **must name those two steps in order**. That is D3 below, and
A4 makes it an acceptance criterion proven end-to-end through the real CLI.

### 3.4 Already-satisfied §17 removals (verify, do not re-remove)

| §17 item | Disposition | Evidence |
|---|---|---|
| `current_feature_id` as workflow identity | Already removed at T04 (v1.15). Survives only in migration rows (P8) | E33 |
| Universal fixed 18-phase assumption | Already removed at T07. `PHASE_SEQUENCE` is a 21-entry **registry**; a *flow* is what a WorkItem traverses; `PROGRESS_MAP`'s `N/18` values are the derived GREENFIELD view, pinned by `progress_map_and_gate_numbers_are_the_derived_greenfield_views` | E3, lint output |
| Fixed 8-gate assumption | Already removed at T09 — gates are policy-derived and omittable with evidence. The 8-gate *registry* is GREENFIELD's gate set, and `gate_labels_are_flow_relative` passes | E3 |

T11's work on these three is to **pin them** (A15) and to make the shipped
documentation stop implying otherwise (M7), not to remove them again.

---

## 4. Milestones

Eight milestones. Each ends green: full suite green **and** `lint-skill`
`failed: []`. One `TNN-checkpoint-a01-XX.md` is written **before** the next
milestone begins.

> **Safe resume boundary: the end of any milestone.** A fresh agent resuming
> mid-phase must restart at a milestone boundary, never mid-milestone, and must
> verify claimed state against disk (`--collect-only -q` is the cheap check).

> **Last milestone after which a partial tree is still recoverable: M1.**
> M1 is the only milestone with an internal red window. Once M1 is green, every
> later milestone is additive or documentation-only, and abandoning the phase at
> any later boundary leaves a working, self-consistent engine — the only cost is
> an un-closed finding, which the checkpoint records.

### M1 — Remove the legacy runtime binding (structural, riskiest, first)

Scope: R1–R5, D1–D4, X1–X3.

**Proof shape: nothing else moves.** M1's correctness argument is that after the
removal, `tests/test_integration_01_happy_path.py`, the three integration files,
`.claude/settings.json`, `.gitignore` and all nine dry-run transcripts are still
byte-identical, GREENFIELD's traversal is unchanged, and `migrate-workflow`
still leaves `.workflow/` byte-for-byte untouched. If any of those move in M1,
the removal reached further than intended and M1 is wrong.

**Declared red window** (the only one in the phase): between deleting rung 6 and
updating the ~12 legacy-binding tests listed in X1. The implementer must close
it inside M1 and must not begin M2 while it is open.

### M2 — Guard consistency

Scope: D5 (`.sdle/` ownership), D6 (`cmd_manifest_build` exclusion), D7 (hook
carve-out path normalisation), D8 (`cmd_workitem_use` hardening + reason
collision), D9 (`ACTIVE_CONTEXT_SETTERS`), X4, X5.

### M3 — Spec Kit tier ambiguity fails closed

Scope: D10. Self-contained; touches `cmd_feature_resolve` and its tests only.

### M4 — Governance downgrade evidence

Scope: D11 (a distinct audited event when a re-assessment lowers the recorded
final level), D12 (prompt-layer sentence forbidding re-assessment as a
gate-clearing device).

### M5 — Schema, version and the branch-guard fail-open

Scope: D13 (`pending_branch_ack`), D14 (v1.16 → v1.17 with a `1.16 → 1.17` row),
X6. **The only milestone that edits `templates/state.json`**, and therefore the
only one that touches the two `FROZEN` pins (E18).

**Severability note:** if the phase must be abandoned for external reasons, M5
may be dropped as a unit provided the checkpoint records D13 as DEFERRED with
its reason. Do not drop D13 while keeping D14 — a version bump advertising a
schema change that did not happen is worse than neither.

### M6 — The 16 mandatory hardening tests

Scope: N1–N16. **New tests only.** If a hardening test finds a defect, that is a
TP-003 category 3 finding: fix the implementation inside M6 and record it.

### M7 — Documentation convergence

Scope: `README.md`, `CLAUDE.md`, `docs/architecture/` (ADR-008 + ADR-001
correction), the six new documentation directories (E22), the prompt-layer
residuals (E21), and the NB-2…NB-6 closures.

### M8 — Dry-run transcript convergence (severable, last)

Scope: D15. Deliberately last and deliberately severable — see §7.3.

---

## 5. Behavioral delta

### 5.1 Deliberate changes

| # | Change | Contract basis |
|---|---|---|
| **D1** | Delete rung 6 from `resolve_decision`. With zero registered WorkItems the ladder returns `reason="none"` whether or not `.workflow/state.json` exists. `Resolution.rung` loses the value `"legacy"`. | §17 "repository-global `.workflow/`"; §17 "transitional dual-path code" |
| **D2** | Delete the `if decision.rung == "legacy": return paths` arm of `bind_workitem`. A successful `bind_workitem` now **always** returns `Paths` with a non-`None` `workitem`. | §17 |
| **D3** | Widen the `workitem_required` refusal: when `legacy_state_present(paths)` is true, the message additionally names the two-step migration path (§3.3) in order, and `data` carries `{"legacy_state": <path>}`. The reason string stays `workitem_required` — no new reason, no CLI-contract break. Closes T02 NB-2. | §17 exit criterion; §28 "provide the replacement safety property"; §22 "structured JSON" |
| **D4** | Delete the 12 now-unreachable `workitem is None` carve-outs (E12) and their docstring paragraphs. `collect_validation_findings`' `decision.workitem is None and decision.rung is None` test is **kept** — `validate` runs the ladder speculatively and must still report an unresolved repository as a warning (P5). | §17 "transitional dual-path code" |
| **D5** | Add `".sdle/"` to `SDLE_OWNED_PREFIXES`. | §18 isolation; T08 finding |
| **D6** | Give `cmd_manifest_build` the same relocation/ownership exclusion its sibling `cmd_security_review_evidence` already has, so the Gate 7 manifest stops listing the WorkItem's Spec Kit artifacts and the repository `.sdle/` as implementation changes. Closes T04 N-7. | §18 "implementation diff baseline" PRESERVE — the manifest must describe *implementation*, not SDLE's own bookkeeping |
| **D7** | Normalise the candidate path before matching `SPECS_CARVE_OUT` in `hooks.py`, so `workitems/<id>/specs/../.sdle/state.json` no longer escapes the write fence. Closes T04 N-3. | §17 "hooks where still applicable"; invariant 6 |
| **D8** | Error-harden `cmd_workitem_use` in line with its siblings (an `OSError` becomes a refusal, not a traceback) and rename its `UsageError` reason from `workitem_required` to `workitem_flag_required`, so a usage error (exit 2) and the resolution refusal (exit 1) stop sharing one reason string. Apply the same rename to `cmd_migrate_workflow`'s missing-`--workitem` `UsageError`. Closes T03-4/5/6. | §18 "Exit codes 0/1/2/3 PRESERVE"; invariant 7 (one fact, one name) |
| **D9** | Make `ACTIVE_CONTEXT_SETTERS` load-bearing: `write_active_context` asserts its `set_by` argument is a member and raises otherwise. A dead constant becomes an enforced one rather than being deleted, because the *fact* it encodes (exactly three writers) is worth keeping. Closes T03-4. | invariant 7; §17 "obsolete skill constants" |
| **D10** | `cmd_feature_resolve` applies §9's own 0/1/>1 rule inside the chosen tier: **more than one candidate refuses `feature_ambiguous`**, listing them, instead of picking the newest mtime. The escape hatch is the existing explicit `feature bind`. Closes T04 N-2 (two WorkItems at Phase 4 can no longer cross-adopt via the repository-global tier). | §9 "Never silently pick one among multiple plausible"; §10 "WorkItem A Spec Kit output cannot be mistaken for WorkItem B" |
| **D11** | When `governance assess` records a final level **below** a level already recorded for the same WorkItem, emit a distinct, additional audit event (`governance_downgraded`) carrying both levels and both signal sets, and surface it in the omission evidence that `gate omit` writes. It **audits**, it does not refuse: a genuine re-scope (auth removed from scope) is legitimate and refusing would be a false floor. Closes T09 NB-2's asymmetry. | §15 "Every required, omitted, approved, rejected or excepted gate must be explainable and auditable"; §12 "Claude cannot lower deterministic policy floors" |
| **D12** | One sentence in the prompt layer (`modules/gate-protocol.md`, and the gate-facing capability file) stating that re-assessing risk is not a means of clearing a gate, and that a downgrade is recorded. | §15; T09 NB-2 recommendation |
| **D13** | Close the `branch_guard` fail-open (T03-1): add state field `pending_branch_ack` (null by default), written when the first step of a two-step command (`skip` / `reset` / `restart` / `implement preflight`) acknowledges the branch, and required to match at the second step. Switching branch between the two steps now produces an audited `branch_mismatch` instead of an unaudited action. | §28 "Never remove an existing safety control"; a declared fail-open with no other owner |
| **D14** | Bump the version string 1.16 → 1.17 in all five locations `_check_version_consistency` reads, add `VERSION_MIGRATION` row `1.16 → 1.17` (content: add `pending_branch_ack: null` if missing — the D13 field), and the matching step in `MIGRATIONS`. A README version-history row records what v1.17 is. | `lint-skill` `version_string_consistent` + `migration_covers_every_state_field`; CLAUDE.md "Changing the state schema additionally needs a new `VERSION_MIGRATION` row" |
| **D15** | Update the 18 stale `.workflow/` lines in `docs/dry-runs/` (E20) to the WorkItem runtime shape, and re-baseline the two transcript byte-identity pins to a *declared-substitution* comparison (§7.3). | CLAUDE.md: the transcripts are the behavioural specification; §17 exit criterion |
| **D16** | Add one `lint-skill` check, `documentation_set_is_present`, asserting that §17's nine documentation targets exist and are non-empty. | §17 Documentation; `lint-skill` is the mechanism that stops a manual checklist rotting |

### 5.2 Preserved invariants

Each of these is an acceptance criterion in §8, not an aspiration.

| # | Invariant | How T11 proves it |
|---|---|---|
| **B1** | **The core refuses; it does not warn.** Every new failure path is a refusal with a reason, a message and structured `data`. | A2, A16 |
| **B2** | **Single writer — a refusal leaves `audit.md` byte-identical.** Every new precondition (D10, D13) is a *pure reader* placed ahead of the first `append_audit`, exactly as `flow_precondition` and `governance_precondition` already are. | A9 |
| **B3** | **Claude cannot lower a deterministic floor.** D11 adds evidence, never permission. No policy floor value changes in T11. | A13, N12 |
| **B4** | **The ladder never guesses.** D1 removes a rung; it adds no tie-break, no ordering, no "most recent". D10 *extends* the no-guessing rule into Spec Kit discovery. | A5, N8 |
| **B5** | Exit codes 0/1/2/3 keep their meanings. D8 moves one reason string between two codes that were already distinct; no code changes meaning. | A16 |
| **B6** | JSON on stdout, human text on stderr; `sdle.py constants` / `lint-skill` keep nesting under `data`. | A16 |
| **B7** | Atomic writes; the audit hash chain; drift; artifact SHA/fingerprints; the secrets scan; test evidence; the implementation diff baseline; path safety; rate limits; the dirty-tree guard; the untrusted-content scan. | A14 pins the §18 matrix row-by-row |
| **B8** | Cross-platform launchers (`sdle.sh` / `sdle.ps1`) and `no_powershell_only_cmdlets`. | A17, N16 |
| **B9** | Migration discipline: `migrate-workflow` never mutates, renames or deletes `.workflow/`. | A6, N7 |
| **B10** | **CLAUDE.md invariants 1–8 all still hold**, in particular invariant 8 (gates stay in the parent) and invariant 6 (single writer). No T11 change delegates a gate or adds a second writer. | A18 |
| **B11** | GREENFIELD's traversal, gate set and integration-01 driver are unchanged. `tests/test_integration_01_happy_path.py` stays byte-identical to `4b1aa71` for the whole phase. | A1 |
| **B12** | Dry-run/regression philosophy: transcripts remain the behavioural specification and remain machine-compared. D15 changes *what* they say, never *whether* they are pinned. | A20 |

---

## 6. Files expected to change

### 6.1 Product code

| Path | Milestone | Nature |
|---|---|---|
| `scripts/sdle.py` | M1–M5, D16 | Rung removal; 12 carve-out deletions; refusal message; `SDLE_OWNED_PREFIXES`; `cmd_manifest_build`; `cmd_workitem_use`; `cmd_feature_resolve`; governance downgrade event; `pending_branch_ack` + migration step; new lint check |
| `.claude/hooks/hooks.py` | M2 | `SPECS_CARVE_OUT` path normalisation; `FENCE_REASONS[".workflow"]` reworded from "transitional legacy runtime" to "archival legacy runtime; migrate it with …" |
| `.claude/skills/sdle/SKILL.md` | M1, M4, M5, M7 | Resolution paragraph (drop the legacy rung sentence); version strings; `VERSION_MIGRATION` row; the D12 sentence's cross-reference; line 358's post-T04 inaccuracy (T04 N-4) |
| `.claude/skills/sdle/modules/gate-protocol.md` | M4, M7 | D12 sentence; the three stale `.workflow/` paths |
| `.claude/skills/sdle/modules/phase-execution.md` | M7 | The five stale `.workflow/` paths |
| `.claude/skills/sdle/templates/state.json` | M5 | `workflow_version` → `1.17`; `pending_branch_ack: null` |
| `.claude/commands/sdle-start.md` | M1 | The legacy-`.workflow/` paragraph becomes the migration instruction |
| `.claude/commands/sdle-approve.md` | M7 | Stop naming module paths in prose (T10 NB-2) |

### 6.2 Documentation

| Path | Milestone | Nature |
|---|---|---|
| `README.md` | M7 | Resolution ladder; the legacy paragraphs; v1.17 title + version row; five-hook count; `Read, Grep, Glob` restatements pointed at their authority |
| `CLAUDE.md` | M7 | The "transitional `.workflow/`" sentence in Architecture; the gitignore sentence; version; the six new doc directories |
| `docs/architecture/ADR-001-deterministic-core.md` | M7 | "Four hooks" → five (T10 NB-3) |
| `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md` | M7 | **NEW.** Records what was removed, what was preserved and why (§3), the D10/D11/D13 decisions, and every deferral from §9 |
| `docs/SDLE-Reference-Guide.md` | M7 | Version header; resolution section; runtime paths |
| `docs/workitems/` | M7 | **NEW directory** (E22) |
| `docs/lifecycle/` | M7 | **NEW directory** |
| `docs/risk-and-gates/` | M7 | **NEW directory** |
| `docs/brownfield/` | M7 | **NEW directory** |
| `docs/spec-kit-integration/` | M7 | **NEW directory** |
| `docs/troubleshooting/` | M7 | **NEW directory** — must contain the §3.3 migration path and the `workitem_required` / `workitem_ambiguous` / `feature_ambiguous` / `index_malformed` recovery procedures |
| `docs/dry-runs/*.md` | M8 | D15 |

### 6.3 Files that must NOT change

| Path | Why |
|---|---|
| `.gitignore` | P7; and leaving it keeps two byte-identity pins intact |
| `.claude/settings.json` | The fence deliberately is not there; byte-pinned twice |
| `tests/test_integration_01_happy_path.py` | B11 — byte-identical since T07 and must stay so |
| `tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py` | Same pin |
| `docs/transition/transition.md` | Immutable migration contract |
| Any `docs/transition/phases/T00…T10-*.md` | Prior phases' artifacts are immutable |
| `.claude/agents/sdle-transition-*.md`, `tools/transition/`, `docs/transition/`, `SDLE-TRANSITION-*` at repo root | §1.4: the control plane MAY be removed only in a **separate post-transition cleanup after T11 has independently passed**, and MUST NOT delete itself while the transition is executing |

---

## 7. Tests

### 7.1 Anti-contradiction clause

This plan **explicitly permits** the following test-file edits. Any other test
change is out of scope and must be raised as a plan deviation in the handoff.

- **X-GEN.** Where a plan-authorised product change *mechanically forces* a
  closed-set assertion to grow or shrink (an enumerated tuple, an exact-set
  equality, an exhaustive `assert x == (...)`), the implementer may re-value
  that assertion to the new closed set, provided (a) the set stays exhaustive,
  (b) the change is recorded in the handoff with the authorising D-item, and
  (c) no assertion is deleted or weakened to an `in`/`>=` shape.
- **conftest.py.** `tests/conftest.py` may be edited to: drop `Project.runtime`'s
  `workitem is None → .workflow` branch once no fixture uses it; add fixtures the
  hardening tests need (a legacy-only repository, a two-worktree pair, a
  fresh-subprocess launcher). It may **not** change what any existing fixture
  produces for an existing test.
- **T10 NB-1 remediation.** `test_units_gate_policy.py::_hooks_top_level` may be
  extended to capture `ast.Import` / `ast.ImportFrom` and the module docstring.
  This is a strict strengthening and is the remedy T10's verifier wrote out.

### 7.2 Existing tests affected

Every entry is classified under TP-003. There is no fourth category.

| # | Test(s) | TP-003 | Action |
|---|---|---|---|
| **X1** | `test_units_workitem_runtime.py::test_rung3_legacy_state_stays_readable_when_no_workitem_exists`; `test_units_workitem_resolution.py::test_the_legacy_dual_read_rung_still_binds` | 2 — deliberately superseded by D1 | **Invert**, do not delete. Each becomes "with zero WorkItems and legacy state present, the ladder returns `none` and the refusal names the migration path". Strictly more assertion than before. |
| **X2** | `test_units_governance.py::test_e1_is_skipped_under_the_legacy_binding_and_only_there`; `test_units_artifact_review.py::test_e2_stands_aside_under_the_legacy_binding_and_only_there`; `test_units_gate_policy.py::test_n18_the_legacy_runtime_can_never_omit_a_gate`; `test_units_speckit_binding.py::test_n7_the_legacy_binding_keeps_its_baseline_behaviour`, `::test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding` and the `plant_legacy_workflow` helper's dependents | 2 — D4 removes the carve-out each one describes | Rewrite each as "the precondition now applies unconditionally, because there is no binding without a WorkItem". The "and only there" half becomes "always". |
| **X3** | `test_units_capabilities.py::test_n22_the_legacy_rung_and_migrate_workflow_are_untouched`; `test_units_gate_policy.py::test_n31_the_legacy_rung_and_migrate_workflow_are_untouched`; `test_units_gate_policy.py::test_n31_no_t11_leakage` | 2 — these are anti-leakage pins whose declared owner is T11 (E15, E16) | Split each: the **`migrate-workflow` leaves `.workflow/` byte-identical** half is *kept verbatim* (it is B9 and must never be lost); the **legacy rung binds** half is replaced by its inverse. `test_n31_no_t11_leakage` is retired and replaced by `test_t11_the_legacy_rung_is_gone`, asserting the removal positively. |
| **X4** | `test_units_flow_model.py::test_the_two_guard_surfaces_are_unchanged` | 2 — D5/D6 adopt exactly the finding this test says T11 owns | X-GEN re-valuation: the tuple gains `".sdle/"`; the `cmd_manifest_build` AST assertions invert to require the exclusion. Docstring rewritten to record that T11 adopted it and why (§3.2 replacement-safety argument). |
| **X5** | `test_units_workitem_resolution.py` `ACTIVE_CONTEXT_SETTERS` pin (≈ line 1459) | 1 — value unchanged by D9 | Keep; add an assertion that a non-member `set_by` now raises |
| **X6** | `test_units_capabilities.py::test_n20_n24_the_frozen_files_are_byte_identical` and `test_units_gate_policy.py::test_n25_…the frozen files…` for the single entry `templates/state.json` | 2 — D13/D14 change that file | Re-baseline **only** the `templates/state.json` entry, to `4b1aa71`, and add a companion assertion that the diff against `4b1aa71` consists solely of the `workflow_version` value and the added `pending_branch_ack` key. The other entries (`.gitignore`, `.claude/settings.json`, the three integration files) keep their existing baselines untouched. |
| **X7** | `test_units_capabilities.py::test_n26_every_baseline_check_is_still_present_and_passing` | 2 — D16 adds a check | X-GEN: add `T11_CHECKS = ("documentation_set_is_present",)` and extend the exact-set equality. The equality stays exact. |
| **X8** | `test_units_speckit_binding.py` newest-mtime selection tests (≈ lines 574–599) | 3 — defect discovered (T04 N-2), fixed by D10 | Rewrite: two candidates in one tier now refuse `feature_ambiguous`. The single-candidate and zero-candidate cases keep their existing assertions verbatim. |
| **X9** | `test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical` | 2 — D7 changes `hooks.py`, and T10 NB-1 asks for the strengthening | Extend `_hooks_top_level` per §7.1, re-baseline the hooks pin to `4b1aa71`, and keep every existing definition-name / guard-registry / hook-file assertion. Net coverage strictly increases. |
| **X10** | `test_units_capabilities.py::test_n20_the_nine_dry_run_transcripts_are_byte_identical`; `test_units_gate_policy.py::test_n27_the_nine_dry_run_transcripts_are_byte_identical` | 2 — D15 | See §7.3. Both become declared-substitution comparisons; neither is deleted and neither becomes vacuous. |
| **X11** | Any test asserting the v1.16 string or the 16-row migration chain | 2 — D14 | X-GEN re-valuation to `1.17` / 17 rows |
| **X12** | `test_units_workitem_resolution.py` rung-enum assertion `decision.rung in {None, "explicit", "cwd", "sole", "context", "branch", "legacy"}` | 1 — unchanged behaviour under a permissive assertion | **Tighten**: drop `"legacy"` from the permitted set. Not required for green, but leaving it would let the rung silently return |

**Not affected, and this is load-bearing:** `test_units_workitem.py`,
`test_units_state.py`, `test_units_transitions.py`, `test_units_infra.py`,
`test_units_cli.py`, `test_units_discovery.py`, `test_units_baseline.py`,
`test_hooks.py` (behaviour), `test_lint_skill.py` and all three integration
files. If any of those needs a change, the implementer has overreached and must
stop and record it.

### 7.3 The dry-run transcripts — declared disposition (§13 precedent)

**The removals do not change what a GREENFIELD run looks like.** Every fixture
registers a WorkItem (E32), so integration 01 never took the legacy rung and its
traversal is untouched. B11 requires it stay byte-identical, and A1 proves it.

What *is* wrong is that the transcripts still print `.workflow/` runtime paths
(E20) — stale since T02, deliberately untouched at T04 (N-6), and now flatly
contradicting §17's exit criterion. Leaving them is the "silently dropped
finding" this phase must not produce; CLAUDE.md calls them the behavioural
specification.

**Disposition: update them (D15), declared, in the last milestone.** The two
pins (E17) become:

> For each file in `docs/dry-runs/`, compute `at_baseline(f)`; apply the
> **declared substitution set** (an enumerated list of `.workflow/…` →
> `workitems/<id>/.sdle/…` rewrites, written out in the test); assert the result
> equals `here(f)` exactly.

This keeps both pins non-vacuous and strictly auditable: any change *other* than
the declared substitutions still fails. The substitution set is enumerated in the
test file, not computed, so a wildcard cannot silently absorb a real edit.

**If M8 is dropped**, the transcripts stay as they are, both pins stay as they
are, and the checkpoint records D15 as DEFERRED with this reason. That is the
only acceptable alternative outcome; silently leaving them without a record is
not.

### 7.4 New tests required (§17's 16 mandatory hardening tests)

§17's list has **16** bullets, not 17 (E31). All 16 are planned. Where coverage
already exists it is named, and the new test states what it adds — a hardening
test that only re-runs an existing assertion is not a hardening test.

| # | §17 bullet | Existing coverage | What N-adds |
|---|---|---|---|
| **N1** | Two WorkItems in separate branches/worktrees | `test_units_workitem_resolution.py::test_two_worktrees_drive_two_workitems_with_no_flag` | Drive **both** worktrees through a full run to `complete` concurrently-interleaved, and assert each `audit.md` verifies independently and neither contains the other's execution id |
| **N2** | State isolation | `test_two_workitems_complete_independent_runs`, `test_each_workitem_keeps_its_own_audit_ledger`, `test_a_lock_on_one_workitem_never_blocks_another` | Extend isolation to the artifacts T05–T09 added: `execution.json`, `governance.json`, `reviews.json`, `discovery`, `evidence/`. Assert byte-identity of WI-B's whole `.sdle/` across a full WI-A run |
| **N3** | WorkItem index merge-conflict validation | none | Plant `<<<<<<<` / `=======` / `>>>>>>>` markers in `workitems/index.md`: assert `index_malformed`, exit **3**, file byte-identical afterwards, and that `workitem create` refuses rather than "repairing". Second case: a badly-resolved merge producing duplicate ids → `validate` reports a duplicate **ERROR** |
| **N4** | Corrupt state | partial | Corrupt `workitems/<id>/.sdle/state.json`: exit 3, `audit.md` byte-identical, no `.tmp` sibling left, and `doctor` still reports usefully |
| **N5** | Corrupt audit | `audit verify` tests | A tampered chain refuses at the choke point, writes nothing, and the refusal names the broken entry |
| **N6** | Interrupted atomic write | infra tests | Assert that a stray partial temp file beside `state.json` is never read as authoritative and does not survive the next successful write |
| **N7** | **Interrupted legacy migration** — post-removal meaning: `migrate-workflow` is now the *only* legacy path, so this matters more, not less | `test_a_crash_during_migration_leaves_no_resolvable_target` | Parameterise the interruption over **every** write point including the manifest and completion-summary copies (closes T02 NB-5). At each: `.workflow/` byte-identical, no resolvable target, and a re-run succeeds. Then prove §3.3 end-to-end: legacy-only repo → `workitem create` → `migrate-workflow` → a working WorkItem runtime, through `run_cli` |
| **N8** | Ambiguous resolution | rung tests | Post-D1: zero WorkItems + legacy state → `workitem_required` whose message names both migration steps in order; >1 plausible → `workitem_ambiguous` with candidates and **no** pick |
| **N9** | Missing Spec Kit | `speckit_missing` paths | Assert fail-closed at the first Spec Kit-owned phase, exit 1, nothing written |
| **N10** | Unsupported Spec Kit capability | `test_n4_a_missing_capability_refuses_and_writes_nothing` | Assert the refusal is reached *before* any WorkItem-scoped write and that `capabilities` still reports without refusing |
| **N11** | Stale baseline | T08 baseline tests | Assert a stale baseline blocks an `ITERATIVE` WorkItem's reliance on it and that the finding names the invalidating commit |
| **N12** | Policy floor enforcement | T09 gate-policy tests | Assert directly that a *proposed* level below a hard floor is refused, and — with D11 in place — that a downgrade re-assessment is recorded as `governance_downgraded` and appears in the omission evidence |
| **N13** | Gate omission evidence | T09 tests | Assert every omitted gate carries: the policy that permitted it, the governance record SHA it was derived from, and the audit event; and that `complete` refuses when an omission is no longer justified |
| **N14** | **Restart after `/clear`** — post-removal meaning: *same working directory, same active context, no conversation* | none | Drive a WorkItem to mid-flow, then reconstruct the entire operating context using **only** on-disk artifacts through a fresh `run_cli` subprocess: phase, flow, gate disposition, required capability files. Assert `audit.md` is byte-identical across the reconstruction (a read must never write) |
| **N15** | **Restart in a fresh Claude session** — post-removal meaning: *different session token, no persisted active context* | none | Same as N14 but additionally delete `workitems/.active-context.json` and pass a **new** `--session`. Assert resolution still succeeds from durable state alone, the WorkItem-local session lock does not falsely block, and the reconstruction is identical to N14's |
| **N16** | **Windows/Linux behaviour** — see §10 for what is and is not observable on this host | scattered | **Observable here, so planned:** every emitted JSON path uses `/` on this platform; no `os.sep` literal reaches an emitted payload; `sdle.sh` and `sdle.ps1` agree on the interpreter-resolution contract; `lint-skill`'s `no_powershell_only_cmdlets` passes; hashing is line-ending-normalised where the comparison is textual. **Not planned:** any assertion whose truth requires executing on Linux |

Additional new tests outside the §17 list, required by the D-items:

| # | Test |
|---|---|
| **N17** | D3: the `workitem_required` refusal names `workitem create` then `migrate-workflow`, in that order, and carries `legacy_state` in `data` |
| **N18** | D5/D6: `.sdle/` no longer reaches a second WorkItem's dirty-tree guard nor the Gate 7 manifest; and no *other* prefix was added |
| **N19** | D7: `workitems/<id>/specs/../.sdle/state.json` is now **denied** by the write fence |
| **N20** | D8: the two reason strings are distinct and carry their own exit codes; `cmd_workitem_use` turns an `OSError` into a refusal |
| **N21** | D10: two candidates in the repository-global tier refuse `feature_ambiguous` and write nothing; `feature bind` still resolves it |
| **N22** | D13: switching branch between the two steps of `skip`/`reset`/`restart`/`implement preflight` now produces an audited `branch_mismatch` and the action does not run |
| **N23** | D14: the `1.16 → 1.17` migration is idempotent and preserves every `MIGRATION_VERIFIED_FIELDS` value |
| **N24** | D16: the new lint check fails loudly when a documentation directory is removed (asserted on a copied tree, never on the live one) |
| **N25** | R2, asserted positively: for every non-`RUNTIME_FREE` command, a successful `bind_workitem` returns a `Paths` whose `workitem` is not `None`. Proven over the parser's registered command set, not a hand-copied list |

---

## 8. Acceptance criteria

Objectively testable. Each names how it is proven.

- [ ] **A1** `tests/test_integration_01_happy_path.py`, `test_integration_02_to_05.py`, `test_integration_06_to_09.py`, `.claude/settings.json` and `.gitignore` are byte-identical to `4b1aa71` at the end of the phase (`git diff --stat 4b1aa71 -- <paths>` is empty).
- [ ] **A2** `resolve_decision` can no longer return `rung == "legacy"`; `grep` finds no `"legacy"` rung literal in `sdle.py`, and `bind_workitem`'s only non-raising return is a bound `Paths`.
- [ ] **A3** No `paths.workitem is None` guard remains in `sdle.py` except (a) inside `Paths` itself and (b) `collect_validation_findings`' speculative-resolution warning. Proven by an AST test (N25), not by grep alone.
- [ ] **A4** From a repository containing **only** a legacy `.workflow/` runtime, `workitem create` followed by `migrate-workflow --workitem <id>` produces a working WorkItem runtime, driven through `run_cli`. Proven by N7.
- [ ] **A5** With zero WorkItems and legacy state present, every non-`RUNTIME_FREE` command refuses `workitem_required` (exit 1) with a message naming both migration steps in order. Proven by N8/N17.
- [ ] **A6** After any `migrate-workflow` run — successful, refused, or interrupted at any write point — every file under `.workflow/` has the same SHA-256 it had before. Proven by N7.
- [ ] **A7** `PROJECT_ROOT_MARKERS` still contains `(".workflow", "state.json")`; `.workflow` is still in `hooks.py::FENCED` and in `SDLE_OWNED_PREFIXES`; `.gitignore` still ignores `.workflow/`.
- [ ] **A8** All 16 §17 hardening tests exist as named test functions and pass (N1–N16).
- [ ] **A9** A refused advance, approval, omission, skip or gate action leaves `audit.md` byte-identical — asserted for every new refusal introduced by D3, D10, D11, D13.
- [ ] **A10** `lint-skill` reports `failed: []` with **43** checks (42 + D16), and `test_n26`'s exact-set equality holds against `BASELINE_CHECKS + T10_CHECKS + T11_CHECKS`.
- [ ] **A11** `version_string_consistent` passes at `1.17` across all five locations; `migration_covers_every_state_field` passes with **17** migration rows.
- [ ] **A12** All nine §17 documentation targets exist and are non-empty; the six new directories (E22) are named as new in the handoff.
- [ ] **A13** No hard risk-floor value changed. Proven by comparing the parsed floor table against `4b1aa71`.
- [ ] **A14** Every row of the §18 Capability Preservation Matrix marked PRESERVE has a named passing test, listed row-by-row in the handoff. Any row claimed superseded cites the transition-contract section that supersedes it.
- [ ] **A15** `sdle.py constants` still reports 21 registry phases and 5 flows; the GREENFIELD flow is unchanged element-wise from `4b1aa71`.
- [ ] **A16** Exit codes: every new refusal returns 1, every new usage error 2, every new integrity failure 3. Proven per-test.
- [ ] **A17** `no_powershell_only_cmdlets` passes; both launchers still exist and neither gained a platform-only construct.
- [ ] **A18** No product subagent gained a write tool; `product_agents_are_read_only`, `product_agents_declare_the_fence` and `product_agents_declare_the_non_approval_clause` all still pass.
- [ ] **A19** Every finding in §9 has a disposition recorded in `ADR-008` — FIXED with the D-item, DEFERRED with a reason, or NOT-A-DEFECT with a reason. Count in ADR-008 equals the count in §9.
- [ ] **A20** Both dry-run transcript pins still exist and are non-vacuous — proven by mutating one transcript in a scratch copy and observing the test fail.
- [ ] **A21** No file under `docs/transition/`, `tools/transition/` or `.claude/agents/sdle-transition-*` was modified or deleted, except `docs/transition/progress.md` and this phase's own new artifacts (§1.4).
- [ ] **A22** Full suite green: raw exit 0, `collected == passed`, captured with `--junitxml` and read without a pipe. **Figure to be observed by the implementer and independently re-derived by the verifier; it is `UNKNOWN` at planning time (E34).**

---

## 9. Inherited-findings triage

Every open finding T11 inherits, with exactly one disposition. There is no T12.

| ID | Source | Disposition | Rationale |
|---|---|---|---|
| **TR1** | T10 NB-1 — `test_n28` AST extraction misses imports and the module docstring | **FIXED** (X9) | A proven coverage narrowing on a guardrail file, with a remediation already written by T10's verifier |
| **TR2** | T10 NB-2 — `sdle-approve.md` names module paths in prose | **FIXED** (M7) | Invariant 7; the engine now owns "which capability files a phase needs" |
| **TR3** | T10 NB-3 — ADR-001 says "four hooks", there are five | **FIXED** (M7) | Present-tense architectural claim, now false |
| **TR4** | T10 NB-4 — `Read, Grep, Glob` restated in eight unchecked places | **FIXED, partially** (M7) | The four agent *frontmatters* are machine-checked already. T11 rewrites the four agent **bodies** and the four documents to point at `PRODUCT_AGENT_TOOLS` as the authority rather than restate the literal. No new lint check: the enforcement path is already checked, and a ninth lint rule for prose would be cost without a guarantee |
| **TR5** | T10 NB-5 — docs paraphrase `CAPABILITY_MAP` rows | **NOT-A-DEFECT** | Each site already points at `CAPABILITY_MAP` as authoritative and the pattern predates T10. Recorded in ADR-008 so a later editor does not read the prose as normative |
| **TR6** | T10 NB-6 — prompt files state the fence's effect without ADR-007 §3's local-runtime caveat | **FIXED, minimally** (M7) | One clause added to `SKILL.md` Step 6b and the two capability modules: "…when the runtime honours the registered hook". The four agent bodies are addressed to an operator and keep their plain statement |
| **TR7** | T09 NB-2 — HIGH→LOW re-assessment is the practical route to omitting a required gate | **FIXED as evidence, not as refusal** (D11, D12, N12) | The floor was never lowered; the *inputs* changed, and ADR-006 §3 discloses that. Refusing a downgrade would block a legitimate re-scope — a false floor. Auditing it closes the asymmetry T09 named without inventing a rule the contract does not state |
| **TR8** | T09 NB-3 — §15's HIGH list names a documentation review that no gate implements | **DEFERRED beyond V1**, recorded in ADR-008 | Adding a ninth gate is a **lifecycle** change owned by T07/T09, not a §17 removal-and-hardening change. It would touch all four phase tables, `phase-execution.md`, every `PROGRESS_MAP` denominator, the state template's `approvals`, integration 01's `EXPECTED_TRAVERSAL` and `GATES`, and all nine transcripts — i.e. it would change what a GREENFIELD run looks like, at the last milestone of the last phase, for a requirement §17 does not ask for and §26's definition of done does not list. §15 calls the list a *default intent*; seven of its eight items map onto existing gates. ADR-008 records it as the single named V1 gap with a proposed shape for a follow-on |
| **TR9** | T08 — `.sdle/` in neither `SDLE_OWNED_PREFIXES` nor `cmd_manifest_build`'s exclusion | **FIXED** (D5, D6, N18) | Replacement safety property (§28): `.sdle/` is written only by `config` and `baseline`, both of which already produce their own audited records, so excluding it from the dirty-tree guard loses no evidence — while *not* excluding it breaks cross-WorkItem isolation, which §8/§9 do guarantee |
| **TR10** | T04 N-2 — Spec Kit tier-2 newest-mtime cross-adoption between concurrent WorkItems | **FIXED** (D10, N21, X8) | A silent wrong pick from a repository-global staging area — the precise failure §9 and §10 forbid. Fix is strictly fail-closed and has an existing explicit escape hatch (`feature bind`) |
| **TR11** | T04 N-7 — `cmd_manifest_build` lacks its sibling's relocation exclude | **FIXED** (D6) | Same edit as TR9's second half |
| **TR12** | T04 N-3 — write-fence carve-out matches a non-normalised path | **FIXED** (D7, N19) | A fence bypass. Bounded (the engine's own refusal is the guarantee, not the hook) but cheap to close |
| **TR13** | T04 N-4 — `SKILL.md:358` inaccurate after T04's fence carve-out | **FIXED** (M7) | |
| **TR14** | T04 N-6 / T02 residual — stale `.workflow/` paths in `phase-execution.md`, `gate-protocol.md` and `docs/dry-runs/` | **FIXED** (M7 for the modules, M8 for the transcripts; M8 severable per §7.3) | |
| **TR15** | T03-1 — `branch_guard` fail-open between a two-step command's confirmations | **FIXED** (D13, N22) | A declared fail-open in a guard with no other owner. Needs the schema change T11 is making anyway for D14 |
| **TR16** | T03-4 — `ACTIVE_CONTEXT_SETTERS` dead in production | **FIXED** (D9, X5) | |
| **TR17** | T03-5 — `cmd_workitem_use` not error-hardened | **FIXED** (D8, N20) | |
| **TR18** | T03-6 — `workitem_required` reused for a `UsageError` | **FIXED** (D8, N20) | One reason string, two exit codes, is an invariant-7 violation on the CLI contract itself |
| **TR19** | T03-7 — `init` with both a corrupt index and legacy state reports `index_malformed`, not `legacy_workflow_present` | **NOT-A-DEFECT** | Both are refusals; both are correct; a corrupt index is the more fundamental problem and reporting it first is the right order. Pinned by a new assertion in N3 so the ordering stops being untested |
| **TR20** | T03-8 — on a mismatched branch the ledger records `branch_mismatch_accepted` even when the command then refuses | **FIXED as a by-product of D13** | `pending_branch_ack` moves the acknowledgement out of the audit-before-refuse position. Verify explicitly; if it does not fall out, record as DEFERRED |
| **TR21** | T03-10 — `SKILL.md`'s branch-mismatch paragraph over-generalises "re-run the same command — which proceeds" | **FIXED** (M7) | D13 changes this paragraph's subject matter anyway |
| **TR22** | T02 NB-2 — the `legacy_workflow_present` message never names archiving `.workflow/` | **FIXED** (D3) | Post-T11 this message is the user's only signpost |
| **TR23** | T02 NB-4 — the post-commit `workitem.json` write sits outside the migration commit window | **DEFERRED**, recorded in ADR-008 | The commit marker is the target `state.json`, written last; a failure after it leaves a correct, resolvable runtime with slightly stale metadata, which the next command re-derives. Changing the commit window at the last phase risks the atomicity property N7 exists to protect. Recorded with a proposed shape |
| **TR24** | T02 NB-5 — the migration crash test never exercises the manifest/completion copies | **FIXED** (N7) | |
| **TR25** | `design/`, `reviews/`, `clarifications/` remain repository-level; `design/app/app-design.md` is shared across WorkItems | **DEFERRED**, recorded in ADR-008 | T04's explicit recorded decision. Moving them is a storage-layout change of T02/T04 magnitude, not a §17 removal, and §10 explicitly warns against copying shared artifacts into every WorkItem for directory aesthetics. ADR-008 states the V1 position: these are repository-level by design, and the follow-on question is which of them are genuinely WorkItem-scoped |
| **TR26** | `docs/transition/RESUME.md` is stale (E36) | **FIXED** (M7) | Updated at the end of the phase to describe the completed state; it is explicitly non-authoritative but a stale pointer is what misled a prior context |

**A19 requires ADR-008 to carry all 26 rows.** A finding that appears here and
not there is a phase failure.

---

## 10. What can and cannot be observed on this host

§17 mandates a **Windows/Linux** hardening test while CI has never executed
(E35). Stating this plainly is a requirement of the phase, not a caveat.

**Observable on this host, and therefore planned (N16):**

- POSIX separators in every emitted JSON path, on Windows;
- absence of `os.sep` literals in emitted payloads;
- `lint-skill`'s `no_powershell_only_cmdlets` over every prompt file;
- both launchers present, and neither carrying a platform-only construct;
- line-ending-normalised comparison wherever a test compares file text
  (`git show` emits LF, the working tree is CRLF);
- `pathlib`-only path construction in the code paths T11 touches.

**Not observable on this host, and therefore NOT planned as a test:**

- an actual run on Linux;
- an actual run on Python 3.11;
- any CI outcome on `ubuntu-latest` or `windows-latest`.

The handoff and verification MUST record Python 3.11 as `NOT_RUN` and CI as
`UNKNOWN`. **No agent may report a cross-platform result it did not observe.**
The honest V1 statement — which ADR-008 must carry — is: *the engine is written
to be cross-platform and is mechanically checked for platform-only constructs;
it has been executed only on Windows / Python 3.14 in this migration.*

---

## 11. Failure modes

| # | Failure mode | Detection | Response |
|---|---|---|---|
| **F1** | Removing rung 6 bricks a legacy-only repository because some command needed for recovery turns out **not** to be `RUNTIME_FREE` | N7's end-to-end recovery test fails | Stop. Do not widen `RUNTIME_FREE_COMMANDS` speculatively — establish exactly which command failed and why, and prefer restoring the two-command path over adding a third |
| **F2** | The removal reaches further than intended and integration 01 or a transcript moves during M1 | A1 / the transcript pins fail inside M1 | Revert the offending edit. A GREENFIELD change in M1 is by definition out of scope — M8 is the only milestone allowed to move a transcript |
| **F3** | Deleting a carve-out makes a precondition fire where it previously stood aside, breaking a test that had nothing to do with the legacy rung | Suite red outside the X1–X3 set | Category 3 (defect discovered) or category 1 (unchanged behaviour, test must go green). It is **not** a licence to reinstate the carve-out |
| **F4** | D13's `pending_branch_ack` interacts with `pending_confirm_action` and produces a double-confirmation or a stale-confirmation regression | Existing confirm/stale-guard tests fail | These are two independent keys; if they cannot be made independent, drop D13 as a unit (M5 is severable) and record it DEFERRED rather than half-implement it |
| **F5** | D10 refuses a case the suite depends on for setup (a fixture that leaves two feature directories around) | Unrelated Spec Kit tests fail | Fixtures may be adjusted under §7.1's conftest clause; product behaviour may not be relaxed back to newest-mtime |
| **F6** | D14's version bump breaks a pin nobody expected | `version_string_consistent` or an X11 pin fails | X-GEN re-valuation; if a *sixth* location turns up, add it to `_check_version_consistency` so the lint rule stays the single authority |
| **F7** | The declared-substitution transcript comparison (§7.3) is written as a wildcard and becomes vacuous | A20's mutation check | The substitution list must be an enumerated literal in the test; a regex that matches anything is a plan violation |
| **F8** | An agent run is killed mid-flight by API limits (≈18 such kills so far, including a weekly one) | No durable checkpoint for the current milestone | Resume at the **last completed milestone boundary**, never mid-milestone. Verify the claimed state against disk before trusting a checkpoint |
| **F9** | A false green from the shell proxy: plain `python -m pytest` prints `Pytest: No tests collected` and exits 0 | `collected != passed`, or a suspiciously fast run | Always `rtk proxy python -m pytest …`; capture with pytest's own `--junitxml`; read `$?` with **no pipe** between |
| **F10** | A false negative from a plain `grep -rn` | A "clean" grep that contradicts a file you have read | Reproduce every **negative** with `rtk proxy "grep -rnE …"` or a Python walk before relying on it |
| **F11** | A literal `\|` in a `progress.md` cell makes `validate.py` exit 3 | `validate.py` exit 3 | Escape or reword. Note also that a secrets tripwire fires on masked-key prose in `progress.md` — a documented false positive |
| **F12** | The transition guard refuses a `>` redirection for the planner/implementer role | The guard's refusal text | Use the tool's own output-file flag (`--junitxml`, `-o`). **Declare the refusal verbatim in the handoff; never route around it** |
| **F13** | Suite wall-clock varies 4× under CPU contention | A run that takes far longer than ~26 min | Never run another command while a suite is in flight. The Bash tool caps a foreground command at 600 s — the suite needs a long-running invocation |
| **F14** | An `F1`-style flake assumption is resurrected | Any test failure | **`ENVIRONMENT_FLAKE` is VOID.** Any failure is a presumed real regression until proven otherwise by inspection, not by re-running |

---

## 12. Rollback / recovery strategy

**Rollback point: `11363d9`** (T10 implementation). `4b1aa71` is HEAD and adds
only `docs/transition/` content.

| Situation | Recovery |
|---|---|
| M1 fails structurally | `git checkout 11363d9 -- scripts/ tests/ .claude/` restores the pre-T11 engine wholesale. Nothing outside those trees is touched by M1 |
| A later milestone fails | Revert that milestone's commits only. Each milestone is a separate commit with its own checkpoint, so `git revert` of one milestone never unpicks another |
| The phase must be abandoned | Any milestone boundary is a valid stopping point **after M1**. Before M1 completes, the correct action is a full revert to `11363d9` — a partially-removed rung is the one state this plan does not permit to persist |
| A user's real repository is on the legacy runtime | §3.3, and the `troubleshooting/` doc M7 creates |

**Commit discipline:** one commit per milestone, message naming the milestone and
the D-items it lands. The checkpoint file is written **before** the next
milestone starts, not after.

---

## 13. Unknowns and decision requirements

| # | Unknown | Class | Why it does not block |
|---|---|---|---|
| **U1** | Full-suite figure at HEAD | UNKNOWN (E34) | Deliberately not re-run by the planner. The implementer observes it; the verifier re-derives it independently. No plan decision depends on the number |
| **U2** | Python 3.11 behaviour | UNKNOWN (E35) | T11 introduces no new syntax level and no dependency. Recorded as `NOT_RUN`, never predicted |
| **U3** | CI on `ubuntu-latest` / `windows-latest` | UNKNOWN (E35) | Never observed at any point in the migration. §10 states the honest V1 position instead of guessing |
| **U4** | Whether any external user depends on the legacy runtime migration path | UNKNOWN | §20 explicitly allows reducing the compatibility path "only by explicit decision" — so this plan **does not reduce it**. `migrate-workflow` survives in full (P3). The unknown is therefore resolved in the safe direction and needs no human input |
| **U5** | Exact count of assertions X-GEN will have to re-value | UNKNOWN | Bounded by §7.1's clause and recorded per-change in the handoff. Not a decision |
| **U6** | Whether TR20 falls out of D13 automatically | UNKNOWN | Stated as a verify-then-record item, with DEFERRED as the declared fallback |

**No material unresolved decision exists.** Every candidate blocker was examined
and resolved within the contract:

- *A ninth "documentation review" gate?* — §17 does not ask for it; §26 does not
  list it; §15 calls the list a default intent. Deferred **on the record**
  (TR8), which is the disposition my instructions explicitly permit.
- *Refuse a HIGH→LOW re-assessment?* — would create a false floor blocking
  legitimate re-scope, and no contract section requires it. Audited instead
  (TR7).
- *Reduce the §20 migration path?* — §20 permits it only by explicit human
  decision, so the plan does not (U4).

Status recommendation therefore stands at **PLANNED**.

---

## 14. Scope exclusions

Nothing below may leak into T11.

1. **No post-transition control-plane cleanup.** `.claude/agents/sdle-transition-*`,
   `tools/transition/`, `docs/transition/`, `SDLE-TRANSITION-KICKOFF.md`,
   `SDLE-TRANSITION-KIT-*` all remain. §1.4 places their removal in a *separate*
   cleanup after T11 has independently passed, and forbids the control plane
   deleting itself mid-transition (A21).
2. **No new lifecycle phase and no new gate** — including the §15 documentation
   review (TR8). Flow membership and the phase registry are frozen at T07's
   shape; `GREENFIELD_V1_PHASES` does not move.
3. **No `sdle.py` module split.** §23 is explicitly a *recommended* sequence
   ("do not begin by splitting `sdle.py` only because it is large"), and a
   10 799-line refactor in the same phase as the removals would destroy the
   "nothing else moved" proof that M1 depends on.
4. **No YAML dependency.** §11's decision stands: JSON for machine-owned state.
5. **Nothing from §27's deferred list**: release/build management, deployment,
   central DB or service, REST API, web UI, MCP, cross-repository orchestration,
   distributed locks, knowledge graph, RAG, OPA/Rego, n8n, LangGraph, other
   coding-agent adapters, autonomous deployment.
6. **No change to the transition contract**, to any prior phase's artifacts, or
   to `docs/transition/baseline.md`.
7. **No product-code or test edits by the planner or the verifier.** This plan
   is the only artifact this context writes, besides `progress.md`.
8. **No weakening of any test to make T11 pass** (§1.16). Every test change in
   §7.2 either inverts a superseded assertion, strengthens coverage, or
   re-values a mechanically-forced closed set — never relaxes a shape.
