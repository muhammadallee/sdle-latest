# T07 Implementation Handoff — Attempt a01

**Phase:** T07 — Replace the fixed universal sequence with declarative flow selection
**Attempt:** 01
**Implementer context:** fresh/isolated. This attempt spans **two contexts**: the
first was terminated mid-M7 by an API session limit — an interruption under
§24.6, **not** a verification FAIL — and the second resumed from the working
tree and the checkpoints. The attempt number is therefore unchanged.
**Status recommendation:** **IMPLEMENTED**

**HEAD:** `77ca0b8` — **nothing is committed.** The whole phase is in the
working tree.
**Precondition HEAD / plan revision:** `77ca0b8`, `T07-plan.md` **revision 2**.
Revision 1 at `7dba4b6` is superseded; the two commits are byte-identical for
every product file, so `7dba4b6` is used throughout as the diff base and both
were checked.
**Rollback point:** `c0775b3` · **Product baseline:** `f8fdaa0`

---

## Inputs read from disk

`CLAUDE.md`; `docs/transition/transition.md` §13, §24.3, §24.6, TP-003, TP-011;
`docs/transition/progress.md`; `docs/transition/phases/T07-plan.md` **revision 2**;
`T07-checkpoint-a01-01..06`; the working tree; `git status`, `git log`,
`git diff` and `git show 7dba4b6:…`; `scripts/sdle.py`; the prompt files; the
test suite; `.claude/hooks/hooks.py`; `tools/transition/validate.py`.

**The repository was treated as the authority.** Every claim inherited from the
checkpoints that this handoff repeats was re-derived from a command run in the
resuming context — the suite, the lint counts, the flow arithmetic, the AST
closed sets, the byte-identity diffs and the `skipif` grep. Where a checkpoint's
figure and a fresh derivation disagreed, the derivation won; none did.

---

## Changes made

### Engine — `scripts/sdle.py` (+783 / −65)

Top-level symbol diff against `7dba4b6`, computed by AST: **10 added, 25
changed, 0 removed.**

**Added:** `GREENFIELD_V1_PHASES`, `DEFAULT_FLOW`, `MANDATORY_FLOW_PHASES`,
`GATE_NUMBER_PLACEHOLDER`, `Flow`, `flow_for_state`, `_mig_1_15`,
`flow_precondition`, `_check_flow_model`, `cmd_flow_show`.

**Changed:** `Constants`, `load_constants`, `CURRENT_VERSION`, `MIGRATIONS`,
`cmd_init`, `render_header`, `cmd_header`, `cmd_state_dump`,
`evaluate_classification`, `cmd_governance_gates`, `record_governance_audit`,
`apply_advance`, `cmd_gate_show`, `write_completion_summary`,
`cmd_gate_approve`, `_approve_drift`, `cmd_gate_reject`, `cmd_remediate_begin`,
`cmd_skip`, `cmd_restart`, `cmd_doctor`, `run_sync_checks`,
`_check_no_hardcoded_progress`, `cmd_constants`, `build_parser`.

The mechanism, in one paragraph: `PHASE_SEQUENCE` becomes a **20-entry
registry**; a `Flow` is an ordered subset of it; `Constants.flows` injects the
frozen `GREENFIELD_V1_PHASES` and parses the four declared rows out of a new
`### FLOW_PHASES` table; `Constants.flow()` validates on demand and refuses
`flow_table_invalid` (exit 3) rather than defaulting; `flow_for_state()` is the
single seam every traversal call site now goes through; progress fractions,
gate numbers and gate labels are derived per flow; the flow binds once in
`cmd_init` from `classification.flow` and is stored in the new `state.flow`
(`CURRENT_VERSION` 1.15 → **1.16**, `_mig_1_15` naming `GREENFIELD`
unconditionally); `flow_precondition` refuses `flow_mismatch` ahead of the
first ledger append at all three enforcement sites; `run_sync_checks` grows
seven checks.

### Prompt layer

- **`SKILL.md`** (+57/−32) — `impact_analysis` rows in `PHASE_SEQUENCE`,
  `NEXT_PHASE` and `PHASE_LABEL_MAP`; the eight gate labels take
  `{gate_number}`; the new `### FLOW_PHASES` table and its GREENFIELD note; the
  heading becomes *The GREENFIELD Flow — 18 Phases, 8 Gates* with the
  never-restate-a-number instruction; the Step 1 flow paragraph; the 16th
  `VERSION_MIGRATION` row; the version string in frontmatter and heading; and
  the frontmatter `description`'s "gated **18-phase** lifecycle" clause.
  **`PROGRESS_MAP` is byte-identical.**
