# T11 checkpoint a01-01 — M1 complete

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M1 (remove the legacy runtime binding)
**Status at this boundary:** M1 GREEN. Safe resume point.
**Written before:** M2 begins.

---

## 1. Where the phase started

| Fact | Value | How obtained |
|---|---|---|
| HEAD at phase start | `97100e2` (plan commit) | `git log --oneline -8` |
| Dirty at phase start | `.claude/settings.local.json` only (out of scope, untouched) | `git status --porcelain` |
| Baseline full suite | **1616 passed, 0 failed, 0 skipped, 0 errors — RAW EXIT 0, 1553.75s (25:53)** | `rtk proxy python -m pytest -q --junitxml=…/baseline.xml`; junit attrs `tests=1616 failures=0 errors=0 skipped=0` |
| Baseline `lint-skill` | **42 checks, `failed: []`**, exit 0 | `python scripts/sdle.py lint-skill` |
| Baseline `validate.py` | `TRANSITION_VALID: complete=11/12 next=T11`, exit 0 | `python tools/transition/validate.py` |
| Interpreter | **Python 3.13.0** on win32 | `python --version` |

Note: the plan's §10 says "Windows / Python 3.14". The observed interpreter on
this host is **3.13.0**. Recorded as observed; Python 3.11 remains `NOT_RUN`
and CI remains `UNKNOWN`.

The plan's byte-identity baselines name `4b1aa71`. `97100e2` adds only
`docs/transition/phases/T11-plan.md`, so every product path is identical at the
two commits; `4b1aa71` is used verbatim as the plan specifies.

---

## 2. What M1 changed

### Product — `scripts/sdle.py` (18 edit groups, applied by one scripted patch)

| D-item | Change | Anchor |
|---|---|---|
| D1 | Rung 6 (`decision.rung = "legacy"`) deleted from `resolve_decision`; the `if not known:` branch now returns `reason="none"` unconditionally | `resolve_decision`, comment `# Rung 6 — nothing is registered.` |
| D2 | `if decision.rung == "legacy": return paths` deleted from `bind_workitem` | `bind_workitem`, final `return dataclass_replace(...)` |
| D3 | `workitem_required` widened: when `legacy_state_present(paths)` the message names `workitem create` then `migrate-workflow --workitem <id>` in order and `data` carries `legacy_state`. **Same reason string, same exit code 1** | `bind_workitem`, `if decision.reason == "none":` |
| D4 | **11** unreachable `paths.workitem is None` carve-outs deleted | see table below |
| R7 (part) | `SKILL.md` resolution paragraph; `.claude/commands/sdle-start.md` legacy paragraph | below |

**The 11 carve-outs deleted** (plan E12 lists 12 *sites*; the 12th,
`collect_validation_findings`, is explicitly **kept** by D4 itself — P5):
`gate_requirements_for_state`, `bind_for_governance`, `bind_for_discovery`,
`discovery_precondition`, `baseline_precondition`, `establish_baseline`,
`review_precondition`, `governance_precondition`, `flow_precondition`,
`cmd_gate_omit`, `gate_precondition_hook`.

Two reason strings became unreachable and were deleted with their branches:
`governance_workitem_required`, `discovery_workitem_required`.

**A3 verified by AST, not grep:** exactly two `X.workitem is None` comparisons
remain in `sdle.py` — `Paths.workitem_root` (the dataclass describing its own
shape) and `collect_validation_findings` (P5). Pinned by
`test_n25_no_unbound_runtime_carve_out_survives_in_the_engine`.

### PRESERVED — verified after the patch, not assumed

- `PROJECT_ROOT_MARKERS` still contains `(".workflow", "state.json")` (**P1** —
  asserted inside the patch script itself and re-asserted by
  `test_t11_the_legacy_rung_is_gone`).
- `Paths.legacy_workflow`, `legacy_state_present`, `cmd_migrate_workflow`,
  the `runtime_state_outside_workitem` validate finding, `.workflow/` in
  `SDLE_OWNED_PREFIXES` and in `hooks.py::FENCED`, `.workflow/` in
  `.gitignore` — all untouched (P2–P7).
- `.gitignore`, `.claude/settings.json` and the three integration files are
  **byte-identical to `4b1aa71`** (`git diff --stat 4b1aa71 -- …` empty).
- `docs/dry-runs/` byte-identical to `4b1aa71` (M8 owns those).

