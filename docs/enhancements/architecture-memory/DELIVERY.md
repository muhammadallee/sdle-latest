# Delivery — Project Architecture Memory and Microservice Placement

> WorkItems are isolated units of delivery; architecture is accumulated
> repository-level knowledge shared across WorkItems.

Branch `feature/project-architecture-memory`, from the baseline commit
`3642ffb`. See [`PROGRESS.md`](PROGRESS.md) for the wave-by-wave record and
the environment deviations, and [`REVIEW-ROUND-1.md`](REVIEW-ROUND-1.md) /
[`REVIEW-ROUND-2.md`](REVIEW-ROUND-2.md) for the two independent reviews.

---

## 1. What changed

SDLE gained **repository-level architecture memory** and a governed phase that
reads and writes it. Every flow now decides *where a capability lives* before
anything is specified, and records that decision where every later WorkItem
can read it.

| Layer | Change |
|---|---|
| Engine (`scripts/sdle.py`) | the `architecture` command group, the catalog and its validator, placement validation, revision control with idempotent replay, the abandonment cascade, two lint checks, the narrowed dirty-tree ownership |
| Lifecycle | `architecture_placement` + `gate_architecture` in all five flows; registry 21 → 23; state schema `1.17` → `1.18` |
| Prompts | `modules/architecture-placement.md`, six `guidelines/*.md`, `CAPABILITY_MAP` rows, renumbered `phase-execution.md` blocks |
| Hooks | `.sdle/architecture` joins the write fence — and `.sdle/` itself deliberately does not |
| Docs | ADR-013, ADR-014, the frozen contracts, dry runs 17–20, and propagation across the whole documentation set |
| Tests | `tests/test_units_architecture.py` (58 tests) plus updates to fifteen existing modules |

## 2. The fixed decisions, and where each one lives

| | Decision | Realized by |
|---|---|---|
| D1 | WorkItem stays the execution boundary | no project-wide workflow was built; the placement record, evidence and gate are WorkItem-scoped |
| D2 | The repository is the architecture-memory boundary | `.sdle/architecture/catalog.json`, derived from `project_root` alone |
| D3 | Architecture is evolutionary | `KEEP_EMBEDDED_AND_MONITOR` with mandatory re-evaluation conditions → `EXTRACT_EXISTING_CAPABILITY`; DR-18 walks it |
| D4 | The constitution is the engineering profile | `guidelines/constitution.md`'s five categories; ADR-014; no engineering-profile artifact exists |
| D5 | Guidelines are advisory | `guidelines/` is a second capability home, lazily loaded; the precedence chain is stated in `modules/architecture-placement.md` and ADR-014 |
| D6 | An explicit phase with its own gate before `spec_draft` | `MANDATORY_FLOW_PHASES` + the `architecture_phase_precedes_spec_in_every_flow` lint check, which asserts *adjacency* |
| D7 | The engine owns the catalog | `architecture schema` / `assess --input` / `show` / `apply` / `realize`; the write fence; agents never write it |
| D8 | Requirements isolation preserved | placement reads the binding; no code globs `requirements/` |
| D9 | Conceptual separation | architecture state is context in the rendering, never rewritten into requirements |
| D10 | Architecture writes coexist with dirty-tree protection | `SDLE_OWNED_PREFIXES` **narrowed** from `.sdle/` to three engine-written members; `config.json` and `policies/` are visible again |
| D11 | Catalog mutation is replay-safe | stable decision id + proposal digest; `apply` and `realize` both replay idempotently |
| D12 | Constitution availability is outcome-sensitive | all three conditions checked — the declared technology flag, the derived new boundary, the derived ownership transfer |
| D13 | Bootstrap is separate from placement | `bootstrapDelta`, accepted only while uninitialized, evidence-backed, reference-checked |
| D14 | Approved-but-unrealized decisions are durable | engine-driven `ABANDONED`/`SUPERSEDED` on restart, reset and rerun; `PLANNED` → `WITHDRAWN`, reclaimable; history appended, never rewritten |
| D15 | Structured and rendered artifacts are bound | shared decision id and digest, rendered SHA verified before `apply`, and no drift re-approval path around it |