- **`modules/phase-execution.md`** (+23/−10) — the ordinal-free
  `impact_analysis` block; the execute-only-the-bound-flow note; the eight
  `(Gate N/8)` parentheticals become "ask `gate show`"; the display-before-
  `gate_spec` step; the conditional design-document sentence.
- **`modules/gate-protocol.md`** (+7/−6) — `Gate {gate_number}/{gate_total}`,
  `All {gate_total} gates passed`. The stale `.workflow/completion-summary.json`
  path on that line is deliberately left (T11 / T04 N-6).
- **`templates/state.json`** (+2/−1) — `flow`, `workflow_version` 1.16.
  `approvals` and `progress` untouched.
- **`.claude/commands/sdle-restart.md`** (+4/−1) — the `1-18` argument hint goes
  (E42/D16); the number indexes the bound flow.

### Documentation

- **`README.md`** (+19/−7), **`docs/SDLE-Reference-Guide.md`** (+35/−7),
  **`CLAUDE.md`** (+22/−7), **`docs/dry-runs/README.md`** (+6/−0),
  **`docs/architecture/ADR-004-declarative-flow-model.md`** (new).

### Tests

- **`tests/test_units_flow_model.py`** — new, **98** tests.
- **`tests/test_lint_skill.py`** — 17 → **28** (+11 firing tests, one per new check).
- **`tests/test_units_governance.py`** — 180 → **181**.
- Seven files carry version/count literal updates only.

---

## Deliberate behavior changes

1. **`PHASE_SEQUENCE` is no longer a lifecycle.** It is a 20-entry registry and
   **no flow is all of it**. A WorkItem traverses one of five flows.
2. **GREENFIELD is frozen in the engine, not derived from the registry.** This
   is the design decision of the re-plan and it holds: `GREENFIELD` is
   `GREENFIELD_V1_PHASES` and is **deliberately not** a `FLOW_PHASES` row, so a
   new registry row cannot silently join it. `every_registry_phase_is_used_by_some_flow`
   makes an orphaned phase fail loudly instead.
3. **`impact_analysis` is a real, governed, GATELESS phase** at registry
   position 2, in `DEFECT_FIX` and `HOTFIX` only — a recorded human decision.
   There is **no ninth `approvals` key**; `approvals` has exactly eight.
   Governed means: `artifact record` enforces the size floor and fingerprints
   it, `artifact review` binds a TP-011 review to that exact SHA, and the
   content is displayed before `gate_spec`, which strengthens invariant 4. Its
   `phase-execution.md` block contains **zero** `feature bind` and **zero**
   `featureDirectory`, because the feature directory does not exist yet.
4. **The flow binds once, at `init`, and there is no command that re-binds it.**
   `state["flow"]`'s AST writer set is exactly `{cmd_init, _mig_1_15}`.
   Re-assessing with a different flow refuses **`flow_mismatch`**, exit 1, two
   named remedies.
5. **Progress, gate numbers and gate labels are flow-relative.**
   `gate_implement` reports `(2, 3)` under HOTFIX.
6. **`restart --to <N>` indexes the bound flow** (D16), so it matches the
   `Phase N/M` the user was shown. Identical under GREENFIELD.
7. **`forward_jump` absorbs "not in this flow"** (D17). A registry phase outside
   the bound flow refuses `forward_jump` with `data["in_flow"] is False`; a
   non-registry phase still refuses `unknown_phase`.
8. **`classification.advisory` becomes `False` in the record**, and
   `record_governance_audit`'s ledger line says the flow selects the lifecycle
   while the type is advisory (D13). **`cmd_governance_gates` keeps
   `"advisory": True`** — the would-be gate set really is still inert.
9. **The completion summary gains `flow`** (D14). `all_gates_approved` keeps its
   meaning, now scoped to the gates the flow has.
10. **`lint-skill` 22 → 29 checks.**

---

## Preserved behavior / invariants

- **Invariant 6, single writer.** `flow_precondition` is a pure reader and every
  one of its three call sites is ahead of that command's first `append_audit`.
  All three `flow_mismatch` paths assert **`audit.md` byte-identical**, a
  byte-identical recursive SHA map of the whole scratch repository, and
  `audit verify` exit 0. **The core refuses; it does not warn.**
