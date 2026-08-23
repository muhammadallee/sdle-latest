# Resume here

Cold-start note for the next session. Authority order is unchanged: the repository, `transition.md`, `progress.md`, and the persisted phase artifacts. **This file is a convenience, not a source of truth** — if it disagrees with `progress.md` or the repo, they win.

Run `python tools/transition/validate.py` first. It should print `TRANSITION_VALID: complete=2/12 next=T02`, exit 0.

---

## The next action

**Run a fresh T02 verifier** (`sdle-transition-verifier`) against `docs/transition/phases/T02-plan.md` and `T02-handoff-a01.md`.

Nothing else should happen first. T02 is `IMPLEMENTED`, not `COMPLETE`, and contract §24.4 requires verification in a fresh isolated context that assumes the implementation may be wrong. The session boundary is aligned with that requirement, not a workaround for it.

## State

| | |
|---|---|
| Branch | `transition/workitem-v1` |
| Phases complete | T00, T01 (independently verified PASS) |
| T02 | `IMPLEMENTED` attempt 1 at `ab889a1` — **not verified** |
| Rollback point for T02 | `7b9374b` (T01) |
| SDLE product baseline | `f8fdaa0` |
| Suite at this commit | 341 passed, raw exit 0 |
| `lint-skill` | 22/22, v1.14, 19 phases / 8 gates / 14 migration rows |

## Three things a fresh context will otherwise get wrong

**1. The suite is green now. Do not inherit the flake assumption.**
Every full run before commit `6e8af8c` was red with `PermissionError: WinError 5` from `os.replace` at `sdle.py:463`, and the earlier plans' F1 `ENVIRONMENT_FLAKE` procedure exists to absorb it. `6e8af8c` fixed it with a bounded retry. **The F1 path is now void.** Any test failure is a presumed real regression — investigate it, do not pattern-match it to the old signature. `T02-plan.md` §13 was written before the fix and still assumes a red suite; read it with that correction in mind.

**2. CI has never run. `f8fdaa0` is green on Python 3.14.6/Windows only.**
CI pins 3.11 on `ubuntu-latest` and `windows-latest`. The branch is local-only, no 3.11 interpreter exists on this host, and no CI outcome has been observed at any point. Treat "green on 3.11" as `UNKNOWN`, never as `OBSERVED`. If the branch has since been pushed, read the actual run rather than assuming.

**3. `T00-plan.md` contains a known-wrong figure.**
It says "21 top-level subcommands". The verified count is **65 `add_parser` registrations** (33 top-level + 32 nested, 49 invocable paths), before T01's `workitem` group and T02's additions. Plans are immutable once written, so the correction lives in `T00-handoff-a01.md` and `T00-verification-a01.md`. Treat that plan's other quantitative claims as unverified.

## What the T02 verifier must scrutinise

Four divergences the implementer declared rather than absorbed — each needs an independent judgement, not acceptance:

1. **Gate 7 `ARTIFACT_OWNERSHIP`** is re-pointed inside `resolve_artifact_path` rather than by editing the SKILL.md table, which the plan forbids. Without it every Gate 7 approval refused `artifact_missing`. Is redirecting at the resolver a legitimate reading of the constraint, or a way around it?
2. **The `workflow_migrated` audit entry lands before the commit write**, merging D8 step 11 into step 8, because a literal reading would commit a stale `audit_sha`. Target `state.json` is still written last as the sole commit marker.
3. **Plan §6 contradicts §7.1** on the shared fixture. Reconciled by overriding `project` back to `bare_project` in `test_units_workitem.py`; all 57 T01 assertions should be byte-identical — verify that.
4. **A migrated repo keeps refusing `init` for additional WorkItems** until the legacy `.workflow/` is archived by hand, because migration never deletes it. Claimed as the plan's deliberate fail-safe direction and on T11's removal list. Confirm it is deliberate and recorded, not an accident.

Also verify the standing items: no T03+ leakage, the resolution ladder never *guesses* a WorkItem (rung 5 refuses), the legacy dual-read rung still exists (it is what stops an existing repo being bricked, and is load-bearing until T11), `migrate-workflow` never mutates `.workflow/`, and no test was weakened rather than rebound.

## Control plane

`tools/transition/agent_guard.py` has been repaired three times this session and re-signed each time — see `T00-blocker.md` §9, §10, §11. The user granted **standing approval for guard false-positive fixes only**: changes that stop it blocking provably read-only or sanctioned operations. Anything that would let it permit a **new mutation** still needs explicit approval. Every fix keeps the full procedure: patch, re-sign only the `agent_guard.py` line via `validate.py::sha256`, re-run all three matrices, record in the blocker.

`docs/transition/control-plane.sha256` is the integrity manifest; `validate.py` exits 3 on any mismatch.