## 3. The new phase and gate

```
GREENFIELD            20 phases, 9 gates   gate_architecture is Gate 2
BROWNFIELD_DISCOVERY  21 phases, 9 gates   Gate 2
ITERATIVE             18 phases, 8 gates   Gate 1
DEFECT_FIX            16 phases, 7 gates   Gate 1
HOTFIX                12 phases, 4 gates   Gate 1
```

`gate_architecture` is **required at every risk level, in every flow, for
every WorkItem type**, derived inside `gate_requirements` exactly as
`terminal_gate` is — so no policy dictionary and no repository override can
relax it. `lint-skill`'s `architecture_gate_is_universally_required` checks all
4 × 4 combinations.

## 4. The catalog

`.sdle/architecture/catalog.json`, version 1, with a monotonic `revision`:
capabilities, services, candidates, data ownership and decisions. Structurally
validated on every read *and* on every write, so a delta that would produce an
unreadable catalog is refused before the bytes land. One invariant is enforced
rather than described: **exactly one `ACTIVE` owner per datum**, which is why a
new ownership row enters `PLANNED` at `apply` and becomes `ACTIVE` only at
`realize`, in the same step that supersedes the previous owner.

Every entity carries `introducedBy` as well as `decisionReference`: the first
never moves, and the abandonment cascade reads it, so disposing of a decision
can only dispose of what that decision created.

## 5. The five outcomes

`EXTEND_EXISTING_SERVICE` · `CREATE_NEW_SERVICE` ·
`KEEP_EMBEDDED_AND_MONITOR` · `EXTRACT_EXISTING_CAPABILITY` ·
`ARCHITECTURE_REVIEW_REQUIRED`

Exactly one per placement. The fifth is recordable and **not approvable** —
the honest answer when the evidence does not support a placement. Sixteen
evidence dimensions, a per-outcome floor of which must carry a finding, and
**no numeric score** is computed, accepted or stored.

## 6. Constitution and guidelines

The constitution is the engineering profile, structured into mandatory /
preferred / **available** / prohibited / architecture-decision-required —
"available" meaning *permitted*, not *chosen*, which is the distinction that
stops a constitution reading as a shopping list. Six advisory guideline files
are mapped in `CAPABILITY_MAP` and lint-enforced against orphaning. Project
`guidance/` stays optional and untrusted; the two levels are never merged.

## 7. Propagation

`spec_draft` stays inside the approved boundary · `plan_draft` addresses target
services, contracts, data ownership and migration · `tasks_draft` names the
service on every meaningful task and splits cross-service work three ways ·
`analyze` checks tasks against the placement and the catalog ·
`design_generation` grows service-aware sections including explicit
non-responsibilities · `implement` realizes the boundary and must raise rather
than redesign · `gate_implement` approval realizes the decision.

## 8. Tests added

`tests/test_units_architecture.py` — 58 tests covering the catalog, the
placement phase, the gate, revision control and replay, the constitution rule,
bootstrap, realization, abandonment and the two boundaries. Fifteen existing
modules were updated for the new phase, the new gate ordinals and `1.18`;
`tests/conftest.py` gained `record_architecture` and `pass_architecture_gate`
so no driver re-derives the proposal schema.

## 9. Dry runs

17 (placement into an existing service) · 18 (embedded candidate, then
extraction) · 19 (stale revision and idempotent replay) · 20 (bootstrap, and
placing without a constitution). All sixteen existing transcripts were
**recomputed from the engine** — every progress fraction, gate ordinal and
flow size — rather than edited by hand.
`docs/dry-runs/verification-matrix.md` carries the four new rows and the runs
behind them. Round 2 added two contract checks that close the gap the sweep
exposed: the existing checks parse three machine-readable *shapes*, so a
transcript could agree with the engine in its `SDLE_STATE` lines while its
prose still said "All 8 gates passed" about nine. The prose forms are checked
now too.