- **The B1/NB-6 fixes at `0a9b8c7` and `c0775b3` are not regressed.** The
  three-step order in `apply_advance` — `governance_precondition(paths)` (pure),
  then `flow_precondition`, then `governance_precondition(paths, state)` — keeps
  `governance_stale` / `governance_blocked` unmaskable *and* keeps the new
  refusal ahead of the first write. A record that is both stale and
  flow-disagreeing still refuses `governance_stale`.
- **Gate discipline / fail safe.** Every flow refuses `gate_not_approved` at its
  own first gate; approving a gate a flow does not run refuses `not_at_gate` and
  writes nothing; the unrun gate stays `null` forever.
- **Invariant 3 (SpecKit opacity), 4 (gate content in conversation), 7 (one
  source of truth), 8 (gates stay in the parent)** — no `speckit-*` name
  surfaced, the impact analysis is displayed before its downstream gate, every
  new constant has exactly one home, and no subagent was added.
- **The ladder never guesses.** No new resolution rung; `cmd_migrate_workflow`
  is byte-identical; the legacy `.workflow/` dual-read still binds when no
  WorkItem is registered.
- **`cmd_init` stays outside `apply_advance`** (A12), so governance does not
  become an `init` precondition by the back door.
- **`NEXT_PHASE` readers stay the closed set** `{load_constants,
  run_sync_checks, cmd_constants}`.
- **Denominators 18/18/16/14/10** and **`PROGRESS_MAP`'s 19 rows byte-identical.**
- **A13's 15 names are byte-identical**, including `write_atomic`,
  `append_audit`, `governance_precondition` and `required_gate_set`.

---

## Test changes and TP-003 classification

**Three categories, no fourth.** `git diff --name-status 7dba4b6 -- tests/` =
**ten `M`, zero `D`, zero `R`**.

| Test | Category | Rationale |
|---|---|---|
| `tests/test_units_flow_model.py` (new, 98) | **1 — new** | The phase's own suite: N1–N26. |
| `tests/test_lint_skill.py` +11 functions | **1 — new** | One firing test per new check. **No `-def` line in the diff** — no function removed. Three removed lines are fixture *literals* inside existing firing tests whose planted text had to move with the gate labels and the version string. |
| `test_classification_is_marked_advisory_in_the_record` → `test_the_classification_flag_no_longer_claims_to_be_advisory` | **2 — superseded** | D13 flips the record's flag. **Strengthened:** it now asserts the record says `False` **and** that `governance gates` still says `True`, which is the T07/T09 boundary. |
| `test_governance_changes_no_lifecycle_behaviour` → `test_risk_and_type_change_no_lifecycle_behaviour` | **2 — superseded** | The T06 differential asserted four variants traverse identically while three named different **flows**. At T07 that asserts the opposite of the design. Rewritten to hold the flow constant and vary type and risk, with guard clauses proving the flow really was held constant so a null result cannot pass for the uninteresting reason. |
| `test_the_flow_is_the_one_governance_value_that_moves_the_lifecycle` (new) | **1 — new** | The other half of the pair: five clones at identical LOW risk land on three distinct phases. |
| `tests/conftest.py` — `record_governance`'s `"flow": "ITERATIVE"` → `"GREENFIELD"` | **2 — superseded** | **The one permitted line.** Inert at T06; selects traversal at T07, and the `started` fixture sits at `constitution_draft`. Diff is 7/1 — one changed line plus six comment lines. No fixture, helper, signature or `Project` method added or changed. |
| `tests/test_units_governance.py` — `governance_input()`'s own default flow | **2 — superseded** | **Declared divergence:** a *second* shared default the anti-contradiction clause did not enumerate, in a file whose cases `init` then `advance --to gate_constitution`. Changed for the same reason and in the same category. `test_units_governance.py:1454` deliberately **keeps `ITERATIVE`** as the live witness that a non-GREENFIELD flow round-trips through the record. |
| `test_units_cli.py`, `test_units_infra.py` — `phase_count == 18` → `19` | **2 — superseded** | `constants.phase_count` is the **registry's** non-terminal count and the registry gained a phase. Both carry a comment saying which count they mean, because GREENFIELD's is still 18. |
| `test_units_repo_config.py`, `test_units_state.py`, `test_units_transitions.py`, `test_units_speckit_binding.py`, `test_units_workitem_runtime.py` | **2 — superseded** | `1.15` → `1.16` version literals, the added `1.15->1.16` migration step, and one test rename (`…_is_1_15_…` → `…_is_1_16_…`). |

