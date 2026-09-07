# T11 checkpoint a01-08 — the blocker is cleared; the phase is complete

**Phase:** T11 · **Attempt:** 01 · **Checkpoint:** 08 (final)
**Milestone:** M7 remainder — the one item `T11-checkpoint-a01-07.md` left open
**Status at this boundary:** **ALL EIGHT MILESTONES COMPLETE AND GREEN.**
`T11-blocker.md` is resolved, not deleted. The phase is `IMPLEMENTED`.

---

## 1. Objective currently being worked

Close out T11: clear the M7 blocker, finish TR26, re-derive every figure in a
fresh context, and persist `T11-handoff-a01.md`.

This checkpoint is written **after** the last implementation work rather than
before a next milestone, because there is no next milestone and there is no
T12. It exists so that a fresh context resuming after this point — most likely
the verifier — knows exactly which claims were observed here and which were
inherited.

---

## 2. Completed since checkpoint 07

### 2.1 The blocker was resolved by a user decision, and is retained as history

`T11-blocker.md` recorded two walls: the shipped write fence denied
`docs/workitems/README.md` (W1), and the auto-mode permission classifier denied
the minimal correction to `.claude/hooks/hooks.py` (W2). It offered four options
and recommended **Option A**.

**The user took Option A.** The fence correction was applied, the regression
tests were added, `docs/workitems/README.md` was created, and TR26 was finished.

`T11-blocker.md` is **kept on disk unmodified**. A blocker that was raised and
then answered is part of the phase's evidence — deleting it would erase the
record that a guardrail defect was found, escalated rather than routed around,
and decided by the person entitled to decide it. `progress.md` records the
resolution in the T11 row rather than dropping the history of the block.

### 2.2 The write fence is now anchored (out-of-plan, user-approved)

This is **not** a D-item. It is a product change made outside the plan, approved
by the user, and it is recorded as exactly that rather than forced into an X row
that does not fit it.

**The defect.** `hooks.py::in_dir(path, name)` matched `/{name}/` **anywhere**
in a path. `SDLE_OWNED_PREFIXES` — the ownership the fence exists to protect —
is entirely repository-root-relative. The hook was therefore strictly broader
than the engine: it denied `docs/workitems/`, a documentation path SDLE does not
own, never writes, and has **no choke-point refusal for**.

That asymmetry is the one failure mode a tripwire must not have. Everywhere else
in this system a hook denial is the cheap early echo of a refusal the engine
would make anyway. Here the hook refused where the engine had nothing to say —
and CLAUDE.md's own position is that the script's refusal at the choke point
*is* the guarantee, the hook merely a tripwire. A fence that fires on paths it
does not own teaches the reader that the fence is noise.

**The fix.** A new `fenced_target(path, name)`; `write_fence` calls it instead
of `in_dir`. It anchors the match at the start of the repository-relative path,
mirroring `SDLE_OWNED_PREFIXES`. Two shapes count as repository-relative and
both anchor: a path under `PROJECT_DIR` (which `relative` strips) and a path
that is not absolute at all (which is relative to the project directory by
definition, and is how the fence has always read `.workflow/state.json`). Only
an **absolute path outside the repository** falls through to `in_dir`'s loose
match, as defence in depth. Absoluteness is tested after backslash
normalisation, so `C:/other/tree/...` counts as absolute; `posixpath.isabs`
would call it relative and wrongly anchor another tree's path against this root.

**What did not change.** `in_dir` keeps its loose form character for character
— it is the fallback, and the `SCANNED` / `untrusted_read` call site still uses
it unchanged, where a deliberately broad warn-and-acknowledge scan is the
intent rather than an ownership claim. `FENCED` is unchanged
(`.workflow`, `workitems`, `requirements`, `guidance`), so P6 holds and
`.workflow/` is still fenced.

**Relationship to T10 NB-6 (TR6): it does not supersede it.** NB-6 is about the
prompt layer stating the fence's *effect* without ADR-007 §3's caveat that a
registered hook firing at all is Claude Code's guarantee, not SDLE's. That was
fixed separately in M7. NB-6 concerns **whether** the fence runs; this concerns
**which paths it denies when it does**. ADR-008 §5.3 states this explicitly so a
later reader does not collapse the two. `SKILL.md`'s write-fence sentence was
re-checked against the corrected behaviour and needed no edit — it names the
four fenced roots and the carve-out and never claimed a segment-anywhere match.

**Evidence — 21 new test cases in `tests/test_hooks.py`**, all driving the
registered command as a subprocess like every other test in that file:

| Pin | Cases |
|---|---|
| `test_the_fence_denies_owned_paths_in_both_forms` | 6 owned paths × repo-relative **and** absolute. The first cut of the fix anchored only the absolute form and left the repo-relative form of `docs/workitems/README.md` still denied; this is the pin for that |
| `test_the_fence_permits_paths_the_engine_does_not_own` | 9 paths — the §17 documentation targets, fenced names one directory down, and names that merely *begin* with a fenced name (`workitems-archive/`) |
| `test_the_fence_stays_loose_outside_the_repository` | 4 foreign absolute paths, POSIX and Windows drive-letter |
| `test_every_fenced_name_is_anchored_at_the_repository_root` | Over the whole `FENCED` tuple, read out of the source by AST rather than hand-copied, so a name added later inherits both halves |
| `test_the_fence_is_a_subset_of_what_the_engine_owns` | `FENCED ⊆ SDLE_OWNED_PREFIXES`, asserted against the engine constant, and asserted to be a **strict** subset with the reason recorded |

6 + 9 + 4 + 1 + 1 = **21**, which is exactly the collection delta
(1710 → 1731) between the blocked state and now.

### 2.3 `docs/workitems/README.md` — the ninth documentation target

239 lines. Covers what a WorkItem is, the on-disk layout, isolation and
versioning, the strict `index.md` columns and why `index_malformed` is never
auto-repaired, resolution with rung 6 gone, which commands are runtime-free,
`.workflow/`'s two surviving roles, the active context, the write fence, and
recovery. It opens by naming `scripts/sdle.py` as the authority and itself as a
derived view, like its five siblings.

All nine `DOCUMENTATION_TARGETS` now exist and are non-empty, so
`documentation_set_is_present` passes and `lint-skill` is `failed: []`.

### 2.4 TR26 — `docs/transition/RESUME.md`

Now describes the completed state. It was deliberately left until last because
it should describe a finished phase, and until this checkpoint the phase was not
finished.

**An inconsistency was caught and repaired here, and it is worth naming.** An
earlier context wrote ADR-008's TR26 row as **FIXED** while `RESUME.md` still
said `complete=6/12 next=T06`. That is a record written ahead of the fact —
precisely the failure mode this phase exists to eliminate. It has been checked
against disk in this context: `RESUME.md` now carries `complete=11/12 next=T11`,
names T11 as `IMPLEMENTED, NOT YET VERIFIED`, and points the verifier at
ADR-008. TR26 is now genuinely FIXED, and `RESUME.md` itself records the lesson.

---

## 3. Remaining

**Nothing implementable.** The remaining work is not implementation:

1. `T11-handoff-a01.md` — written immediately after this checkpoint.
2. `progress.md` T11 → `IMPLEMENTED`, clearing `BLOCKED`.
3. Independent verification by a fresh `sdle-transition-verifier`.
4. After a PASS: the post-transition control-plane cleanup that contract §1.4
   permits — **a separate change**, never part of this phase.

---

## 4. Files changed since checkpoint 07

| Path | Nature |
|---|---|
| `.claude/hooks/hooks.py` | `fenced_target` added; `write_fence` calls it; `in_dir` gains a docstring and keeps its behaviour |
| `tests/test_hooks.py` | +21 cases, +154 lines. No existing assertion changed |
| `docs/workitems/README.md` | **NEW** (239 lines) |
| `docs/architecture/ADR-008-…md` | §5.3 added; the §5 change table grew to three rows; TR26's row made true |
| `docs/transition/RESUME.md` | TR26 |

---

## 5. Tests actually run in this context — every figure re-derived here

The Bash tool caps a foreground command at 600 s and this suite takes ~26 min,
so a single foreground full-suite run is **impossible in this environment**.
Backgrounded runs have truncated repeatedly. The suite was therefore run in
**six foreground segments**, and the segments were then *proved exhaustive*
against the collection rather than assumed to be.

| # | Files | Result |
|---|---|---|
| 1 | 3 integration files | **88 passed in 208.50s** |
| 2 | workitem, workitem_resolution, workitem_runtime, state, transitions, cli, infra | **320 passed in 350.43s** |
| 3 | speckit_binding, repo_config, discovery, baseline, lint_skill | **304 passed in 286.75s** |
| 4 | governance, artifact_review | **235 passed in 173.35s** |
| 5 | gate_policy, flow_model | **470 passed in 285.46s** |
| 6 | hooks, capabilities, hardening | **314 passed in 283.77s** |
| | **Total** | **1731 passed, 0 failed, 0 errors, 0 skipped** |

**Exhaustiveness, proven not asserted.** Each segment wrote its own
`--junitxml`. Parsed independently: `tests=1731 failures=0 errors=0 skipped=0`,
and the union of `testcase` ids across the six files has **1731 unique
members**. `python -m pytest --collect-only -q` reports **1731 collected**. The
two id sets were compared element-wise and are identical (six entries differ
only in pytest's `::` versus `.` class separator in the junit `classname`
attribute — the same six tests, `test_units_infra.py::TestLauncherResolution`).

