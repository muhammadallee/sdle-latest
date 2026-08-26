# T07 Plan — Replace Fixed Universal Sequence with Declarative Flow Selection

**Phase:** T07
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED
**Contract sections:** §13 (the phase), §5 (overview row), §18 (`fixed 18 phases | REPLACE T07`), §24.2 (this stage)
**Precondition HEAD:** `c0775b3` on `transition/workitem-v1`
**Rollback point:** `c0775b3`
**SDLE product baseline:** `f8fdaa0`

> **The planner wrote no product code and edited no test.** Every figure below was
> produced by a command run in this planning context and is classed `OBSERVED`.
> Where a fact was not established here it says `UNKNOWN` and no outcome is predicted.

---

## Objective

Retire the assumption that every WorkItem traverses the same nineteen phases.

Introduce a **declarative flow table** naming the five contract-required flows,
bind exactly one flow per WorkItem, and make every traversal decision read that
flow instead of the single global `NEXT_PHASE` chain — **without** weakening a
single deterministic guarantee, and **without** building a generic workflow
engine.

§13's exit criterion, restated as the thing that must be demonstrable:

> Flow selection changes which phases execute without compromising
> deterministic state transitions.

Two things T07 deliberately does **not** do, both because §13 says so:

1. **It does not delete the old fixed tables.** `PHASE_SEQUENCE`, `NEXT_PHASE`,
   `PHASE_LABEL_MAP`, `PROGRESS_MAP` and `PHASE_TO_GATE_KEY` all remain, all
   remain linted, and `GREENFIELD` is defined as *exactly* `PHASE_SEQUENCE`.
   That equality **is** the compatibility translation §13 requires.
2. **It does not make gates conditional on risk.** That is T09. T07 changes
   which *phases* are in a flow; T09 changes which *gates* a risk level
   requires. The boundary is enforced by a test that already exists and must
   stay green untouched (see A11).

---

## Repository evidence

Every row was checked in this context at `c0775b3`.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `c0775b3`; tree clean apart from `.claude/settings.local.json` | OBSERVED | `git rev-parse HEAD` = `c0775b3d3f7d7f62e6bb7891114f1d2f11ac5727`; `git status --porcelain` = one line, ` M .claude/settings.local.json` |
| E2 | Full suite is green | OBSERVED | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **`791 passed in 849.77s (0:14:09)`, RAW EXIT 0**; `grep -c "short test summary"` over the captured run = **0**, so zero skips, xfails and errors |
| E3 | Collected == passed | OBSERVED | `python -m pytest --collect-only -q` → **`791 tests collected in 0.67s`** |
| E4 | `lint-skill` is clean at 22 checks | OBSERVED | `python scripts/sdle.py --project-root . lint-skill` raw exit **0**; `"failed": []`; count of `"passed": true` = **22** |
| E5 | Transition control plane is valid and T07 is next | OBSERVED | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=7/12 next=T07`, exit **0** |
| E6 | `c0775b3` is the NB-6 follow-up on top of T06 a02 and touched product code | OBSERVED | `git diff --numstat 0a9b8c7 c0775b3` = `scripts/sdle.py 9/0`, `tests/test_units_governance.py 66/6`, plus two control-plane files |
| E7 | Host Python is 3.13; Python 3.11 and CI have never run | OBSERVED / UNKNOWN | Prior verification artifacts record host 3.13.0; branch is local-only. **No CI outcome is predicted.** |
| E8 | Disk has headroom | OBSERVED | `df -h .` → `D: 400G, 21G avail` |
| E9 | The four phase tables live in `SKILL.md` under `### PHASE_SEQUENCE (ordered)`, `### NEXT_PHASE`, `### PHASE_TO_GATE_KEY`, `### PHASE_LABEL_MAP`, `### PROGRESS_MAP`; `### GATE_TO_EXECUTION_PHASE` lives in `modules/gate-protocol.md` | OBSERVED | `grep -n '^###' .claude/skills/sdle/SKILL.md`; `load_constants` reads `paths.gate_protocol_md` for the last one |
| E10 | `GATE_PHASES` is already **derived**, not stored | OBSERVED | `Constants.gate_phases` property: `[p for p in self.phase_sequence if p in self.phase_to_gate_key]`, and SKILL.md's note under PHASE_TO_GATE_KEY says so |
| E11 | The linter enforces one linear chain | OBSERVED | `run_sync_checks` → `next_phase_chains_sequence`, `phase_set_matches_*`, `progress_denominator_matches_phase_count` |
| E12 | `apply_advance` is the single traversal choke point, with a closed three-member caller set | OBSERVED | `governance_precondition` docstring; `test_units_governance.py` asserts `callers == ["apply_advance", "cmd_gate_approve", "cmd_skip"]` and `movers == ["cmd_advance", "cmd_gate_approve", "cmd_skip"]` |
| E13 | `cmd_init` performs a phase move **without** `apply_advance`, reading `consts.next_phase["requirements_check"]` directly | OBSERVED | `cmd_init` body: `nxt = consts.next_phase["requirements_check"]` |
| E14 | T06 records the engineering flow and marks it advisory | OBSERVED | `evaluate_classification` returns `{"type": ..., "flow": ..., "advisory": True}` with the docstring "ADVISORY: nothing in the engine routes on either value at T06"; `ENGINEERING_FLOWS` is the closed five-member tuple |
| E15 | The would-be gate set is inert and a test pins that | OBSERVED | `required_gate_set` docstring; `test_no_phase_movement_function_consults_the_would_be_gate_set` asserts no `cmd_advance` / `cmd_gate*` / `cmd_skip` / `apply_advance` function references `required_gate_set` or the string `wouldBeRequiredGates` |
| E16 | The shared test fixture records `flow: "ITERATIVE"` today | OBSERVED | `tests/conftest.py`, `Project.record_governance`, `"classification": {"type": "enhancement", "flow": "ITERATIVE"}` |
| E17 | T06 shipped a differential test asserting classification changes **no** traversal | OBSERVED | `test_governance_changes_no_lifecycle_behaviour` in `tests/test_units_governance.py`, variants `baseline`/`classification_only`/`risk_only`/`both` carrying `ITERATIVE`, `DEFECT_FIX`, `ITERATIVE`, `HOTFIX`; asserts `traversal == EXPECTED_TRAVERSAL` for all four |
| E18 | `EXPECTED_TRAVERSAL` and `run_happy_path` are owned by the dry-run 01 integration test | OBSERVED | `tests/test_units_governance.py` line 28: `from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path` |
| E19 | `spec_draft` is where the Spec Kit feature directory comes into existence | OBSERVED | `modules/phase-execution.md`, Phase 4 block: "**Feature-Directory Resolution (MANDATORY after spec runs):** `sdle.sh feature resolve`" |
| E20 | Every later generation phase requires a resolved feature directory | OBSERVED | Phases 6, 8, 9, 11, 15 each call `sdle.sh feature bind --require-feature`, which "additionally refuses when no feature directory is recorded" |
| E21 | `gate_analyze`'s artifact is `tasks.md`, the same file `gate_tasks` owns | OBSERVED | `### ARTIFACT_OWNERSHIP` maps both `gate_tasks` and `gate_analyze` to `{speckit_feature_directory}/tasks.md`; Phase 11 runs `drift rebaseline --gate gate_tasks` for exactly this reason |
| E22 | The checklist is already optional | OBSERVED | Phase 8 block: "If checklist.md was **not produced** or is <100 bytes … Do **not** set status to 'failed'. Do not halt." |
| E23 | The implement prompt asserts design documents unconditionally | OBSERVED | Phase 15 block appends `"Design documents are available at design/app/app-design.md and (if present) design/db/db-design.md."` |
| E24 | `compute_drift` and `cmd_repo_staleness` iterate gates but skip anything unapproved or unresolvable | OBSERVED | `compute_drift` `continue`s on a non-`approved` decision and on a missing baseline; `cmd_repo_staleness` `continue`s when `resolve_artifact_path` returns nothing |
| E25 | `.claude/hooks/hooks.py` names exactly one phase, `implement` | OBSERVED | `grep -n 'phase\|gate' .claude/hooks/hooks.py` → only `state.get("current_phase") != "implement"` and prose |
| E26 | No prompt file contains a `N/9`, `N/13` or `N/16` string today | OBSERVED | `grep -nE '[0-9]+/(9\|13\|16)\b'` over `SKILL.md`, `phase-execution.md`, `gate-protocol.md`, `security-review.md` → exit 1, no matches |
| E27 | `**v1.15**` at `README.md:575` is the first `\*\*vN.N\*\*` match the version linter finds | OBSERVED | `grep -n '\*\*v1\.1' README.md`; `_check_version_consistency` uses `re.search(r"\*\*v([0-9]+\.[0-9]+)\*\*", text)` |
| E28 | `SDLE v1.15` at `docs/SDLE-Reference-Guide.md:7` is the first match of the guide's header regex | OBSERVED | `grep -n 'SDLE v1.15' docs/SDLE-Reference-Guide.md` → first hit is line 7 |
| E29 | `tests/test_lint_skill.py` asserts no check **count**; it asserts `failed == []` and one firing test per rule | OBSERVED | `test_the_repo_passes_every_check` asserts `result.data["failed"] == []`; every other case uses `assert_only_failure` |
| E30 | The state template carries no `flow` field and `CURRENT_VERSION` is `1.15` | OBSERVED | `.claude/skills/sdle/templates/state.json`; `scripts/sdle.py` `CURRENT_VERSION = "1.15"` |
| E31 | `parse_md_table` refuses rather than defaulting on a missing heading, a malformed row or zero rows | OBSERVED | `constants_heading_missing`, `constants_malformed`, `constants_empty` raises in `parse_md_table` |
| E32 | `_normalise_cell` strips exactly one outer backtick pair and maps `-`/`none`/`(none)` to `None` | OBSERVED | `_normalise_cell` body and `_NULLISH` |
| E33 | The nine dry-run transcripts are all `N/18` GREENFIELD runs | OBSERVED | `docs/dry-runs/README.md` scenario table and the header format block `progress=<N/18>` |
| E34 | Traversal call-site volume in `scripts/sdle.py` | OBSERVED | `grep -c`: `consts.next_phase` **10**, `consts.progress` **12**, `consts.gate_phases` **7**, `consts.index(` **7**, `consts.phase_at(` **1**, `consts.gate_number` **5**, `consts.phase_sequence` **12** |
| E35 | `.claude/commands/sdle-restart.md` restates a constant in its argument hint | OBSERVED | `argument-hint: "<phase number 1-18>"` |
| E36 | The F1 `ENVIRONMENT_FLAKE` procedure is void | OBSERVED / INFERRED | E2 shows a fully green suite; `6e8af8c` fixed the `write_atomic` `WinError 5` flake. **Any T07 failure is a presumed regression.** |

