# T07 Plan — Replace Fixed Universal Sequence with Declarative Flow Selection

**Phase:** T07
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED
**Revision:** 2 — supersedes the plan committed at `7dba4b6`, in response to a material user decision (see *Decision inputs*). Revision 1 is preserved in Git at `7dba4b6` and is not deleted.
**Contract sections:** §13 (the phase), §5 (overview row), §18 (`fixed 18 phases | REPLACE T07`), §24.2 (this stage)
**Precondition HEAD:** `7dba4b6` on `transition/workitem-v1`
**Rollback point:** `7dba4b6`
**SDLE product baseline:** `f8fdaa0`

> **The planner wrote no product code and edited no test.** Every figure below was
> produced by a command run in this planning context and is classed `OBSERVED`.
> Where a fact was not established here it says `UNKNOWN` and no outcome is predicted.

---

## Decision inputs (human-owned, recorded so a verifier can see the provenance)

Revision 1 resolved §13's `DEFECT_FIX` sketch — *"Defect -> Impact analysis -> existing
spec mapping -> spec delta/gap -> targeted plan/tasks -> implement -> validate -> review"* —
by mapping every sketch name onto an existing phase, under a self-imposed
*"no new phases, no reordering"* constraint.

**The user reviewed revision 1 and made a material decision:**

> **Impact analysis must exist as a real step: add a new, GATELESS phase
> `impact_analysis`, placed early in registry order, present in `DEFECT_FIX`
> and `HOTFIX` only.**
>
> Everything else in revision 1 was explicitly approved — *"Rest is fine."*

Rationale the user accepted, recorded here because it constrains the design:

| # | Reason | Class |
|---|---|---|
| DI-1 | The *"no reordering"* blocker applies to **existing** phases only. `analyze` cannot precede `tasks_draft` because `ARTIFACT_OWNERSHIP` binds `gate_analyze` to `{speckit_feature_directory}/tasks.md` (E21). **A new phase carries no such binding**, so it can sit early in registry order and deliver §13's actual intent — impact analysis *before* the spec — instead of a compromise. | INFERRED from E21 |
| DI-2 | **Gateless keeps it cheap.** `checklist_draft` is the existing precedent: a real registry phase producing a real artifact with no gate (E22, E37). No ninth `approvals` key means **no `approvals` schema change, no extra version bump, no extra migration row**, and it avoids baking "8 gates" differently into `gate-protocol.md`, `docs/SDLE-Reference-Guide.md` (E39 names four sites) and `docs/dry-runs/01-happy-path.md`, and avoids gate numbering 1–8 becoming flow-relative in prose. | INFERRED from E22/E37/E39 |
| DI-3 | **`GREENFIELD`'s traversal must not change.** All nine dry-runs stay valid and byte-identical, and the `N/18` denominators stay correct for GREENFIELD. | user decision |

Scope discipline the user also set, and this revision holds to it:

- §13's other unimplemented sketch names — *existing spec mapping*, *spec delta/gap*,
  *Converge*, *Human Review* — **stay mapped onto existing phases exactly as
  revision 1 mapped them.** The user approved that mapping. This revision does
  not expand scope beyond impact analysis.
- Every other element of revision 1 stands and is carried forward verbatim in
  substance: no linter check weakened; `no_hardcoded_progress` generalised to
  every flow denominator; all nine dry-runs valid and byte-identical with no new
  transcripts authored; §13's legacy-structure removal deliberately **not**
  performed (T11 owns it per §17); flows as ordered subsets otherwise; the single
  permitted `conftest.py` edit; one deliberate red window; `cmd_init`'s traversal
  staying outside `apply_advance`.

---

## Objective

Retire the assumption that every WorkItem traverses the same phase list.

Introduce a **phase registry** and a **declarative flow table**, bind exactly one
flow per WorkItem, and make every traversal decision read that flow — **without**
weakening a single deterministic guarantee and **without** building a generic
workflow engine.

§13's exit criterion, restated as the thing that must be demonstrable:

> Flow selection changes which phases execute without compromising
> deterministic state transitions.

Two things T07 deliberately does **not** do, both because §13 and §17 say so:

1. **It does not delete the old fixed tables.** `PHASE_SEQUENCE`, `NEXT_PHASE`,
   `PHASE_LABEL_MAP`, `PROGRESS_MAP` and `PHASE_TO_GATE_KEY` all remain and all
   remain linted. §17 assigns their removal to T11.
2. **It does not make gates conditional on risk.** That is T09. T07 changes which
   *phases* are in a flow; T09 changes which *gates* a risk level requires. The
   boundary is enforced by two tests that already exist and must stay green
   untouched (A11).

---

## Repository evidence

Every row was checked in this context at `7dba4b6` unless stated otherwise.
Citations are by symbol or greppable anchor, never by bare line number.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `7dba4b6`; tree clean apart from `.claude/settings.local.json` | OBSERVED | `git rev-parse HEAD` = `7dba4b6a19021cb61ea5db389a42b09ba68176b4`; `git status --porcelain` = one line, ` M .claude/settings.local.json` |
| E2 | Full suite is green | OBSERVED | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **`791 passed in 1305.96s (0:21:45)`, RAW EXIT 0**; `grep -c "short test summary"` over the captured run = **0**, so zero skips, xfails and errors |
| E3 | Collected == passed | OBSERVED | `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` → **`791 tests collected in 0.62s`**, raw exit 0 |
| E4 | `lint-skill` is clean at 22 checks, v1.15 | OBSERVED | `python scripts/sdle.py --project-root . lint-skill` raw exit **0**; 22 `[PASS]` lines, 0 `[FAIL]`; `"failed": []`; `tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows.`; `version_string_consistent: all four locations report v1.15` |
| E5 | Transition control plane is valid and T07 is next | OBSERVED | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=7/12 next=T07`, raw exit **0** |
| E6 | `7dba4b6` is revision 1 of this plan and touched no product file | OBSERVED | `git log --oneline -8` → `7dba4b6 Plan T07 declarative flow selection` on top of `c0775b3 Close NB-6: no audit entry survives a refused skip` |
| E7 | Host Python is 3.13.0; Python 3.11 and CI have never run | OBSERVED / UNKNOWN | `python --version` → `Python 3.13.0`; branch is local-only. **No CI outcome is predicted.** |
| E8 | Disk has headroom | OBSERVED | `df -h .` → `D: 400G, 21G avail`. No `os error 112` was seen in this context. |
| E9 | The parsed constant tables live under these headings in `SKILL.md`: `PHASE_SEQUENCE (ordered)`, `NEXT_PHASE`, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`, `VERSION_MIGRATION`; `GATE_TO_EXECUTION_PHASE` lives in `modules/gate-protocol.md` | OBSERVED | `grep -n '^###' .claude/skills/sdle/SKILL.md` returns exactly those seven headings plus `### The script is the authority`; `load_constants` reads `paths.gate_protocol_md` for the eighth table |
| E10 | `GATE_PHASES` is derived by **filtering an explicitly declared set**, not by taking the registry wholesale | OBSERVED | `Constants.gate_phases`: `[p for p in self.phase_sequence if p in self.phase_to_gate_key]`. The `in` test is against `PHASE_TO_GATE_KEY`, a complete per-gate declaration. Adding a `PHASE_SEQUENCE` row does **not** add a gate. |
| E11 | The linter today enforces one linear chain over the whole phase set | OBSERVED | `run_sync_checks` → `phase_set_matches_{next_phase,phase_label_map,progress_map}`, `next_phase_chains_sequence`, `progress_denominator_matches_phase_count` |
| E12 | `apply_advance` is the single traversal choke point with a closed three-member caller set | OBSERVED | `tests/test_units_governance.py` asserts `callers == ["apply_advance", "cmd_gate_approve", "cmd_skip"]` and `movers == ["cmd_advance", "cmd_gate_approve", "cmd_skip"]` |
| E13 | `cmd_init` moves a phase **without** `apply_advance`, reading the registry chain directly | OBSERVED | `cmd_init` body contains `nxt = consts.next_phase["requirements_check"]` and two `consts.progress_for(...)` writes |
| E14 | `consts.next_phase` is read by exactly six engine functions plus the linter and the dump | OBSERVED | AST walk over `scripts/sdle.py` mapping every `next_phase` occurrence to its enclosing function: `cmd_init`, `apply_advance`, `cmd_gate_approve` (×2), `cmd_skip`, `cmd_doctor`, `run_sync_checks` (×2), `cmd_constants`; `load_constants` writes it |
| E15 | `progress_for` has five call sites and `gate_number` four consumers, all mapped to their enclosing function by AST in this context | OBSERVED | `progress_for` → `cmd_init` (×2), `apply_advance`, `_approve_drift`, `cmd_restart`. `gate_number` → written by `load_constants` (×2); read by `cmd_gate_show`, `cmd_gate_approve`, `cmd_gate_reject`, `cmd_constants`. Both sets are small and closed. |
| E16 | T06 records the engineering flow and marks it advisory | OBSERVED | `evaluate_classification` returns `{"type": ..., "flow": ..., "advisory": True}` with the docstring "ADVISORY: nothing in the engine routes on either value at T06"; `ENGINEERING_FLOWS` is the closed five-member tuple `("GREENFIELD", "BROWNFIELD_DISCOVERY", "ITERATIVE", "DEFECT_FIX", "HOTFIX")` |
| E17 | The would-be gate set is inert and two tests pin that | OBSERVED | `test_no_phase_movement_function_consults_the_would_be_gate_set` and `test_the_phase_movement_prefixes_actually_match_something` in `tests/test_units_governance.py` |
| E18 | The shared test fixture records `flow: "ITERATIVE"` today | OBSERVED | `tests/conftest.py`, `Project.record_governance`, literal `"classification": {"type": "enhancement", "flow": "ITERATIVE"}` |
| E19 | T06 shipped a differential test asserting classification changes **no** traversal | OBSERVED | `test_governance_changes_no_lifecycle_behaviour`; `GOVERNANCE_VARIANTS` carries `DEFECT_FIX`, `ITERATIVE`, `HOTFIX`; the loop asserts `traversal == EXPECTED_TRAVERSAL` for all four variants |
| E20 | `EXPECTED_TRAVERSAL` is a frozen 19-element list **element-wise identical to today's `PHASE_SEQUENCE`**, owned by the dry-run 01 integration test and imported by the governance suite | OBSERVED | `tests/test_integration_01_happy_path.py`, `EXPECTED_TRAVERSAL = [...]`; `tests/test_units_governance.py` line beginning `from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path` |
| E21 | `gate_analyze`'s artifact is `tasks.md`, the same file `gate_tasks` owns | OBSERVED | `### ARTIFACT_OWNERSHIP` maps both `gate_tasks` and `gate_analyze` to `{speckit_feature_directory}/tasks.md`; the `analyze` block runs `drift rebaseline --gate gate_tasks` for exactly this reason |
| E22 | The checklist is already optional and its phase is gateless | OBSERVED | `checklist_draft` appears in `PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_LABEL_MAP` and `PROGRESS_MAP` and in **neither** `PHASE_TO_GATE_KEY` **nor** `ARTIFACT_OWNERSHIP`; its `phase-execution.md` block says "If checklist.md was **not produced** … Do **not** set status to 'failed'. Do not halt." |
| E23 | `ARTIFACT_OWNERSHIP` is keyed by **gate key**, and the registration check iterates gate phases only | OBSERVED | `### ARTIFACT_OWNERSHIP` header row is `gate_key`; `run_sync_checks` loops `for gate_phase in consts.gate_phases:` before testing `ARTIFACT_OWNERSHIP` / `GATE_TO_EXECUTION_PHASE` / template `approvals` |
| E24 | `artifact record` works for **any** phase and needs no gate | OBSERVED | `cmd_artifact_record` takes `--phase`/`--path`, falls back to `state["current_phase"]`, fingerprints, writes `current_artifact`/`current_artifact_sha`, appends `artifact_recorded`, and has an `--optional` branch the checklist uses |
| E25 | T06's artifact review is **path-keyed**, not gate-keyed | OBSERVED | `cmd_artifact_review` validates `--result`/`--actor-type`/`--actor-name`/`--type` and keys on `review_key(paths, args.path)`; `cmd_artifact_reviews` lists by `path` |
| E26 | `workitems/` is inside the write fence; only `workitems/<id>/specs/` is carved out — and a `reviews/` directory **under a WorkItem is already proven fenced** | OBSERVED | `.claude/hooks/hooks.py`: `FENCED = (".workflow", "workitems", "requirements", "guidance")` and `SPECS_CARVE_OUT = re.compile(r"(?:^\|/)workitems/[^/]+/specs/")` with the reason string "Nothing else under workitems/ is exempt". `pytest --collect-only` shows an existing denial case `test_write_fence_denies_governance_files[/proj/workitems/wi-a/reviews/security-review-2026-01-01-0900.md]`. The project-root `reviews/` is **not** fenced, which is why `security_review` writes there today. |
| E27 | `security_review` is the precedent for a Claude-written, project-root-relative, timestamped analysis document | OBSERVED | `phase-execution.md` Phase 17: `review_filename = "reviews/security-review-<YYYY-MM-DD-HHmm>.md"`, written by Claude, then fingerprinted by Post-SpecKit Verification |
| E28 | `spec_draft` is where the Spec Kit feature directory comes into existence, and every later generation phase requires it | OBSERVED | Phase 4 block: "**Feature-Directory Resolution (MANDATORY after spec runs):** `sdle.sh feature resolve`"; Phases 6, 8, 9, 11, 15 each call `sdle.sh feature bind --require-feature`, which "additionally refuses when no feature directory is recorded" |
| E29 | Gate ordinals are restated in **three** places besides `PHASE_TO_GATE_KEY` | OBSERVED | `PHASE_LABEL_MAP` values `Gate 1: …` … `Gate 8: …`; `phase-execution.md` gate blocks `(Gate 1/8)` … `(Gate 8/8)`; `gate-protocol.md` `✋ APPROVAL REQUIRED — Gate {gate_number}/8: {Gate Label}` and `Gate 8/8 (security) approved` and `All 8 gates passed` |
| E30 | `phase-execution.md` block headers restate the phase ordinal, and the linter captures only the **id** from them | OBSERVED | `grep -n '^\*\*Phase ' modules/phase-execution.md` → 17 headers `**Phase 2 — \`constitution_draft\`:**` … `**Phase 18 — \`gate_security\`:**`; `run_sync_checks` uses `re.findall(r"^\*\*Phase \d+ — \`([a-z_]+)\`", …)` and asserts nothing about the number |
| E31 | "Phase N" is used as a cross-reference identifier in prompt files, **including `modules/security-review.md`** | OBSERVED | `grep -rn 'Phase [0-9]' .claude/` → `SKILL.md` "Phase 13 precedes Phase 15", `gate-protocol.md` "(Phase 13 in `modules/phase-execution.md`)" and "Re-execute Phase …", `security-review.md` "Phase 17 in `modules/phase-execution.md` pre-computes …" and "the pre-computed path from Pha…" |
| E32 | `compute_drift` and `cmd_repo_staleness` skip anything unapproved or unresolvable | OBSERVED | `compute_drift` `continue`s on a non-`approved` decision and on a missing baseline; `cmd_repo_staleness` `continue`s when `resolve_artifact_path` returns nothing |
| E33 | `.claude/hooks/hooks.py` names exactly one phase, `implement` | OBSERVED | the only phase literal in that file is `state.get("current_phase") != "implement"` |
| E34 | No prompt file contains a `N/10`, `N/14` or `N/16` string today | OBSERVED | `grep -nE '[0-9]+/(10\|14\|16)'` over `SKILL.md`, `phase-execution.md`, `gate-protocol.md`, `security-review.md` → **exit 1, no matches**. The same files yield **21** matches for `[0-9]+/18` in `SKILL.md` alone. |
| E35 | `parse_md_table` refuses rather than defaulting; `_normalise_cell` strips exactly **one** outer backtick pair | OBSERVED | `parse_md_table` raises `constants_unreadable` / `constants_heading_missing` / `constants_malformed` / `constants_empty`; `_normalise_cell` tests `value.startswith(...)` and `value.endswith(...)` against a single backtick and then does `value = value[1:-1]` — **one** pair, not repeated |
| E36 | The state template has no `flow` field, `progress` is the literal `"1/18"`, `approvals` has exactly eight keys, and `CURRENT_VERSION` is `1.15` | OBSERVED | `.claude/skills/sdle/templates/state.json`; `grep -n 'CURRENT_VERSION\s*=' scripts/sdle.py` |
| E37 | `checklist_draft` has a `phase-execution.md` block, a `PHASE_LABEL_MAP` label, a `PROGRESS_MAP` value and a Guidance File Map row, and needs no gate machinery at all | OBSERVED | as E22 plus `### Guidance File Map` row `\| \`checklist_draft\` \| \`guidance/checklist.md\` \|` |
| E38 | `tests/test_lint_skill.py` asserts no check **count**; it asserts `failed == []`, `len(checks) > 15`, and one firing test per rule via `assert_only_failure`, which requires that **exactly one** check fails | OBSERVED | `test_the_repo_passes_every_check`; `assert_only_failure` body asserts `not others` |
| E39 | The "8 gates" / "18 phases" prose sites | OBSERVED | `README.md` headline `**18 phases · 8 approval gates …**`, `## 18-Phase Workflow` fenced block, `**8 approval gates total.**`, history row; `docs/SDLE-Reference-Guide.md` line 7 covers-version row, `## 7. The 18-Phase Workflow — Detailed Reference`, glossary "There are 8 gates, numbered 1–8", completion-summary paragraph; `CLAUDE.md` "gated 18-phase SDLC workflow"; `docs/dry-runs/README.md` and `docs/dry-runs/01-happy-path.md` |
| E40 | `README.md`'s phase block and the Reference Guide's §7 use GREENFIELD phase ordinals as section keys | OBSERVED | `README.md` fenced block `Phase  1 … Phase 18`; `docs/SDLE-Reference-Guide.md` `### Phase 8 — Generate Checklist (\`checklist_draft\`)` |
| E41 | `_check_doc_phase_tables` only requires each phase **name** to appear somewhere in the document | OBSERVED | `missing = [phase for phase in consts.phase_sequence if phase != "complete" and f"\`{phase}\`" not in text and phase not in text]` |
| E42 | `.claude/commands/sdle-restart.md` restates a constant in its argument hint | OBSERVED | `argument-hint: "<phase number 1-18>"`; the other four commands' hints contain no lifecycle constant |
| E43 | `write_completion_summary` counts `phase_history` and hardcodes `all_gates_approved: True` | OBSERVED | `write_completion_summary` body |
| E44 | Only three ADRs exist; `ADR-004-*` is free | OBSERVED | `ls docs/architecture/` → `ADR-001-deterministic-core.md`, `ADR-002-repository-configuration-boundary.md`, `ADR-003-governance-inputs-and-artifact-review.md` |
| E45 | The F1 `ENVIRONMENT_FLAKE` procedure is void | OBSERVED / INFERRED | E2 shows a fully green suite; `6e8af8c` fixed the `write_atomic` `WinError 5` flake. **Any T07 failure is a presumed real regression.** |

