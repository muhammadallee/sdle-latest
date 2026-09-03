# T10 checkpoint — attempt 01, milestone M3

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M3 — the two capability files, the map rows that name them, and X1
**Milestone status:** COMPLETE
**HEAD:** `875b361009e2c16d66c2a99ebda0d734a45915db` (OBSERVED, `git rev-parse HEAD`). Nothing is committed; all work is live in the working tree.
**Rollback:** `git checkout -- scripts/sdle.py .claude/skills/sdle tests/test_units_gate_policy.py && rm tests/test_units_capabilities.py` returns to the end of M2.

> **Context note.** This checkpoint was written by a *second* implementer
> context. The first was terminated by an API session limit after checkpoint 02
> and after it had already applied the whole of `m3.py` to disk. That is an
> interruption per §24.6, not a verification FAIL, so this is still attempt 01.
> Every figure below was re-derived by a command run in this context; none is
> copied from checkpoint 01 or 02.

---

## The ordering correction, verified against disk rather than accepted

Checkpoint 02's successor context recorded, as its last words, that
*"the leakage test's `modules` literal fires at M3, not M5"*. That is a real
correction to the plan's milestone table, and it was verified here two ways
before acting on it.

**By reading.** `tests/test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage`
enumerates **two** closed sets in one function — the `.claude/agents/` contents
*and* `sorted(modules/*.md)`, the latter asserted equal to the three-element
literal `["gate-protocol.md", "phase-execution.md", "security-review.md"]`. The
plan's red-window note (Implementation sequence, "The declared red window")
reasons only about the agents set and therefore places the whole of X1 in M5.

**By running.** The full suite at the state this context inherited — M1 + M2
complete, `m3.py` applied, `tests/` untouched:

| Measurement | Result |
|---|---|
| `rtk proxy python -m pytest -q`, redirected, `$?` read with no pipe | **1 failed, 1401 passed in 1404.10 s**, `RAW_EXIT=1` |
| The single failure | `tests/test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage` |
| The failing assertion | `assert modules == ["gate-protocol.md", "phase-execution.md", "security-review.md"]`, actual `['code-review.md', 'design-review.md', 'gate-protocol.md', 'phase-execution.md', 'security-review.md']` |
| Any other failure | none |

So the window opened at M3 exactly as the correction says, and it was the
`modules` literal alone. **X1's split was therefore applied at M3**, with the
`modules` literal re-valued here and the `agents` literal re-valued at M5, in
the working step that grows each set. No red window survives a milestone
boundary in either direction.

**This is recorded as a deviation from the plan's milestone table, not hidden
inside it.** The plan puts all of X1 in M5; half of it landed in M3 because the
set it guards grew in M3. Nothing was weakened to make that possible — see the
X1 shape evidence below.

---

## What M3 changed

### Product files — applied by the previous context, verified here

| File | Change | Verified by |
|---|---|---|
| `modules/design-review.md` | **new** capability file: how a design review is conducted, delegated to `sdle-design-review`, and recorded by the *parent* with `artifact review --actor-type agent` | on disk; `git status` shows it untracked |
| `modules/code-review.md` | **new** capability file, same shape for implementation review | on disk |
| `SKILL.md` | four `CAPABILITY_MAP` rows re-valued to name the new files (`design_generation`, `gate_design`, `implement`, `gate_implement`); Step 5 renamed *Capabilities — What to Load*; Step 6 stops naming a module; new **Step 6b: Product Subagents** | `git diff` = `45 3` |
| `modules/phase-execution.md` | two pointer lines only — `--actor-type agent --actor-name <agent>` is the one door, and the review capability for the phase is where the procedure lives | `git diff` = `2 1`; **no block added, removed or renumbered** |
| `modules/gate-protocol.md` | one inserted numbered step naming the review capability, and the two following steps renumbered 5→6, 6→7 | `git diff` = `3 2`; `GATE_TO_EXECUTION_PHASE` untouched |

`scripts/sdle.py` was **not** touched by M3: `git diff --numstat` is still
`206 11`, exactly M1 + M2.

### Test files — applied in this context