**Refusals encountered by the planner.** One, declared verbatim and not routed around:

```
PreToolUse:Bash hook error: [python tools/transition/agent_guard.py planner]: SDLE transition agent guard: planner Bash/PowerShell must be observational; blocked command shape
```

It fired on an attempt to run the suite with stdout redirected to a scratch file.
The suite was then run unredirected via the background task facility, which the
guard permits; no guard change was requested and none was made.

---

## Behavioral delta

### Deliberate changes

**D1 — A flow is an ordered subset of `PHASE_SEQUENCE`. Nothing is reordered and no phase is invented.**

`PHASE_SEQUENCE` becomes the **phase registry**: the closed catalogue of the
nineteen phases SDLE knows how to execute, in canonical order. A *flow* is an
ordered subset of that registry, preserving registry order.

Two consequences, both deliberate and both departures from §13's *suggested*
shapes (§13 labels them "Suggested lifecycle shape", not requirements):

- **No new phases.** §13's GREENFIELD sketch names "Converge" and "Human
  Review" and its DEFECT_FIX sketch names "Impact analysis", "existing spec
  mapping" and "spec delta/gap". Adding registry entries for these would change
  GREENFIELD's traversal, which would destroy the compatibility translation
  §13 explicitly requires, break all nine dry-runs at once, and change the
  `N/18` denominator that appears in ~40 documented strings. They map onto
  existing phases instead: converge/human review onto `gate_security`
  (the terminal human gate that writes the completion summary), impact
  analysis and spec delta onto `spec_draft` + `analyze`.
- **No reordering.** §13's DEFECT_FIX sketch puts impact analysis *before* the
  spec. `ARTIFACT_OWNERSHIP` binds `gate_analyze` to `{speckit_feature_directory}/tasks.md`
  (E21), so `analyze` cannot precede `tasks_draft` without inventing a new
  artifact — a new-phase change by another name. Registry order is preserved.

**D2 — The five flows, by exact phase membership.**

`GREENFIELD` is **derived from `PHASE_SEQUENCE`**, not listed. That mirrors the
`GATE_PHASES` precedent (E10) and makes the compatibility translation true by
construction rather than by a lint check that could be edited.

The other four are declared in a new `### FLOW_PHASES` table in `SKILL.md`:

| Flow | Phases (registry order) | Non-terminal phases | Gates |
|---|---|---:|---:|
| `GREENFIELD` | *(derived: all of `PHASE_SEQUENCE`)* | 18 | 8 |
| `BROWNFIELD_DISCOVERY` | identical membership to `GREENFIELD`, declared explicitly | 18 | 8 |
| `ITERATIVE` | GREENFIELD minus `constitution_draft`, `gate_constitution` | 16 | 7 |
| `DEFECT_FIX` | `requirements_check`, `spec_draft`, `gate_spec`, `plan_draft`, `gate_plan`, `tasks_draft`, `gate_tasks`, `analyze`, `gate_analyze`, `implement`, `gate_implement`, `security_review`, `gate_security`, `complete` | 13 | 5 |
| `HOTFIX` | `requirements_check`, `spec_draft`, `gate_spec`, `plan_draft`, `tasks_draft`, `implement`, `gate_implement`, `security_review`, `gate_security`, `complete` | 9 | 3 |

Rationale, per flow:

- **`ITERATIVE`** — §13: "Use established repository baseline. No full
  repository rediscovery." The constitution is the repository-level baseline
  artifact: `ARTIFACT_OWNERSHIP` maps `gate_constitution` to the static,
  repository-scoped `.specify/memory/constitution.md`, not to a WorkItem path,
  and T04 deliberately left `.specify/memory/` at the repository root. An
  iterative WorkItem inherits it. Everything else is retained.
- **`DEFECT_FIX`** — additionally drops `checklist_draft` (already optional,
  E22) and `design_generation` + `gate_design` (a defect fix produces no new
  application or database design document; `design/app/app-design.md` is
  repository-shared and pre-existing).
- **`HOTFIX`** — §13: "Shorter but never ungoverned. Mandatory risk/policy
  checks remain." HOTFIX is defined to be **exactly the mandatory minimum**
  (D3), so "never ungoverned" becomes a testable identity rather than a
  judgement call.
- **`BROWNFIELD_DISCOVERY`** — declared with GREENFIELD's membership at T07
  and **owned by T08**, which introduces the discovery phase and
  `.sdle/baseline.*` (§14). Declaring it now means the flow is selectable and
  bound, and T08's change to its row is a one-line, visible, lint-checked diff.
  A test pins the current equality so the T08 change cannot happen silently.

**D3 — `MANDATORY_FLOW_PHASES`: the governance floor a flow may never drop below.**

A closed set, defined once in `scripts/sdle.py`, enforced by `lint-skill` **and**
by the `Constants` loader (so a hand-edited SKILL.md cannot smuggle a
degenerate flow past the engine at runtime):