**Zero category 3 (`D`, deleted) and zero renamed-away tests.** No assertion was
weakened; the two rewrites above both assert strictly more than what they
replace.

**A22 — the grep's actual output, quoted verbatim rather than summarised:**

```
tests/test_units_infra.py:49:@pytest.mark.skipif(SH is None, reason="POSIX sh not available")
```

Exactly one hit, **pre-existing**, and it did not fire — the captured run has no
`short test summary` section. T07 added no skip, no xfail and no deletion.

---

## Commands actually run

All in this context unless marked. `rtk proxy` is used throughout because a bare
`python -m pytest` under the `rtk` hook prints `Pytest: No tests collected` and
exits 0 — a false green.

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **RAW EXIT 0** | **`901 passed in 1026.22s (0:17:06)`** |
| `grep -c "short test summary"` over that captured run | — | **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | RAW EXIT 0 | **`901 tests collected in 0.52s`** — collected == passed |
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_flow_model.py tests/test_units_governance.py -q -p no:cacheprovider -rsxX"` | RAW EXIT 0 | `307 passed in 258.22s` — the M7 documentation blast radius |
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` × **4**, once after every document edit | RAW EXIT 0 each | **29 checks, 29 PASS, 0 FAIL, `"failed": []`**; `Parsed 20 phases, 8 gates, 16 migration rows`; `all four locations report v1.16` |
| `lint-skill` in a `git archive 7dba4b6` scratch tree | RAW EXIT 0 | **22** checks — the A18 baseline |
| `comm` over the two check-name lists | — | **7 added, 0 removed** |
| `rtk proxy "python tools/transition/validate.py"` | **RAW EXIT 0** | `TRANSITION_VALID: complete=7/12 next=T07` |
| `git diff --exit-code 7dba4b6 -- <must-not-change list>` | **RAW EXIT 0** | zero bytes |
| `git diff --exit-code 77ca0b8 -- <same list>` | **RAW EXIT 0** | zero bytes |
| `git diff --exit-code 77ca0b8 -- docs/transition/` | **RAW EXIT 0** | zero bytes — no verifier or contract artifact touched |
| `python .claude/hooks/hooks.py write-fence` × 4 payloads | exit 0 | permit / permit / deny / deny (below) |
| AST scripts over `scripts/sdle.py` and `git show 7dba4b6:scripts/sdle.py` | — | A5-P3, A12, A13, A17, A19 |
| `python --version` | — | **3.13.0** |
| Python 3.11 | **NOT_RUN** | never observed at any point in this migration |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN / UNKNOWN** | local-only branch; **no outcome predicted** |

### Suite arithmetic — the +110 accounted for exactly

Per-file `--collect-only`, run against both trees in this context (the baseline
tree reconstructed with `git archive 7dba4b6 | tar -x`):

| File | Base | Head | Δ |
|---|---:|---:|---:|
| `tests/test_units_flow_model.py` | 0 | **98** | +98 |
| `tests/test_lint_skill.py` | 17 | **28** | +11 |
| `tests/test_units_governance.py` | 180 | **181** | +1 |

`791 + 98 + 11 + 1 = 901`. No other file's count moved.

### The write-fence probe (A24 / F7)

`.claude/hooks/hooks.py write-fence` invoked as its own process, JSON payload on
stdin, `CLAUDE_PROJECT_DIR` set to the repository. `.claude/hooks/` is
byte-identical to `7dba4b6`, so this is the shipped fence:

| Path | Verdict |
|---|---|
| `reviews/impact-analysis-2026-08-31-1430.md` | **permit** (no output) |
| `reviews/security-review-2026-08-31-1430.md` | **permit** — the precedent the path was chosen from |
| `workitems/todo-api/.sdle/state.json` | **deny** |
| `.workflow/state.json` | **deny** |

---

## Git evidence

- **HEAD:** `77ca0b8b4884a2bbf5f3966ba8a1d0249999ec85` on
  `transition/workitem-v1`. **Nothing is committed.**
- **Working tree** (`git status --porcelain`), `.claude/settings.local.json`
  excluded as pre-existing and out of scope:

```
 M .claude/commands/sdle-restart.md          4 / 1
 M .claude/skills/sdle/SKILL.md             57 / 32
 M .claude/skills/sdle/modules/gate-protocol.md      7 / 6
 M .claude/skills/sdle/modules/phase-execution.md   23 / 10
 M .claude/skills/sdle/templates/state.json  2 / 1
 M CLAUDE.md                                22 / 7
 M README.md                                19 / 7
 M docs/SDLE-Reference-Guide.md             35 / 7
 M docs/dry-runs/README.md                   6 / 0
 M scripts/sdle.py                         783 / 65
 M tests/conftest.py                         7 / 1
 M tests/test_lint_skill.py                113 / 3
 M tests/test_units_cli.py                   4 / 1
 M tests/test_units_governance.py          101 / 15
 M tests/test_units_infra.py                 2 / 1
 M tests/test_units_repo_config.py           1 / 1
 M tests/test_units_speckit_binding.py       2 / 2
 M tests/test_units_state.py                 4 / 4
 M tests/test_units_transitions.py           1 / 1
 M tests/test_units_workitem_runtime.py      7 / 6
