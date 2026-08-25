# Resume here

Cold-start note for the next session. Authority order is unchanged: the repository, `transition.md`, `progress.md`, and the persisted phase artifacts. **This file is a convenience, not a source of truth** — if it disagrees with `progress.md` or the repo, they win.

Run `python tools/transition/validate.py` first. It should print `TRANSITION_VALID: complete=6/12 next=T06`, exit 0.

---

## The next action

**Implement T06** (`sdle-transition-implementer`) against `docs/transition/phases/T06-plan.md`, then verify it with a fresh verifier.

T05 is `COMPLETE`: independently verified `PASS`, artifact `docs/transition/phases/T05-verification-a01.md`. **The contract's stability gate is cleared** — §5's "do not skip directly to T07+ before T01-T05 are stable" is satisfied, and the structural half of the migration is finished.

T06 is the largest phase so far: eight milestones. **M3 is the declared safe resume boundary** — M1-M3 are additive and behaviour-neutral, M4 is where enforcement begins. A fresh agent resuming mid-phase should read the checkpoints and restart at a milestone boundary rather than mid-milestone.

**T06 enforces; it does not merely record.** §12's "Blocking findings stop progression" and TP-011's "MUST NOT allow a stale review to authorize downstream consumption" are unambiguous MUSTs. What T06 does *not* change is traversal: classification, risk level and the would-be gate set move nothing, and the eight gates stay unconditional. That narrower absence-of-change property is pinned by plan A17/A18.

## State

| | |
|---|---|
| Branch | `transition/workitem-v1` |
| Phases complete | T00-T05 (all independently verified PASS) |
| Rollback point for T06 | `475795a` (T05 implementation) |
| SDLE product baseline | `f8fdaa0` |
| Suite | **569 passed, raw exit 0** (569 collected; ~10-17 min, varies) |
| `lint-skill` | 22/22, **v1.15**, 19 phases / 8 gates / 15 migration rows |
| Python 3.11 / CI | `NOT_RUN` / `UNKNOWN` — never observed at any point |

## Three things a fresh context will otherwise get wrong

**1. The suite is green. Do not inherit the flake assumption.**
Every full run before commit `6e8af8c` was red with `PermissionError: WinError 5` from `os.replace` at `sdle.py:463`, and the early plans' F1 `ENVIRONMENT_FLAKE` procedure exists to absorb it. `6e8af8c` fixed it with a bounded retry. **The F1 path is void.** Any test failure is a presumed real regression — investigate it, do not pattern-match it to the old signature. T02 ran its entire phase without invoking F1 once.

**2. CI has never run. The branch is green on Python 3.14.6 / Windows only.**
CI pins 3.11 on `ubuntu-latest` and `windows-latest`. The branch is local-only, no 3.11 interpreter exists on this host, and no CI outcome has been observed. Treat "green on 3.11" as `UNKNOWN`, never as `OBSERVED`. If the branch has since been pushed, read the actual run rather than assuming.

**3. `T00-plan.md` contains a known-wrong figure.**
It says "21 top-level subcommands". The verified count is **65 `add_parser` registrations** (33 top-level + 32 nested, 49 invocable paths), before T01's `workitem` group and T02's additions. Plans are immutable once written, so the correction lives in `T00-handoff-a01.md` and `T00-verification-a01.md`. Treat that plan's other quantitative claims as unverified.

## Open findings carried forward, by owning phase

From the T02, T03 and T04 verification artifacts. **None is blocking.** T02's NB-1 and T04's N-1 are closed and no longer listed.