```
requirements_check  spec_draft  gate_spec  plan_draft  tasks_draft
implement  gate_implement  security_review  gate_security  complete
```

Each membership has a named reason:

| Phase | Why it can never be dropped |
|---|---|
| `requirements_check` | Bootstrap. `cmd_init` writes it as the first phase unconditionally. |
| `spec_draft` | The only phase that creates the Spec Kit feature directory (E19). Without it every later `feature bind --require-feature` refuses (E20). |
| `gate_spec` | The first human gate. A flow with no gate before implementation would be ungoverned. |
| `plan_draft` | `speckit-tasks` derives from `plan.md`. |
| `tasks_draft` | `speckit-implement` derives from `tasks.md`; `gate_tasks`/`gate_analyze` own it. |
| `implement` + `gate_implement` | The implementation manifest carries the secrets scan and the test evidence. §15's preserve list names both; §28 forbids removing a safety control because new requirements did not repeat it. |
| `security_review` + `gate_security` | §15's preserve list; the terminal human gate; the completion summary is written here. |
| `complete` | Terminal. |

By construction `HOTFIX` == `MANDATORY_FLOW_PHASES`. The lint check is
`every_flow_retains_the_mandatory_phases`; the runtime check refuses
`flow_table_invalid` (exit 3) rather than defaulting.

**D4 — One new state field, `flow`, bound once and never re-bound.**

`state.json` gains `flow`. `workflow_version` `1.15` → **`1.16`**, with a 16th
`VERSION_MIGRATION` row and `_mig_1_15`.

- `_mig_1_15` sets `flow: "GREENFIELD"` unconditionally when the field is
  missing. That is the compatibility translation stated as code: **every
  pre-v1.16 workflow traversed exactly `PHASE_SEQUENCE`, which is GREENFIELD.**
  The migration never consults the governance record — a migration must not
  change what an in-flight workflow is doing.
