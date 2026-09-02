# T09 Implementation Checkpoint — Attempt a01 / Checkpoint 04

**Phase:** T09
**Attempt:** 01
**Milestone:** M4 — inherited findings
**Written at:** while M4's full suite is in flight, before starting M5

## Objective currently being worked

M4 of `docs/transition/phases/T09-plan.md`: the three inherited findings T09
was named the owner of. Independently revertable, touching nothing M1–M3
touched.

* **D14 / T05 NB-4** — `read_repo_config` becomes fail-closed. Plan tests N26,
  X-table rows X8 and X9.
* **D15 / T05 NB-3** — a new `lint-skill` check binds the README's
  `REPO_CONFIG_DEFAULTS` literal to the engine's dict. X12.
* **D16 / T08 NB-3** — the README clause that stated a guarantee without its
  qualifier.

## Completed since previous checkpoint

1. **`scripts/sdle.py` — `read_repo_config` is fail-closed.** The
   `except …: return config` shape is gone. Presence and readability are now
   separate questions: an absent `config.json` still yields the documented
   defaults verbatim (so T09 stays a no-op for every repository that predates
   T05), while an unreadable, non-JSON or non-object document refuses
   `config_malformed` at exit 1.

   **Observable behaviour is unchanged**, and that is the point of the design
   rather than an assumption about it: `read_repo_config`'s only caller is
   `cmd_config_show`, which runs `repo_config_findings` first and already
   refuses on every condition the handler used to swallow. N26 asserts both
   halves — the caller-level reason and exit code are identical, and the
   reader called *directly*, past that predicate, now raises.

2. **`scripts/sdle.py` — new lint check
   `repo_config_defaults_match_documentation`.** Every fenced ```json block in
   `README.md` and `docs/SDLE-Reference-Guide.md` is parsed; any block that is
   an object carrying `configVersion` must equal `REPO_CONFIG_DEFAULTS`
   exactly. Keyed on the field rather than the block's position, so moving the
   section cannot silently disable the rule; an unparseable block is a failure
   rather than something to skip; and finding *no* block at all is also a
   failure, so the rule cannot pass vacuously. **`lint-skill` is now 33
   checks, `failed: []`** — the 32 observed at HEAD all still present and
   passing.

3. **`README.md` — D16.** The clause ending *"…so an inference can never be
   read as an observation"* is replaced by one that names what the engine
   actually checks (the label is present and is one of the closed three; an
   observation cites a path inside the repository; an inference names a basis
   none of which is unknown) and what it does not (whether the author applied
   the right label — still a claim by its author).

4. **Tests.** X8 in `test_units_baseline.py`, X9 (docstring) in
   `test_units_governance.py`, N26 appended to `test_units_repo_config.py`,
   and three firing tests for the new lint rule appended to
   `test_lint_skill.py`.

## The anti-contradiction clause, honoured exactly

X8 is `tests/test_units_baseline.py::test_n15_the_baseline_reader_never_swallows_and_defaults`,
which **asserted** that `read_repo_config` is fail-open:

```
assert swallowed, "read_repo_config was expected to be fail-open (T05 NB-4)"
```

The clause permits replacing the final block — `swallower`, `swallowed` and
that assertion — with the inverse, and nothing else. That is what was done: the
`read_baseline` half above it is untouched, and the replacement keeps a
non-vacuity guard (`assert handlers, …`) so a reader with no exception handler
at all could not satisfy the new assertion trivially. The docstring is rewritten
because it described the removed contrast; describing it as a contrast that no
longer exists would be a false statement in the test that pins the property.

TP-003 category for X8 and X9: **category 2** — the test asserts something the
phase deliberately changes.

## A closed set I chose not to grow

The first attempt extracted the refusal into a private `_config_malformed`
constructor. That failed
`test_units_repo_config.py::test_the_repository_configuration_members_have_a_closed_reference_set`,
which asserts by **exact equality** which functions may reach the repository
configuration boundary.

That was the test doing its job, and the right response was to change the code
rather than the assertion: the helper existed only to build one message, and
widening a containment proof to buy a message constructor is a bad trade. The
reader now decides the problem and raises once, inside itself, with no new
function. The closed set is **unchanged** — so unlike X15/X16/X17 this produced
no X row at all.

## Remaining

M5 only: the prompt layer (`SKILL.md`, `modules/gate-protocol.md`,
`.claude/commands/sdle-approve.md`), the documentation (`README.md`,
`docs/SDLE-Reference-Guide.md`), and tests N27–N31.
`docs/architecture/ADR-006-risk-adaptive-gate-policy.md` is already on disk and
has been checked to contain none of the 22 policy-identifier needles.

Drafts written and **not yet applied**:

```
scratchpad\t09_m5_docs.py    (SKILL.md, gate-protocol.md, sdle-approve.md,
                              README.md, SDLE-Reference-Guide.md)