**X1 (TP-003 category 2), `tests/test_units_gate_policy.py`.**
`test_n31_no_t10_or_t11_leakage` is split in two.

- `test_t10_ships_exactly_the_declared_agents_skills_and_modules` carries the
  three T10-half assertions, each still **exact equality against a written-out
  set** — never relaxed to a prefix test, a subset or an `any`.
- `test_n31_no_t11_leakage` carries the T11 half **verbatim**, message string
  included: it still reads `"T04 N-7 / T05 NB-7(b) is T11's, not T09's"`,
  because X1 says that half is moved and not touched otherwise. A staged draft
  had modernised it to `not T10's`; that was reverted here.

**X-GEN re-valuations recorded verbatim** (plan X-GEN, clauses a/b/c — the
assertion keeps its shape, the literals are recorded, nothing is deleted):

| Literal | Old | New |
|---|---|---|
| `modules` | `["gate-protocol.md", "phase-execution.md", "security-review.md"]` | `["code-review.md", "design-review.md", "gate-protocol.md", "phase-execution.md", "security-review.md"]` |
| agents | *derived*: `stray = [n for n in agents if not n.startswith("sdle-transition-")]`, `assert stray == []` | `assert agents == ["sdle-transition-implementer.md", "sdle-transition-orchestrator.md", "sdle-transition-planner.md", "sdle-transition-verifier.md"]` — M5 adds the four product agents to this same list |
| `skills` | `["apply-sdle-transition", "sdle"]` | **unchanged** — T10 adds no skill directory |

The agents assertion is *stronger* after the change than before: `stray == []`
said nothing about which control-plane files exist, where the enumeration does.

**New file `tests/test_units_capabilities.py`** — the M3 slice only, 293 lines.
It contains the capability-map section (N1, N2, N3, N4, N5, N7, N8 ×3) and the
N6/N28 content section. The remaining sections land in the milestone that
builds what they cover: `resume` at M4, the agents and the fence at M5, the
"nothing else moved" guardrails at M6. Adding the file whole here would have
opened an undeclared red window for `resume` and for four files that do not
exist.

`new_prompt_files()` currently returns the **two** capability files and
`test_n6_the_needle_sets_are_not_vacuous` asserts `== 2`. M5 extends it to the
four product agent prompts and re-values that to `== 6`; both literals are
recorded here so the growth is visible rather than discovered.

**N3 landed here, as checkpoint 02 scheduled it**, with its `>= 4` non-vacuity
guard intact: the union is now `{design-review, code-review, gate-protocol,
phase-execution, security-review}` = 5 members, and the longest row is 2, so
every row is a *strict* subset with room to spare.

---

## Evidence — every figure re-derived in this context

| Measurement | Result | Command |
|---|---|---|
| Full suite, **end of M3** | **1439 passed in 1413.17 s, `RAW_EXIT=0`** | `rtk proxy python -m pytest -q -p no:cacheprovider`, redirected to a file, `$?` read with no pipe |
| `short test summary` sections in that capture | **0** | `grep -c` |
| Full suite, state inherited (pre-X1) | 1 failed / 1401 passed, `RAW_EXIT=1` — the single failure is the one X1 re-values | same |
| Collected delta | 1402 → 1439 | the two runs above |
| Targeted: `test_units_capabilities.py test_units_gate_policy.py test_lint_skill.py` | **439 passed in 154.79 s, `RAW_EXIT=0`** | `rtk proxy python -m pytest -q <files>` |
| `lint-skill` | **39 checks, `failed: []`, exit 0** | `python scripts/sdle.py lint-skill`, payload under `data` |
| `constants` → `capability_map` | **21 rows**, key set equals `phase_sequence` | `python scripts/sdle.py constants` |
| Union of all rows | 5 files, equal to the `modules/*.md` on disk | same |
| `git diff --numstat` (tracked, in scope) | `SKILL.md 45 3`; `gate-protocol.md 3 2`; `phase-execution.md 2 1`; `sdle.py 206 11`; `test_units_gate_policy.py 40 16` | `git diff --numstat` |
| Untracked, in scope | `modules/code-review.md`, `modules/design-review.md`, `tests/test_units_capabilities.py` | `git status --porcelain` |
| Out of scope, untouched | `.claude/settings.local.json` (modified before this phase began) | same |
| Python | **3.13.0**. Python 3.11: `NOT_RUN` | `python -V` |
| CI | `NOT_RUN` | never observed at any point in this migration |

