# Resume here

Cold-start note for the next session. Authority order is unchanged: the repository, `transition.md`, `progress.md`, and the persisted phase artifacts. **This file is a convenience, not a source of truth** — if it disagrees with `progress.md` or the repo, they win.

Run `python tools/transition/validate.py` first. It should print `TRANSITION_VALID: complete=4/12 next=T04`, exit 0.

---

## The next action

**Run a fresh T04 planner** (`sdle-transition-planner`) against `transition.md` §10 — *Spec Kit WorkItem Context*.

T03 is `COMPLETE`: independently verified `PASS`, artifact `docs/transition/phases/T03-verification-a01.md`. Nothing about T03 is outstanding.

**T04 carries a specific inherited debt.** Finding NB-1 from T02: `resolve_artifact_path` contains a transitional `.workflow/` prefix bridge (`legacy_prefix = ".workflow/"`) that re-points the Gate 7 `ARTIFACT_OWNERSHIP` template at the WorkItem runtime without editing the SKILL.md table. T02 was allowed to add it; **T04 must delete it** when it moves `ARTIFACT_OWNERSHIP`, not inherit it. Verified present and unchanged at `8c4425b`.

## State

| | |
|---|---|
| Branch | `transition/workitem-v1` |
| Phases complete | T00, T01, T02, T03 (all independently verified PASS) |
| Rollback point for T04 | `beb28f2` (T03 implementation) |
| SDLE product baseline | `f8fdaa0` |
| Suite | **438 passed, raw exit 0** (438 collected, zero skips/xfails/errors; ~8 min) |
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

From `T02-verification-a01.md` and `T03-verification-a01.md`. **None is blocking.**

| ID | Owner | What |
|---|---|---|
| NB-1 (T02) | **T04 — must delete** | The transitional `.workflow/` prefix bridge in `resolve_artifact_path`. T04 must remove it when it moves `ARTIFACT_OWNERSHIP`, not inherit it. |
| T03-1 | **T11 hardening** | Declared fail-open window in `branch_guard`, reproduced by the verifier: switching branch *between* the two steps of `skip`/`reset`/`restart`/`implement preflight` lets the action run with no `branch_mismatch` audited. Minimal fix is a dedicated `pending_branch_ack` key so the branch acknowledgement stops sharing a slot with the command's own confirmation — needs a schema change, hence T11. |
| T03-4 | any phase | `ACTIVE_CONTEXT_SETTERS` is dead in production code (invariant 7 smell) — referenced only by a test while the real `setBy` values are string literals at three call sites. Wire it in or drop it. |
| T03-5 | any phase | `cmd_workitem_use` is not error-hardened like `cmd_init`/`cmd_migrate_workflow`: neither `write_active_context` nor `clear_active_context` is wrapped, so an `OSError` escapes as a traceback instead of a contract exit code. |
| T03-6 | any phase | `cmd_workitem_use` reuses the reason string `workitem_required` for a `UsageError` (exit 2), colliding with the resolution refusal (exit 1). Exit codes disambiguate; the name carries two meanings. |
| T03-7 | any phase | Untested edge-case ordering change: `init` in a repo with **both** a corrupt `workitems/index.md` and a legacy `.workflow/state.json` now reports `index_malformed` (exit 3) rather than `legacy_workflow_present` (exit 1). Fails closed, but nothing pins it. |
| T03-8 | any phase | On a mismatched branch the second invocation audits `branch_mismatch_accepted` even when the command then refuses for its own reason — the ledger records an acceptance for an action that did not occur. |
| T03-10 | docs | `SKILL.md`'s branch-mismatch paragraph says "re-run the same command — which proceeds"; exact for the five single-step critical commands, but `skip`/`reset`/`restart`/`implement preflight` yield their own confirmation step first. The Reference Guide already words this correctly. |
| NB-2, NB-4, NB-5 (T02) | T11 | Legacy-removal and migration-hardening items: the `legacy_workflow_present` message never names archiving `.workflow/`; the post-commit `workitem.json` write sits outside the commit window; the migration crash test never exercises the manifest/completion copies. |

### Process lessons, not code findings

- **T03-2/T03-3 — handoff evidence must be re-derived, not asserted.** T03's handoff over-cited the plan (claiming D5 "considered and rejected" sticky acknowledgement, which D5 never mentions) and claimed an empty skip/xfail grep that in fact matches a pre-existing `@pytest.mark.skipif` in `test_units_infra.py`. Both *conclusions* were right; the *evidence* was not. Check what a grep actually matches before quoting it.
- **Checkpoints can be accurate about the engine and wrong about tests.** T03's checkpoints 01–04 implied test files existed that did not. A resuming agent must verify claimed state against disk — `--collect-only` is the cheap check.
- **The `rtk` shell proxy will hand you a false green.** Plain `python -m pytest` prints `Pytest: No tests collected` and exits 0. Use `rtk proxy python -m pytest`, redirect to a file, and read `$?` with no pipe between. It also truncates `git diff` and `grep`; `rtk proxy "<command>"` returns full output and changes nothing about what executes.
- **The full suite takes ~8 minutes.** Give it a 600000 ms timeout; the default 2 min kills it mid-run.

## Control plane

`tools/transition/agent_guard.py` was repaired three times during T00–T01 and re-signed each time — see `T00-blocker.md` §9, §10, §11. It refused **nothing** during T02 verification. The user granted **standing approval for guard false-positive fixes only**: changes that stop it blocking provably read-only or sanctioned operations. Anything that would let it permit a **new mutation** still needs explicit approval. Every fix keeps the full procedure: patch, re-sign only the `agent_guard.py` line via `validate.py::sha256`, re-run all three matrices, record in the blocker.

`docs/transition/control-plane.sha256` is the integrity manifest; `validate.py` exits 3 on any mismatch.

**Environment note:** a token-optimising shell proxy (`rtk`) intercepts shell commands in this environment and truncates `git diff` / `grep` output. Its documented passthrough `rtk proxy "<command>"` returns full output and changes nothing about what executes, leaving the transition guard fully in force. Verifiers comparing diff output should be aware of the truncation.