**Refusals encountered by the planner.** None. Every command run in this context
was observational and the transition guard refused nothing. Had it refused, the
refusal text would be quoted verbatim here and not routed around.

---

## Behavioral delta

### Deliberate changes

**D0 — `PHASE_SEQUENCE` becomes the phase registry, and the registry stops being
any flow.**

`PHASE_SEQUENCE` is the closed catalogue of the phases SDLE knows how to execute,
in canonical order. A *flow* is an ordered subset of the registry, preserving
registry order. After T07 the registry has **20** entries; **no flow has all 20**.

This is the single fact from which every other change in this revision follows,
and it is the fact revision 1 did not have to face.

**D1 — The new phase: `impact_analysis`, gateless, registry position 2.**

| Property | Value | Why |
|---|---|---|
| id | `impact_analysis` | §13's DEFECT_FIX sketch step 2, "Impact analysis" |
| `PHASE_SEQUENCE` position | **2**, immediately after `requirements_check` and before `constitution_draft` | §13's sketch orders it `Defect -> Impact analysis -> …`, i.e. straight after the requirement is understood and before any baseline or spec work. It satisfies the user's constraint that it precede `spec_draft`, and it is the position at which every downstream phase can consume it. |
| Gate | **none** | DI-2. `checklist_draft` is the precedent (E22). |
| `PHASE_TO_GATE_KEY` row | **none** | it is not a gate |
| `ARTIFACT_OWNERSHIP` row | **none** | that table is keyed by gate key and the registration check iterates `consts.gate_phases` only (E23). A gateless phase is never examined by `gate_registered_*`. |
| `GATE_TO_EXECUTION_PHASE` row | **none** | same reason |
| `templates/state.json` `approvals` key | **none** | the `approvals` object keeps exactly its eight keys (E36). **No `approvals` schema change.** |
| `PHASE_LABEL_MAP` row | `Impact Analysis` | `phase_set_matches_phase_label_map` covers the registry; `Constants.label()` must resolve it when it is the current phase |
| `PROGRESS_MAP` row | **none** — see D7 | `PROGRESS_MAP` becomes explicitly the GREENFIELD view, and `impact_analysis` is not in GREENFIELD |
| `NEXT_PHASE` rows | `requirements_check -> impact_analysis` (edited) and `impact_analysis -> constitution_draft` (new) | `next_phase_chains_sequence` is left **unchanged** and continues to prove the registry is one linear canonical order. `NEXT_PHASE` is no longer any flow's chain — see D11. |
| `phase-execution.md` block | new, with **no** ordinal in its header — see D8 | E30/E31 |
| Guidance File Map row | **none** | that map is scoped to "before invoking SpecKit"; this phase invokes no Spec Kit skill |
| Flows containing it | `DEFECT_FIX`, `HOTFIX` only | user decision |

**D2 — What `impact_analysis` produces, and how it is governed without a gate.**

Artifact: **`reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md`**, written by Claude,
then fingerprinted by the engine.

Why that path, with the alternatives and the evidence that rules them out:

- `{state.specKit.featureDirectory}/…` is **impossible**: the feature directory does
  not exist until `spec_draft` runs (E28), and this phase runs before it. For the
  same reason the block must **not** call `feature bind --require-feature` — it
  would refuse — and must not reference `{state.specKit.featureDirectory}`.
- `workitems/<id>/…` is **refused by the write fence**: `workitems` is `FENCED`
  and only `workitems/<id>/specs/` is carved out (E26). Putting the artifact
  there would require editing `.claude/hooks/hooks.py`, which is on T07's
  must-not-change list and is out of scope.
- `reviews/` is the **exact `security_review` precedent** (E27): a Claude-written,
  project-root-relative, timestamped analysis document, outside the fence,
  already gitignored, needing no `.gitignore` change, no hooks change and no new
  path plumbing.

Governance without a gate — this is what "gateless does not mean ungoverned" means
mechanically, and every step uses machinery that already exists:

1. **Fingerprinted.** `sdle.sh artifact record --phase impact_analysis --path <file>`
   (E24) — size floor, SHA-256, `artifact_recorded` audit event, retry counter reset.
2. **Reviewed (TP-011).** `sdle.sh artifact review --path <file> --type impact-analysis
   --result PASS --actor-type agent --actor-name sdle-orchestrator` (E25). The review
   is path-keyed and bound to the exact SHA, so TP-011 clauses 1–8 are satisfied
   with **zero** new code. A later edit to the file makes the review stale by the
   existing mechanism.
3. **Shown to the human.** Under `DEFECT_FIX` and `HOTFIX`, before presenting
   `gate_spec`, the orchestrator displays the impact analysis content in
   conversation — the same pattern the `tasks_draft` block already uses to display
   `checklist.md` before Gate 4. Invariant 4 is therefore honoured: the human sees
   the artifact before approving the first gate downstream of it.

**No state field is added for the path.** `security_review_artifact` exists only
because `ARTIFACT_OWNERSHIP` substitutes `{security_review_artifact}` for a gate.
A gateless phase needs no resolution, so `current_artifact` / `current_artifact_sha`
— which `artifact record` already writes — are sufficient. This is the concrete
saving DI-2 predicted.

**D3 — `GREENFIELD` is no longer derived from the registry. This is the coupling
this revision exists to resolve.**

Revision 1 derived `GREENFIELD` from `PHASE_SEQUENCE`, following the `GATE_PHASES`
precedent, so that §13's required compatibility translation was true by
construction. **Adding any registry entry silently adds it to GREENFIELD**, which
would break exactly the property that derivation protected.

*Read correctly, the `GATE_PHASES` precedent argues against the derivation.*
`GATE_PHASES` filters the registry **through an explicitly declared set**,
`PHASE_TO_GATE_KEY` (E10): adding a `PHASE_SEQUENCE` row does not add a gate,
because gate-ness is declared per gate, not inherited from the registry.
Deriving `GREENFIELD` as *all of* `PHASE_SEQUENCE` has the opposite property — it
unions in anything new. The two are not the same construction, and only the first
is safe once the registry stops being GREENFIELD.

**Chosen: pin `GREENFIELD`'s membership explicitly, in one place, and prove that
place still equals the pre-T07 `PHASE_SEQUENCE`.**

