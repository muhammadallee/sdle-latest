# T10 checkpoint — attempt 01, milestone M1

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M1 — `_skill_files` becomes derived
**Started at HEAD:** `875b361009e2c16d66c2a99ebda0d734a45915db` (OBSERVED, `git rev-parse HEAD`)
**Rollback:** `git checkout -- scripts/sdle.py` restores the pre-M1 tree; whole-phase rollback is `git reset --hard 875b361`.
**Milestone status:** COMPLETE

---

## Baseline established in this context, before any edit

The planner recorded the full-suite result `UNKNOWN` and did not run it. This
implementer ran it first, at `875b361`, with nothing else in flight.

| Measurement | Result | How |
|---|---|---|
| Full suite at `875b361` | **1402 tests, 0 failures, 0 errors, 0 skipped, `RAW_EXIT=0`, 1420.89 s** | `rtk proxy python -m pytest -q -p no:cacheprovider --junitxml=…` redirected to a file, `$?` read with no pipe |
| JUnit root attributes | `tests=1402 failures=0 errors=0 skipped=0` | `xml.etree` over the emitted `baseline.xml` |
| `short test summary` sections in the capture | `0` | `grep -c` |
| `lint-skill` at `875b361` | **33 checks, `failed: []`, exit 0** | `python scripts/sdle.py lint-skill`; payload nested under `data` |
| `tables_wellformed` message | `Parsed 21 phases, 8 gates, 16 migration rows.` | same run |
| Python | **3.13.0** (`python -V`). Python 3.11: `NOT_RUN` | |
| CI | `NOT_RUN` | never observed at any point in this migration |

T09's 1402/1402 is cited nowhere as evidence here. The figure above is this
context's own observation and happens to agree with it.

---

## What M1 changed

One file, `scripts/sdle.py`. Two edits, both structural, neither behavioural.

1. **`Paths` gains `modules_dir` and `agents_dir`.** `gate_protocol_md`,
   `phase_execution_md` and `security_review_md` now derive from `modules_dir`
   instead of each restating `"modules"`. `agents_dir` is
   `skill_root.parent.parent / "agents"` — `.claude/agents/`, the sibling of
   `.claude/skills/`.
2. **`_skill_files` becomes derived** (plan D6). It was a fixed list of four
   property names; it is now

   ```
   SKILL.md  +  sorted(modules/*.md)  +  product_agent_files(paths)
   ```

   with a new module-level helper `product_agent_files(paths)` returning the
   sorted `agents_dir/sdle-*.md` minus the `sdle-transition-` prefix, and the
   empty list — never an error — when there is no `.claude/agents/`.

New constants: `PRODUCT_AGENT_GLOB`, `CONTROL_PLANE_AGENT_PREFIX`.

**Why this had to be first.** `_skill_files` feeds three checks:
`discovery_vocabulary_is_not_restated_in_prompt_files`, `_check_no_powershell`
and `_check_no_hardcoded_progress`. Any capability file M3 adds, and any agent
prompt M5 adds, would have been invisible to all three until somebody
remembered to edit that function. Deriving it first makes the prompt-layer
split *widen* those checks instead of quietly diluting them.

## Proof that it changed nothing

`_skill_files` previously returned exactly `[SKILL.md, phase-execution.md,
gate-protocol.md, security-review.md]`. `modules/` holds exactly those three
files and `.claude/agents/` held only `sdle-transition-*`, so the derived
result is the same set. The order changed (now name-sorted); every consumer
accumulates offenders and reports them sorted or whole, and all three were
empty regardless.

| Evidence | Result |
|---|---|
| `lint-skill` check-name set, before vs after | **identical** (33 names) |
| `lint-skill` check *message* strings, before vs after | **identical — zero diffs**, compared programmatically against the captured baseline capture |
| `failed` / exit | `[]` / 0 |
| Targeted: `test_lint_skill.py test_units_discovery.py test_units_flow_model.py test_units_infra.py` | **226 passed**, `RAW_EXIT=0`, 252.27 s |
| Full suite after M1, first pass | **1401 passed / 1 failed**, `RAW_EXIT=1`, 1441.91 s. Collected 1402 — unchanged. The single failure is recorded below. |
| Full suite after the M1 fix | targeted re-run only; see below |
| `git diff --numstat` | `75 11 scripts/sdle.py` only. `.claude/settings.local.json` is modified in the working tree, was modified before this phase began, and is explicitly out of scope — untouched here. |

## One failure, found and fixed inside M1

`tests/test_units_artifact_review.py::test_t06_creates_no_subagent` failed:
it bans the literal string `subagent` anywhere in `scripts/sdle.py`, and M1's
first pass used the word three times in comments and a docstring describing
`.claude/agents/*.md`.

**This is not the plan's declared red window and must not be confused with
it.** X2 does retire that literal ban — but not until M5, and the plan confines
T10's single red window to M5. M1 had opened an undeclared second one.

Fix: M1 now says **"product agent prompts"** for the files it enumerates, which
is the accurate noun for a file anyway. The word `subagent` enters `sdle.py`
for the first time at M5, in the same working step that applies X2 and retires
the ban — which is where the plan puts it.

This is sequencing, not the wording discipline D11 rejected. D11's objection is
to keeping the ban and dodging it forever; here the ban is genuinely retired at
M5 and the engine says "subagent" from M5 onward.

| Post-fix evidence | Result |
|---|---|
| `grep -c subagent scripts/sdle.py` | **0** (asserted by the fix script itself) |
| `pytest tests/test_units_artifact_review.py tests/test_lint_skill.py` | **79 passed**, 59.99 s |
| `lint-skill` | 33 checks, `failed: []`, exit 0 |

The full suite is re-run in full at M4 and again at M6; the M1 failure was a
single named test with a single named cause, re-run green.

## A planner unknown resolved against the real tree (U5)

`_searchable_files()` (X3) **cannot** simply gain `.claude/agents/`.
`sdle-transition-planner.md` contains `OBSERVED`, `INFERRED` and `UNKNOWN` —
the *transition contract's* evidence vocabulary, spelled identically to §14's
`DISCOVERY_CLASSIFICATIONS`. Verified by a programmatic needle scan over all
four control-plane agent files: policy needles none in any file; discovery
needles `['INFERRED', 'OBSERVED', 'UNKNOWN']` in `sdle-transition-planner.md`
only.

X3's stated response applies: **do not narrow the root; restrict to product
agents and record the reason.** M5 does exactly that, in both copies of the
helper (X3 and X4). The `sdle-transition-` prefix exclusion inside
`_skill_files` is the same decision at the engine level, and is why M1 is a
no-op.

## Resume instructions for a fresh context

- Next milestone is **M2** (`CAPABILITY_MAP`). Its patch script is
  `<scratchpad>/t10/m2.py`. Every patch script round-trips line endings
  through `<scratchpad>/t10/patchlib.py`, because the tree is mixed: `sdle.py`,
  `SKILL.md`, `README.md`, the Reference Guide and the test files are CRLF;
  `hooks.py`, `CLAUDE.md`, the modules, the commands and the agent files are LF.
- Verify claimed state against disk before trusting this file:
  `grep -n "def _skill_files" -A 25 scripts/sdle.py` should show the derived
  version, and `python scripts/sdle.py lint-skill` should report 33 checks.
- Nothing under `tests/` has been touched yet. `docs/transition/` is the only
  other tree written.
