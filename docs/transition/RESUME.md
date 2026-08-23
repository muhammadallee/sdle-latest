# Resume here

Cold-start note for the next session. Authority order is unchanged: the repository, `transition.md`, `progress.md`, and the persisted phase artifacts. **This file is a convenience, not a source of truth** — if it disagrees with `progress.md` or the repo, they win.

Run `python tools/transition/validate.py` first. It should print `TRANSITION_VALID: complete=3/12 next=T03`, exit 0.

---

## The next action

**Run a fresh T03 planner** (`sdle-transition-planner`) against `transition.md` §9 — *WorkItem Resolution and Parallel Developer Isolation*.

T02 is `COMPLETE`: independently verified `PASS` in a fresh context, artifact `docs/transition/phases/T02-verification-a01.md`. Nothing about T02 is outstanding.

T03 is where the resolution ladder grows the rungs T02 deliberately withheld. T02 shipped only the subset — explicit `--workitem` → sole registered WorkItem → legacy dual-read → refuse `workitem_required` → refuse `workitem_ambiguous`. T03 owns **CWD-based resolution, persisted active context, branch/WorkItem metadata, AI-assisted inference, and asking the user**, plus branch/worktree rules and the new `sdle validate` checks. Contract §9's mandatory ambiguity behaviour is absolute: `>1 plausible -> ASK`. Never silently pick.

## State

| | |
|---|---|
| Branch | `transition/workitem-v1` |
| Phases complete | T00, T01, T02 (all independently verified PASS) |
| Rollback point for T03 | `ab889a1` (T02) |
| SDLE product baseline | `f8fdaa0` |
| Suite | 341 passed, raw exit 0 (verified twice, 341 collected, zero skips/xfails/errors) |
| `lint-skill` | 22/22, v1.14, 19 phases / 8 gates / 14 migration rows |
| Python 3.11 / CI | `NOT_RUN` / `UNKNOWN` — never observed at any point |

## Three things a fresh context will otherwise get wrong

**1. The suite is green. Do not inherit the flake assumption.**
Every full run before commit `6e8af8c` was red with `PermissionError: WinError 5` from `os.replace` at `sdle.py:463`, and the early plans' F1 `ENVIRONMENT_FLAKE` procedure exists to absorb it. `6e8af8c` fixed it with a bounded retry. **The F1 path is void.** Any test failure is a presumed real regression — investigate it, do not pattern-match it to the old signature. T02 ran its entire phase without invoking F1 once.

**2. CI has never run. The branch is green on Python 3.14.6 / Windows only.**
CI pins 3.11 on `ubuntu-latest` and `windows-latest`. The branch is local-only, no 3.11 interpreter exists on this host, and no CI outcome has been observed. Treat "green on 3.11" as `UNKNOWN`, never as `OBSERVED`. If the branch has since been pushed, read the actual run rather than assuming.

**3. `T00-plan.md` contains a known-wrong figure.**
It says "21 top-level subcommands". The verified count is **65 `add_parser` registrations** (33 top-level + 32 nested, 49 invocable paths), before T01's `workitem` group and T02's additions. Plans are immutable once written, so the correction lives in `T00-handoff-a01.md` and `T00-verification-a01.md`. Treat that plan's other quantitative claims as unverified.

## Open findings carried forward, by owning phase

From `T02-verification-a01.md` §Findings. **None is blocking**; all seven are documentation gaps, coverage gaps or stale figures, and none changes shipped engine behaviour.

| ID | Owner | What |
|---|---|---|
| NB-3 | **T03 — input** | The dirty-tree tripwire cannot fire in a multi-WorkItem repository, because the hook correctly refuses to guess. A real coverage reduction that only T03's resolution can restore. Feed this into T03 planning. |
| NB-1 | T04 | `.workflow/` is now a magic prefix inside `resolve_artifact_path`. T04 must **delete** the transitional bridge when it moves `ARTIFACT_OWNERSHIP`, not inherit it. |
| NB-2 | T11 | The `legacy_workflow_present` refusal names only `migrate-workflow`. Post-migration, following it for a second WorkItem *clones* the migrated legacy workflow; archiving `.workflow/` by hand is the real remedy and is never named. |
| NB-4 | T11 / hardening | The post-commit `workitem.json` write sits outside the commit window; a crash there leaves a resolvable target with no `migration` object and `target_exists` blocking re-run. |
| NB-5 | T11 | The migration crash test injects at writes #2–#5 only; the optional manifest and completion-summary copies are never exercised. |
| NB-6 | process | Two T02 handoff figures are wrong: `tests/test_units_workitem.py` is 46/29, not 34/22 (stale evidence — every hunk is still declared, so no undeclared scope); and the A15 grep is not empty, it returns `--skip-tests`, an SDLE CLI flag rather than a pytest marker. Handoff figures need re-deriving, not copying. |
| NB-7 | none | `6e8af8c`'s `write_atomic` comment contains a stray word ("ponytail:"). Cosmetic, out of transition scope. |

## Control plane

`tools/transition/agent_guard.py` was repaired three times during T00–T01 and re-signed each time — see `T00-blocker.md` §9, §10, §11. It refused **nothing** during T02 verification. The user granted **standing approval for guard false-positive fixes only**: changes that stop it blocking provably read-only or sanctioned operations. Anything that would let it permit a **new mutation** still needs explicit approval. Every fix keeps the full procedure: patch, re-sign only the `agent_guard.py` line via `validate.py::sha256`, re-run all three matrices, record in the blocker.

`docs/transition/control-plane.sha256` is the integrity manifest; `validate.py` exits 3 on any mismatch.

**Environment note:** a token-optimising shell proxy (`rtk`) intercepts shell commands in this environment and truncates `git diff` / `grep` output. Its documented passthrough `rtk proxy "<command>"` returns full output and changes nothing about what executes, leaving the transition guard fully in force. Verifiers comparing diff output should be aware of the truncation.
