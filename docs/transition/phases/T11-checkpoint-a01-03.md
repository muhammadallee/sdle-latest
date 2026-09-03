# T11 checkpoint a01-03 — M3 complete

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M3 (Spec Kit tier ambiguity fails closed)
**Status at this boundary:** M3 GREEN. Safe resume point.
**Written before:** M4 begins.

---

## 1. What M3 changed

**D10 — `cmd_feature_resolve` applies §9's own 0/1/>1 rule inside the chosen
tier.** More than one candidate now refuses `feature_ambiguous` and lists them.
Baseline picked the newest mtime and refused only on an exact timestamp tie.

The defect this closes (T04 N-2 / TR10) is concrete: tier 2 is the
repository-global `specs/`, which is where Spec Kit 0.15.0 hardcodes feature
*creation*. Two WorkItems both standing at the specification phase stage into
one shared directory, and the newest-mtime rule hands whichever runs second the
other one's specification — silently, with no refusal and no audit entry saying
a choice had been made. **Recency is not evidence of ownership.**

| Change | Anchor |
|---|---|
| `len(candidates) > 1` refuses; the timestamp comparison is gone | `cmd_feature_resolve`, comment `# T11 D10.` |
| The refusal's `data` gains `workitem` and `remedy_tier`; `candidates` is now name-sorted | same |
| `_feature_candidates` sorts by **name**, not mtime | `_feature_candidates` |
| The dead `legacy = specs_root is None` branch removed with its `.specify/specs`-only tier list | `cmd_feature_resolve` |
| `Paths.speckit_specs_root`'s docstring corrected: `None` now means *unbound*, not *legacy-bound* | `Paths.speckit_specs_root` |

### Plan deviation PD-D — the plan's named escape hatch does not exist

§5.1 **D10** says: *"The escape hatch is the existing explicit `feature bind`."*
It is not. `feature bind` takes one flag, `--require-feature`; it **emits** the
environment already recorded in `state.specKit` and cannot name a feature id.
If `feature resolve` refuses, `feature bind` has nothing to bind. Verified by
reading the subparser (`fbind.add_argument` — one argument) and
`cmd_feature_bind` (a pure reader).

Two options were weighed:

- **(a) add `--feature-id` to `feature resolve`** — new CLI surface, a new
  override flag, at the last phase of the migration. An override flag is also
  precisely the shape §9 warns about: it makes "SDLE will not guess" negotiable.
- **(b) name the remedy that already works** — tier 1 is
  `workitems/<id>/specs/` and takes precedence over every shared tier, so
  *moving* the directory this WorkItem owns into its own tier resolves the
  ambiguity **by precedence**, with SDLE still choosing nothing.

**(b) was taken.** It adds no surface, keeps the fail-closed property total,
and the refusal message names it with the concrete path. Because "a
fail-closed refusal is only honest if the way out actually works", the remedy
is *performed end to end* by `test_n21_the_named_remedy_is_a_real_one` rather
than described — the test reads `remedy_tier` out of the refusal, does exactly
that move, and asserts the next `feature resolve` succeeds and leaves the other
WorkItem's staged directory untouched.

### Plan deviation PD-E — a residual of M1 closed in M3

`cmd_feature_resolve` carried a `legacy = specs_root is None` branch. It was
**not** in D4's list, because E11/E12 enumerated textual `paths.workitem is
None` and this one reads the derived `speckit_specs_root` instead. After D1/D2
it was unreachable (`feature` is not `RUNTIME_FREE`, so `bind_workitem` has
returned a bound `Paths`), and its docstring said *"T11 removes that rung, not
T04"* — naming T11 as its owner. Removed here, with M3, because M3 rewrites the
same function; recorded rather than folded in silently. It is R1/R3's intent
(*"all carve-outs which become unreachable"*), not new scope.

`Paths.speckit_specs_root` still returns `None`, and deliberately: the source
view `cmd_migrate_workflow` builds with `dataclass_replace(paths,
workitem=None)` is genuinely unbound (P2). A3 permits exactly that — a
`workitem is None` test inside `Paths` itself.

---

## 2. Tests

| Table row | Test | TP-003 | Action |
|---|---|---|---|
| X8 | `test_n7_ambiguity_inside_the_chosen_tier_still_refuses_and_lists` | 3 (defect fixed) | Rewritten. It used to force the two mtimes **equal**, because only a tie refused. The equalising is gone and the timestamps are now deliberately far apart, so a return of the newest-mtime rule would make this test *fail* rather than pass quietly |
| X8 | `test_n7_a_timestamp_tie_still_refuses_exactly_as_it_did` | — | **New.** The exact case baseline already refused, kept as its own test with the same reason string and candidate list, so nothing was traded away for the widening |
| X8 | `test_n7_tier_one_wins_even_when_a_later_tier_is_far_newer`, `test_n7_tier_two_wins_over_tier_three_and_is_adopted`, `test_n7_all_tiers_empty_refuses_and_lists_what_was_searched` | 1 | **Unchanged.** These are *tier-precedence* tests with one candidate per tier; D10 does not touch them. §7.2 asked that the single- and zero-candidate cases keep their assertions verbatim, and they do |

**New tests (N21):** `test_n21_two_candidates_in_the_shared_tier_refuse_and_write_nothing`
(both WorkItems' `state.json` and `audit.md` byte-identical across the refusal —
B2 — and both staged directories untouched),
`test_n21_the_named_remedy_is_a_real_one`, and
`test_n21_one_candidate_in_the_shared_tier_still_resolves` (the adoption path
kept verbatim).

**No test was deleted in M3.**

**No test outside `test_units_speckit_binding.py` changed.** Every existing
`feature resolve` caller — including all three integration files and
`test_units_flow_model.py` — sets up exactly one candidate in the chosen tier,
verified by a walk over every `feature", "resolve` site in `tests/`, so F5 did
not materialise.

---

## 3. Evidence at the M3 boundary

| Check | Command | Result |
|---|---|---|
| Targeted | `rtk proxy "python -m pytest tests/test_units_speckit_binding.py -q --tb=short"` | **59 passed in 74.32s**, `EXIT=0` read with **no pipe** |
| New tests really run | `pytest … --collect-only` | all five named tests collected |
| Regression (A1's files + flow) | `rtk proxy "python -m pytest tests/test_integration_01_happy_path.py tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py tests/test_units_flow_model.py -q"` | **195 passed in 373.75s**, 0 failed |
| `lint-skill` | `python scripts/sdle.py lint-skill` | **42 checks, `failed: []`** |
| A1 byte identity | `git diff --stat 4b1aa71 -- <3 integration files> .claude/settings.json .gitignore docs/dry-runs/` | empty |

`ENVIRONMENT_FLAKE` remains VOID and was not invoked. No failure was re-run.

---

## 4. Resuming from here

**Remaining:** M4 (D11, D12, N12-part) · M5 (D13, D14, X6, X11, N22, N23) ·
M6 (N1–N16) · M7 (documentation, ADR-008 with all 26 TR rows, D16/X7/N24,
TR2/3/4/6/13/14/21/26) · M8 (D15, X10 — severable).

**Carry forward:** `scripts/sdle.py::CURRENT_VERSION` is a **sixth** version
location and `_check_version_consistency` does not read it. M5 must add it
there (F6's instruction) rather than edit it by hand.

Recoverability unchanged: every remaining milestone is additive or
documentation-only.
