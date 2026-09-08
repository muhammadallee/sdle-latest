# T10 checkpoint — attempt 01, milestone M2

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M2 — `CAPABILITY_MAP` becomes a parsed constant
**Milestone status:** COMPLETE
**Rollback:** `git checkout -- scripts/sdle.py .claude/skills/sdle/SKILL.md` returns to the end of M1.

---

## What M2 changed

Two files.

**`.claude/skills/sdle/SKILL.md`** — a new `### CAPABILITY_MAP` table in
Internal Constants, inserted immediately before `### VERSION_MIGRATION`. It maps
all 21 registry phases to the capability files each requires, using
FLOW_PHASES' cell convention (space separated, **not** backticked — one pair of
backticks around the whole cell is stripped and the list mangles into a single
unrecognisable path). At M2 it maps only the three modules that exist; M3
re-values the four rows that will name the two new capability files.

The prose above the table states the two properties the checks enforce: it is a
**floor, not a ceiling** (a capability file may point at another one, and
following that is correct), and `SKILL.md` is never a value because it is the
always-loaded orchestrator, not a capability.

**`scripts/sdle.py`** —

- `Constants.capability_map` field and `Constants.capabilities_for(phase)`, a
  non-raising accessor that answers `[]` for a phase with no row. Non-raising on
  purpose: a read-only reporter must still be able to say where a WorkItem *is*
  rather than refusing because a table has a hole in it, and the lint check is
  what makes the hole impossible in a repository that lints.
- The `parse_md_table(skill, "CAPABILITY_MAP")` loop in `load_constants`,
  deliberately **unvalidated** there — exactly as FLOW_PHASES is — so a broken
  row surfaces as the named check it breaks rather than as one opaque
  `tables_wellformed` failure that short-circuits everything after it.
- `capability_map` added to `cmd_constants`' payload. Nothing was removed to
  make room.
- `_check_capability_map(paths, consts)` — six checks, wired into
  `run_sync_checks` between the flow checks and the discovery checks.

## Evidence

| Measurement | Result |
|---|---|
| `lint-skill` | **39 checks** (33 + 6), `failed: []`, exit 0 |
| New check names | `capability_map_covers_every_registry_phase`, `every_capability_file_exists`, `capability_map_never_names_the_orchestrator`, `every_capability_file_is_linted`, `every_row_is_a_strict_subset_of_the_capability_set`, `capability_cross_references_are_mapped_files` |
| All 33 pre-T10 check names | still present, still passing |
| `constants` payload | `capability_map` has **21 rows**; row-key set equals `phase_sequence` exactly |
| Union of all rows | `['modules/gate-protocol.md', 'modules/phase-execution.md', 'modules/security-review.md']` — exactly the `modules/*.md` on disk |
| Progressive property | every row is a **strict** subset of the union; longest row 2, shortest 1 |
| Targeted: `test_lint_skill.py test_units_flow_model.py test_units_discovery.py test_units_governance.py test_units_gate_policy.py` | **748 passed**, 489.42 s |

## One deviation from the plan's milestone table, recorded

The plan puts **N3** in M2. N3's non-vacuity guard requires the capability union
to have **≥ 4 members**, and at M2 the union has exactly 3 — the two new
capability files do not exist until M3. Asserting it at M2 would have opened an
undeclared red window for the sake of a one-milestone earlier landing.

**N3 therefore lands in M3, with its `>= 4` guard intact and unweakened.** The
engine-side half of the same property —
`every_row_is_a_strict_subset_of_the_capability_set` — is live from M2 and is
already passing. No assertion was softened; one was scheduled one milestone
later. The new test file is not yet in `tests/`; it is added whole at M5, which
is when the agents it also covers exist.

## Ordering note carried forward

The `CAPABILITY_MAP` prose at M2 says "the engine reports the row for the
current phase" rather than naming `sdle.sh resume`, because `resume` does not
exist until M4. M4 changes that one sentence to name the command. Each
milestone's prose is true at the milestone.

## Resume instructions for a fresh context

- Next milestone is **M3**: `modules/design-review.md`, `modules/code-review.md`,
  the four re-valued map rows, SKILL.md Steps 5/6/6b, and pointer edits in
  `phase-execution.md` and `gate-protocol.md`. Patch script:
  `<scratchpad>/t10/m3.py`.
- Verify against disk first: `python scripts/sdle.py lint-skill` should report
  **39** checks with `failed: []`, and `python scripts/sdle.py constants` should
  carry a 21-row `capability_map` under `data`.
- Nothing under `tests/` has been touched yet.
