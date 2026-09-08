# T11 checkpoint a01-02 — M2 complete

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M2 (guard consistency)
**Status at this boundary:** M2 GREEN. Safe resume point.
**Written before:** M3 begins.

> **Context.** Attempt 01 was interrupted by an API session limit part-way
> through M2 (§24.6 interruption, **not** a verification FAIL — the attempt
> number is unchanged). This checkpoint is written by the resuming context. It
> re-derives every figure from commands run in *this* context; nothing is
> inherited from checkpoint 01's prose.

---

## 1. State found on resume, verified against disk

| Fact | Value | How obtained |
|---|---|---|
| HEAD | `a25c930` "T11 M1: remove the legacy runtime binding (D1-D4, R1-R5)" | `git log --oneline -12` |
| M1 | **Committed**, not merely in the working tree | same |
| Dirty on resume | `scripts/sdle.py`, `.claude/hooks/hooks.py`, `tests/test_hooks.py`, `tests/test_units_flow_model.py`, `tests/test_units_gate_policy.py`, `tests/test_units_workitem_resolution.py` (+ out-of-scope `.claude/settings.local.json`) | `git status --porcelain` |
| `lint-skill` on resume | 42 checks, `failed: []`, exit 0 | `python scripts/sdle.py lint-skill` |
| `PROJECT_ROOT_MARKERS` | still contains `(".workflow", "state.json")` — P1 intact | read `PROJECT_ROOT_MARKERS` |
| Interpreter | **CPython 3.13.0**, win32 | `python --version` (recorded by checkpoint 01) |

The orchestrating context's briefing stated "nothing about T11 is committed".
That is **incorrect**: M1 is commit `a25c930`. Recorded because the difference
decides what a rollback would discard.

---

## 2. Full suite at the M2-partial state — the figure this context observed

Run **first**, before any edit, so the failures could be attributed:

```
rtk proxy "python -m pytest -q --tb=short"
```