?? docs/architecture/ADR-004-declarative-flow-model.md
?? tests/test_units_flow_model.py
?? docs/transition/phases/T07-checkpoint-a01-01..08.md
?? docs/transition/phases/T07-handoff-a01.md
```

- **Diff scope:** exactly the plan's *Files expected to change*, minus nothing
  and plus nothing. Every file on the **must-not-change** list diffs clean
  against both `7dba4b6` and `77ca0b8`, including
  `tests/test_integration_01_happy_path.py`, `modules/security-review.md`,
  `.claude/hooks/`, `.claude/settings.json`, `scripts/sdle.sh`,
  `scripts/sdle.ps1`, `.github/`, `tools/`, `requirements/`, ADR-001..003, all
  nine dry-run transcripts, and every T00–T06 transition artifact.

---

## Declared divergences from the plan

Three, each recorded when it was found, none silent, none weakening anything.

1. **`DEFECT_FIX` has 6 gates, not the plan's 5.** D4's summary column says
   `14 non-terminal, 5 gates`; the **same row's own explicit phase list** has 15
   entries, 14 non-terminal and **6** gate phases. Re-derived here from
   `constants`: `DEFECT_FIX entries=15 non-terminal=14 gates=6`. Membership is
   the decision and the count is derived from it, so the membership is
   implemented exactly as declared and the correct figure is **14/6**. A8's
   `14/5` and D4's column are wrong. **No documentation written in this phase
   restates 5.**
2. **A15's third clause, "HOTFIX is the subset-minimum of the five flows", is
   false as written.** Implemented literally as `set(HOTFIX) <= set(flow)` it
   fails against GREENFIELD, BROWNFIELD_DISCOVERY and ITERATIVE, because HOTFIX
   carries `impact_analysis` and those three deliberately do not — the clause
   contradicts the user decision the same plan implements. Replaced by two exact
   assertions that are both true and together forbid exactly what the clause was
   for: `len(HOTFIX) <= len(flow)` for every flow, and
   `set(HOTFIX) - {"impact_analysis"} <= set(flow)` for every flow. Both verified
   `True` here. A15's first two clauses are implemented verbatim and pass.
3. **`flow_mismatch`'s placement inside `apply_advance`.** D10 asks for the
   check *after* `governance_precondition` **and** before any `append_audit`;
   those cannot both hold, because `governance_precondition(paths, state)`
   appends. `governance_precondition` is on A13's byte-identical list and may
   not be split. Resolved by the three-step order described above, with a test
   pinning each half.

Plus one divergence from the **anti-contradiction clause**: a second shared
fixture default (`test_units_governance.py`'s own `governance_input()`) had to
move for the same reason as the one permitted `conftest.py` line. The clause's
intent — one attributable shared default per file, changed for a stated reason,
no new shared machinery — is kept; its literal one-line count is not, because a
second file carried a default the clause did not enumerate.

---

## Known limitations / risks

- **U1 — Python 3.11 and CI are `NOT_RUN` / `UNKNOWN`.** Host is 3.13.0. T07
  adds only stdlib table arithmetic and no syntax newer than 3.11. **No outcome
  is predicted.**
- **U2 — whether `speckit-plan` degrades under `ITERATIVE` with no
  `.specify/memory/constitution.md` is UNKNOWN.** Tests never invoke Spec Kit.
  Validating a repository baseline is T08's.
- **U3/U4 — the *quality* of a defect flow's Spec Kit output and of the impact
  analysis is unmeasurable by this suite.** What is pinned mechanically: the
  artifact exists, clears the size floor, is fingerprinted, is review-bound to
  its exact SHA, and is displayed to the human before `gate_spec`.
- **U5 — `BROWNFIELD_DISCOVERY` is declared equal to GREENFIELD.**
  `test_brownfield_discovery_is_greenfield_until_t08_changes_it` is **meant to
  fail** when T08 changes it, and must not be softened to a subset assertion.
- **U6 — an in-flight pre-v1.16 workflow carrying a non-GREENFIELD record will
  refuse `flow_mismatch` at its next advance.** Declared consequence, not a
  defect; it *was* traversing GREENFIELD.
- **U7 — suite runtime variance.** 1026 s here, 1305.96 s recorded by the
  revision-2 planner on the same machine. **Never give a full run the two-minute
  default; budget 1,500,000 ms.**
- **Tooling.** A plain `grep -rn` under the `rtk` hook produced a **false
  negative** for A22's `skipif` line; `rtk proxy "grep -rnE …"` and an
  independent Python walk both found it. Any grep-based negative claim in a
  verification should be reproduced with `rtk proxy` or in Python.
- **Line endings.** `SKILL.md`, `scripts/sdle.py`, `tests/conftest.py` and
  `tests/test_units_governance.py` are CRLF in the working tree and LF in the
  index — **pre-existing**, and `git diff --numstat` shows only the intended
  line changes. A byte-comparison of a working-tree file against `git show` must
  normalise newlines first; A16 initially read `False` for exactly that reason
  and is `True` once normalised.

---

## Claims for the verifier to independently check

1. `901 passed`, RAW EXIT 0, `--collect-only` 901, `short test summary` count 0,
   and the +110 decomposing as 98 + 11 + 1.
2. `lint-skill` 29/29 exit 0, `20 phases, 8 gates, 16 migration rows`, `v1.16` —
   and that the baseline at `7dba4b6` is **22** with **zero** checks removed.
3. **A5-P3 by your own hand:** parse `PHASE_SEQUENCE` out of
   `git show 7dba4b6:.claude/skills/sdle/SKILL.md` and compare element-wise with
   `constants.flows["GREENFIELD"]` — 19 entries, equal, no `impact_analysis`.
4. `GREENFIELD` is **not** a `FLOW_PHASES` row key, the registry has 20 entries
   and **no flow has 20**.
5. `DEFECT_FIX` is **14/6**, not 14/5 — re-derive from the flow's own phase list
   rather than from D4's summary column.
6. `approvals` has exactly **eight** keys in the template and never gains a
   ninth during a full DEFECT_FIX run; **`gate_impact_analysis` appears in
   exactly one file**, `tests/test_units_flow_model.py`, at 7 lines, **all
   negative assertions proving its absence** — a naive grep will look like
   leakage and is not.
7. The three `flow_mismatch` paths leave `audit.md` byte-identical, and
   `test_the_governance_refusals_are_not_masked_by_the_flow_check` still passes.
8. The AST closed sets: `state["flow"]` writers `{cmd_init, _mig_1_15}`;
   `consts.next_phase` readers `{load_constants, run_sync_checks, cmd_constants}`;
   `apply_advance` callers exclude `cmd_init`; `required_gate_set` callers are
   the two governance commands.
9. A13's 15 names byte-identical; the must-not-change list clean; the nine
   transcripts byte-identical with zero `impact_analysis`.
10. The write fence permits `reviews/impact-analysis-<ts>.md` with
    `.claude/hooks/` unmodified.
11. `PROGRESS_MAP`'s 19 rows byte-identical (**normalise CRLF first**).
12. No T08+ leakage: no `.sdle/baseline*`, `governance gates` still
    `advisory: true`, no gate conditional on risk, `BROWNFIELD_DISCOVERY ==
    GREENFIELD`, no new file under `.claude/`.

---

## Blocker

**None.** No material decision arose. The three plan defects above are ordinary
defects — found by running tests, resolved in the repository, and declared here
rather than escalated.

## One thing the orchestrator must do

**Nothing is committed.** HEAD is `77ca0b8` and the entire phase — engine,
prompts, documentation, ADR-004, the new test module, eight checkpoints and this
handoff — is in the working tree. The assignment named the handoff and the
`progress.md` row as the deliverables and did not ask for a commit, and the
standing rule is to commit only when asked. The `Commit` column of the
`progress.md` row is therefore `-`.