**Limitation, stated plainly:** six segments are not identical to one process.
Cross-file ordering effects that only a single process would surface are not
covered by this evidence. The partial mitigation is an **inherited, not
re-observed** figure: a single full-process run was recorded at the blocked
state in `T11-blocker.md` §5 — `tests=1710 failures=2 errors=10` from that run's
junit XML, with all twelve non-passing outcomes traced to the one missing
directory — and 1710 + 21 new fence cases = 1731, which is the number observed
here. The arithmetic corroborates; it does not substitute. **The verifier
should attempt a single full-process run and treat that as the outstanding
evidence gap.**

| Other check | Command | Result |
|---|---|---|
| `lint-skill` | `python scripts/sdle.py lint-skill` (stdout to a file; raw `$?`, no pipe) | **exit 0**, **43 checks**, `failed: []` |
| `validate.py` | `python tools/transition/validate.py` | **exit 0**, `TRANSITION_VALID: complete=11/12 next=T11` |
| A1 | `git diff --stat 4b1aa71 -- <3 integration files> .claude/settings.json .gitignore` | **empty** |
| A7 | `PROJECT_ROOT_MARKERS`, `FENCED`, `.gitignore` | `(".workflow", "state.json")` present; `.workflow` still fenced; `.workflow/` still ignored |
| A2 | `grep '"legacy"' scripts/sdle.py` | no match (exit 1) |
| A11 | `sdle.py constants` | `version_chain` = **17**; `CURRENT_VERSION = "1.17"` |
| A15 | `sdle.py constants` | `phase_sequence` **21**, `flows` **5**, `gate_phases` **8** |
| A20 | mutation probe, below | **both pins failed, then restored byte-identical** |
| Python 3.11 | no 3.11 interpreter on this host | **NOT_RUN** |
| CI | never executed at any point in this migration | **UNKNOWN** |

### 5.1 A20 proven by mutation, not by argument

`docs/dry-runs/01-happy-path.md` was appended with a line that is **not** in
`DRY_RUN_SUBSTITUTIONS`, the two pins were run, and both **failed**. The file
was then restored from a byte-for-byte copy and the SHA-256 verified equal to
the original (`e7a918caa67ba3755ccefbe587c96da3312c7fe63bbe758251732c2947fb474c`
before and after; the mutated file hashed
`69d2d2f4437b45f44e30b793cfcdc8ad827365b44df9e6063d82d2b2932ea71b`).

---

## 6. Current failures

**None.**

`ENVIRONMENT_FLAKE` is VOID for this phase and was not invoked at any point. No
test was re-run in the hope of a different answer.

---

## 7. Git status / diff summary

- HEAD: **`42c7d5b`** — "T11 M4: governance downgrade evidence (D11, D12, N12)"
- M1–M4 are committed (`a25c930`, `17f7ea2`, `90e52d0`, `42c7d5b`).
  **M5–M8 are uncommitted, live in the working tree.**
- Whole phase, `97100e2` → working tree: **46 tracked files changed,
  3662 insertions, 454 deletions**, plus 12 untracked paths
  (`tests/test_units_hardening.py`, ADR-008, six documentation directories, and
  four `T11-*` transition artifacts).
- `.claude/settings.local.json` is dirty and **out of scope — untouched**.
- A21: under `docs/transition/`, `tools/transition/` and
  `.claude/agents/sdle-transition-*`, the only changes are `RESUME.md`,
  `progress.md` and **new** `T11-*` files. No prior phase artifact was modified
  or deleted. The four modified `.claude/agents/sdle-*-review|discovery.md` are
  **product** agents (TR4), which plan §6.1 authorises.

---

## 8. Unresolved decisions

**None.** The one material decision this phase raised — narrowing a shipped
guardrail at the final milestone — was escalated in `T11-blocker.md` and
decided by the user. Everything else was resolved inside the contract and is
recorded in ADR-008.

Four findings remain **DEFERRED beyond V1**, each with a reason and, for three
of them, a pinning test: **TR8** (the single named V1 gap), **TR20**, **TR23**,
**TR25**.

---

## 9. Exact resume instruction

A fresh context resuming here should **not** implement anything. It should:

```
python tools/transition/validate.py          # expect complete=11/12 next=T11, exit 0
python scripts/sdle.py lint-skill            # expect 43 checks, failed: [], exit 0
python -m pytest --collect-only -q           # expect 1731 collected
```

Then read, in order: `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`
(the findings ledger is the phase's whole point), `T11-handoff-a01.md`, and
this checkpoint. `T11-blocker.md` describes a **resolved** condition and must
not be read as current state.

**Do not re-implement any milestone.** Everything is on disk and green.