## 10. Docs updated

ADR-013, ADR-014, `architecture-memory-contracts.md`, `README.md`,
`CLAUDE.md`, `docs/GETTING-STARTED.md`, `docs/SDLE-Reference-Guide.md`,
`docs/lifecycle/`, `docs/risk-and-gates/`, `docs/troubleshooting/` (all twelve
new refusal reasons, each with a deterministic remedy), `docs/dry-runs/`,
`docs/tutorials/`.

**The ordinal sweep covers the whole surface, including the three places the
engine-driven pass did not reach.** Inserting `gate_architecture` at GREENFIELD
position 2 moves `gate_implement` from Gate 7 to Gate 8 and `checklist_draft`
from Phase 8 to Phase 10, so a final sweep was run over `.claude/hooks/hooks.py`
(the secrets tripwire's `systemMessage`), `.claude/commands/` (`sdle-approve.md`)
and `scripts/sdle.py`'s `argparse` help strings. All three now name the phase
or gate **key** rather than its ordinal — `gate_implement`, `checklist_draft` —
which is what the engine matches on and what cannot go stale again. The one
test that asserted on the old wording (`test_hooks.py`'s secrets context) was
updated with it. `templates/state.json` also still carried a literal
`"progress": "1/18"`; it is cosmetic (`init` overwrites it from the bound flow
at `sdle.py:1751`) but wrong, and is now `1/20`.

ADR-001 … ADR-012 keep their original ordinals deliberately. ADR-013 carries a
short section saying so, and why: an ADR records a decision as it was made, and
back-dating its numbers would put the record at odds with the commit it
describes.

## 11. Review findings accepted

**Forty-four across two rounds; all accepted, none rejected.**

**Round 1** — 22 findings, one CRITICAL, four HIGH. The CRITICAL was a catalog
mutation reachable with no human decision behind it (`architecture realize`
was ungated); the HIGHs were an envelope field read from the wrong object, a
catalog write placed after the first audit append, an unfiltered capability
sweep that reached across WorkItems, and three silent no-ops where a refusal
belonged. See [`REVIEW-ROUND-1.md`](REVIEW-ROUND-1.md).

**Round 2** — 22 findings, one CRITICAL, three HIGH, and a verification pass
over every Round-1 disposition: 15 landed, 3 were incomplete, 1 was
half-amended in the contract, 2 recurred as new instances of the same class,
and **1 had regressed**. That regression is the finding worth naming: the
Round-1 fix guarded re-assessment on the *presence* of an approvals entry
rather than on its *decision*, and `gate reject` writes a truthy one — so a
rejected architecture gate became a dead end, closing the only documented
exit `ARCHITECTURE_REVIEW_REQUIRED` has. It is exactly what a second round
exists to catch, and no test covered it. There is one now. The Round-2 HIGHs
were the sibling drift door (`drift rebaseline` unguarded where
`gate approve` was guarded) and two documentation sets that contradicted
themselves on the same page. See [`REVIEW-ROUND-2.md`](REVIEW-ROUND-2.md).

## 12. Review findings rejected

**None.** [`claude-review-rejections.md`](../../../claude-review-rejections.md)
records that explicitly, and notes the two findings where "accept" involved a
choice about *how*.

## 13. Verification

Per the operator's instruction on 2026-09-28 — *"stop the tests altogether …
will run the full test at the end only via ci/cd"* — the full suite is **not**
run in this session; CI runs `pytest -q` and `lint-skill` on `ubuntu-latest`
and `windows-latest`. What was executed locally, verbatim:

```
$ python scripts/sdle.py lint-skill
… 47 checks, all [PASS], 0 FAIL, exit 0

$ python -m pytest -q tests/test_units_architecture.py
58 passed   (after the round-2 fixes)

$ python -m pytest -q tests/test_dry_run_contracts.py
186 passed   (146 before the round-2 prose checks were added)

$ python -m pytest -q tests/test_units_gate_policy.py tests/test_units_governance.py       tests/test_units_architecture.py
629 passed, 1 failed  → the one failure was a stale test fixture, fixed and
                        re-run green

$ python -m pytest -q tests/test_units_invariants.py
9 passed in 1.70s

$ python -m pytest -q tests/test_units_capabilities.py tests/test_lint_skill.py \
      tests/test_units_state.py tests/test_units_transitions.py
300 passed  (after the round-1 re-run: all green)

$ python smoke_architecture.py     # end-to-end scratch repository
all smoke checks passed  (33 checks: uninitialized catalog → placement →
gate → catalog revision 1 → replay → stale → conflict → realize → abandon)
```

`lint-skill` grew from 44 checks to 47.

## 14. Remaining limitations and follow-ups

1. **The full suite has not been run to completion on this branch.** The
   precise split, module by module, because "verified in batches" is not
   something a reader can act on:

   **Re-run green in this session** — `test_units_architecture.py`,
   `test_dry_run_contracts.py`, `test_units_invariants.py`,
   `test_units_capabilities.py`, `test_lint_skill.py`, `test_units_state.py`,
   `test_units_transitions.py`, `test_units_gate_policy.py`,
   `test_units_governance.py`, `test_units_flow_model.py`,
   `test_integration_01_happy_path.py`, `test_integration_02_to_05.py`,
   `test_integration_06_to_09.py`, `test_integration_10_to_13.py`.

   **Partially re-run** — `test_units_repo_config.py` (the eleven selections
   the boundary change touches, not the module) and `test_hooks.py` (the
   eighteen `-k secrets` tests, after the `gate_implement` wording change in
   `hooks.py`; the rest of the module did not run).

   **Not re-run at all** — `test_units_speckit_binding.py`,
   `test_units_hardening.py`, `test_units_manifest_changes.py`,
   `test_units_implementation_evidence.py`, `test_units_doc_links.py`,
   `test_units_documented_commands.py`, `test_units_retired_names.py`,
   `test_units_shipped_surface.py`, `test_units_workitem_resolution.py`,
   `test_units_discovery.py`, `test_units_artifact_review.py`,
   `test_units_gate_artifacts.py`, `test_units_execution_identity.py`,
   `test_units_cli.py`, `test_units_infra.py`,
   `test_units_install_contract.py`, `test_units_policy_midflight.py`,
   `test_units_workitem.py`, `test_units_workitem_runtime.py`,
   `test_units_baseline.py`.

   Any of those twenty may still carry a stale GREENFIELD ordinal, a `/18`
   denominator, or an `advance` that steps straight from a constitution
   approval to `spec_draft`. The four repair shapes are written up in
   [`PROGRESS.md`](PROGRESS.md) under "Test-module repair log"; applying them
   is mechanical. **CI is the gate; treat a red CI run as expected work, not
   as a surprise.**
2. **A third round is warranted.** §8.3 permits one when Round 2 produces an
   accepted CRITICAL, and it did (R2-001). Round 2's own "areas not reached"
   list names `tests/conftest.py`, the five integration drivers and six test
   modules whose diffs it did not read.
3. **The `main` baseline is synthetic.** The checkout was a zip snapshot, not
   a clone; `git init` created the baseline the diff is measured against.
4. **`docs/enhancements/` is not in the lint-enforced documentation set** —
   deliberately: that set is the shipped product's derived views, and this
   directory is an execution record.
5. Part 10's non-goals stand untouched: no SRS decomposition, no enterprise
   architecture repository, no automatic extraction engine, no contract
   generation.