`tests/test_units_artifact_review.py` is **not** yet modified: X2 lands at M5,
in the same working step as the four agents.

---

## Two forward references, recorded rather than reworded twice

Checkpoint 02 established that each milestone's prose should be true at the
milestone. M3's prose breaks that in two places, deliberately:

1. `modules/design-review.md` and `modules/code-review.md` both open with
   *"`sdle.sh resume` reports which capability files the current phase
   requires"*, and `modules/phase-execution.md` says the same.
2. `SKILL.md` Step 5 says *"`sdle.sh resume` reports `capabilities`"*.

`resume` does not exist until M4, which is the very next milestone and is
implemented in the same working session. Rewording all four now and again at M4
would churn four files for one milestone's worth of accuracy. **M4 closes the
gap by making the sentences true**, and M4 additionally rewrites the one
`CAPABILITY_MAP` prose sentence checkpoint 02 flagged ("The engine reports the
row…" → "`sdle.sh resume` reports the row…").

---

## Verification of the plan's own claims about M3

| Plan claim | Verified |
|---|---|
| F8 — `phase-execution.md` is not split | `git diff` is 2 added / 1 removed lines; `every_phase_has_execution_block` and `execution_block_numbers_are_the_greenfield_positions` both still pass |
| F1 — no authority in the new capability files | `test_n6_no_engine_owned_value_is_restated_in_a_new_prompt_file` passes for both files: no policy identifier, no discovery identifier, no progress fraction, no `Gate <n>`, no `Phase <n>`, no risk level, no PowerShell-only cmdlet |
| N28 / invariant 3 | `test_n28_invariant_3_holds_for_every_new_prompt_file` passes: no `speckit`, no `/speckit.` in either file, case-insensitive |
| D14 — one door | both capability files record findings only through `artifact review --actor-type agent --actor-name <agent>`; neither names a new command |
| A18 — no new writer yet | `scripts/sdle.py` is byte-for-byte its M2 state |

---

## Remaining

- **M4** — `cmd_resume` + the `resume` parser entry, the `gate_disposition`
  extraction out of `cmd_gate_show`, the SKILL.md prose fix, `/sdle-continue`
  and `/sdle-start`; append N9–N12b and N23 to `tests/test_units_capabilities.py`.
  Patch script `<scratchpad>/t10/m4.py` — its anchors were dry-run against
  disk in this context and all matched.
- **M5** — the four product agents, `product-agent-fence`, the three agent lint
  checks, X1's agents re-valuation, X2, X3, X4, X5, X7, N13–N19, N25.
  Scripts: `m5a_v2.py` (agents + X2), `m5a_x1_agents.py` (X1's second half),
  `m5b_fence.py`, `m5c_firetests.py`. **The single declared red window opens
  and closes inside M5**, before its checkpoint.
- **M6** — README, Reference Guide, CLAUDE.md, ADR-007 (`m6_docs.py` +
  `adr007.md`); the guardrail section of the test file; full suite, `lint-skill`,
  `validate.py`, the acceptance matrix, `T10-handoff-a01.md`, `progress.md` →
  `IMPLEMENTED`.

## Exact resume instruction for a fresh context

1. `git rev-parse HEAD` must be `875b361`; `git status --porcelain` must show
   the six modified / five untracked paths listed above.
2. `python scripts/sdle.py lint-skill` must report **39 checks, `failed: []`**.
3. `rtk proxy python -m pytest -q --collect-only tests/test_units_capabilities.py`
   must collect the M3 slice; the file must **not** yet mention `resume`.
4. `grep -n "def cmd_resume" scripts/sdle.py` must find **nothing** — that is
   what makes the next milestone M4.
5. Then run `<scratchpad>/t10/m4.py` after re-reading it against disk.

Do not run any other command while a full suite is in flight: two runs in this
context differed by 4× in wall clock purely from contention.