```
GREENFIELD_V1_PHASES : tuple[str, ...]   # scripts/sdle.py, frozen
  requirements_check  constitution_draft  gate_constitution
  spec_draft  gate_spec  plan_draft  gate_plan
  checklist_draft  tasks_draft  gate_tasks  analyze  gate_analyze
  design_generation  gate_design  implement  gate_implement
  security_review  gate_security  complete          # 19 entries
```

- It is **GREENFIELD's only home.** `GREENFIELD` is deliberately **not** a row in
  `FLOW_PHASES`. `Constants.flows` injects it from this constant and then
  validates it through the *same* rules as every declared flow. Invariant 7 holds:
  one fact, one place.
- `FLOW_PHASES` carries a note in the same style as the existing `GATE_PHASES`
  note under `PHASE_TO_GATE_KEY` (E9/E10), telling the reader that GREENFIELD is
  the frozen v1 list held by the engine and that `sdle.sh constants` is how to see it.
- Placing it in `scripts/sdle.py` rather than `SKILL.md` is consistent with
  `MANDATORY_FLOW_PHASES` (D6) and with §18's row *"lifecycle constants in
  `SKILL.md` — MIGRATE only after T07/T09 stable"*: the engine owns the frozen
  baseline and the floors; `SKILL.md` owns the editable declarations.

**The compatibility translation is provable four independent ways, none of which a
registry edit can move:**

| # | Proof | Why it cannot drift |
|---|---|---|
| P1 | `GREENFIELD_V1_PHASES == EXPECTED_TRAVERSAL`, asserted by a test that imports the list from `tests/test_integration_01_happy_path.py` | `EXPECTED_TRAVERSAL` is element-wise identical to today's `PHASE_SEQUENCE` (E20) **and** A6 requires that file byte-identical to `7dba4b6`. Changing the engine constant would force an edit to a file the acceptance criteria freeze. |
| P2 | A golden literal in `tests/test_units_flow_model.py` spelling out all 19 ids, compared to `GREENFIELD_V1_PHASES` | An independent second witness in a file the verifier reads |
| P3 | Verifier-runnable: `git show 7dba4b6:.claude/skills/sdle/SKILL.md` parsed for `PHASE_SEQUENCE`, compared element-wise to `constants.flows.GREENFIELD` at the T07 head | Compares against Git history, not against anything the implementer wrote |
| P4 | `_mig_1_15` sets `flow: "GREENFIELD"` unconditionally (D9), so every pre-v1.16 state is *named* GREENFIELD, and P1–P3 fix what that name *means* | The migration never consults the governance record |

**What replaces the lost derivation guarantee.** Derivation gave one thing for
free: *no registry phase can be orphaned*. That is restored, and strengthened, by
a new lint check `every_registry_phase_is_used_by_some_flow` (L5). A phase added
to the registry that no flow names now **fails `lint-skill` loudly** instead of
silently joining GREENFIELD. T08's author adding a discovery phase must name its
flows; if they want it in GREENFIELD they must edit the frozen constant, which is
a loud, reviewable, three-witness change.

**Rejected alternative — derive `GREENFIELD` as `PHASE_SEQUENCE` minus a declared
exclusion set.** It has the same failure mode one level removed: a registry
addition still joins GREENFIELD by default, and the safety depends on the author
remembering to add an exclusion. It also puts GREENFIELD's membership in two
places (the registry and the exclusion list) with the union rule implicit. The
frozen-baseline design fails closed; the exclusion design fails open.

**D4 — The five flows, by exact phase membership.**

`FLOW_PHASES`, a new table in `SKILL.md`'s Internal Constants, declares **four**
rows. `GREENFIELD` is injected from `GREENFIELD_V1_PHASES` (D3).

| Flow | Source | Phases (registry order) | Non-terminal | Gates |
|---|---|---:|---:|---:|
| `GREENFIELD` | `GREENFIELD_V1_PHASES` (engine, frozen) | the 19 pre-T07 registry entries | 18 | 8 |
| `BROWNFIELD_DISCOVERY` | `FLOW_PHASES` | identical membership to GREENFIELD, declared explicitly | 18 | 8 |
| `ITERATIVE` | `FLOW_PHASES` | GREENFIELD minus `constitution_draft`, `gate_constitution` | 16 | 7 |
| `DEFECT_FIX` | `FLOW_PHASES` | `requirements_check`, **`impact_analysis`**, `spec_draft`, `gate_spec`, `plan_draft`, `gate_plan`, `tasks_draft`, `gate_tasks`, `analyze`, `gate_analyze`, `implement`, `gate_implement`, `security_review`, `gate_security`, `complete` | 14 | 5 |
| `HOTFIX` | `FLOW_PHASES` | `requirements_check`, **`impact_analysis`**, `spec_draft`, `gate_spec`, `plan_draft`, `tasks_draft`, `implement`, `gate_implement`, `security_review`, `gate_security`, `complete` | 10 | 3 |

Rationale per flow (unchanged from revision 1 except where `impact_analysis` enters):

- **`ITERATIVE`** — §13: *"Use established repository baseline. No full repository
  rediscovery."* The constitution is the repository-level baseline artifact:
  `ARTIFACT_OWNERSHIP` maps `gate_constitution` to the static, repository-scoped
  `.specify/memory/constitution.md`, and T04 deliberately left `.specify/memory/`
  at the repository root. An iterative WorkItem inherits it. **`impact_analysis`
  is deliberately not in ITERATIVE** — the user scoped it to defect work.