scratchpad\t09_m5_block.py   (N27-N31, appended to tests/test_units_gate_policy.py;
                              needs `import subprocess` added to that file)
```

## Files changed so far

| Path | Change |
|---|---|
| `scripts/sdle.py` | M1 policy data, M2 requirement model, M3 enforcement, M4 fail-closed reader + lint check |
| `tests/test_units_gate_policy.py` | **new**, 1269 lines (M1+M2+M3) |
| `tests/test_units_governance.py` | X5, X2, X3, X4, X13, X14, X1, X16, X9 |
| `tests/test_units_baseline.py` | X6, X7, X8 |
| `tests/test_units_workitem_resolution.py` | X15 |
| `tests/test_units_artifact_review.py` | X17 |
| `tests/test_units_repo_config.py` | N26 block |
| `tests/test_lint_skill.py` | X12 block |
| `README.md` | D16 |
| `docs/architecture/ADR-006-...md` | **new** |

## Tests actually run this milestone

| Command | Result |
|---|---|
| `python scripts/sdle.py lint-skill` after the engine patch | **33 checks, `failed: []`**, exit 0; the new check reports `1 documented configuration block(s) equal REPO_CONFIG_DEFAULTS` |
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_repo_config.py tests/test_units_baseline.py …"` (first attempt) | **1 failed, 167 passed** — the closed-reference-set finding above |
| the same three files after the fix | **`168 passed in 166.68s`**, RAW_EXIT=0 |
| **Full suite** | **IN FLIGHT** at the time of writing — see the resume instruction |

## Current failures

None outstanding at the time of writing. The full-suite result is recorded in
checkpoint 05.

## Git status / diff summary

- HEAD `ad08d4b`; nothing committed this attempt.
- Modified: `scripts/sdle.py`, `README.md`, six test files.
  Untracked: `tests/test_units_gate_policy.py`,
  `docs/architecture/ADR-006-risk-adaptive-gate-policy.md`, the four
  checkpoints. `.claude/settings.local.json` was already modified at HEAD and
  is explicitly out of scope; it has not been touched.
- Rollback: `git checkout e1cf341 -- scripts/sdle.py README.md`.

## Unresolved decisions

None requiring a human. No `T09-blocker.md`.

## Exact resume instruction

1. `cd D:/Learning/AI/sdle-git-repo/sdle-latest`; confirm HEAD `ad08d4b`.
2. Read `scratchpad/t09_m4_full.txt`. If it has no `RAW_EXIT=` line or no
   `N passed` summary, **re-run the full suite** rather than assuming:
   `rtk proxy "python -m pytest -q -p no:cacheprovider --no-header" > <file> 2>&1`
   with `run_in_background: true`, then read `$?` with no pipe. Expected: the
   1379 collected after M3, plus M4's added tests.
3. Verify M4 is on disk: `python scripts/sdle.py lint-skill` must report **33**
   checks with `failed: []`, and `read_repo_config` must contain no `Return`
   inside any `ExceptHandler`.
4. Apply M5: `scratchpad/t09_m5_docs.py`, then add `import subprocess` to
   `tests/test_units_gate_policy.py` and append `scratchpad/t09_m5_block.py`.
   Re-read both against disk first; every anchor must still be unique.
5. Finish with the full suite, `lint-skill`, `python tools/transition/validate.py`,
   `docs/transition/phases/T09-handoff-a01.md`, and `progress.md` ->
   `IMPLEMENTED`.
6. Tooling traps: always `rtk proxy` for pytest, redirect, read `$?` with no
   pipe; the Bash tool caps a foreground command at 600s, so the ~23-minute
   suite needs `run_in_background` or an `until` loop; a plain `grep -rn` has
   produced a false negative, so reproduce negatives with a Python walk;
   `lint-skill` and `constants` nest their payload under `data`; the working
   tree is CRLF and `git show` is LF; a `PostToolUse` secrets tripwire fires on
   a substring inside the phrase naming this phase — false positive, no
   credential.
