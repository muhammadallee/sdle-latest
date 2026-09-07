# Resume here

Cold-start note for the next session. Authority order is unchanged: the repository, `transition.md`, `progress.md`, and the persisted phase artifacts. **This file is a convenience, not a source of truth** — if it disagrees with `progress.md` or the repo, they win.

Run `python tools/transition/validate.py` first. It should print `TRANSITION_VALID: complete=11/12 next=T11`, exit 0. It will keep saying `next=T11` until T11 is independently verified and marked `COMPLETE`.

---

## The next action

**Verify T11** with a fresh `sdle-transition-verifier` against `docs/transition/phases/T11-plan.md` and `T11-handoff-a01.md`.

T11 is the **last phase of the migration**. There is no T12. It is `IMPLEMENTED, NOT YET VERIFIED`: all eight milestones are on disk, the suite is green and `lint-skill` reports 43/43.

**A finding silently dropped at T11 is unrecoverable** — this is the phase whose whole purpose was to close the ledger. The verifier's first job is `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`, which must carry all 26 inherited findings with exactly one disposition each (**20 FIXED · 4 DEFERRED · 2 NOT-A-DEFECT**), the four declared scenario divergences (§5.1), the three out-of-plan product changes (§5, including the write-fence anchoring in §5.3), the branch-guard deviation from B2 (§5.2), and TR8 as the single named V1 gap (§8).

After a `PASS`, the only remaining work is the **post-transition control-plane cleanup** contract §1.4 permits — and §1.4 is explicit that it happens in a *separate* change, after T11 has independently passed, never while the transition is executing.

## State

| | |
|---|---|
| Branch | `transition/workitem-v1` |
| Phases complete | T00–T10 (all independently verified PASS) |
| T11 | `IMPLEMENTED, NOT YET VERIFIED` (attempt a01) |
| Rollback point for T11 | `11363d9` (T10 implementation) |
| Byte-identity baseline for frozen files | `4b1aa71` |
| SDLE product baseline | `f8fdaa0` |
| Product version | **v1.17** (was v1.15 at T06) |
| Suite | see `T11-handoff-a01.md` for the observed figure; raw exit read with no pipe |
| `lint-skill` | **43 checks, `failed: []`**, raw exit 0 |
| Python 3.11 / CI | `NOT_RUN` / `UNKNOWN` — never observed at any point |

## What changed at T11, in one paragraph

The repository-global `.workflow/` runtime is **gone as a runtime**. The resolution ladder lost its sixth rung, `bind_workitem` now always returns a bound WorkItem, and the twelve `workitem is None` carve-outs are deleted. `.workflow/` survives as exactly two things — a **migration source** and a **project-root marker** — and `PROJECT_ROOT_MARKERS` must keep `('.workflow', 'state.json')` or a legacy-only repository becomes undiscoverable and therefore unmigratable. Recovery from a legacy-only repository is two runtime-free commands in order: `workitem create`, then `migrate-workflow --workitem <id>`.

## Four things a fresh context will otherwise get wrong

**1. The suite is green. Do not inherit the flake assumption.**
Every full run before commit `6e8af8c` was red with `PermissionError: WinError 5` from `os.replace`. `6e8af8c` fixed it with a bounded retry. **The F1 `ENVIRONMENT_FLAKE` path is VOID.** Any test failure is a presumed real regression — investigate it, do not pattern-match it to the old signature.

**2. CI has never run. The branch is green on Python 3.14 / Windows only.**
CI pins 3.11 on `ubuntu-latest` and `windows-latest`. No 3.11 interpreter exists on this host and no CI outcome has been observed at any point. Treat "green on 3.11" as `UNKNOWN`, never as `OBSERVED`. ADR-008 §6 states this position and it must not be softened.

**3. Two plan figures are known-wrong, and the corrections are the observed ones.**
The T11 plan's E20 says 18 stale transcript lines; the observed figure is **17 lines carrying 20 occurrences** — three lines carry two each. The plan's §9 reads as 20 FIXED / 3 DEFERRED / 2 NOT-A-DEFECT / 1 to-be-verified; TR20 resolved to DEFERRED, so the ledger is **20 / 4 / 2 = 26**. Count the ADR's table, not any prose summary. `T00-plan.md`'s "21 top-level subcommands" also remains wrong (65 `add_parser` registrations); plans are immutable, so corrections live in handoffs.

**4. Execution ids are not unique, by contract.**
`<3-letter-git-user-prefix>-<UTC-datetime>` at second resolution is what §"Execution identity" specifies, and it calls the identity *lightweight*. Two WorkItems started by the same user in the same second share a label. The isolation boundary is the **WorkItem**, not the execution id. A T11 hardening test asserted the inequality and passed only when the two `init` calls straddled a second boundary; that is recorded in ADR-008 §5.1. Do not "fix" the engine to make an id unique — that would violate the contract to satisfy a test.

## Open findings carried forward

All 26 inherited findings are dispositioned in **ADR-008 §7**, which supersedes the per-phase lists this file used to carry. Nothing is tracked here any more. The four `DEFERRED` rows are TR8, TR20, TR23 and TR25; TR8 is the **single named V1 gap** (§15's HIGH-risk list names a documentation review that no gate implements) and has a proposed two-step shape in ADR-008 §8 so the deferral is actionable rather than decorative.

### Process lessons, not code findings

- **Handoff evidence must be re-derived, not asserted.** T03's handoff over-cited its plan and claimed a grep result that did not hold. Both conclusions were right; the evidence was not. Check what a command actually returns before quoting it — and re-derive it in the context that quotes it.
- **A document can be a claim ahead of the fact.** ADR-008 recorded TR26 as FIXED ("RESUME.md updated to describe the completed state") while this file still pointed at T06. Writing the record before doing the work is the exact failure mode T11 exists to eliminate.
- **Checkpoints can be accurate about the engine and wrong about tests.** Verify claimed state against disk; `--collect-only` is the cheap check.
- **The `rtk` shell proxy will hand you a false green.** Plain `python -m pytest` prints `Pytest: No tests collected` and exits 0. Use `rtk proxy python -m pytest`, redirect to a file, and read `$?` with no pipe between. Heredocs fed to `python -` hang; use a file. `lint-skill` and `constants` nest their payload under `data`.
- **The full suite takes ~30 minutes.** Background it and poll, and confirm completion by locating the `N passed` summary line — a truncated tail is not a result.
- **Never `cd` into a subdirectory in a Bash call.** The shell cwd persists across calls and breaks every repository-root-relative hook command path, which blocked an entire T11 session.

## Control plane

`tools/transition/agent_guard.py` was repaired three times during T00–T01 and re-signed each time — see `T00-blocker.md` §9, §10, §11. The user granted **standing approval for guard false-positive fixes only**: changes that stop it blocking provably read-only or sanctioned operations. Anything that would let it permit a **new mutation** still needs explicit approval. Every fix keeps the full procedure: patch, re-sign only the `agent_guard.py` line via `validate.py::sha256`, re-run all three matrices, record in the blocker.

`docs/transition/control-plane.sha256` is the integrity manifest; `validate.py` exits 3 on any mismatch. This file is deliberately **not** in it — it is mutable phase evidence, which is what makes updating it here legitimate.

**Environment note:** a token-optimising shell proxy (`rtk`) intercepts shell commands in this environment and truncates `git diff` / `grep` output. Its documented passthrough `rtk proxy "<command>"` returns full output and changes nothing about what executes, leaving the transition guard fully in force. Verifiers comparing diff output should be aware of the truncation.