- **`DEFECT_FIX`** — gains `impact_analysis` (the user's decision) and, as in
  revision 1, drops `checklist_draft` (already optional, E22) and
  `design_generation` + `gate_design` (a defect fix produces no new application or
  database design document; `design/app/app-design.md` is repository-shared and
  pre-existing). §13's remaining sketch names stay mapped as revision 1 mapped
  them: *existing spec mapping* and *spec delta/gap* onto `spec_draft` + `analyze`;
  *Converge* and *Human Review* onto `gate_security`, the terminal human gate that
  writes the completion summary.
- **`HOTFIX`** — §13: *"Shorter but never ungoverned. Mandatory risk/policy checks
  remain."* HOTFIX is the ⊆-minimum flow and is now **exactly the governance floor
  plus impact analysis** (D6).
- **`BROWNFIELD_DISCOVERY`** — declared with GREENFIELD's membership at T07 and
  **owned by T08** (§14). Declaring it now means the flow is selectable and bound,
  and T08's change to its row is a one-line, visible, lint-checked diff. A test
  pins the current equality so the T08 change cannot happen silently.

**Table format decision, from evidence.** `FLOW_PHASES` uses one row per flow with
a **space-separated, un-backticked** phase list:

```
### FLOW_PHASES
| flow | phases (registry order, space separated) |
|---|---|
| `HOTFIX` | requirements_check impact_analysis spec_draft gate_spec plan_draft tasks_draft implement gate_implement security_review gate_security complete |
```

`_normalise_cell` strips exactly **one** outer backtick pair (E35), so a cell of
individually backticked ids would be mangled into `` a`, `b ``. Un-backticked
avoids that entirely. A future editor who backticks the cell anyway does not fail
open: the ids become unrecognised and `every_flow_is_an_ordered_subset_of_the_registry`
(L2) fires. The flow-name cell keeps its backticks, as every other table does.

**D5 — Where the registry order shows through, and where it deliberately does not.**

Inserting a phase at registry position 2 shifts the registry index of everything
after it by one. Three things depend on an ordinal, and each is resolved
explicitly:

| Ordinal restated in | After T07 | Consequence |
|---|---|---|
| `PROGRESS_MAP` values `N/18` | **unchanged**, and re-documented as *the GREENFIELD view*. Runtime progress becomes flow-derived (D7). | zero diff to 19 rows; nine dry-runs stay byte-correct |
| `PHASE_LABEL_MAP` gate labels `Gate 1: …` … `Gate 8: …` | the literal ordinal is replaced by a `{gate_number}` placeholder, substituted at render time with the gate's number **in the bound flow** (D7) | GREENFIELD renders byte-identically; `DEFECT_FIX` renders `Gate 1: Specification Approval` for `gate_spec` instead of a stale `Gate 2:` |
| `phase-execution.md` block headers `**Phase N — \`id\`:**` | **unchanged for all 17 existing blocks**; the new block carries no ordinal (D8) | no renumbering, so the "Phase N" cross-references in `SKILL.md`, `gate-protocol.md` and the must-not-change `modules/security-review.md` (E31) all stay correct |

Renumbering the block headers to registry indices was considered and **rejected**:
E31 shows `modules/security-review.md` cross-references "Phase 17", and that file
is on T07's must-not-change list. Renumbering would drag an unrelated file into
the diff for no behavioural gain.

**D6 — `MANDATORY_FLOW_PHASES`, and what the HOTFIX identity becomes.**

A closed set, defined once in `scripts/sdle.py`, enforced by `lint-skill` **and**
by `Constants.flow()`:

```
requirements_check  spec_draft  gate_spec  plan_draft  tasks_draft
implement  gate_implement  security_review  gate_security  complete      # 10
```

Each membership has a named reason (unchanged from revision 1):

| Phase | Why it can never be dropped |
|---|---|
| `requirements_check` | Bootstrap. `cmd_init` writes it as the first phase unconditionally. |
| `spec_draft` | The only phase that creates the Spec Kit feature directory (E28). Without it every later `feature bind --require-feature` refuses. |
| `gate_spec` | The first human gate. A flow with no gate before implementation would be ungoverned. |
| `plan_draft` | `speckit-tasks` derives from `plan.md`. |
| `tasks_draft` | `speckit-implement` derives from `tasks.md`; `gate_tasks`/`gate_analyze` own it. |
| `implement` + `gate_implement` | The implementation manifest carries the secrets scan and the test evidence. §15's preserve list names both; §28 forbids removing a safety control because new requirements did not repeat it. |
| `security_review` + `gate_security` | §15's preserve list; the terminal human gate; the completion summary is written here. |
| `complete` | Terminal. |

**`impact_analysis` is deliberately NOT added to `MANDATORY_FLOW_PHASES`** — doing
so would force it into GREENFIELD and ITERATIVE, contradicting the user's decision.

Revision 1's identity `HOTFIX == MANDATORY_FLOW_PHASES` therefore becomes:

```
set(HOTFIX) - {"impact_analysis"} == set(MANDATORY_FLOW_PHASES)     # exact equality
set(flow) >= set(MANDATORY_FLOW_PHASES)   for every flow            # the floor
HOTFIX is the subset-minimum of the five flows                      # nothing is shorter
```

All three are **exact set assertions, not subset assertions**, so `HOTFIX` cannot
silently grow a second non-mandatory phase, and §13's "shorter but never
ungoverned" stays a testable identity rather than a judgement call. Stated in one
sentence: **`HOTFIX` is the governance floor plus exactly one phase, and that
phase is the impact analysis §13 asks for.**

**D7 — Progress, gate numbering and labels become derived, per flow.**

- `progress` becomes `<position in flow>/<flow non-terminal count>`. `complete`
  maps to `<count>/<count>`. Denominators are **18 / 18 / 16 / 14 / 10** for
  GREENFIELD / BROWNFIELD_DISCOVERY / ITERATIVE / DEFECT_FIX / HOTFIX.
  For GREENFIELD this reproduces `PROGRESS_MAP` **exactly** — the M1 proof.
- `gate_number` becomes the gate's 1-based position among the flow's gate phases;
  `gate_total` becomes the flow's gate count. GREENFIELD reproduces `1..8` and `8`
  exactly. `HOTFIX` shows `Gate 2/3` where GREENFIELD shows `Gate 7/8` for
  `gate_implement`.
- `Constants.label(phase, flow=None)` substitutes `{gate_number}` in a gate label
  with the derived number, defaulting to GREENFIELD when no flow is supplied, so
  every existing caller keeps today's output byte-identical.
- `PROGRESS_MAP` and `PHASE_TO_GATE_KEY`'s `gate number` column stay in `SKILL.md`
  as the human-readable **GREENFIELD views**, and a new lint check pins them equal
  to the derived values (L4). They stop being independent sources of truth and
  become checked derived views — a strengthening of invariant 7, not a relaxation.
  Their removal belongs to T11.
- `templates/state.json`'s `"progress": "1/18"` stays as the GREENFIELD default;
  `cmd_init` overwrites it from the bound flow on its first write (E13).

**D8 — One deliberately narrow linter change, and the check that more than pays for it.**

`every_phase_has_execution_block` matches block headers with
`^\*\*Phase \d+ — \`([a-z_]+)\`` (E30). The new block cannot carry an ordinal
(D5), so the pattern becomes:

```
^\*\*Phase (?:\d+ — )?`([a-z_]+)`
```

and the new block is headed:

```
**Phase `impact_analysis` (DEFECT_FIX and HOTFIX only — no GREENFIELD position):**
```

**Stated honestly: making the ordinal optional broadens what counts as a header,
so in isolation it is a marginal loosening.** It is paid for, with interest, by a
new check `execution_block_numbers_are_the_greenfield_positions` (L7): every block
header that carries a number must equal that phase's 1-based position in
GREENFIELD, and every GREENFIELD phase's block must carry its number. Those 17
numbers are unchecked restated constants today (E30); after T07 they are
lint-pinned derived views. Net: strictly stronger for 18 of the 19 GREENFIELD
phases, and equal for `impact_analysis`.

**D9 — One new state field, `flow`, bound once and never re-bound.** *(unchanged
from revision 1)*

`state.json` gains `flow`. `workflow_version` `1.15` → **`1.16`**, with a 16th
`VERSION_MIGRATION` row and `_mig_1_15`. **The `approvals` object is untouched**
(D1), so this is one field, not two, and there is exactly one version bump.

- `_mig_1_15` sets `flow: "GREENFIELD"` unconditionally when the field is missing.
  That is the compatibility translation stated as code: **every pre-v1.16 workflow
  traversed exactly the pre-T07 `PHASE_SEQUENCE`, which is GREENFIELD** (D3/P4).
  The migration never consults the governance record — a migration must not change
  what an in-flight workflow is doing.
- `cmd_init` binds it: from the governance record's `classification.flow` when a
  record exists, otherwise `"GREENFIELD"`. Governance deliberately remains **not**
  an `init` precondition (T06's decision, unchanged), so the no-record case must
  exist and must be the safe one. `cmd_init` audits `flow_selected`.
- Nothing else ever writes it. **There is deliberately no `flow set` / `flow select`
  command** — a second writer of traversal identity would be a bypass of
  governance, and the model must not be able to reshape the lifecycle by issuing
  a command.

**D10 — `flow_mismatch`: a flow cannot change under a running workflow.**
*(unchanged from revision 1)*

`apply_advance`, immediately after `governance_precondition` succeeds, refuses when
a governance record exists and its `classification.flow` differs from `state["flow"]`:

```
reason: flow_mismatch  (exit 1)
This WorkItem is traversing <bound>; the governance record now proposes
<proposed>. A flow cannot change under a workflow that has already started.
Either re-assess with flow <bound>, or `reset workflow` and start again.
```

It refuses; it does not warn. Placement is pinned: after the existing
`forward_jump` and `gate_not_approved` refusals and after
`governance_precondition`, so no existing refusal is masked, and — critically —
**before any state mutation and before any `append_audit`**, so a refused advance
leaves `audit.md` byte-identical (B1 / NB-6, fixed at `0a9b8c7` and `c0775b3`,
must not regress). The two early pure-reader prechecks in `cmd_gate_approve` and
`cmd_skip` gain the same check, in the same position, with the same `state=None`
discipline, for exactly the reason T06 recorded: those two commands append to the
ledger before they call `apply_advance`.

**Declared consequence, not a defect:** a workflow initialised before v1.16 that
already carries a T06 governance record proposing a non-GREENFIELD flow will refuse
`flow_mismatch` at its next advance. That is correct — it *was* traversing
GREENFIELD — and the remedy is one command. Pinned by N16. Recorded for T11.

**D11 — `NEXT_PHASE` stops being any flow's chain and becomes the registry's
canonical-order proof.**

Today `NEXT_PHASE` is simultaneously the registry order and the GREENFIELD
traversal chain. After D1 the two diverge: `NEXT_PHASE["requirements_check"]`
becomes `impact_analysis`, which GREENFIELD does not have.

**This makes revision 1's "no traversal function reads `NEXT_PHASE`" a hard
correctness requirement rather than hygiene.** E14 shows six engine functions read
it today — `cmd_init`, `apply_advance`, `cmd_gate_approve`, `cmd_skip`, `cmd_doctor`
— and any one left behind would route a GREENFIELD run through `impact_analysis`.

The pin becomes a **closed reader set** rather than an enumeration of traversal
functions:

```
functions in scripts/sdle.py that read Constants.next_phase
  == {"load_constants", "run_sync_checks", "cmd_constants"}
```

`load_constants` populates it, `run_sync_checks` lints it,`cmd_constants` dumps it.
Any *new* reader anywhere in the file fails the assertion — strictly stronger than
revision 1's six-function enumeration. `next_phase_chains_sequence` is left
byte-unchanged and keeps proving the registry is one linear canonical order.

§17 lists "universal fixed 18-phase assumption" under T11's removals; that is where
the table goes. §13 forbids removing it now.

**D12 — One new read-only command, `flow show`.** *(unchanged from revision 1)*

Returns the bound flow, its ordered phases, its gate phases, the next phase from
here, and — when a governance record exists — the proposed flow and whether it
agrees. Always read-only; it is how the orchestrator asks the script instead of
reading a table, which is SKILL.md's own instruction. `constants` gains a `flows`
key for the same reason. Neither writes anything.

**D13 — Text that T07's own change makes untrue is fixed by T07.**

Revision 1's three items, unchanged:

- `record_governance_audit`'s ledger message says `classification <type>/<flow> (advisory)`.
  The flow is no longer advisory; the parenthetical becomes accurate.
- `evaluate_classification` returns `"advisory": True` and a docstring saying
  "nothing in the engine routes on either value at T06". The value flips to `False`
  and the docstring records that the **flow** now binds traversal while the **type**
  is still consumed by nothing until T09. A value change, not a shape change:
  `GOVERNANCE_RECORD_VERSION` stays `"1"`. The separate `"advisory": True` emitted
  by `cmd_governance_gates` **stays `True`** — the would-be gate set really is still
  inert. Its explanatory `note` is reworded to say that gates *within the selected
  flow* run unconditionally.
- `phase-execution.md` Phase 15 appends `"Design documents are available at
  design/app/app-design.md and (if present) design/db/db-design.md."` unconditionally.
  Under `DEFECT_FIX` and `HOTFIX` they may not exist. The sentence becomes
  conditional on the file being present.

Two items this revision adds, for the same reason — T07's own change makes them
wrong, so they are owned by T07 and are not adopted hygiene:

- `phase-execution.md`'s gate-block parentheticals `(Gate 1/8)` … `(Gate 8/8)`
  (E29) are GREENFIELD-only. They become "the gate number the script reports for
  the bound flow", consistent with D7.
- `gate-protocol.md`'s `Gate {gate_number}/8`, `Gate 8/8 (security) approved` and
  `All 8 gates passed` become flow-derived. **The stale
  `.workflow/completion-summary.json` path on that same line is left exactly as it
  is** (T11 / T04 N-6).

**D14 — `write_completion_summary` records which lifecycle was traversed.**

Adds `"flow": state["flow"]` to the summary. No existing key is removed or
changed; `all_gates_approved` keeps its meaning, now scoped to the bound flow's
gates (E43).

**D15 — Not changed, and worth stating.** `compute_drift` and `cmd_repo_staleness`
iterate the full gate set but already skip anything unapproved or unresolvable
(E32). Out-of-flow gates are never approved, so both are flow-correct with **zero**
edits. `.claude/hooks/hooks.py` names only `implement`, which is in
`MANDATORY_FLOW_PHASES` (E33), so the hooks are untouched — which is also why the
`impact_analysis` artifact must live outside the fence (D2). `write_atomic`,
`append_audit`, the audit hash chain, `save_state`, `read_state`, `bind_workitem`,
`resolve_decision`, `cmd_migrate_workflow`, `SDLE_OWNED_PREFIXES`,
`RUNTIME_FREE_COMMANDS` and the write fence are all untouched.

### Preserved invariants

Each must be demonstrable *after* traversal becomes flow-dependent.

| Invariant | How T07 preserves it |
|---|---|
| **Gate discipline** — no advance past a gate without explicit approval, no forward jumps | The `gate_not_approved` and `forward_jump` refusals stay in `apply_advance`, in their existing order, ahead of everything T07 adds. A gate inside the flow is unconditional exactly as today. A gate outside the flow never becomes the current phase, so there is nothing to bypass. `impact_analysis` adds **no** gate and therefore adds no approval path. |
| **Fail safe** — freeze on failure, never advance | Every T07 refusal is raised before any mutation of `state` and before any `append_audit`. `flow_table_invalid` is exit 3. Nothing defaults. |
| **Single writer** | Only `sdle.py` writes state and audit. T07 adds no writer. `flow show` and `constants` are read-only. The `impact_analysis` artifact is written by Claude to an unfenced path and *fingerprinted* by the engine, exactly like the security review (E27). |
| **A refusal leaves `audit.md` byte-identical** (B1 / NB-6) | The `flow_mismatch` check is added to the two early pure-reader prechecks in `cmd_gate_approve` and `cmd_skip` alongside the governance one, at the same position, with `state=None`. Pinned by A9. |
| **The ladder never guesses** | Untouched. WorkItem resolution is not in T07's diff. |
| **Legacy `.workflow/` dual-read still works** (T11 removes it) | Under the legacy binding `paths.workitem is None`, so `governance_precondition` returns early and there is no record to disagree with; `_mig_1_15` gives such a state `GREENFIELD`, which is what it was traversing. |
| **`migrate-workflow` never mutates `.workflow/`** | Not in T07's diff; pinned by A13. |
| **Invariant 3** — `speckit-*` never shown outside verbose | `impact_analysis` invokes no Spec Kit skill and its block names none. No new user-facing string names a Spec Kit command. |
| **Invariant 4** — gate content in conversation | Strengthened: the impact analysis is displayed before `gate_spec` in the two flows that produce it (D2.3). |
| **Invariant 7** — one source of truth per fact | `GREENFIELD` has exactly one home (D3). `PROGRESS_MAP`, `PHASE_TO_GATE_KEY`'s gate-number column, the gate ordinals inside `PHASE_LABEL_MAP` and the ordinals in `phase-execution.md` block headers all become lint-pinned derived views. The one deliberate, contract-mandated duplication is `NEXT_PHASE` (D11). |
| **Invariant 8** — gates stay in the parent session | Flow selection is a *deterministic* consequence of the governance record; it is not a gate, and no subagent is introduced. |
| **The core refuses; it does not warn** | `flow_mismatch` and `flow_table_invalid` are refusals with named remedies. No new warning is added anywhere. |
| **TP-011** — every governed artifact reviewed against its exact SHA | The `impact_analysis` artifact is fingerprinted and review-registered by the existing path-keyed machinery (D2). No new review mechanism, no gate. |

---

## What "the four phase tables agree" means after T07

This is the question the linter redesign has to answer. The answer is that **no
check is weakened**, two are re-targeted onto a stricter subject, one is
generalised, one is narrowly broadened and over-compensated, and **seven are added**.

**Kept, byte-for-byte unchanged:**

| Existing check | Still means |
|---|---|
| `tables_wellformed` | The constants parsed. Short-circuits everything else. Message becomes `Parsed 20 phases, 8 gates, 16 migration rows` plus the flow count. |
| `phase_set_matches_next_phase` | `NEXT_PHASE` still covers the registry identically. |
| `phase_set_matches_phase_label_map` | `PHASE_LABEL_MAP` still covers the **registry** identically — labels are per-phase, not per-flow. `impact_analysis` gains a row. |
| `next_phase_chains_sequence` | `NEXT_PHASE` still chains the registry exactly once, ending terminal. It is now the registry's canonical-order proof and nothing else (D11). |
| `gate_registered_<key>` (×8) | Every registered gate is still in `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE` and the state template's `approvals`. **The template keeps all eight approval keys and gains none**; a flow that omits a gate leaves it `null` forever. |
| `single_state_template`, `version_string_consistent`, `migration_covers_every_state_field`, `no_powershell_only_cmdlets` | Unchanged in rule; `version_string_consistent` reports v1.16 and `migration_covers_every_state_field` covers the new `flow` field. |
| `doc_lists_every_phase_README`, `doc_lists_every_phase_SDLE-Reference-Guide` | Unchanged in rule. Both documents must now also name `impact_analysis` (E41 — a mention anywhere in the text suffices). |

**Re-targeted onto a stricter subject (not weakened — see the note):**

| Check | Change |
|---|---|
| `phase_set_matches_progress_map` | Subject moves from *the registry* to *GREENFIELD*. `PROGRESS_MAP` must equal GREENFIELD's phase set **exactly** (no missing, no extra). |
| `progress_denominator_matches_phase_count` | Denominator moves from `Constants.phase_count` (now 19) to *GREENFIELD's non-terminal count* (18), which is what those strings actually mean. |

> **Why this is a strengthening.** Today `PROGRESS_MAP` is checked for its **key
> set only**. After T07 it is checked for (a) exact equality with GREENFIELD's
> phase set, (b) the correct denominator for GREENFIELD, **and** (c) every
> individual value equalling the derived GREENFIELD progress (L4) — which is
> checked for the first time. GREENFIELD is itself frozen (D3) and lint-proved to
> be an ordered subset of the registry (L2), so the smaller subject is not a
> smaller guarantee. Strictly more is asserted about `PROGRESS_MAP` after T07 than
> before.

**Generalised (strictly stronger):**

| Check | Change |
|---|---|
| `no_hardcoded_progress_outside_progress_map` | Today it scans for `\d+/18` using `consts.phase_count`. It becomes a scan for `\d+/<d>` over **every flow denominator** — `18`, `16`, `14`, `10`. E34 confirms zero matches at HEAD for `10`, `14` and `16` across all four skill files, so the generalisation is free of false positives. |

**Narrowly broadened, and over-compensated (D8):**

| Check | Change |
|---|---|
| `every_phase_has_execution_block` | The header ordinal becomes optional in the regex so a phase with no GREENFIELD position can have a block. Paid for by L7, which pins all 17 existing ordinals for the first time. |

**Added — seven new checks:**

| # | New check | Asserts |
|---|---|---|
| L1 | `flow_table_covers_the_required_flows` | `FLOW_PHASES`'s four row keys plus the injected `GREENFIELD` name exactly equal `ENGINEERING_FLOWS` — no missing flow, no extra flow, and `GREENFIELD` is **not** a declared row. |
| L2 | `every_flow_is_an_ordered_subset_of_the_registry` | For all five flows including GREENFIELD: every phase named is in `PHASE_SEQUENCE`; no duplicates; strictly increasing registry position; starts `requirements_check`; ends `complete`. |
| L3 | `every_flow_retains_the_mandatory_phases` | D6's floor, for all five flows. |
| L4 | `progress_map_and_gate_numbers_are_the_derived_greenfield_views` | `PROGRESS_MAP` equals the derived GREENFIELD progress for every GREENFIELD phase, and `PHASE_TO_GATE_KEY`'s `gate number` column equals the derived GREENFIELD gate numbering. |
| L5 | `every_registry_phase_is_used_by_some_flow` | **The replacement for the lost derivation guarantee (D3).** No registry phase may be orphaned; a phase added to `PHASE_SEQUENCE` and named by no flow fails loudly. |
| L6 | `gate_labels_are_flow_relative` | Every gate phase's `PHASE_LABEL_MAP` value contains the `{gate_number}` placeholder and **no** literal `Gate <digit>` ordinal, so the ordinal cannot be re-hardcoded. |
| L7 | `execution_block_numbers_are_the_greenfield_positions` | Every `phase-execution.md` block header that carries an ordinal equals that phase's 1-based GREENFIELD position, and every GREENFIELD phase's block carries its ordinal. |

**Total: 22 → 29 checks.** Each new check gets an additive firing test in
`tests/test_lint_skill.py` following the existing `assert_only_failure` pattern
(E38 — that file asserts no check count, so nothing there breaks).

**Design constraint the firing tests impose, and the implementer must honour.**
`assert_only_failure` requires that **exactly one** check fails for a given planted
breakage, and `lint-skill` must still return exit 0 with a `failed` list rather
than raising. Therefore:

- `load_constants` **parses** `FLOW_PHASES` into raw data and does **not** validate
  it. It raises only for the reasons it raises today (heading missing, malformed,
  empty — E35).
- Validation lives in two places: `run_sync_checks`, as the named checks L1–L3,
  and `Constants.flow(name)`, which is called only when a *traversal* asks for a
  flow and refuses `flow_table_invalid` (exit 3) there. `lint-skill` never calls
  `Constants.flow()`.
- Each firing test must plant a breakage that trips exactly one of L1–L7. Where two
  checks would both fire on the same breakage, the test must choose a breakage that
  isolates one (for example: L3 is fired by dropping `gate_implement` from
  `ITERATIVE`, which leaves the row an ordered subset and so does not trip L2).

---

## Dry-run disposition (contract §13, explicit)

§13 gates the removal of legacy fixed-sequence structures on three conditions.
T07 satisfies "new flow tests pass" and "migration path exists", gives the
disposition below, and **does not perform the removal** — §17 assigns that to T11.

| Transcript | Disposition | Reason |
|---|---|---|
| `01-happy-path.md` | **Valid, unchanged, and load-bearing** | A GREENFIELD run. `EXPECTED_TRAVERSAL` and `run_happy_path` are imported by the governance suite (E20). Its integration test must stay green **with zero edits** — T07's compatibility proof (A6), and one of the four witnesses in D3. |
| `02` rejection/remediation | Valid, unchanged | GREENFIELD; rejection and remediation are flow-independent. |
| `03` retry/skip | Valid, unchanged | GREENFIELD; `skip` advances to the next phase *in the flow*, identical under GREENFIELD. |
| `04` drift re-approval | Valid, unchanged | Drift is gate-keyed and skips unapproved gates (E32, D15). |
| `05` untrusted content | Valid, unchanged | Pre-lifecycle scanning; no traversal. |
| `06` secrets / dirty tree | Valid, unchanged | `implement` is in every flow (D6). |
| `07` audit integrity / session lock | Valid, unchanged | No traversal. |
| `08` restart / reset / state jump | **Valid, unchanged — with a recorded semantic note** | `restart phase N` becomes flow-relative (D16 below). Under GREENFIELD the transcript is byte-correct. A non-GREENFIELD restart transcript is **not** authored at T07. |
| `09` bootstrap failures | Valid, unchanged | Pre-`init`; no flow is bound yet. |

**No transcript documents behaviour that ceases to exist.** All nine remain the
GREENFIELD acceptance specification, and **all nine remain byte-identical**.
`impact_analysis` appears in none of them, which is correct: it is not in GREENFIELD.

**Not regenerated at T07, deliberately:** no transcript is authored for `ITERATIVE`,
`DEFECT_FIX`, `HOTFIX` or `BROWNFIELD_DISCOVERY`. A dry-run is a *conversational*
artifact containing simulated Spec Kit output; authoring four more would multiply
the documentation debt these files already carry (T04's N-6) without adding a
single executable guarantee. Non-GREENFIELD traversal is pinned instead by
end-to-end engine tests driving the real CLI (N1–N7), which is strictly stronger
evidence than prose.

**One documentation change:** a short paragraph in `docs/dry-runs/README.md`
recording exactly the above. The pre-existing stale `.workflow/` lines inside those
files are **not** touched (T11's, per T04 N-6).

**D16 — `restart --to <N>` becomes flow-relative.** `restart` currently indexes
`PHASE_SEQUENCE`. Under a flow it indexes the **flow's** phase list, so it stays
consistent with the `Phase N/M` the user is shown. Identical under GREENFIELD.
`.claude/commands/sdle-restart.md`'s `argument-hint` loses its restated `1-18` (E42).

**D17 — `forward_jump` absorbs "not in this flow"; `unknown_phase` keeps its
meaning.** A target not in the registry still refuses `unknown_phase` (exit 1) —
`test_advance_refuses_unknown_phase` stays green untouched. A target in the registry
but not in the bound flow refuses `forward_jump`, with `"in_flow": false` in `data`
so the caller can tell the two apart. This is now reachable in the ordinary case:
`advance --to impact_analysis` under GREENFIELD refuses `forward_jump`, not
`unknown_phase`. Index fields in the refusal payload are computed defensively
(`None` when the phase is outside the flow) so index lookup can never raise and
mask the real reason.

---

## Files expected to change

**Engine**

- `scripts/sdle.py` — the whole of T07's mechanism:
  `Flow` dataclass, `Constants.flows` / `Constants.flow()`; `FLOW_PHASES` parsing
  in `load_constants` (parse only, no validation — see the firing-test constraint);
  `GREENFIELD_V1_PHASES`; `MANDATORY_FLOW_PHASES`; `flow_for_state()`;
  `flow_mismatch`; `flow_table_invalid`; `CURRENT_VERSION` → `1.16`; `_mig_1_15`
  and its `MIGRATIONS` row; `Constants.label()` gaining the `{gate_number}`
  substitution; `cmd_flow_show` and its parser registration; `cmd_constants`
  gaining `flows`; the seven new lint checks, the two re-targeted checks, the
  generalised `_check_no_hardcoded_progress` and the block-header regex; and the
  traversal call sites in `cmd_init`, `apply_advance`, `cmd_advance`,
  `cmd_gate_approve`, `_approve_drift`, `cmd_gate_reject`, `cmd_gate_show`,
  `cmd_skip`, `cmd_restart`, `cmd_doctor`, `render_header`, `cmd_state_dump`,
  `write_completion_summary`, `evaluate_classification`, `record_governance_audit`,
  `cmd_governance_gates`.
  **Not touched:** `compute_drift`, `cmd_repo_staleness`, `write_atomic`,
  `append_audit`, `save_state`, `read_state`, `bind_workitem`, `resolve_decision`,
  `cmd_migrate_workflow`, `cmd_workitem_*`, `cmd_config_*`, `cmd_feature_*`,
  `cmd_artifact_record`, `cmd_artifact_review`, `governance_precondition`'s body,
  `required_gate_set`.

**Prompt layer**

- `.claude/skills/sdle/SKILL.md` — `impact_analysis` rows in `PHASE_SEQUENCE`,
  `NEXT_PHASE` (one edited, one new) and `PHASE_LABEL_MAP`; the eight
  `PHASE_LABEL_MAP` gate labels gaining `{gate_number}`; the new `### FLOW_PHASES`
  table plus its GREENFIELD note; a short flow paragraph in Step 1 stating that
  governance is assessed **before `init`** because that is where the flow binds;
  the version string (frontmatter + heading); the 16th `VERSION_MIGRATION` row;
  the `18-Phase Workflow` heading and description qualified as the GREENFIELD flow.
  **`PROGRESS_MAP` is not edited** — its 19 rows stay byte-identical as the
  GREENFIELD view.
- `.claude/skills/sdle/templates/state.json` — `flow` field, `workflow_version`
  `1.16`. `approvals` **unchanged**; `progress` **unchanged**.
- `.claude/skills/sdle/modules/phase-execution.md` — the new `impact_analysis`
  block (ordinal-free header; no `feature bind`; writes
  `reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md`; `artifact record`;
  `artifact review`; advance to the flow's next phase); the display-before-`gate_spec`
  step in the `spec_draft` block, conditional on the artifact existing; the
  traversal instruction (ask `advance` / `flow show`; a phase absent from the flow
  is never executed and never mentioned); D13's conditional design-document
  sentence; D13's `(Gate N/8)` parentheticals.
- `.claude/skills/sdle/modules/gate-protocol.md` — gate numbering is `Gate N/M`
  from the script, not a fixed `N/8`; the completion line's "All 8 gates passed"
  becomes flow-derived. **The stale `.workflow/completion-summary.json` path on
  that same line is left alone (T11 / T04 N-6).**
- `.claude/commands/sdle-restart.md` — argument hint (E42, D16).

**Documentation**

- `README.md` — title version, the `**v1.16**` history row inserted **above**
  `**v1.15**` (the version linter takes the first `\*\*vN.N\*\*` match), the
  `18 phases · 8 approval gates` headline qualified as GREENFIELD, the
  `## 18-Phase Workflow` fenced block retitled as the GREENFIELD flow and otherwise
  left intact, and a new short **Flows** section naming all five flows and
  `impact_analysis` (satisfying `doc_lists_every_phase_README`).
- `docs/SDLE-Reference-Guide.md` — the covers-version row, the §7 heading qualified,
  the glossary "There are 8 gates" qualified as GREENFIELD, and one new section on
  the flow model containing an `impact_analysis` subsection with **no** GREENFIELD
  ordinal (E40).
- `CLAUDE.md` — the "gated 18-phase SDLC workflow" sentence, and lines in the
  cross-file sync list for the seven new checks.
- `docs/dry-runs/README.md` — the disposition paragraph.
- `docs/architecture/ADR-004-declarative-flow-model.md` — **new** (E44): what was
  chosen, what was rejected (deriving GREENFIELD from the registry; the
  exclusion-set variant; renumbering the execution blocks; a generic workflow
  engine; a `flow set` command; adding a ninth gate), the user decision recorded
  above, and every deliberate divergence from §13's suggested shapes.

**Tests**

- `tests/test_units_flow_model.py` — **new**, the phase's own suite.
- `tests/test_lint_skill.py` — **additive only**: one firing test per new check.
- `tests/conftest.py` — **exactly one line** (see the anti-contradiction clause).
- `tests/test_units_governance.py` — the rewritten differential (N8) plus the
  `advisory` and audit-message assertions D13 invalidates.
- Version-assertion lines wherever `1.15` is asserted, migration-row-count
  assertions, any completion-summary key-set assertion (D14), and
  ordered-audit-event assertions the new `flow_selected` entry shifts.

**Must not change** (`git diff --exit-code 7dba4b6` over this list must be exit 0):

```
.claude/hooks/                     .claude/settings.json
scripts/sdle.sh                    scripts/sdle.ps1
scripts/README.md                  .github/
.gitignore                         .gitattributes
requirements/                      tools/
docs/dry-runs/01..09 (the nine transcripts themselves)
docs/architecture/ADR-001, ADR-002, ADR-003
.claude/skills/sdle/modules/security-review.md
tests/test_integration_01_happy_path.py
docs/transition/transition.md      docs/transition/baseline.md
docs/transition/phases/T00..T06 (every plan, handoff, verification, checkpoint, blocker)
```

---

## Anti-contradiction clause (shared fixtures)

T07 changes traversal, which every shared fixture depends on. To keep the diff
attributable:

**The only permitted edit to `tests/conftest.py` is one line:**
`Project.record_governance`'s default `"classification": {"type": "enhancement",
"flow": "ITERATIVE"}` becomes `"flow": "GREENFIELD"` (E18).

TP-003 category **2 — deliberately superseded behaviour**: at T06 that value was
recorded and inert, so any member of `ENGINEERING_FLOWS` was equally valid as a
fixture default; at T07 it selects the traversal. The shared `started` fixture sits
at `constitution_draft`, a phase only GREENFIELD and BROWNFIELD_DISCOVERY have.
`GREENFIELD` is therefore the value that keeps every existing assertion in every
other file byte-identical.

**Every other change to `tests/conftest.py` is forbidden** — no new fixture, no new
helper, no signature change, no `Project` method. All new helpers live in
`tests/test_units_flow_model.py`. If the implementer believes a second conftest
edit is unavoidable, that is a plan defect: record it as a declared divergence with
the reason, do not make it silently.

`tests/test_lint_skill.py` may receive **new test functions only**. No existing test
in that file may be modified or deleted. `tests/test_integration_01_happy_path.py`
may not be touched at all (A6).

---

## Existing tests affected

TP-003 classification. There is no fourth category.

| File / test | Category | Why |
|---|---|---|
| `tests/conftest.py` `record_governance` | **2 — superseded** | The anti-contradiction clause. One line. |
| `test_units_governance.py::test_governance_changes_no_lifecycle_behaviour` (E19) | **2 — superseded** | It asserts all four governance variants traverse identically. T07's whole point is that three of the four must not (`ITERATIVE`, `DEFECT_FIX`, `HOTFIX`). Rewritten as N8 — and the rewrite is *stronger*, because it keeps the risk half of the assertion. |
| `test_units_governance.py` — `record["classification"] == {..., "advisory": True}` and any assertion on the `(advisory)` ledger text | **2 — superseded** | D13. |
| Any test asserting `workflow_version == "1.15"`, the `1.14 → 1.15` terminal migration row, or the parsed migration-row count of 15 | **2 — superseded** | D9's version bump. Same shape of edit T04 made for `1.15`. |
| Any test asserting the parsed **phase count** of 19 or a `PHASE_SEQUENCE` length | **2 — superseded** | D0/D1. The registry becomes 20. |
| Any test asserting the completion-summary key set exactly | **2 — superseded** | D14 adds `flow`. |
| Ordered-audit-event assertions that see the new `flow_selected` entry | **2 — superseded** | D9. The entry is a *new* governed fact, not a changed one. |
| `test_integration_01_happy_path.py`, `EXPECTED_TRAVERSAL`, `run_happy_path` | **1 — unchanged, must stay green with zero edits** | The compatibility proof (A6) and witness P1 of D3. |
| `test_units_transitions.py` | **1 — unchanged** | Driven by `started`, which is GREENFIELD after the conftest flip. |
| `test_integration_02_to_05.py`, `test_integration_06_to_09.py` | **1 — unchanged** apart from any version literal | GREENFIELD transcripts. |
| `test_units_governance.py::test_no_phase_movement_function_consults_the_would_be_gate_set` and `::test_the_phase_movement_prefixes_actually_match_something` | **1 — unchanged, and must stay green untouched** | T07's structural proof that it did not drift into T09 (A11). |
| `test_units_governance.py` closed-caller-set and `movers` assertions (E12) | **1 — unchanged, and must stay green untouched** | T07 must not add a fourth caller of `governance_precondition` or of `apply_advance`. In particular `cmd_init` must **not** start calling `apply_advance` (A12). |
| `test_lint_skill.py::test_the_repo_passes_every_check` | **1 — unchanged** | Asserts `failed == []` and `len(checks) > 15`; 29 still satisfies it (E38). |
| `test_units_workitem.py`, `test_units_workitem_resolution.py`, `test_units_workitem_runtime.py`, `test_units_speckit_binding.py`, `test_units_repo_config.py`, `test_hooks.py`, `test_units_infra.py`, `test_units_cli.py`, `test_units_artifact_review.py` | **1 — unchanged** apart from version literals | No traversal dependency beyond the shared fixture. |

**No test may be weakened, skipped, xfailed or deleted.** The suite currently has
zero skips and zero xfails (E2/E3) and must still have zero at the end.

---

## New tests required

All in `tests/test_units_flow_model.py` unless noted. Every one drives the real CLI
as a subprocess through the existing `Project` fixture machinery.

**Traversal**

- **N1** `GREENFIELD` end-to-end: traversal equals `EXPECTED_TRAVERSAL`, 8 gates,
  `18/18` at completion, and `impact_analysis` appears **nowhere** in
  `phase_history` or the ledger.
- **N2** `ITERATIVE` end-to-end: `init` lands on `spec_draft`;
  `constitution_draft`, `gate_constitution` and `impact_analysis` never appear;
  7 gates approved; final progress `16/16`; `approvals.gate_constitution` still
  `null`; `audit verify` exit 0.
- **N3** `DEFECT_FIX` end-to-end: 14 non-terminal phases, 5 gates, `init` lands on
  **`impact_analysis`**, `design_generation` / `gate_design` / `checklist_draft`
  absent, final progress `14/14`.
- **N4** `HOTFIX` end-to-end: 10 non-terminal phases, 3 gates, `init` lands on
  `impact_analysis`, `gate_implement` renders as `Gate 2/3`, final progress `10/10`,
  a completion summary is still written, and the summary records `flow: "HOTFIX"`.
- **N5** `BROWNFIELD_DISCOVERY` traverses identically to `GREENFIELD` **and the test
  says explicitly that T08 owns changing this**, so T08's edit cannot be silent.
- **N6** The five traversals are pairwise distinct as sets except the deliberate
  `GREENFIELD == BROWNFIELD_DISCOVERY` pair — the exit criterion, asserted directly.

**The new phase specifically**

- **N7** `impact_analysis` as a governed, gateless phase:
  1. it is in `PHASE_SEQUENCE` at position 2 and in exactly `{DEFECT_FIX, HOTFIX}`;
  2. it has **no** `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP` or
     `GATE_TO_EXECUTION_PHASE` entry, and `templates/state.json` `approvals` still
     has exactly the eight pre-T07 keys;
  3. `artifact record --phase impact_analysis --path reviews/impact-analysis-…md`
     fingerprints it and appends exactly one `artifact_recorded` event;
  4. `artifact review --path <same>` records a review bound to that SHA, and
     rewriting the file makes the review stale by the existing mechanism;
  5. `advance` out of it lands on `spec_draft` in **both** DEFECT_FIX and HOTFIX;
  6. under GREENFIELD, `advance --to impact_analysis` refuses `forward_jump` with
     `data["in_flow"] is False` — **not** `unknown_phase`;
  7. no gate can ever be current at `impact_analysis`: `gate approve` /
     `gate reject` refuse and write nothing.

**The T07/T09 boundary**

- **N8** The rewritten differential (replacing E19): four repositories cloned before
  any run. Flow differing ⇒ traversal differs, exactly as the flow table says.
  **Risk differing with flow held constant ⇒ traversal, approvals, artifact-SHA key
  set and ordered lifecycle audit events are identical.** `governance gates` still
  reports `advisory: True` and still differs by risk while changing nothing.

**Gate discipline under a flow**

- **N9** Within any flow, `advance` past a gate phase whose approval is not recorded
  refuses `gate_not_approved` — parametrised over all five flows.
- **N10** `advance --to <registry phase not in this flow>` refuses `forward_jump`
  with `data["in_flow"] is False`; `advance --to <not in the registry>` still
  refuses `unknown_phase` (D17).
- **N11** `gate approve --gate gate_design` in `HOTFIX` refuses (that gate is never
  the current phase) and writes nothing.

**Binding and immutability**

- **N12** `init` with no governance record binds `GREENFIELD`; `init` after a
  `HOTFIX` assessment binds `HOTFIX`; both audit `flow_selected`; `state["flow"]`
  is the only place it is stored.
- **N13** No CLI path other than `init` and `migrate` writes `flow`: a recursive SHA
  map before and after `governance assess`, `flow show`, `constants`,
  `governance show` and `governance gates` is unchanged.
- **N14** Re-assessing with a different flow mid-run refuses `flow_mismatch` at the
  next `advance`, at `gate approve`, and at `skip` — and in all three cases
  `audit.md` is **byte-identical** before and after and `audit verify` exits 0 (the
  B1/NB-6 property, re-proved for the new refusal).
- **N15** No CLI path adds an approvals key: `state["approvals"]` has exactly the
  eight pre-T07 keys at every point of a `DEFECT_FIX` run.
- **N16** D10's declared consequence: a v1.15 state carrying a non-GREENFIELD T06
  record migrates to `flow: "GREENFIELD"` and then refuses `flow_mismatch` with the
  remedy named.

**Migration**

- **N17** `_mig_1_15` adds `flow: "GREENFIELD"` to a v1.15 state, is idempotent,
  never consults the governance record, and preserves every
  `MIGRATION_VERIFIED_FIELDS` value. A v1.13 state migrates the whole chain to 1.16
  and lands on `GREENFIELD`.

**Structure — the compatibility translation and the registry/flow split**

- **N18** *(P1)* `GREENFIELD_V1_PHASES` equals `EXPECTED_TRAVERSAL`, imported from
  `test_integration_01_happy_path`.
- **N19** *(P2)* `GREENFIELD_V1_PHASES` equals a golden 19-element literal spelled
  out in this test file, and `constants.flows["GREENFIELD"]` equals it too.
- **N20** `GREENFIELD` is **not** a row key in `FLOW_PHASES`, and adding a phase to
  `PHASE_SEQUENCE` does **not** change `constants.flows["GREENFIELD"]` — proved by
  parsing a scratch `SKILL.md` with a planted extra registry row and asserting
  GREENFIELD is unchanged while `every_registry_phase_is_used_by_some_flow` fires.
  **This is the test that would have caught the revision-1 coupling.**
- **N21** *(D11)* The set of functions in `scripts/sdle.py` that read
  `Constants.next_phase` is exactly `{"load_constants", "run_sync_checks",
  "cmd_constants"}` (AST). `NEXT_PHASE` survives as a linted table with no traversal
  consumer, and `next_phase_chains_sequence` still passes over the 20-entry registry.
- **N22** `Constants.flow()` refuses `flow_table_invalid` (exit 3) on a hand-broken
  `FLOW_PHASES` — unknown phase id, out-of-order phase, duplicate, missing mandatory
  phase, missing terminal `complete`, unknown flow name. It never defaults. And
  `load_constants` alone does **not** raise for those, so `lint-skill` still reports
  per-check failures.
- **N23** `set(HOTFIX) - {"impact_analysis"} == set(MANDATORY_FLOW_PHASES)` exactly;
  every flow is a superset of `MANDATORY_FLOW_PHASES`; `HOTFIX` is the
  subset-minimum of the five (D6).
- **N24** Derived GREENFIELD progress equals `PROGRESS_MAP` for every GREENFIELD
  phase; derived GREENFIELD gate numbers equal `PHASE_TO_GATE_KEY`'s column; derived
  GREENFIELD gate labels render byte-identically to the pre-T07 literals
  (`Gate 1: Constitution Approval` … `Gate 8: Security Review Approval`).
- **N25** `flow show` is read-only and refuses cleanly with no state.
- **N26** Two WorkItems in one repository on different flows advance independently;
  the first's `state.json` and `audit.md` are byte-unchanged while the second runs
  (the T02 isolation property, re-proved under flows).

**Lint** (additive, in `tests/test_lint_skill.py`)

- **N27–N33** One `assert_only_failure` test per new check L1–L7, each planting a
  breakage that isolates exactly one check (see the firing-test constraint).

---

## Failure modes

| # | Failure mode | Detection | Mitigation |
|---|---|---|---|
| F1 | **A leftover `consts.next_phase` reader routes a GREENFIELD run through `impact_analysis`.** After the registry insertion the registry chain is no longer the GREENFIELD chain (D11); E14 lists six engine readers today. | The nine dry-run integration tests fail immediately; N21 fails permanently. | **Milestone ordering is a hard constraint: M1 removes every traversal reader and M3 inserts the registry row. M3 must not begin until M1's zero-test-edit green suite exists.** N21's closed reader set makes a re-introduction impossible to merge. |
| F2 | **The fixture flow flip is missed and every fixture-driven test traverses `ITERATIVE`.** `started` sits at `constitution_draft`, which `ITERATIVE` does not have. | Hundreds of failures at once. | The conftest flip and the `cmd_init` binding land in the **same milestone (M5)**, in that order. This is the phase's one deliberate red window. |
| F3 | Derived progress, gate numbering or gate labels do not reproduce the GREENFIELD tables, silently changing header strings and audit messages. | The integration transcripts assert those strings. | M1 lands the derivation with **zero test edits**; the green suite is the proof. N24 pins it permanently, including the label rendering. |
| F4 | `FLOW_PHASES` parses to nothing or to a wrong list, and `advance` computes a wrong next phase — the exact fail-open `parse_md_table` exists to prevent (E35). | `tables_wellformed` short-circuits `lint-skill`; `Constants.flow()` raises exit 3. | The loader raises `IntegrityError`, never returns a default. N22 pins six distinct breakages. The space-separated un-backticked cell format is chosen precisely because `_normalise_cell` would mangle a backticked list (D4). |
| F5 | A flow omits a phase a later phase depends on (`spec_draft`, `tasks_draft`), and a real run dies inside Spec Kit. | Not caught by tests — tests never invoke Spec Kit. | `MANDATORY_FLOW_PHASES` enforced at **both** lint time and load time (D6), with a documented reason per member. |
| F6 | **`impact_analysis`'s block calls `feature bind --require-feature` or references `{state.specKit.featureDirectory}`.** The feature directory does not exist yet (E28), so a real run would refuse and halt at phase 2 of every defect flow. | Not caught by tests — tests never invoke Spec Kit. | Stated as a prohibition in D2 and in the block itself. A review item for the verifier: grep the new block for `feature bind` and `featureDirectory` and require **zero** hits. |
| F7 | **The `impact_analysis` artifact path trips the write fence**, so a real run cannot write it. | Not caught by the unit suite — the fence is a Claude Code hook. | The path is `reviews/…`, outside `FENCED` (E26), identical in shape to the security review (E27). A verifier check drives `.claude/hooks/hooks.py`'s `write-fence` directly against the chosen path and requires it to permit. |
| F8 | The new refusal appends to the ledger before it fires, regressing B1/NB-6. | N14 asserts byte-identical `audit.md` on all three refusal paths. | The check is placed with the existing pure-reader prechecks, `state=None`, ahead of every `append_audit`. |
| F9 | A firing test trips two new checks at once and `assert_only_failure` fails. | `tests/test_lint_skill.py` fails. | The firing-test constraint above: parse without validating, and choose isolating breakages. |
| F10 | T07 drifts into T09 by consulting `required_gate_set` when choosing phases. | `test_no_phase_movement_function_consults_the_would_be_gate_set` (E17) fails. | That test stays green untouched. A11. |
| F11 | `cmd_init` starts calling `apply_advance` to get flow-aware movement, reversing T06's deliberate "governance is not an `init` precondition". | The `movers` assertion (E12) fails. | A12 forbids it. `cmd_init` uses the flow's own next-phase lookup, exactly as it uses `next_phase` today (E13). |
| F12 | The generalised progress lint fires on innocent text (`2/10`, a date, a ratio). | `lint-skill` fails. | E34: zero matches at HEAD for `10`, `14` and `16` across all four skill files. Re-checked after every document edit. |
| F13 | The version bump misses a site, or the README history row goes below `**v1.15**` and the linter reads the wrong first match. | `version_string_consistent` fails. | T02 hit this and recorded the lesson; the row goes **above**. |
| F14 | Documentation edits break `doc_lists_every_phase_*` by removing a phase name while qualifying the "18 phases" prose, or by forgetting to name `impact_analysis` in both documents. | `lint-skill` fails. | Re-run `lint-skill` after **each** document edit, as T05 did. Both documents gain an explicit `impact_analysis` mention (E41). |
| F15 | Renumbering pressure leaks into `modules/security-review.md`, which is on the must-not-change list (E31). | A4's `git diff --exit-code` fails. | D5/D8: no block header is renumbered. The new block carries no ordinal. |
| F16 | The suite takes 15–20 minutes; an agent is killed mid-flight (nine times so far in this migration). | — | One checkpoint per milestone; M4 is the declared safe resume boundary. Budget 1500000 ms per full run. |
| F17 | Disk exhaustion (`os error 112` was seen earlier in this migration). | An I/O error in the run. | 21 GB free at plan time (E8). **If a disk error appears, stop and report — do not trust the result.** |
| F18 | Windows/POSIX divergence in the new code. | Untestable here. | The new engine code is pure table arithmetic; no path handling is added. The one new path is a forward-slash relative string handed to existing helpers. |

### Deliberate red window

**Exactly one, confined to M5.** Between the `cmd_init` flow-binding change and the
`tests/conftest.py` flip, every test using the `started` / `project` fixtures
traverses `ITERATIVE` and fails. The implementer **must** make both edits before
running the suite. If the suite is run inside that window, a large failure count is
expected and is **not** an environment flake — F2's signature is failures
concentrated on `constitution_draft` / `gate_constitution`. Any failure with a
different signature is a presumed real regression (E45).

**M3, the registry insertion, is deliberately NOT a red window.** By M3 the engine
traverses `GREENFIELD_V1_PHASES` and nothing reads the registry chain, so adding a
row to `PHASE_SEQUENCE` is observable only through the lint checks that M2 already
re-targeted. If M3 turns the suite red, that is F1 and the fix is in M1, not M3.

Every other milestone ends with the full suite green.

---

## Rollback/recovery strategy

- **Rollback point: `7dba4b6`.** `git reset --hard 7dba4b6` restores the pre-T07
  tree exactly. T07 introduces no repository-level artifact, no new directory and
  no change to `.gitignore`, so a reset needs no cleanup. The `reviews/` directory
  the new phase writes into is already gitignored and already created by
  `security_review`.
- **The only durable data effect is the `flow` state field**, added by `_mig_1_15`.
  Downgrading a v1.16 state to v1.15 is not supported — identical to every prior
  version bump, and `read_state` refuses `unknown_version` with a named remedy
  rather than guessing.
- **Nothing is deleted.** `NEXT_PHASE`, `PROGRESS_MAP` and the gate-number column
  all survive; a revert of T07 leaves them authoritative again with no migration
  needed in either direction of the tables. `PROGRESS_MAP`'s 19 rows are never
  edited, so a revert cannot lose them.
- **The registry insertion is independently revertible.** M3 is a self-contained
  milestone: reverting the `impact_analysis` rows plus the two flow-row edits
  returns the registry to 19 entries without touching the flow mechanism.
- **Milestone recovery.** One `T07-checkpoint-a01-NN.md` per milestone. Each
  checkpoint must record what is *on disk*, verified — not what was intended.
  T03's lesson: checkpoints have been accurate about the engine and wrong about
  tests. `python -m pytest --collect-only -q` is the cheap check and must be quoted
  in every checkpoint.
- **Declared safe resume boundary: end of M4.** M1–M4 are behaviour-neutral for
  GREENFIELD (the seam, the table, the registry row, the schema); M5 is where
  binding begins and where the red window lives. A fresh agent resuming mid-phase
  should restart at a milestone boundary, never mid-milestone.

---

## Milestones

| M | Content | Green at end? | Structural proof |
|---|---|---|---|
| **M1** | **The flow seam.** `Flow`, `Constants.flows` / `Constants.flow()`, `flow_for_state()`, `GREENFIELD_V1_PHASES`; GREENFIELD sourced from the frozen constant; **every** traversal call site (E14, E15) routed through the flow, including `cmd_init`; progress, gate numbering and gate labels derived; `{gate_number}` placeholder in `PHASE_LABEL_MAP`. Registry unchanged. No `Constants` attribute removed; `constants` output keeps every existing key. | **Yes** | **`git diff --name-only -- tests/` is EMPTY and the suite is 791 passed.** T07's equivalent of T02's `Paths` seam. Additionally: `grep` proves no traversal function names `next_phase`. |
| **M2** | `### FLOW_PHASES` (four rows) in SKILL.md; parse-only loader plus `Constants.flow()` validation; `MANDATORY_FLOW_PHASES`; the two re-targeted checks; the generalised progress check; L1–L6; N19, N22–N24, and the L1–L6 firing tests. Registry still 19 entries. | **Yes** | `lint-skill` 22 → 28 checks, all PASS; only additive test functions added; `assert_only_failure` passes for each new check. |
| **M3** | **The registry insertion.** `impact_analysis` into `PHASE_SEQUENCE` (position 2), `NEXT_PHASE` (one edited row, one new), `PHASE_LABEL_MAP`; `DEFECT_FIX` and `HOTFIX` rows gain it; the `phase-execution.md` block; the block-header regex change and L7 plus its firing test; `README.md` and Reference Guide mentions; N7 parts 1–2, N18, N20, N21. | **Yes** | `lint-skill` 29/29; `tables_wellformed` reports **20 phases**; `constants.flows["GREENFIELD"]` still 19 entries and equal to `EXPECTED_TRAVERSAL`. **This milestone is where the coupling this revision fixes would have shown up.** |
| **M4** | Schema: `flow` in the template, `CURRENT_VERSION` `1.16`, `_mig_1_15`, the 16th `VERSION_MIGRATION` row, the version-string sites, N17. `flow_for_state` reads the field; every state is still GREENFIELD. `approvals` untouched. | **Yes** | `migration_covers_every_state_field` and `version_string_consistent` PASS at v1.16; only version literals edited in tests. **Safe resume boundary.** |
| **M5** | Binding and enforcement: `cmd_init` binds from the record, `flow_selected` audit entry, `flow_mismatch` in `apply_advance` and in both pure-reader prechecks, D13's five text fixes, D14's summary key, **the one conftest line**. N12–N16. | **Yes** (red window inside) | The suite returns to 791+ green. `test_the_gate_approval_precheck_runs_before_the_first_audit_write` and the closed-caller-set tests still pass untouched. |
| **M6** | `tests/test_units_flow_model.py` in full: N1–N11, N25, N26; the N8 rewrite of the T06 differential. | **Yes** | Five flows demonstrated end to end; N8 shows risk still moves nothing; `impact_analysis` proven governed and gateless. |
| **M7** | `flow show`; `constants.flows`; the remaining prompt and documentation layer; ADR-004; the dry-run disposition paragraph; `sdle-restart.md`. `lint-skill` re-run after **every** document edit. | **Yes** | `lint-skill` 29/29; `doc_lists_every_phase_*` still PASS; the nine transcripts byte-identical. |
| **M8** | Full suite, `lint-skill`, `validate.py`, must-not-change `git diff --exit-code`, the write-fence probe (F7), handoff. | **Yes** | All acceptance criteria evidenced. |

---

## Acceptance criteria

Objective, and each independently checkable by the verifier.

- [ ] **A1** `python -m pytest -q -p no:cacheprovider -rsxX` is **RAW EXIT 0**, `--collect-only -q` reports the same number, and the captured run contains **no** `short test summary` section (zero skips, xfails, errors). The count is ≥ 791 and every added id is accounted for.
- [ ] **A2** `lint-skill` is **raw exit 0** with **29 checks, 29 PASS, `"failed": []`**, reporting `20 phases, 8 gates, 16 migration rows` and `all four locations report v1.16`.
- [ ] **A3** `python tools/transition/validate.py` is raw exit 0.
- [ ] **A4** `git diff --exit-code 7dba4b6 <head>` over the must-not-change list is **exit 0**, including `tests/test_integration_01_happy_path.py` and `.claude/skills/sdle/modules/security-review.md`.
- [ ] **A5** **The compatibility translation, four ways.** (P1) a test asserts `GREENFIELD_V1_PHASES == EXPECTED_TRAVERSAL`; (P2) a golden literal in `tests/test_units_flow_model.py` matches it; (P3) the verifier independently parses `PHASE_SEQUENCE` out of `git show 7dba4b6:.claude/skills/sdle/SKILL.md` and finds it element-wise equal to `constants.flows["GREENFIELD"]` at the T07 head; (P4) `_mig_1_15` sets `GREENFIELD` unconditionally.
- [ ] **A6** `tests/test_integration_01_happy_path.py` is **byte-identical** to its content at `7dba4b6` and passes.
- [ ] **A7** **GREENFIELD is not derived from the registry.** `GREENFIELD` is not a row key in `FLOW_PHASES`; adding a phase to a scratch `PHASE_SEQUENCE` leaves `constants.flows["GREENFIELD"]` unchanged and makes `every_registry_phase_is_used_by_some_flow` fire (N20). The registry has **20** entries and **no** flow has 20.
- [ ] **A8** Driving the real CLI in scratch repositories, the four non-GREENFIELD flows complete end to end with the phase counts and gate counts in D4's table (18/8, 16/7, 14/5, 10/3), and the traversals are pairwise distinct except the declared `GREENFIELD == BROWNFIELD_DISCOVERY` pair.
- [ ] **A9** **`impact_analysis` is a real, governed, gateless phase.** It is at `PHASE_SEQUENCE` position 2; it is in exactly `DEFECT_FIX` and `HOTFIX`; `init` under both lands on it; it has no `PHASE_TO_GATE_KEY` / `ARTIFACT_OWNERSHIP` / `GATE_TO_EXECUTION_PHASE` entry; `templates/state.json` `approvals` has exactly the eight pre-T07 keys and `state["approvals"]` never gains a ninth; its artifact is fingerprinted by `artifact record` and review-registered by `artifact review` against that exact SHA; its `phase-execution.md` block contains **zero** occurrences of `feature bind` and `featureDirectory`.
- [ ] **A10** For `flow_mismatch` raised at `advance`, at `gate approve` and at `skip`: `audit.md` is **byte-identical** before and after, `state.json` is byte-identical, and `audit verify` exits 0.
- [ ] **A11** In every flow, `advance` past an unapproved gate refuses `gate_not_approved`; `advance` to a registry phase outside the flow (including `impact_analysis` under GREENFIELD) refuses `forward_jump` with `data["in_flow"] is False`; `advance` to a non-registry phase still refuses `unknown_phase`. `test_no_phase_movement_function_consults_the_would_be_gate_set` and `test_the_phase_movement_prefixes_actually_match_something` are **byte-identical** to `7dba4b6` and pass; `required_gate_set` is still called by exactly `cmd_governance_assess` and `cmd_governance_gates`.
- [ ] **A12** The closed caller sets are unchanged: `governance_precondition` callers are exactly `["apply_advance", "cmd_gate_approve", "cmd_skip"]` and `apply_advance` callers are exactly `["cmd_advance", "cmd_gate_approve", "cmd_skip"]`. **`cmd_init` does not call `apply_advance`.**
- [ ] **A13** AST extract-and-compare against `7dba4b6`: `write_atomic`, `append_audit`, `save_state`, `read_state`, `bind_workitem`, `resolve_decision`, `cmd_migrate_workflow`, `compute_drift`, `cmd_repo_staleness`, `governance_precondition`, `required_gate_set`, `cmd_artifact_record`, `cmd_artifact_review`, `SDLE_OWNED_PREFIXES`, `RUNTIME_FREE_COMMANDS` are **byte-identical**.
- [ ] **A14** `_mig_1_15` sets `flow: "GREENFIELD"`, is idempotent, and contains **no** reference to the governance record. A v1.13 state migrates the full chain to 1.16.
- [ ] **A15** **The HOTFIX identity.** `set(HOTFIX) - {"impact_analysis"}` **equals** `set(MANDATORY_FLOW_PHASES)` exactly; every flow is a superset of `MANDATORY_FLOW_PHASES`; `HOTFIX` is the subset-minimum of the five flows; the mandatory set is enforced at both lint time and load time; a hand-broken `FLOW_PHASES` yields exit 3 from `Constants.flow()` and never a default, while `lint-skill` still returns per-check failures rather than raising.
- [ ] **A16** Derived GREENFIELD progress equals `PROGRESS_MAP` for every GREENFIELD phase; derived GREENFIELD gate numbers equal `PHASE_TO_GATE_KEY`'s column; derived GREENFIELD gate labels render byte-identically to the pre-T07 literals; **`PROGRESS_MAP`'s 19 rows are byte-identical to `7dba4b6`**; all three are lint-checked (L4, L6).
- [ ] **A17** **No traversal function reads `NEXT_PHASE`.** The AST reader set for `Constants.next_phase` is exactly `{"load_constants", "run_sync_checks", "cmd_constants"}`. `next_phase_chains_sequence` still passes over the 20-entry registry.
- [ ] **A18** No linter check was weakened: the two re-targeted checks assert strictly more (the note in *What "the four phase tables agree" means*), the one broadened regex is compensated by L7, and 22 → 29 checks with a firing test each. The verifier reproduces this by diffing `run_sync_checks` and reading every check body.
- [ ] **A19** There is **no** command that writes `state["flow"]` other than `init` and `migrate`. `grep` for a `flow set` / `flow select` parser registration returns nothing. `flow show` and `constants` are read-only: a recursive SHA map of the project is unchanged across both.
- [ ] **A20** Two WorkItems on different flows advance independently; the first's `state.json` and `audit.md` are byte-unchanged while the second runs.
- [ ] **A21** `git diff --name-status 7dba4b6 -- tests/` shows **zero `D`** and zero `R`; every `M` is justified in the handoff under a TP-003 category; `tests/conftest.py` shows exactly the one permitted line; `tests/test_lint_skill.py` shows added functions only; `tests/test_integration_01_happy_path.py` shows no change at all.
- [ ] **A22** No `pytest.mark.skip`, `pytest.skip(` or `xfail` is added anywhere under `tests/`. **The grep's actual output is quoted in the handoff, not summarised** — `tests/test_units_infra.py` carries a pre-existing `@pytest.mark.skipif(SH is None, …)` and a claim of "no matches" would be false (T03's recorded lesson).
- [ ] **A23** The dry-run disposition in this plan is reproduced in the handoff, all nine transcripts remain **byte-identical**, `impact_analysis` appears in none of them, and `docs/dry-runs/README.md` carries the disposition paragraph.
- [ ] **A24** The write fence permits `reviews/impact-analysis-<ts>.md`: the verifier drives `.claude/hooks/hooks.py`'s `write-fence` entry point directly against that path and observes a permit, with `.claude/hooks/` byte-identical to `7dba4b6`.
- [ ] **A25** No future-phase leakage: no repository-level `.sdle/baseline.*` is created or read; `cmd_governance_gates` still emits `advisory: true`; no gate becomes risk-conditional; no product subagent or skill is added; the legacy `.workflow/` dual-read rung and `migrate-workflow` still work unchanged; `BROWNFIELD_DISCOVERY` still equals GREENFIELD and its test says T08 owns changing that.
- [ ] **A26** Python 3.11 and CI are recorded as **`NOT_RUN` / `UNKNOWN`**. No outcome is predicted.

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is `PLANNED`.**

The one material decision this phase faced — whether impact analysis is a real
phase — was taken by the user and is recorded above as a decision input, with its
rationale, so a verifier can see it was a human call rather than a planner's
invention. The coupling that decision created (a registry that is a superset of
GREENFIELD) is resolved in D3 from repository evidence, not deferred.

| ID | Unknown | Class | Effect |
|---|---|---|---|
| U1 | Python 3.11 and CI behaviour | **UNKNOWN** | Never observed at any point in this migration. T07 adds only stdlib table arithmetic and no syntax newer than 3.11, so a later CI failure could not invalidate the design — but **no outcome is predicted**. |
| U2 | Whether `speckit-plan` degrades under `ITERATIVE` in a repository with no `.specify/memory/constitution.md` | **UNKNOWN** | Tests never invoke Spec Kit. §13's own premise for ITERATIVE is "use established repository baseline", and validating that baseline is §14 — **T08's**. T07 adds no baseline check and records this as T08's input. |
| U3 | Whether `speckit-implement` output degrades under `DEFECT_FIX`/`HOTFIX` with no design documents | INFERRED / UNKNOWN | The prompt's unconditional design-document sentence is fixed by D13, so the orchestrator will not assert a path that does not exist. Output *quality* is unmeasurable here. |
| U4 | Whether the `impact_analysis` prompt block produces a *useful* analysis | **UNKNOWN** | Not measurable by this suite — the same limitation `design_generation` and `security_review` already have. What **is** pinned mechanically: the artifact exists, meets the size floor, is fingerprinted, is review-registered against its exact SHA, and is displayed to the human before `gate_spec`. Content quality is a prompt-craft matter, and T10 owns specialist reviewers. |
| U5 | Whether `BROWNFIELD_DISCOVERY` should differ from `GREENFIELD` before T08 exists | INFERRED | It cannot meaningfully differ without the discovery phase §14 introduces. Declared equal, pinned by N5 so T08's change is visible. |
| U6 | Whether users exist with in-flight v1.15 workflows carrying non-GREENFIELD T06 records | INFERRED — effectively none | The branch is local-only and v1.15 was never released with governance. D10's refusal is nonetheless implemented and pinned rather than assumed away. |
| U7 | Suite runtime variance | OBSERVED | **1305.96 s** in this context, against 849.77 s recorded by revision 1's planner on the same tree — a 1.54× spread on identical code, so a milestone run must never be given the 2-minute default. Budget **1500000 ms**. |

---

## Scope exclusions

Explicitly out of T07. If any appears in the diff it is future-phase leakage.

- **T08 — Brownfield discovery and convergence (§14).** No discovery phase is added
  to the registry. No `.sdle/baseline.*` is created or read. No baseline validity
  check is added anywhere, including for `ITERATIVE` (U2), and **`impact_analysis`
  does not read a baseline** — it reads the requirement, the repository and Git.
  `BROWNFIELD_DISCOVERY`'s real shape is T08's.
- **T09 — Risk-adaptive gates (§15).** **The boundary, stated sharply: T07 selects
  which phases execute; T09 makes gate *requirements* policy-driven.**
  `required_gate_set` stays inert and uncalled by any phase-movement function (A11).
  `governance gates` stays `advisory: true`. No gate inside a flow becomes
  conditional on risk. **`impact_analysis` is not risk-conditional either** — it is
  in `DEFECT_FIX` and `HOTFIX` because the flow says so, never because the risk
  level says so. No hard floor gains a consequence. The `required_gates_by_risk` /
  `required_gates_by_type` policy keys are not read by traversal. `Constants.flow()`
  is deliberately the single seam through which T09 will later compose
  risk-required gates onto a flow; T07 builds the seam and uses none of it.
- **T10 — Skills and subagents (§16).** No product subagent, no skill split, no
  progressive loading. The impact analysis is produced by the parent orchestrator,
  not delegated. Flow selection is deterministic, not delegated.
- **T11 — Legacy removal and hardening (§17).** `NEXT_PHASE`, `PROGRESS_MAP` and
  `PHASE_TO_GATE_KEY`'s gate-number column are **kept** (§13 forbids deleting them
  now). The legacy `.workflow/` dual-read rung, `migrate-workflow` and the
  repo-global compatibility path all keep working. D10's stranded-workflow
  consequence is recorded for T11.
- **§13's other sketch names are not expanded.** *Existing spec mapping*, *spec
  delta/gap*, *Converge* and *Human Review* stay mapped onto existing phases
  exactly as revision 1 mapped them and as the user approved. **Only impact
  analysis becomes a phase.** A second new phase in the diff is scope leakage.
- **No ninth gate.** `impact_analysis` is gateless by decision (DI-2). A
  `gate_impact_analysis` key anywhere in the diff — `PHASE_TO_GATE_KEY`,
  `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE`, `templates/state.json` — is a
  contradiction of the decision this revision exists to implement.
- **Not adopted — every open finding from earlier phases stays with its owner.**
  T04 N-2, N-3, N-4, N-6 (the `.workflow/` documentation residual in
  `phase-execution.md`, `gate-protocol.md` and the nine transcripts), N-7; T03-1
  (the branch-guard fail-open window), T03-4/5/6/7/8/10; T02 NB-2/NB-4/NB-5;
  `.claude/settings.local.json`. **T07 adopts none of them.** In particular,
  `gate-protocol.md`'s completion line is edited for the gate *count* only; its
  stale `.workflow/completion-summary.json` path is left exactly as it is.
- **Owned by T07 and not adoptions**, because T07's own change is what makes them
  wrong: `.claude/commands/sdle-restart.md`'s `1-18` argument hint (D16/E42);
  `phase-execution.md`'s unconditional design-document sentence and its
  `(Gate N/8)` parentheticals (D13/E29); `gate-protocol.md`'s `N/8` gate numbering
  (D13/E29); `PHASE_LABEL_MAP`'s embedded gate ordinals (D5/D7/E29).
- **Deferred features (§27).** No BPM engine, no conditional branching, no parallel
  phases, no loops, no dynamic phase insertion, no policy DSL, no release/build
  model. **A flow is an ordered subset of a fixed registry and nothing more.** If
  the implementation grows a construct that could express a workflow SDLE does not
  currently need, that is a defect under §13, not a feature.