### Prompt layer

- `.claude/skills/sdle/SKILL.md` — the sentence "A legacy repository-global
  `.workflow/state.json` still binds when no WorkItem is registered at all"
  replaced by "There is no sixth rung … it never binds", plus the two-step
  recovery named in order.
- `.claude/commands/sdle-start.md` — the legacy paragraph now instructs the
  recovery rather than implying the runtime works.

### Tests

Applied under §7.1. **X-table entries landed:** X1 (both), X2 (all six named +
three the plan did not name individually — see §3), X3 (all three), X12.

| Test | TP-003 | Action |
|---|---|---|
| `test_rung3_legacy_state_stays_readable_when_no_workitem_exists` | 2 | **Inverted** → `test_rung3_legacy_state_no_longer_binds_and_the_refusal_names_recovery`. Strictly more assertion (reason, exit, both steps, order, `data.legacy_state`, legacy tree untouched). Plus a **new** sibling `test_the_legacy_recovery_path_is_exactly_two_runtime_free_commands` proving A4 end-to-end through `run_cli`. |
| `test_the_legacy_dual_read_rung_still_binds` | 2 | **Inverted** → `test_the_legacy_dual_read_rung_is_gone`; also asserts the with-/without-legacy cases are *indistinguishable* (the rung was deleted, not replaced by an inference — B4). |
| `test_governance_refuses_under_the_legacy_binding` | 2 | Renamed; refusal moved `governance_workitem_required` → `workitem_required`; the "nothing written into `.workflow/`" guarantee kept **and widened** to a whole-directory listing comparison. |
| `test_e1_is_skipped_under_the_legacy_binding_and_only_there` | 2 | **Inverted**: E1 now applies unconditionally. Contrast half (`governance_missing`) kept verbatim; legacy `state.json` SHA pinned. |
| `test_e2_stands_aside_under_the_legacy_binding_and_only_there` | 2 | **Inverted** → `test_e2_no_longer_stands_aside_anywhere`. `test_e2_applies_as_soon_as_a_workitem_holds_the_runtime` untouched. |
| `test_n18_the_legacy_runtime_can_never_omit_a_gate` | 2 | Name and guarantee kept; refusal moved earlier; the "legacy traversal still works" half **inverted** and strengthened with a SHA pin. |
| `test_n7_the_legacy_binding_keeps_its_baseline_behaviour` | 2 | **Inverted** → refuses; both candidate directories still asserted untouched. |
| `test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding` | 2 | **Inverted** → refuses rather than emitting a path into a directory the engine will never write. |
| `test_n22_the_legacy_rung_and_migrate_workflow_are_untouched` | 2 | **Split** per X3: rung half inverted; `migrate-workflow` byte-identity half **kept verbatim** (B9). |
| `test_n31_the_legacy_rung_and_migrate_workflow_are_untouched` | 2 | **Split** identically. |
| `test_n31_no_t11_leakage` | 2 | **Retired and replaced** by `test_t11_the_legacy_rung_is_gone` (X3's instruction). The replacement asserts the removal positively *and* re-asserts P1/P2/P8 positively. |
| rung-enum membership assertion | 1 | **Tightened**: `"legacy"` dropped from the permitted set (X12). |

**New tests added in M1:** `test_n17_the_workitem_required_refusal_names_the_recovery_in_order`,
`test_n17_without_legacy_state_the_refusal_stays_the_short_one`,
`test_n25_every_bound_runtime_command_names_a_workitem`,
`test_n25_no_unbound_runtime_carve_out_survives_in_the_engine`,
`test_the_legacy_recovery_path_is_exactly_two_runtime_free_commands`.
Net **+5** tests (1616 → 1621).

**No test was deleted in M1.**

---

## 3. Plan deviations recorded at this boundary

**PD-1 — three tests fell in X2's *class* but were not named in the X-table.**
The plan's §7.2 X2 row is defined by class ("D4 removes the carve-out each one
describes") and its own list ends with "and the `plant_legacy_workflow`
helper's dependents", i.e. it is explicitly not exhaustive-by-name. Three
further tests were mechanically forced by D1/D2/D4 and are recorded here
individually rather than silently:

1. `test_units_governance.py::test_governance_refuses_under_the_legacy_binding`
   — the `bind_for_governance` carve-out it describes. **Category 2.**
2. `test_units_workitem_resolution.py::test_bind_workitem_writes_nothing_and_prints_nothing`
   — its final block exercised the legacy rung. The block now asserts purity on
   the **refusal** path, which is the path a hook actually takes in such a
   repository. **Category 2**; purity coverage preserved, not reduced.
3. `test_units_workitem_runtime.py::test_migrating_a_state_at_the_legacy_location_leaves_workitem_null`
   — `migrate` is not RUNTIME_FREE, so it can no longer reach a legacy state
   file. **Category 2.** The *rule* it pinned (1.13→1.14 leaves `workitem`
   null off-WorkItem) is **not** dropped: it is now asserted against
   `migrate_state` directly **and** end-to-end through `migrate-workflow`,
   which is the only route a legacy state has left. Net coverage increases.

Per plan §7.1 these are raised as deviations in the handoff. §7.1's instruction
is "must be raised as a plan deviation in the handoff", not "stop" — no
material architecture/contract/baseline decision is implied, so no blocker.

**PD-2 — plan §7.2 "Not affected" list.** No file on that list changed in M1.
Confirmed by `git status`.

**PD-3 — declared process deviation on suite cadence.** The plan asks for a
full suite at every milestone boundary. Each full run costs ~26 minutes of wall
clock and this migration has lost ≈19 agent runs to API limits (F8). M1 — the
only milestone with a red window — got its own full run. Later milestones are
grouped for full runs (see the handoff); every milestone still gets targeted
runs, `lint-skill` and the A-criteria checks it can affect, and the phase ends
on a full green suite (A22). Recorded, not hidden.

---

## 4. Evidence at the M1 boundary

| Check | Command | Result |
|---|---|---|
| Full suite | `rtk proxy python -m pytest -q --junitxml=…/t11_m1.xml` | **1621 passed in 1521.91s (25:21), RAW EXIT 0** |
| Targeted (resolution/runtime) | `pytest tests/test_units_workitem_runtime.py tests/test_units_workitem_resolution.py -q` | 147 passed |
| Targeted (policy/caps/flow/baseline/discovery) | `pytest tests/test_units_gate_policy.py tests/test_units_capabilities.py tests/test_units_flow_model.py tests/test_units_baseline.py tests/test_units_discovery.py -q` | 737 passed |
| `lint-skill` | `python scripts/sdle.py lint-skill` | **42 checks, `failed: []`** |
| A1 byte identity | `git diff --stat 4b1aa71 -- <3 integration files> .claude/settings.json .gitignore docs/dry-runs/` | **empty** |
| A15 registry | `python scripts/sdle.py constants` | phases **21**, flows **5**, gates **8** — unchanged |
| Syntax | `ast.parse(sdle.py)` | ok; CRLF preserved (10793 CRLF / 10793 LF) |

`ENVIRONMENT_FLAKE` was **not** invoked and is VOID for this phase. No failure
was re-run to make it pass.

---

## 5. Resuming from here

**A fresh agent may resume at this boundary.** Verify against disk first:

```
git status --porcelain                       # expect sdle.py, SKILL.md,
                                             # sdle-start.md, 7 test files
python -c "import io;print(sum('workitem is None' in l for l in io.open('scripts/sdle.py',encoding='utf-8')))"
                                             # expect 2
python scripts/sdle.py lint-skill            # expect 42 / failed: []
python -m pytest --collect-only -q | tail -2 # expect 1621
```

**Remaining milestones, in order:** M2 (D5–D9, X4, X5, N18–N20) · M3 (D10, X8,
N21) · M4 (D11, D12, N12-part) · M5 (D13, D14, X6, X11, N22, N23) · M6 (N1–N16)
· M7 (documentation, ADR-008 with all 26 TR rows, TR2/3/4/6/13/14/21/26) ·
M8 (D15, X10 — severable).

**Recoverability:** M1's red window is closed, so from here every milestone is
additive or documentation-only. Abandoning at any later boundary leaves a
working, self-consistent engine. Rollback for the whole phase remains
`git checkout 11363d9 -- scripts/ tests/ .claude/`.

**Tooling reminders that cost time this attempt:** heredocs mangle `\n` escapes
(write patch scripts with the Write tool); a plain `grep` for `legacy"` gave a
false negative that a Python walk found; the Bash tool caps foreground commands
at 600 s so the suite must be backgrounded and polled.