- `cmd_init` binds it: from the governance record's `classification.flow` when
  a record exists, otherwise `"GREENFIELD"`. Governance deliberately remains
  **not** an `init` precondition (T06's decision, unchanged), so the
  no-record case must exist and must be the safe one.
- Nothing else ever writes it. **There is deliberately no `flow set` /
  `flow select` command** — a second writer of traversal identity would be a
  bypass of governance, and the model must not be able to reshape the
  lifecycle by issuing a command.

**D5 — `flow_mismatch`: a flow cannot change under a running workflow.**

`apply_advance`, immediately after `governance_precondition` succeeds, refuses
when a governance record exists and its `classification.flow` differs from
`state["flow"]`:

```
reason: flow_mismatch  (exit 1)
This WorkItem is traversing <bound>; the governance record now proposes
<proposed>. A flow cannot change under a workflow that has already started.
Either re-assess with flow <bound>, or `reset workflow` and start again.
```

It refuses; it does not warn. Placement matters and is pinned: after the
existing `forward_jump` and `gate_not_approved` refusals and after
`governance_precondition`, so no existing refusal is masked, and — critically —
**before** any state mutation, so a refused advance still leaves `audit.md`
byte-identical (B1 / NB-6, freshly fixed at `0a9b8c7` and `c0775b3`, must not
regress). The two early pure-reader prechecks in `cmd_gate_approve` and
`cmd_skip` gain the same check, in the same position and with the same
`state=None` discipline, for exactly the reason T06 recorded: those two
commands append to the ledger before they call `apply_advance`.

**Declared consequence, not a defect:** a workflow initialised before v1.16
that already carries a T06 governance record proposing a non-GREENFIELD flow
will refuse `flow_mismatch` at its next advance. That is correct — it *was*
traversing GREENFIELD — and the remedy is one command. Pinned by a test
(N14). Recorded for T11's hardening list.

**D6 — Progress and gate numbering become derived, per flow.**

- `progress` becomes `<position>/<flow non-terminal count>`, computed by the
  flow. `complete` maps to `<count>/<count>`. For GREENFIELD this reproduces
  `PROGRESS_MAP` **exactly**, which is the M1 proof.
- `gate_number` becomes the gate's 1-based position among the flow's gate
  phases, and `gate_total` becomes the flow's gate count. For GREENFIELD this
  reproduces `1..8` and `8` exactly. So `HOTFIX` shows `Gate 2/3` where
  GREENFIELD shows `Gate 7/8` for the same `gate_implement`.
- `PROGRESS_MAP` and `PHASE_TO_GATE_KEY`'s `gate number` column stay in
  `SKILL.md` as the human-readable GREENFIELD views, and **two new lint checks
  pin them equal to the derived values**. They stop being independent sources
  of truth and become checked derived views. That is a strengthening of
  invariant 7, not a relaxation, and their removal belongs to T11.

**D7 — `restart --to <N>` becomes flow-relative.**

`restart` currently indexes `PHASE_SEQUENCE`. Under a flow it indexes the
**flow's** phase list, so it stays consistent with the `Phase N/M` the user is
shown. Identical under GREENFIELD. `.claude/commands/sdle-restart.md`'s
`argument-hint` loses its restated `1-18` (E35).

**D8 — `forward_jump` absorbs "not in this flow"; `unknown_phase` keeps its meaning.**

A target that is not in the registry at all still refuses `unknown_phase`
(exit 1) — `test_advance_refuses_unknown_phase` stays green untouched. A target
that is in the registry but not in the bound flow refuses `forward_jump`, with
`"in_flow": false` added to `data` so the caller can tell the two apart.
Index fields in the refusal payload are computed defensively (`None` when the
phase is outside the flow) so index lookup can never raise and mask the real
reason.

**D9 — One new read-only command, `flow show`.**

Returns the bound flow, its ordered phases, its gate phases, the next phase
from here, and — when a governance record exists — the proposed flow and
whether it agrees. Always read-only; it is how the orchestrator asks the script
instead of reading a table (SKILL.md's own instruction). `constants` gains a
`flows` key for the same reason. Neither writes anything.

**D10 — Text that T07's own change makes untrue is fixed by T07.**

Three strings become inaccurate *because of* this phase and are therefore owned
by it (they are not adopted hygiene):

- `record_governance_audit`'s ledger message says `classification <type>/<flow> (advisory)`.
  The flow is no longer advisory. The parenthetical becomes accurate.
- `evaluate_classification` returns `"advisory": True` and a docstring saying
  "nothing in the engine routes on either value at T06". The value flips to
  `False` and the docstring records that the **flow** now binds traversal while
  the **type** is still consumed by nothing until T09. This is a value change,
  not a shape change: `GOVERNANCE_RECORD_VERSION` stays `"1"`. The separate
  `"advisory": True` emitted by `cmd_governance_gates` **stays `True`** — the
  would-be gate set really is still inert. Its explanatory `note` is reworded
  to say that gates *within the selected flow* run unconditionally.
- `modules/phase-execution.md` Phase 15 asserts the design documents exist
  (E23). Under `DEFECT_FIX` and `HOTFIX` they may not. The sentence becomes
  conditional on the file being present.

**D11 — Not changed, and worth stating.** `compute_drift` and
`cmd_repo_staleness` iterate the full gate set but already skip anything
unapproved or unresolvable (E24). Out-of-flow gates are never approved, so both
are flow-correct with **zero** edits. `.claude/hooks/hooks.py` names only
`implement`, which is in `MANDATORY_FLOW_PHASES` (E25), so the hooks are
untouched. `write_atomic`, `append_audit`, the audit hash chain, `save_state`,
`read_state`, `bind_workitem`, `resolve_decision`, `cmd_migrate_workflow`,
`SDLE_OWNED_PREFIXES`, `RUNTIME_FREE_COMMANDS` and the write fence are all
untouched.

### Preserved invariants

Each of these must be demonstrable *after* traversal becomes flow-dependent.

| Invariant | How T07 preserves it |
|---|---|
| **Gate discipline** — no advance past a gate without explicit approval, no forward jumps | The `gate_not_approved` and `forward_jump` refusals stay in `apply_advance`, in their existing order, ahead of everything T07 adds. A gate that is in the flow is unconditional exactly as today. A gate that is not in the flow never becomes the current phase, so there is nothing to bypass. |
| **Fail safe** — freeze on failure, never advance | Every T07 refusal is raised before any mutation of `state` and before any `append_audit`. `flow_table_invalid` is exit 3. Nothing defaults. |
| **Single writer** | Only `sdle.py` writes state and audit. T07 adds no writer. `flow show` and `constants` are read-only. |
| **A refusal leaves `audit.md` byte-identical** (B1 / NB-6) | The `flow_mismatch` check is added to the two early pure-reader prechecks in `cmd_gate_approve` and `cmd_skip` alongside the governance one, at the same position, with `state=None`. Pinned by A9. |
| **The ladder never guesses** | Untouched. WorkItem resolution is not in T07's diff. |
| **Legacy `.workflow/` dual-read still works** (T11 removes it) | Under the legacy binding `paths.workitem is None`, so `governance_precondition` returns early and there is no record to disagree with; `_mig_1_15` gives such a state `GREENFIELD`, which is what it was traversing. |
| **`migrate-workflow` never mutates `.workflow/`** | Not in T07's diff; pinned by A13. |
| **Invariant 3** — `speckit-*` never shown outside verbose | No new user-facing string names a Spec Kit command. |
| **Invariant 7** — one source of truth per fact | `GREENFIELD` is derived, not stored twice. `PROGRESS_MAP` and the gate-number column become lint-pinned derived views. The one deliberate, contract-mandated duplication is `NEXT_PHASE` (see below). |
| **Invariant 8** — gates stay in the parent session | Flow selection is a *deterministic* consequence of the governance record; it is not a gate, and no subagent is introduced. |
| **The core refuses; it does not warn** | `flow_mismatch` and `flow_table_invalid` are refusals with named remedies. No new warning is added anywhere. |

**The one declared duplication.** After T07, `NEXT_PHASE` and the derived
GREENFIELD chain encode the same fact. §13 orders this: *"Do not delete old
fixed tables immediately. Introduce a compatibility translation first."*
`NEXT_PHASE` remains parsed, remains linted by the unchanged
`next_phase_chains_sequence`, and is **no longer read by any traversal code
path** — a new lint-adjacent test (N16) asserts that. §17 lists "universal
fixed 18-phase assumption" under T11's removals; that is where the table goes.

---

## What "the four phase tables agree" means after T07

This is the question the linter redesign has to answer. The answer is that the
existing meaning is **kept, not weakened**, and four checks are added on top.

**Kept, byte-for-byte unchanged:**

| Existing check | Still means |
|---|---|
| `tables_wellformed` | The constants parsed. Short-circuits everything else. |
| `phase_set_matches_next_phase` / `_phase_label_map` / `_progress_map` | The three tables cover the registry identically. |
| `next_phase_chains_sequence` | `NEXT_PHASE` still chains the registry exactly. It is now the GREENFIELD chain and the registry's canonical-order proof. |
| `progress_denominator_matches_phase_count` | GREENFIELD's denominator is still 18. |
| `gate_registered_<key>` (×8) | Every registered gate is still in `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE` and the state template's `approvals`. **The template keeps all eight approval keys**; a flow that omits a gate simply leaves it `null` forever. No schema change to `approvals`. |
| `every_phase_has_execution_block` | Every registry phase still has a `phase-execution.md` block — a phase is executable if it is in the registry, independent of which flows use it. |
| `single_state_template`, `version_string_consistent`, `migration_covers_every_state_field`, `no_powershell_only_cmdlets` | Unchanged. |
| `doc_lists_every_phase_*` | Unchanged: README and the Reference Guide still name every registry phase. |

**Generalised (strictly stronger):**

| Check | Change |
|---|---|
| `no_hardcoded_progress_outside_progress_map` | Today it scans for `\d+/18`. It becomes `\d+/<d>` for **every** flow denominator — `18`, `16`, `13`, `9`. E26 confirms this passes at HEAD with zero false positives, so the generalisation is free. |

**Added (four new checks):**

| New check | Asserts |
|---|---|
| `flow_table_covers_the_required_flows` | `FLOW_PHASES` plus the derived GREENFIELD name exactly `ENGINEERING_FLOWS` — no missing flow, no extra flow. |
| `every_flow_is_an_ordered_subset_of_phase_sequence` | Every phase named is in the registry; no duplicates; strictly increasing registry position; starts `requirements_check`; ends `complete`. |
| `every_flow_retains_the_mandatory_phases` | D3's floor. |
| `progress_map_and_gate_numbers_are_the_derived_greenfield_views` | `PROGRESS_MAP` equals the derived GREENFIELD progress for every phase, and `PHASE_TO_GATE_KEY`'s `gate number` column equals the derived GREENFIELD gate numbering. |

Each new check gets an additive firing test in `tests/test_lint_skill.py`
following the existing `assert_only_failure` pattern (E29 — that file asserts
no check count, so nothing there breaks).

---

## Dry-run disposition (contract §13, explicit)

§13 gates the removal of legacy fixed-sequence structures on three conditions.
T07 satisfies "new flow tests pass" and "migration path exists", gives the
disposition below, and **does not perform the removal** — §17 assigns that to
T11. The disposition:

| Transcript | Disposition | Reason |
|---|---|---|
| `01-happy-path.md` | **Valid, unchanged, and load-bearing** | It is a GREENFIELD run. `EXPECTED_TRAVERSAL` and `run_happy_path` (E18) are imported by the governance suite. Its integration test must stay green **with zero edits** — that is T07's compatibility proof (A6). |
| `02` rejection/remediation | Valid, unchanged | GREENFIELD; rejection and remediation are flow-independent. |
| `03` retry/skip | Valid, unchanged | GREENFIELD; `skip` advances to the next phase *in the flow*, identical under GREENFIELD. |
| `04` drift re-approval | Valid, unchanged | Drift is gate-keyed and skips unapproved gates (E24, D11). |
| `05` untrusted content | Valid, unchanged | Pre-lifecycle scanning; no traversal. |
| `06` secrets / dirty tree | Valid, unchanged | `implement` is in every flow (D3). |
| `07` audit integrity / session lock | Valid, unchanged | No traversal. |
| `08` restart / reset / state jump | **Valid, unchanged — with a recorded semantic note** | `restart phase N` becomes flow-relative (D7). Under GREENFIELD the transcript is byte-correct. A non-GREENFIELD restart transcript is **not authored at T07**. |
| `09` bootstrap failures | Valid, unchanged | Pre-`init`; no flow is bound yet. |

**No transcript documents behaviour that ceases to exist.** All nine remain the
GREENFIELD acceptance specification.

**Not regenerated at T07, deliberately:** no transcript is authored for
`ITERATIVE`, `DEFECT_FIX`, `HOTFIX` or `BROWNFIELD_DISCOVERY`. A dry-run is a
*conversational* artifact containing simulated Spec Kit output; authoring four
more would multiply the documentation debt these files already carry (T04's
N-6: ~17 stale `.workflow/` path lines, owned by T11) without adding a single
executable guarantee. Non-GREENFIELD traversal is pinned instead by end-to-end
engine tests driving the real CLI (N1–N6), which is strictly stronger evidence
than prose.

**One documentation change:** a short paragraph is added to
`docs/dry-runs/README.md` recording exactly the above — that all nine
transcripts are GREENFIELD traversals and remain the GREENFIELD acceptance
spec, that other flows are covered by tests rather than transcripts, and that
regenerating them for other flows is unowned future work. The pre-existing
stale `.workflow/` lines in those files are **not** touched (T11's, per T04 N-6).

---

## Files expected to change

**Engine**

- `scripts/sdle.py` — the whole of T07's mechanism:
  `Flow` dataclass and `Constants.flows` / `Constants.flow()`; `FLOW_PHASES`
  parsing in `load_constants`; `MANDATORY_FLOW_PHASES`; `flow_for_state()`;
  `flow_mismatch`; `CURRENT_VERSION` → `1.16`; `_mig_1_15` and its `MIGRATIONS`
  row; `cmd_flow_show` and its parser registration; `cmd_constants` gains
  `flows`; the four new lint checks and the generalised
  `_check_no_hardcoded_progress`; and the traversal call sites in
  `cmd_init`, `apply_advance`, `cmd_advance`, `cmd_gate_approve`,
  `_approve_drift`, `cmd_gate_reject`, `cmd_gate_show`, `cmd_skip`,
  `cmd_restart`, `cmd_doctor`, `render_header`, `cmd_state_dump`,
  `write_completion_summary`, `evaluate_classification`,
  `record_governance_audit`, `cmd_governance_gates`.
  **Not touched:** `compute_drift`, `cmd_repo_staleness`, `write_atomic`,
  `append_audit`, `save_state`, `read_state`, `bind_workitem`,
  `resolve_decision`, `cmd_migrate_workflow`, `cmd_workitem_*`, `cmd_config_*`,
  `cmd_feature_*`, `cmd_artifact_*`, `governance_precondition`'s body,
  `required_gate_set`.

**Prompt layer**

- `.claude/skills/sdle/SKILL.md` — new `### FLOW_PHASES` table in Internal
  Constants; a short flow paragraph in Step 1 stating that governance is
  assessed **before `init`** because that is where the flow binds; the six-site
  version string (frontmatter + heading); the 16th `VERSION_MIGRATION` row; the
  `18-Phase Workflow` heading and description qualified as the GREENFIELD flow.
- `.claude/skills/sdle/templates/state.json` — `flow` field, `workflow_version` `1.16`.
- `.claude/skills/sdle/modules/phase-execution.md` — the traversal instruction
  (ask `advance` / `flow show`; a phase absent from the flow is never executed
  and never mentioned); D10's conditional design-document sentence.
- `.claude/skills/sdle/modules/gate-protocol.md` — gate numbering is
  `Gate N/M` from the script, not a fixed `N/8`; the completion line's "All 8
  gates passed" becomes flow-derived. **The stale `.workflow/completion-summary.json`
  path on that same line is left alone (T11 / N-6).**
- `.claude/commands/sdle-restart.md` — argument hint (E35, D7).

**Documentation**

- `README.md` — title version, the `**v1.16**` history row inserted **above**
  `**v1.15**` (E27), and the `18 phases · 8 approval gates` headline qualified.
- `docs/SDLE-Reference-Guide.md` — line 7's covers-version row (E28), and one
  new short section on the flow model.
- `CLAUDE.md` — the "gated 18-phase SDLC workflow" sentence, and one line in
  the cross-file sync list for the new checks.
- `docs/dry-runs/README.md` — the disposition paragraph.
- `docs/architecture/ADR-004-declarative-flow-model.md` — **new**, following
  ADR-002 and ADR-003: what was chosen, what was rejected (new phases,
  reordering, a generic workflow engine, a `flow set` command), and every
  deliberate divergence from §13's suggested shapes.

**Tests**

- `tests/test_units_flow_model.py` — **new**, the phase's own suite.
- `tests/test_lint_skill.py` — **additive only**: one firing test per new check.
- `tests/conftest.py` — **exactly one line** (see the anti-contradiction clause).
- `tests/test_units_governance.py` — the rewritten differential (N7) plus the
  `advisory` and audit-message assertions D10 invalidates.
- Version-assertion lines wherever `1.15` is asserted, and ordered-audit-event
  assertions the new `flow_selected` entry shifts.

**Must not change** (`git diff --exit-code c0775b3` over this list must be exit 0):

```
.claude/hooks/                     .claude/settings.json
scripts/sdle.sh                    scripts/sdle.ps1
scripts/README.md                  .github/
.gitignore                         .gitattributes
requirements/                      tools/
docs/dry-runs/01..09 (the nine transcripts themselves)
docs/architecture/ADR-001, ADR-002, ADR-003
.claude/skills/sdle/modules/security-review.md
docs/transition/transition.md      docs/transition/baseline.md
docs/transition/phases/T00..T06 (every plan, handoff, verification, checkpoint, blocker)
```

---

## Anti-contradiction clause (shared fixtures)

T07 changes traversal, which every shared fixture depends on. To keep the
diff attributable:

**The only permitted edit to `tests/conftest.py` is one line:**
`Project.record_governance`'s default `"classification": {"type": "enhancement", "flow": "ITERATIVE"}`
becomes `"flow": "GREENFIELD"` (E16).

TP-003 category **2 — deliberately superseded behaviour**: at T06 that value was
recorded and inert, so any member of `ENGINEERING_FLOWS` was equally valid as a
fixture default; at T07 it selects the traversal. The shared `started` fixture's
own docstring says the project sits at `constitution_draft` — a phase only
GREENFIELD has. `GREENFIELD` is therefore the value that keeps every existing
assertion in every other file byte-identical.

**Every other change to `tests/conftest.py` is forbidden** — no new fixture, no
new helper, no signature change, no `Project` method. All new helpers live in
`tests/test_units_flow_model.py`. If the implementer believes a second conftest
edit is unavoidable, that is a plan defect: record it as a declared divergence
with the reason, do not make it silently.

`tests/test_lint_skill.py` may receive **new test functions only**. No existing
test in that file may be modified or deleted.

---

## Existing tests affected

TP-003 classification. There is no fourth category.

| File / test | Category | Why |
|---|---|---|
| `tests/conftest.py` `record_governance` | **2 — superseded** | The anti-contradiction clause. One line. |
| `test_units_governance.py::test_governance_changes_no_lifecycle_behaviour` (E17) | **2 — superseded** | It asserts all four governance variants traverse identically. T07's whole point is that two of them must not. Rewritten as N7 — and the rewrite is *stronger*, because it keeps the risk half of the assertion. |
| `test_units_governance.py` — `record["classification"] == {..., "advisory": True}` and any assertion on the `(advisory)` ledger text | **2 — superseded** | D10. |
| Any test asserting `workflow_version == "1.15"`, the `1.14 → 1.15` terminal migration row, or the parsed migration-row count of 15 | **2 — superseded** | D4's version bump. Same shape of edit T04 made for `1.15`. |
| Ordered-audit-event assertions that see the new `flow_selected` entry | **2 — superseded** | D4. The entry is a *new* governed fact, not a changed one. |
| `test_integration_01_happy_path.py`, `EXPECTED_TRAVERSAL`, `run_happy_path` | **1 — unchanged, must stay green with zero edits** | The compatibility proof (A6). |
| `test_units_transitions.py` (all 22) | **1 — unchanged** | Driven by `started`, which is GREENFIELD after the conftest flip. |
| `test_integration_02_to_05.py`, `test_integration_06_to_09.py` | **1 — unchanged** apart from any version literal | GREENFIELD transcripts. |
| `test_units_governance.py::test_no_phase_movement_function_consults_the_would_be_gate_set` and `::test_the_phase_movement_prefixes_actually_match_something` | **1 — unchanged, and must stay green untouched** | These are T07's structural proof that it did not drift into T09 (A11). |
| `test_units_governance.py` closed-caller-set and `movers` assertions (E12) | **1 — unchanged, and must stay green untouched** | T07 must not add a fourth caller of `governance_precondition` or of `apply_advance`. In particular `cmd_init` must **not** start calling `apply_advance` (A12). |
| `test_units_workitem.py`, `test_units_workitem_resolution.py`, `test_units_workitem_runtime.py`, `test_units_speckit_binding.py`, `test_units_repo_config.py`, `test_hooks.py`, `test_units_infra.py`, `test_units_cli.py`, `test_units_artifact_review.py` | **1 — unchanged** apart from version literals | No traversal dependency beyond the shared fixture. |

**No test may be weakened, skipped, xfailed or deleted.** The suite currently
has zero skips and zero xfails (E2/E3) and must still have zero at the end.

---

## New tests required

All in `tests/test_units_flow_model.py` unless noted. Every one drives the real
CLI as a subprocess through the existing `Project` fixture machinery.

**Traversal**

- **N1** `GREENFIELD` end-to-end: traversal equals `EXPECTED_TRAVERSAL` and
  equals `PHASE_SEQUENCE`, 8 gates, `18/18` at completion.
- **N2** `ITERATIVE` end-to-end: `init` lands on `spec_draft` (not
  `constitution_draft`), `constitution_draft` and `gate_constitution` never
  appear in `phase_history` or the ledger, 7 gates approved, final progress
  `16/16`, `approvals.gate_constitution` is still `null`, `audit verify` exit 0.
- **N3** `DEFECT_FIX` end-to-end: 13 phases, 5 gates, `design_generation`,
  `gate_design` and `checklist_draft` absent, final progress `13/13`.
- **N4** `HOTFIX` end-to-end: 9 phases, 3 gates, `gate_implement` renders as
  `Gate 2/3`, final progress `9/9`, and a completion summary is still written.
- **N5** `BROWNFIELD_DISCOVERY` traverses identically to `GREENFIELD` **and the
  test says explicitly that T08 owns changing this**, so T08's edit cannot be
  silent.
- **N6** The four traversals are pairwise distinct as sets — the exit criterion,
  asserted directly.

**The T07/T09 boundary**

- **N7** The rewritten differential (replacing E17): four repositories cloned
  before any run. Flow differing ⇒ traversal differs, exactly as `FLOW_PHASES`
  says. **Risk differing with flow held constant ⇒ traversal, approvals,
  artifact-SHA key set and ordered lifecycle audit events are identical.**
  `governance gates` still reports `advisory: True` and still differs by risk
  while changing nothing.

**Gate discipline under a flow**

- **N8** Within any flow, `advance` past a gate phase whose approval is not
  recorded refuses `gate_not_approved` — parametrised over all five flows.
- **N9** `advance --to <phase in the registry but not in this flow>` refuses
  `forward_jump` with `data["in_flow"] is False`; `advance --to <not in the
  registry>` still refuses `unknown_phase` (D8).
- **N10** `gate approve --gate gate_design` in `HOTFIX` refuses (that gate is
  never the current phase) and writes nothing.

**Binding and immutability**

- **N11** `init` with no governance record binds `GREENFIELD`; `init` after a
  `HOTFIX` assessment binds `HOTFIX`; both audit `flow_selected`; `state["flow"]`
  is the only place it is stored.
- **N12** No CLI path other than `init` and `migrate` writes `flow`: a recursive
  SHA map before and after `governance assess`, `flow show`, `constants`,
  `governance show` and `governance gates` is unchanged.
- **N13** Re-assessing with a different flow mid-run refuses `flow_mismatch` at
  the next `advance`, at `gate approve`, and at `skip` — and in all three cases
  `audit.md` is **byte-identical** before and after and `audit verify` exits 0
  (the B1/NB-6 property, re-proved for the new refusal).
- **N14** D5's declared consequence: a v1.15 state carrying a non-GREENFIELD
  T06 record migrates to `flow: "GREENFIELD"` and then refuses `flow_mismatch`
  with the remedy named.

**Migration**

- **N15** `_mig_1_15` adds `flow: "GREENFIELD"` to a v1.15 state, is idempotent,
  never consults the governance record, and preserves every
  `MIGRATION_VERIFIED_FIELDS` value. A v1.13 state migrates the whole chain to
  1.16 and lands on `GREENFIELD`.

**Structure**

- **N16** No traversal function reads `consts.next_phase`: an AST assertion over
  `cmd_init`, `apply_advance`, `cmd_gate_approve`, `cmd_skip`, `cmd_restart`,
  `cmd_doctor`. `NEXT_PHASE` survives as a linted table with no engine consumer.
- **N17** `Constants.flow()` refuses `flow_table_invalid` (exit 3) on a
  hand-broken `FLOW_PHASES` — unknown phase id, out-of-order phase, duplicate,
  missing mandatory phase, missing terminal `complete`. It never defaults.
- **N18** `HOTFIX`'s phase list equals `MANDATORY_FLOW_PHASES` exactly, and
  every other flow is a superset — the "never ungoverned" property as an
  identity.
- **N19** Derived GREENFIELD progress equals `PROGRESS_MAP` for all 19 phases;
  derived GREENFIELD gate numbers equal `PHASE_TO_GATE_KEY`'s column.
- **N20** `flow show` is read-only and refuses cleanly with no state.
- **N21** Two WorkItems in one repository on different flows advance
  independently; the first's `state.json` and `audit.md` are byte-unchanged
  while the second runs (the T02 isolation property, re-proved under flows).

**Lint** (additive, in `tests/test_lint_skill.py`)

- **N22–N25** One `assert_only_failure` test per new check: a missing flow, a
  flow naming an unregistered phase, a flow out of registry order, a flow
  dropping a mandatory phase, and a `PROGRESS_MAP` value that no longer matches
  the derived GREENFIELD view.

---

## Failure modes

| # | Failure mode | Detection | Mitigation |
|---|---|---|---|
| F1 | **The fixture flow flip is missed and every fixture-driven test traverses `ITERATIVE`.** `started` sits at `constitution_draft`, which `ITERATIVE` does not have. | Hundreds of failures at once. | The conftest flip and the `cmd_init` binding land in the **same milestone (M4)**, in that order. This is the phase's one deliberate red window — see below. |
| F2 | Derived progress or gate numbering does not reproduce the GREENFIELD tables, silently changing header strings and audit messages. | The integration transcripts assert those strings. | M1 lands the derivation with **zero test edits**; the green suite is the proof. N19 pins it permanently. |
| F3 | `FLOW_PHASES` parses to nothing or to a wrong list, and `advance` computes a wrong next phase — the exact fail-open `parse_md_table` exists to prevent (E31). | `tables_wellformed` short-circuits `lint-skill`; `Constants.flow()` raises exit 3. | The loader raises `IntegrityError`, never returns a default. N17 pins five distinct breakages. The compact cell format is parsed with backticks stripped per item. |
| F4 | A flow omits a phase a later phase depends on (`spec_draft`, `tasks_draft`), and a real run dies inside Spec Kit. | Not caught by tests — tests never invoke Spec Kit. | `MANDATORY_FLOW_PHASES` enforced at **both** lint time and load time (D3), with a documented reason per member. |
| F5 | `flow_mismatch` strands an in-flight migrated workflow. | N14. | Declared consequence with a one-command remedy, pinned, and on T11's list. |
| F6 | The new refusal appends to the ledger before it fires, regressing B1/NB-6. | N13 asserts byte-identical `audit.md` on all three refusal paths. | The check is placed with the existing pure-reader prechecks, `state=None`, ahead of every `append_audit`. |
| F7 | T07 drifts into T09 by consulting `required_gate_set` when choosing phases. | `test_no_phase_movement_function_consults_the_would_be_gate_set` (E15) fails. | That test stays green untouched. A11. |
| F8 | `cmd_init` starts calling `apply_advance` to get flow-aware movement, reversing T06's deliberate "governance is not an `init` precondition". | The `movers` assertion (E12) fails. | A12 forbids it. `cmd_init` uses the flow's own next-phase lookup, as it uses `next_phase` today. |
| F9 | The generalised progress lint fires on innocent text (`2/9`, a date, a ratio). | `lint-skill` fails. | E26: zero matches at HEAD for all three new denominators. Re-checked after every document edit. |
| F10 | The version bump misses a site, or the README history row goes below `**v1.15**` and the linter reads the wrong first match. | `version_string_consistent` fails. | E27/E28 name the exact first-match lines. T02 hit this and recorded the lesson. |
| F11 | Documentation edits break `doc_lists_every_phase_*` by removing a phase name while qualifying the "18 phases" prose. | `lint-skill` fails. | Re-run `lint-skill` after **each** document edit, as T05 did. |
| F12 | The suite takes ~14 minutes; an agent is killed mid-flight (nine times so far in this migration). | — | One checkpoint per milestone; M3 is the declared safe resume boundary. Budget 900000 ms per full run. |
| F13 | Disk exhaustion (`os error 112` was seen earlier in this migration). | An I/O error in the run. | 21 GB free at plan time (E8). **If a disk error appears, stop and report — do not trust the result.** |
| F14 | Windows/POSIX divergence in the new code. | Untestable here. | The new code is pure table arithmetic; no path handling is added. |

### Deliberate red window

**Exactly one, confined to M4.** Between the `cmd_init` flow-binding change and
the `tests/conftest.py` flip, every test using the `started` / `project`
fixtures traverses `ITERATIVE` and fails. The implementer **must** make both
edits before running the suite. If the suite is run inside that window, a large
failure count is expected and is **not** an environment flake — F1's signature
is failures concentrated on `constitution_draft` / `gate_constitution`. Any
failure with a different signature is a presumed real regression (E36).

Every other milestone ends with the full suite green.

---

## Rollback/recovery strategy

- **Rollback point: `c0775b3`.** `git reset --hard c0775b3` restores the
  pre-T07 tree exactly. T07 introduces no repository-level artifact, no new
  directory and no change to `.gitignore`, so a reset needs no cleanup.
- **The only durable data effect is the `flow` state field**, added by
  `_mig_1_15`. Downgrading a v1.16 state to v1.15 is not supported — identical
  to every prior version bump, and `read_state` refuses `unknown_version` with
  a named remedy rather than guessing.
- **Nothing is deleted.** `NEXT_PHASE`, `PROGRESS_MAP` and the gate-number
  column all survive; a revert of T07 leaves them authoritative again with no
  migration needed in either direction of the tables.
- **Milestone recovery.** One `T07-checkpoint-a01-NN.md` per milestone. Each
  checkpoint must record what is *on disk*, verified — not what was intended.
  T03's lesson: checkpoints have been accurate about the engine and wrong about
  tests. `python -m pytest --collect-only -q` is the cheap check and must be
  quoted in every checkpoint.
- **Declared safe resume boundary: end of M3.** M1–M3 are additive and
  behaviour-neutral (the seam, the table, the schema); M4 is where binding
  begins and where the red window lives. A fresh agent resuming mid-phase
  should restart at a milestone boundary, never mid-milestone.

---

## Milestones

| M | Content | Green at end? | Structural proof |
|---|---|---|---|
| **M1** | The flow seam. `Flow`, `Constants.flow()`, `flow_for_state()` hardwired to GREENFIELD. Every traversal call site (E34) routes through it. Progress and gate numbering become derived. **No `Constants` attribute is removed**; `constants` output keeps every existing key. | **Yes** | **`git diff --name-only -- tests/` is EMPTY and the suite is 791 passed.** This is T07's equivalent of T02's `Paths` seam. |
| **M2** | `### FLOW_PHASES` in SKILL.md; strict loader; `MANDATORY_FLOW_PHASES`; the four new lint checks; the generalised progress check; N17–N19, N22–N25. Engine still hardwires GREENFIELD. | **Yes** | `lint-skill` 22 → 26 checks, all PASS; only additive test functions added. |
| **M3** | Schema: `flow` in the template, `CURRENT_VERSION` `1.16`, `_mig_1_15`, the 16th `VERSION_MIGRATION` row, the six version-string sites (E27/E28), N15. `flow_for_state` reads the field; every state is still GREENFIELD. | **Yes** | `migration_covers_every_state_field` and `version_string_consistent` PASS; only version literals edited in tests. **Safe resume boundary.** |
| **M4** | Binding and enforcement: `cmd_init` binds from the record, `flow_selected` audit entry, `flow_mismatch` in `apply_advance` and in both pure-reader prechecks, D10's three text fixes, **the one conftest line**. N11–N14. | **Yes** (red window inside) | The suite returns to 791+ green. `test_the_gate_approval_precheck_runs_before_the_first_audit_write` and the closed-caller-set tests still pass untouched. |
| **M5** | `tests/test_units_flow_model.py` in full: N1–N10, N16, N20, N21; the N7 rewrite of the T06 differential. | **Yes** | Four distinct traversals demonstrated; N7 shows risk still moves nothing. |
| **M6** | `flow show`; `constants.flows`; the whole prompt and documentation layer; ADR-004; the dry-run disposition paragraph. `lint-skill` re-run after **every** document edit. | **Yes** | `lint-skill` 26/26; `doc_lists_every_phase_*` still PASS. |
| **M7** | Full suite, `lint-skill`, `validate.py`, must-not-change `git diff --exit-code`, handoff. | **Yes** | All acceptance criteria evidenced. |

---

## Acceptance criteria

Objective, and each independently checkable by the verifier.

- [ ] **A1** `python -m pytest -q -p no:cacheprovider -rsxX` is **RAW EXIT 0**, `--collect-only -q` reports the same number, and `grep -c "short test summary"` over the captured run is **0** (zero skips, xfails, errors). The count is ≥ 791 and every added id is accounted for.
- [ ] **A2** `lint-skill` is **raw exit 0** with **26 checks, 26 PASS, `"failed": []`**, reporting `19 phases, 8 gates, 16 migration rows` and `all four locations report v1.16`.
- [ ] **A3** `python tools/transition/validate.py` is raw exit 0.
- [ ] **A4** `git diff --exit-code c0775b3 <head>` over the must-not-change list is **exit 0**.
- [ ] **A5** `GREENFIELD`'s phase list, obtained from `constants`, is **element-wise identical** to `PHASE_SEQUENCE`, and is **derived** — the string `GREENFIELD` does not appear as a row key in `FLOW_PHASES`.
- [ ] **A6** `tests/test_integration_01_happy_path.py` is **byte-identical** to its content at `c0775b3` and passes.
- [ ] **A7** Driving the real CLI in scratch repositories, the four non-GREENFIELD flows complete end to end with the phase counts and gate counts in D2's table, and the four traversals are pairwise distinct.
- [ ] **A8** A repository whose only difference is the recorded flow traverses differently; a repository whose only difference is the recorded **risk** traverses identically — same phases, same approvals, same artifact-SHA key set, same ordered lifecycle audit events (N7).
- [ ] **A9** For `flow_mismatch` raised at `advance`, at `gate approve` and at `skip`: `audit.md` is **byte-identical** before and after, `state.json` is byte-identical, and `audit verify` exits 0.
- [ ] **A10** In every flow, `advance` past an unapproved gate refuses `gate_not_approved`; `advance` to a registry phase outside the flow refuses `forward_jump` with `data["in_flow"] is False`; `advance` to a non-registry phase still refuses `unknown_phase`.
- [ ] **A11** `test_no_phase_movement_function_consults_the_would_be_gate_set` and `test_the_phase_movement_prefixes_actually_match_something` are **byte-identical** to `c0775b3` and pass. `required_gate_set` is still called by exactly `cmd_governance_assess` and `cmd_governance_gates`.
- [ ] **A12** The closed caller sets are unchanged: `governance_precondition` callers are exactly `["apply_advance", "cmd_gate_approve", "cmd_skip"]` and `apply_advance` callers are exactly `["cmd_advance", "cmd_gate_approve", "cmd_skip"]`. **`cmd_init` does not call `apply_advance`.**
- [ ] **A13** AST extract-and-compare against `c0775b3`: `write_atomic`, `append_audit`, `save_state`, `read_state`, `bind_workitem`, `resolve_decision`, `cmd_migrate_workflow`, `compute_drift`, `cmd_repo_staleness`, `governance_precondition`, `required_gate_set`, `SDLE_OWNED_PREFIXES`, `RUNTIME_FREE_COMMANDS` are **byte-identical**.
- [ ] **A14** `_mig_1_15` sets `flow: "GREENFIELD"`, is idempotent, and contains **no** reference to the governance record. A v1.13 state migrates the full chain to 1.16.
- [ ] **A15** `HOTFIX`'s phase list **equals** `MANDATORY_FLOW_PHASES`; every other flow is a strict superset; the mandatory set is enforced at both lint time and load time; a hand-broken `FLOW_PHASES` yields exit 3 and never a default.
- [ ] **A16** Derived GREENFIELD progress equals `PROGRESS_MAP` for all 19 phases; derived GREENFIELD gate numbers equal `PHASE_TO_GATE_KEY`'s column; both are lint-checked.
- [ ] **A17** No traversal function reads `consts.next_phase` (AST). `NEXT_PHASE` still parses and `next_phase_chains_sequence` still passes.
- [ ] **A18** There is **no** command that writes `state["flow"]` other than `init` and `migrate`. `grep` for a `flow set` / `flow select` parser registration returns nothing.
- [ ] **A19** `flow show` and `constants` are read-only: a recursive SHA map of the project is unchanged across both.
- [ ] **A20** Two WorkItems on different flows advance independently; the first's `state.json` and `audit.md` are byte-unchanged while the second runs.
- [ ] **A21** `git diff --name-status c0775b3 -- tests/` shows **zero `D`** and zero `R`; every `M` is justified in the handoff under a TP-003 category; `tests/conftest.py` shows exactly the one permitted line; `tests/test_lint_skill.py` shows added functions only.
- [ ] **A22** No `pytest.mark.skip`, `pytest.skip(` or `xfail` is added anywhere under `tests/`. **The grep's actual output is quoted in the handoff, not summarised** — `tests/test_units_infra.py` carries a pre-existing `@pytest.mark.skipif(SH is None, …)` and a claim of "no matches" would be false (T03's recorded lesson).
- [ ] **A23** The dry-run disposition in this plan is reproduced in the handoff, all nine transcripts remain byte-identical, and `docs/dry-runs/README.md` carries the disposition paragraph.
- [ ] **A24** No future-phase leakage: no repository-level `.sdle/baseline.*` is created; `cmd_governance_gates` still emits `advisory: true`; no gate becomes risk-conditional; no product subagent or skill is added; the legacy `.workflow/` dual-read rung and `migrate-workflow` still work unchanged.
- [ ] **A25** Python 3.11 and CI are recorded as **`NOT_RUN` / `UNKNOWN`**. No outcome is predicted.

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is `PLANNED`.**

The design forks were resolved from repository evidence and contract text
rather than deferred, in the same way T06's planner fixed the twelve check ids,
the risk weights, the thresholds and the hard floors without blocking. The
resolutions and their evidence are D1–D10 above. The most consequential —
exact flow membership (D2) — is set out as a single table specifically so a
human can disagree with one row without disturbing the mechanism.

| ID | Unknown | Class | Effect |
|---|---|---|---|
| U1 | Python 3.11 and CI behaviour | **UNKNOWN** | Never observed at any point in this migration. T07 adds only stdlib table arithmetic and no syntax newer than 3.11, so a later CI failure could not invalidate the design — but no outcome is predicted. |
| U2 | Whether `speckit-plan` degrades under `ITERATIVE` in a repository with no `.specify/memory/constitution.md` | **UNKNOWN** | Tests never invoke Spec Kit. §13's own premise for ITERATIVE is "use established repository baseline", and validating that baseline is §14 — **T08's**. T07 adds no baseline check and records this as T08's input. |
| U3 | Whether `speckit-implement` output degrades under `DEFECT_FIX`/`HOTFIX` with no design documents | INFERRED / UNKNOWN | The prompt's unconditional design-document sentence is fixed by D10, so the orchestrator will not assert a path that does not exist. Output *quality* is unmeasurable here. |
| U4 | Whether `BROWNFIELD_DISCOVERY` should differ from `GREENFIELD` before T08 exists | INFERRED | It cannot meaningfully differ without the discovery phase §14 introduces. Declared equal, pinned by N5 so T08's change is visible. |
| U5 | Whether users exist with in-flight v1.15 workflows carrying non-GREENFIELD T06 records | INFERRED — effectively none | The branch is local-only and v1.15 was never released with governance. D5's refusal is nonetheless implemented and pinned rather than assumed away. |
| U6 | Suite runtime variance | OBSERVED | 849.77 s this context. Budget 900000 ms; never the 2-minute default. |

---

## Scope exclusions

Explicitly out of T07. If any appears in the diff it is future-phase leakage.

- **T08 — Brownfield discovery and convergence (§14).** No discovery phase is
  added to the registry. No `.sdle/baseline.*` is created or read. No baseline
  validity check is added anywhere, including for `ITERATIVE` (U2).
  `BROWNFIELD_DISCOVERY`'s real shape is T08's.
- **T09 — Risk-adaptive gates (§15).** **The boundary, stated sharply: T07
  selects which phases execute; T09 makes gate *requirements* policy-driven.**
  `required_gate_set` stays inert and uncalled by any phase-movement function
  (A11). `governance gates` stays `advisory: true`. No gate inside a flow
  becomes conditional on risk. No hard floor gains a consequence. The
  `required_gates_by_risk` / `required_gates_by_type` policy keys are not read
  by traversal. `flow_phases()` is deliberately the single seam through which
  T09 will later compose risk-required gates onto a flow; T07 builds the seam
  and uses none of it.
- **T10 — Skills and subagents (§16).** No product subagent, no skill split, no
  progressive loading. Flow selection is deterministic, not delegated.
- **T11 — Legacy removal and hardening (§17).** `NEXT_PHASE`, `PROGRESS_MAP`
  and `PHASE_TO_GATE_KEY`'s gate-number column are **kept** (§13 forbids
  deleting them now). The legacy `.workflow/` dual-read rung, `migrate-workflow`
  and the repo-global compatibility path all keep working.
- **Not adopted — every open finding from earlier phases stays with its owner.**
  T04 N-2 (Spec Kit discovery tier 2 cross-adoption), N-3 (non-normalised fence
  path), N-4 (`SKILL.md:358`), N-6 (the `.workflow/` documentation residual in
  `phase-execution.md`, `gate-protocol.md` and the nine transcripts), N-7
  (`cmd_manifest_build` exclusion); T03-1 (the branch-guard fail-open window),
  T03-4/5/6/7/8/10; T02 NB-2/NB-4/NB-5; `.claude/settings.local.json`.
  **T07 adopts none of them.** In particular, `gate-protocol.md`'s completion
  line is edited for the gate *count* only; its stale `.workflow/completion-summary.json`
  path is left exactly as it is.
- **Two items are owned by T07 and are not adoptions**, because T07's own
  change is what makes them wrong: `.claude/commands/sdle-restart.md`'s
  `1-18` argument hint (D7/E35) and `phase-execution.md`'s unconditional
  design-document sentence (D10/E23).
- **Deferred features (§27).** No BPM engine, no conditional branching, no
  parallel phases, no loops, no dynamic phase insertion, no policy DSL, no
  release/build model. **A flow is an ordered subset of a fixed registry and
  nothing more.** If the implementation grows a construct that could express a
  workflow SDLE does not currently need, that is a defect under §13, not a
  feature.