| ID | Owner | What |
|---|---|---|
| T04 N-2 | **T11 hardening** | Spec Kit discovery tier 2 (`<project-root>/specs/*`) is a repository-global staging area picked by **newest mtime**, so two WorkItems at Phase 4 concurrently can cross-adopt each other's feature directory. Not covered by any existing test. The same heuristic is the recovery path for a migrated workflow, so a repo with a stray root-level `specs/` could adopt the wrong one. |
| T04 N-7 | **any phase** | `cmd_security_review_evidence` got an exclude for the Spec Kit relocation; `cmd_manifest_build` did not, so the Gate 7 manifest now lists the WorkItem's Spec Kit artifacts as changed files. |
| T04 N-3 | any phase | The write-fence carve-out matches a **non-normalised** path, so `workitems/<id>/specs/../.sdle/state.json` escapes it. |
| T04 N-6 | **T11 documentation sweep** | The T02 `.workflow/` residual: stale runtime paths in `phase-execution.md` (39/169/173/178/192) and `gate-protocol.md` (66/86/104). T04 widened the gap at line 178. Also `docs/dry-runs/` carries ~17 further stale path lines, deliberately untouched. |
| T04 N-4 | any phase | `SKILL.md:358` became inaccurate through T04's own fence carve-out. |
| T03-1 | **T11 hardening** | Declared fail-open window in `branch_guard`, reproduced by the verifier: switching branch *between* the two steps of `skip`/`reset`/`restart`/`implement preflight` lets the action run with no `branch_mismatch` audited. Minimal fix is a dedicated `pending_branch_ack` key — needs a schema change, hence T11. |
| T03-4/5/6 | any phase | `ACTIVE_CONTEXT_SETTERS` is dead in production code (invariant 7 smell); `cmd_workitem_use` is not error-hardened like its siblings, so an `OSError` escapes as a traceback; and it reuses the reason string `workitem_required` for a `UsageError` (exit 2), colliding with the resolution refusal (exit 1). **Explicitly not adopted by T04** — not incidental to its edits. |
| T03-7/8 | any phase | Untested edge-case ordering change (`init` with both a corrupt index and legacy state reports `index_malformed`, not `legacy_workflow_present`); and on a mismatched branch the ledger records `branch_mismatch_accepted` even when the command then refuses for its own reason. |
| T03-10 | docs | `SKILL.md`'s branch-mismatch paragraph says "re-run the same command — which proceeds"; exact for the five single-step critical commands, but `skip`/`reset`/`restart`/`implement preflight` yield their own confirmation step first. |
| T02 NB-2/4/5 | T11 | The `legacy_workflow_present` message never names archiving `.workflow/`; the post-commit `workitem.json` write sits outside the commit window; the migration crash test never exercises the manifest/completion copies. |
| — | unassigned | `design/`, `reviews/`, `clarifications/` stay repository-level (T04's explicit decision, recorded as a residual). `design/app/app-design.md` remains shared across WorkItems. |

### Process lessons, not code findings

- **T03-2/T03-3 — handoff evidence must be re-derived, not asserted.** T03's handoff over-cited the plan (claiming D5 "considered and rejected" sticky acknowledgement, which D5 never mentions) and claimed an empty skip/xfail grep that in fact matches a pre-existing `@pytest.mark.skipif` in `test_units_infra.py`. Both *conclusions* were right; the *evidence* was not. Check what a grep actually matches before quoting it.
- **Checkpoints can be accurate about the engine and wrong about tests.** T03's checkpoints 01–04 implied test files existed that did not. A resuming agent must verify claimed state against disk — `--collect-only` is the cheap check.
- **The `rtk` shell proxy will hand you a false green.** Plain `python -m pytest` prints `Pytest: No tests collected` and exits 0. Use `rtk proxy python -m pytest`, redirect to a file, and read `$?` with no pipe between. It also truncates `git diff` and `grep`; `rtk proxy "<command>"` returns full output and changes nothing about what executes.
- **The full suite takes ~8 minutes.** Give it a 600000 ms timeout; the default 2 min kills it mid-run.

## Control plane

`tools/transition/agent_guard.py` was repaired three times during T00–T01 and re-signed each time — see `T00-blocker.md` §9, §10, §11. It refused **nothing** during T02 verification. The user granted **standing approval for guard false-positive fixes only**: changes that stop it blocking provably read-only or sanctioned operations. Anything that would let it permit a **new mutation** still needs explicit approval. Every fix keeps the full procedure: patch, re-sign only the `agent_guard.py` line via `validate.py::sha256`, re-run all three matrices, record in the blocker.

`docs/transition/control-plane.sha256` is the integrity manifest; `validate.py` exits 3 on any mismatch.

**Environment note:** a token-optimising shell proxy (`rtk`) intercepts shell commands in this environment and truncates `git diff` / `grep` output. Its documented passthrough `rtk proxy "<command>"` returns full output and changes nothing about what executes, leaving the transition guard fully in force. Verifiers comparing diff output should be aware of the truncation.