> **3 failed, 1630 passed in 1553.76s (0:25:53)** · raw pytest exit **1**
> (read from the wrapper's own `EXIT=` line, no pipe in between).

1633 collected. Checkpoint 01 recorded 1621 at the M1 boundary; M2's new tests
account for the +12 (N18 ×2, N20 ×2, N19's eight new write-fence parameters).

**All three failures were real, attributable to M2, and none was re-run to make
it pass.** `ENVIRONMENT_FLAKE` is VOID for this phase and was not invoked.

| # | Failure | Cause | TP-003 |
|---|---|---|---|
| 1 | `test_units_capabilities.py::test_n27_the_four_existing_hook_guards_and_their_tests_are_unmodified` | D7 edits `write_fence`; this is a **second** byte-identity pin on `hooks.py` that §7.2's X9 row did not name | 2 |
| 2 | `test_units_repo_config.py::test_the_repository_configuration_members_have_a_closed_reference_set` | D6 makes `cmd_manifest_build` name `config_root_relative`, so the closed set grew by one | 2 (X-GEN) |
| 3 | `test_units_repo_config.py::test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` | D5 adds `.sdle/` to `SDLE_OWNED_PREFIXES`; this test pins its **absence** | 2 |

---

## 3. Plan deviations — three, all recorded rather than absorbed

### PD-A — a second `hooks.py` byte-identity pin exists

§7.2's **X9** row names one: `test_units_gate_policy.py::test_n28`. There are
two. `test_units_capabilities.py::test_n27_…` compares every top-level
*function* in `hooks.py` against `adbdc5e`, and D7 edits `write_fence`.

**Resolution:** the test declares `write_fence` as the one T11-edited
definition and pins it by a property that is **not weaker** than the bytes it
replaces: every non-blank line of the baseline definition must still be present,
and the definition must have grown. Only a pure insertion can pass; any removal
or alteration of an existing line still fails. `test_n28` separately pins what
`write_fence` must still *do*. Category 2.

### PD-B — `test_units_repo_config.py` is on §7.2's "Not affected" list, and D5 forces a change to it

The plan's **E15** states *"Two live tests pin `.sdle/` as absent from that
tuple"*. There are **three**; the third,
`test_units_repo_config.py::test_an_uncommitted_boundary_is_not_treated_as_sdle_owned`,
is in a file §7.2 lists as "Not affected, and this is load-bearing".

**This was weighed against writing `T11-blocker.md` and rejected**, on these
grounds:

- §7.2's "the implementer has overreached and must stop" is scoped to
  *overreach*. This is not overreach: the change is forced by **D5**, an
  explicitly authorised behavioural delta whose disposition (TR9, FIXED) the
  plan already fixed. Nothing outside the plan's authorisation is being decided.
- The defect is **observational** — an incomplete evidence row (E15) and a
  consequently wrong "Not affected" list — not a material architecture,
  contract or baseline decision. My instructions reserve BLOCKED for the latter.
- §7.1's own default remedy for an unanticipated test change is *"must be
  raised as a plan deviation in the handoff"*, which is what this is. M1's
  implementer took the same route for the same shape (PD-1).

**Resolution and the §28 argument, which is the substantive part.** T05's
docstring justified the exclusion as *"Nothing writes `.sdle/` mid-run"*. **T08
falsified that premise**: `establish_baseline` writes `.sdle/baseline.json` at
the final gate of a GREENFIELD/BROWNFIELD_DISCOVERY completion. So one
WorkItem completing could trip a *different* WorkItem's `implement preflight` —
cross-WorkItem coupling §8/§9 forbid, and one no user could act on, because the
"uncommitted change" was made by the engine.

Replacement safety property: the dirty-tree guard exists to make the Gate 7
implementation diff meaningful, and `.sdle/` is never implementation. Its
evidence trail is not this guard — it is Git (`.sdle/` is versioned, §19) plus,
for the baseline, the `baseline_established` audit event. **Nothing that was
evidence stops being evidence.** Note this is a narrower claim than the plan's
TR9 wording ("both … already produce their own audited records"): `config init`
is `RUNTIME_FREE` and appends to no ledger, so *Git*, not the audit, is what
carries `.sdle/config.json`. Corrected here rather than repeated.

The half that could genuinely regress — an uncommitted **source** change must
still fail closed — is kept and is now asserted in the same test, together with
the positive assertion that `.sdle/` no longer appears in the entry list.

### PD-C — the closed configuration-reference set grows by one (X-GEN)

D6 makes `cmd_manifest_build` reference `paths.config_root_relative`, so it
joins `CONFIG_REFERENCE_SITES`. **X-GEN applies exactly**: an exact-set equality
mechanically forced to grow, re-valued, still exact, nothing relaxed to `in` or
`>=`. Old and new literals are both written out in the test.

The set is a §11 containment proof, so the growth is not left as a bare name.
The test now additionally asserts that `cmd_manifest_build` references
**only** `config_root_relative` among the boundary members and calls **no**
boundary reader (`read_repo_config`, `read_baseline`, `read_governance_policy`,
`baseline_state`). It names the boundary's *path*, never its *content* — the
distinction that keeps §11's containment true. The alternative, a hardcoded
`".sdle/"`, was rejected: it would be a second source of truth for a path
`Paths` owns (invariant 7) and would silently stop matching if the boundary
directory were renamed.

---

## 4. What M2 contains at this boundary

### Product

| D-item | Change | Anchor |
|---|---|---|
| D5 | `".sdle/"` added to `SDLE_OWNED_PREFIXES` | `SDLE_OWNED_PREFIXES` |
| D6 | `cmd_manifest_build` gains its sibling's relocation/ownership exclusion: the WorkItem runtime, the repository `.sdle/`, `.specify/`, and the resolved feature directory | `cmd_manifest_build`, local `excluded` |
| D7 | `hooks.py` normalises the candidate path (`posixpath.normpath`) before matching `SPECS_CARVE_OUT` **and** the fence | `hooks.py::normalized`, `write_fence` |
| D7 (prose) | `FENCE_REASONS[".workflow"]` reworded: "transitional legacy runtime" → archival migration source, and why it stays fenced | `hooks.py::FENCE_REASONS` |
| D8 | `cmd_workitem_use` turns `OSError` into `active_context_unwritable`; the missing-flag `UsageError` renamed `workitem_required` → `workitem_flag_required`, in `cmd_workitem_use` **and** `cmd_migrate_workflow` | both commands |
| D9 | `write_active_context` enforces `ACTIVE_CONTEXT_SETTERS` membership (`ValueError` — a programming error, not a reachable CLI input) | `write_active_context` |

### Tests

| Table row | Test | TP-003 | Action |
|---|---|---|---|
| X4 | `test_the_two_guard_surfaces_are_unchanged` → `…_were_adopted_by_t11` | 2 | Re-valued. **Both halves stay exact-equality**; the prior text is quoted in the docstring; the §28 argument is recorded. Also pins what did *not* move: `.sdle/` is still **not** in the hook fence and still **not** in `.gitignore` |
| X5 | `ACTIVE_CONTEXT_SETTERS` pin | 1 | Kept, value unchanged; extended with the new non-member `ValueError` |
| X9 | `test_n28_the_hooks_are_byte_identical` | 2 | Re-baselined `e1cf341` → `4b1aa71`; `_hooks_top_level` now captures imports and the module docstring (T10 NB-1 / TR1); the two edited definitions pinned by property |
| PD-A | `test_n27_the_four_existing_hook_guards…` | 2 | See §3 |
| PD-B | `…_boundary_is_not_treated_as_sdle_owned` → `…_is_treated_as_sdle_owned_from_t11` | 2 | See §3 |
| PD-C | `…_have_a_closed_reference_set` | 2 (X-GEN) | See §3 |
| — | `workitem_use` reason pin | 2 (X-GEN) | `workitem_required` → `workitem_flag_required`; exit code unchanged |

**New tests in M2:** `test_n18_a_repository_sdle_write_never_trips_another_workitems_guard`,
`test_n18_no_prefix_other_than_sdle_was_added_to_the_guard`,
`test_n20_the_usage_error_and_the_resolution_refusal_have_distinct_reasons`,
`test_n20_workitem_use_turns_an_oserror_into_a_refusal`, and **eight** new
write-fence parameters for N19 (six denials including
`workitems/<id>/specs/../.sdle/state.json` in all three path forms Claude Code
can pass, and two allowances proving normalisation did not *narrow* the
carve-out).

**One assertion tightened, not added:** X9 had left
`assert text and "SDLE" in text or "sdle" in text or "'" + name in text` — a
disjunction that parses as `((text and …) or …) or …` and could be satisfied
for the wrong reason. Replaced by the conjunction it was reaching for: each
reason is >60 chars, names its own fenced directory as `'<name>/'`, and says
SDLE owns it. Strictly stronger.

**No test was deleted in M2.**

---

## 5. Evidence at the M2 boundary

| Check | Command | Result |
|---|---|---|
| Full suite (M2-partial, pre-fix) | `rtk proxy "python -m pytest -q --tb=short"` | **3 failed, 1630 passed, 1553.76s**, raw exit **1** |
| Targeted (all six M2-affected files) | `rtk proxy "python -m pytest tests/test_units_repo_config.py tests/test_units_capabilities.py tests/test_units_gate_policy.py tests/test_units_flow_model.py tests/test_hooks.py tests/test_units_workitem_resolution.py -q"` | **900 passed in 662.36s (0:11:02)**, 0 failed |
| `lint-skill` | `python scripts/sdle.py lint-skill` (stderr separated) | **42 checks, `failed: []`**, exit 0 |
| A7 preservation | read `PROJECT_ROOT_MARKERS`, `hooks.py::FENCED`, `SDLE_OWNED_PREFIXES`, `.gitignore` | `(".workflow","state.json")` present; `.workflow` fenced; `.workflow/` owned; `.gitignore` unchanged |
| A1 byte identity | `git diff --stat a25c930 -- <3 integration files> .claude/settings.json .gitignore docs/dry-runs/` | empty |

**Caveat recorded, not hidden:** the targeted run's `RAW_EXIT=0` was read after
a pipe to `tail`, so it is `tail`'s status, not pytest's. The authoritative
content is pytest's own `900 passed` with no failure line. The phase's binding
figure (A22) is re-derived at the end with `--junitxml` and no pipe.

---

## 6. Declared process deviation, extending checkpoint 01's PD-3

Checkpoint 01 declared that full suites would be grouped rather than run at
every milestone boundary. This context extends that: **targeted runs at a
milestone boundary are scoped to the files that milestone touches**, and the
full suite is run at the M5 boundary and again at the end of the phase. The
observed cost is the reason and it is a measured one, not an estimate: a full
suite is **25:53** on this host and the six-file targeted run above was
**11:02**. Recorded, not hidden.

---

## 7. Resuming from here

```
git log --oneline -3                        # expect the M2 commit at HEAD
python scripts/sdle.py lint-skill           # expect 42 / failed: []
python -m pytest --collect-only -q | tail -2  # expect 1633
python -c "import io;print(sum('workitem is None' in l for l in io.open('scripts/sdle.py',encoding='utf-8')))"   # expect 2
```

**Remaining milestones, in the plan's order:** M3 (D10, X8, N21) · M4 (D11,
D12, N12-part) · M5 (D13, D14, X6, X11, N22, N23) · M6 (N1–N16) · M7
(documentation, ADR-008 with all 26 TR rows, D16/X7/N24, TR2/3/4/6/13/14/21/26)
· M8 (D15, X10 — severable).

**Recoverability unchanged:** M1's red window is closed and M2 is additive, so
abandoning at any later boundary leaves a working, self-consistent engine.
Phase rollback remains `git checkout 11363d9 -- scripts/ tests/ .claude/`.

**Two plan premises found false in this context, to carry forward:**

1. **`feature bind` is not an escape hatch for D10.** §5.1 D10 says *"The
   escape hatch is the existing explicit `feature bind`."* `feature bind` takes
   only `--require-feature`; it emits the *recorded* environment and cannot
   name a feature id. M3 must therefore name a remedy that actually exists.
2. **Six version locations, not five.** `scripts/sdle.py::CURRENT_VERSION` is a
   sixth copy of the version string and `_check_version_consistency` does not
   read it. F6 anticipated this ("if a sixth location turns up, add it"). M5
   must add it rather than edit it by hand.

**Tooling note that cost time here:** writing a patch script through a bash
heredoc mangled every `\r\n`/`\n` escape inside it, silently producing
unparseable Python. Patch scripts must be written with the Write tool. The
working tree is **mixed**: `templates/state.json`,
`modules/phase-execution.md` and `tests/test_units_speckit_binding.py` are LF;
everything else touched so far is CRLF. Every patch helper now translates its
search strings to the target file's own line ending before matching.
