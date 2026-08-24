# T03 Implementation Handoff — Attempt a01

**Phase:** T03 — WorkItem Resolution and Parallel Developer Isolation
**Attempt:** 1
**Implementer context:** fresh/isolated (resumed after the previous implementer of
this same attempt was terminated mid-flight by an API spend limit — an interruption,
not a verification failure, so the attempt was **not** incremented; contract §24.6)
**Status recommendation:** IMPLEMENTED

> Every figure below was produced by a command run in **this** context. Nothing is
> copied forward from the checkpoints. Source is cited by symbol name or greppable
> anchor, never by line number.
>
> **Tooling note for the verifier.** The `rtk` hook rewrites `pytest` and swallows its
> output — a plain `python -m pytest` prints `Pytest: No tests collected`. Every pytest
> figure here was produced with `rtk proxy python -m pytest …`, redirected to a file,
> with **no pipe** between pytest and the `$?` read.

---

## Inputs read from disk

- `docs/transition/transition.md` §9 (primary), §24.3, §24.6, TP-003.
- `docs/transition/phases/T03-plan.md` (authoritative, immutable).
- `docs/transition/phases/T03-checkpoint-a01-01.md` … `-04.md` (M1–M6, written by the
  interrupted implementer) — treated as claims and re-verified against the tree.
- `docs/transition/progress.md`, `CLAUDE.md`, `docs/transition/templates/phase-handoff.md`.
- `scripts/sdle.py`, `tests/`, `.claude/`, `README.md`, `docs/SDLE-Reference-Guide.md`.
- Git: `git status --porcelain`, `git diff --numstat`, `git diff --name-status ab889a1`.

### Discrepancy found on resume — repository wins

The resume brief stated that only M7, the N11 worktree test and the documentation sweep
remained. **The repository disagreed and the repository won:**

- `tests/test_units_workitem_resolution.py` **did not exist**.
- `rtk proxy python -m pytest -q --collect-only` reported `341 tests collected` — the
  exact pre-T03 baseline.

So **N1–N9, N11 and N12 were all unwritten**, not just N11, and the additive
`test_units_workitem_runtime.py` parametrize row was unwritten too. That whole set was
implemented in this context. M1–M6 themselves were confirmed present by symbol grep
(`PROJECT_ROOT_MARKERS`, `discover_project_root`, `launch_cwd`, `ACTIVE_CONTEXT_NAME`,
`active_context_workitem`, `cwd_workitem`, `branch_candidates`, `Resolution`,
`resolve_decision`, `candidate_evidence`, `cmd_workitem_resolve`, `cmd_workitem_use`,
`read_execution`, `recorded_branch`, `BRANCH_CRITICAL_ACTIONS`, `action_key`,
`_own_confirm_token`, `branch_mismatch`, `branch_guard`) and by a re-run of the suite.

### Resume baseline, re-derived in this context

`rtk proxy python -m pytest -q -rsxX` → **`341 passed in 356.37s (0:05:56)`, RAW EXIT 0**,
no short-summary section. This was started before the M7 edits (`conftest` imports
`sdle.py` once at collection). It confirms checkpoint 04's claim.

---

## Changes made

### `scripts/sdle.py` — M7 (D8, `sdle validate`) and one defect fix

| Symbol | Change |
|---|---|
| `workitem_id_wellformed` | **new.** One source for "is this an id `workitem create` could have minted", accepting **both** `WORKITEM_ID_RE` and `AUTO_ID_RE`. |
| `active_context_workitem` | **defect fix** (below): now calls `workitem_id_wellformed` instead of `WORKITEM_ID_RE` alone. |
| `RUNTIME_FREE_COMMANDS` | gains `"validate"` — sixth member. |
| `VALIDATE_ERROR`, `VALIDATE_WARNING`, `_finding`, `_escape_detail`, `_validate_metadata`, `_validate_runtime_state`, `collect_validation_findings`, `cmd_validate` | **new.** |
| `build_parser` | registers the top-level `validate` subcommand. |

`cmd_validate` runs `resolve_decision` **speculatively**, so a resolution refusal becomes
a finding rather than an exit. Findings are `{check, severity, workitem, detail, path}`.
One or more `error` findings raise `IntegrityError("workitem_validation_failed", …)` →
**exit 3** with `data.findings`; warnings-only or clean → **exit 0** with the same shape.
A structurally corrupt registry still surfaces as `read_index`'s `index_malformed`
(also exit 3) — declared, not caught and reshaped.

### `tests/` — M8

| File | Change |
|---|---|
| `tests/test_units_workitem_resolution.py` | **new**, 1461 lines, 81 `def test_`, **96 collected** cases (parametrization). N1–N9, N11, N12. |
| `tests/test_units_workitem_runtime.py` | one additive parametrize row `("validate",)`. |

### Prompt and documentation layer — M8 (D7)

| File | Anchor / change |
|---|---|
| `.claude/skills/sdle/SKILL.md` | Step 1 **only**. `init` invocation now names `--workitem <id>`; the ladder sentence rewritten in the D2 order; four new paragraphs — resolution on later turns, the ask-the-user rule, branch mismatch, `validate`. |
| `.claude/commands/sdle-start.md` | steps 2 and 4 — same ladder/ask guidance and the explicit `--workitem` at `init`. Invocation only. |
| `README.md` | the ladder is now eight rungs; new paragraphs for root discovery, `workitem resolve`, `validate`, the branch policy; the runtime-free sentence names six commands. |
| `docs/SDLE-Reference-Guide.md` | resolution section rewritten; "the third rung is transitional" → "the sixth rung"; `execution.json` artifact row extended; new `workitems/.active-context.json` artifact row; new "Branch and worktree rules" and "`validate`" subsections. |
| `CLAUDE.md` | the gitignore sentence names the active-context file; a new paragraph states the resolution posture and invariant 8. |

**Not touched, deliberately:** `.claude/hooks/hooks.py` (the point of D9),
`.claude/settings.json`, `.claude/skills/sdle/modules/`,
`.claude/skills/sdle/templates/state.json`, `scripts/sdle.sh`, `scripts/sdle.ps1`,
`.github/`, `requirements/`, `docs/dry-runs/`. No constant table, version string,
phase table or gate table was edited anywhere.

### Landed earlier in this attempt (M1–M6, by the interrupted implementer)

M1 `launch_cwd` + `PROJECT_ROOT_MARKERS`/`discover_project_root` marker walk;
M2 the active-context helpers, `workitem use`, persistence at `init` and
`migrate-workflow`, the `.gitignore` line and the single permitted
`conftest.init_git` mirror line; M3 `Resolution`/`resolve_decision`/`candidate_evidence`
and the `workitem_unregistered` refusal, plus the N10 test rewrite; M4
`cmd_workitem_resolve`; M5 the `execution.json` `git` object and `cmd_header`'s additive
`branch_mismatch` key; M6 `BRANCH_CRITICAL_ACTIONS`, `branch_guard`, `_own_confirm_token`,
`CONFIRMABLE`. Verified present and green in this context.

---

## Deliberate behavior changes

1. **D1 — project root is discovered, not assumed.** `resolve_paths` walks up from the
   launch directory to the nearest ancestor holding `workitems/index.md`,
   `.workflow/state.json` or `.git`, in that marker order at each level, falling back to
   the launch directory itself. `--project-root` and `SDLE_PROJECT_ROOT` still win. This
   is a real behavioural change for bare-CWD invocations.
2. **D2 — three new rungs** inside `resolve_decision`, *above* T02's refusals: CWD inside
   a WorkItem, a valid persisted active context, a unique Git-branch match. T02's "sole
   registered" rung stays at position 3 (plan U4).
3. **New refusal `workitem_unregistered`** — the only refusal T03 adds. Standing inside
   `workitems/<x>/` where `<x>` is a real directory the index does not know refuses
   rather than binding a neighbour.
4. **D3 — `workitems/.active-context.json`**, developer-local and gitignored, written
   only by `init`, `migrate-workflow` and `workitem use`.
5. **D4 — `execution.json` gains a `git` object** (`branch`, `startSha`, `worktree`).
   No `state.json` field, so no version bump and no migration row.
6. **D5 — branch-mismatch policy.** Nine `BRANCH_CRITICAL_ACTIONS` refuse once via the
   existing `pending_confirm_action` two-step; everything else warns. `CONFIRMABLE` gains
   `"branch_mismatch"`. `cmd_header` gains an additive `data.branch_mismatch` key and a
   stderr line; `rendered` is byte-unchanged.
7. **D6 — `workitem resolve`**, always exit 0, candidates with evidence, never a pick.
8. **D8 — `sdle validate`**, seven §9 checks, exit 3 on any error.
9. **D7 — prompt layer.** §9 rungs 5 (inference) and 6 (ask) are prompt-layer only, in
   the parent session; inference may rank and annotate the engine's candidate list and is
   never an independent resolver; the answer re-enters as an explicit `--workitem`.

### Declared divergences from the plan

**Divergence 1 — N10 pulled forward from M8 to M3** (the interrupted implementer's,
carried forward verbatim in substance). M3 is what supersedes
`test_dirty_tree_is_silent_when_the_workitem_is_ambiguous`, and leaving the suite red
through M4–M7 would have made later failures hard to attribute. TP-003 **category 2** —
genuinely superseded behaviour; this *is* NB-3 being closed. `.claude/hooks/hooks.py` is
untouched. `started_git` replaces `started` in that test so the branch-invalidated case
is reachable at all (without git, `current_branch` is `None` and a recorded branch can
never go stale).

**Divergence 2 — `_own_confirm_token(args)` refines plan D5** (also carried forward).
The plan's literal guard mechanism livelocks its own pinned `skip` sequence: the guard
would clobber the token the command had just set for itself, so `skip --confirm` would
refuse `no_pending_confirmation` forever. `_own_confirm_token` passes the guard through
when `pending` equals the token *this* command sets for itself. It opens no bypass —
that token can only be pending because the command set it on the immediately preceding
invocation, which the guard had to allow. The plan's declared consequence is preserved
exactly: on a mismatched branch `skip` needs the branch acknowledgement *and then* its
own. Pinned by `test_skip_on_a_mismatched_branch_needs_both_acknowledgements` and its
inverse `test_skip_confirm_alone_still_refuses_no_pending_confirmation`.

**Divergence 3 — D4's `execution.json` git block was pulled forward from M5 to M2**,
because `branch_candidates` (rung 5) reads it.

**Divergence 4 — severity of the speculative-resolution finding.** Plan D8 says a
resolution refusal "becomes a finding" but assigns no severity. It is emitted as
`active_workitem_unresolved`, **warning**. `error` would make every ambiguous repository
exit 3, and `>1 plausible -> ASK` is §9 working correctly, not a registry defect; plan
N9 requires `validate` to run successfully in an ambiguous repository.

**Divergence 5 — D8 case (b) fires only on a genuine disagreement.** A `state.json`
whose `workitem` field is *absent* is a pre-1.14 state awaiting `migrate`, which
`migrate` already reports. Only a non-empty string that differs from the directory name
is a finding. Pinned by `test_validate_tolerates_a_state_file_with_no_workitem_field`.

**Divergence 6 — an unsafe id has its other checks skipped.** Following a symlink out of
the registry to run metadata and runtime checks would *be* the traversal rather than
diagnose one.

**Divergence 7 — one defect fixed in T03's own M2 code.** `active_context_workitem`
tested the persisted id against `WORKITEM_ID_RE` alone, so a `--auto-generate` id
(`WI-<name>-<UTC>`, uppercase prefix) could be persisted by `workitem use` and then
silently ignored by rung 4 forever. Fixed by the new `workitem_id_wellformed`, which is
also what `validate`'s path-escape check uses, so the two cannot disagree. No test was
red — this was found by reading `cmd_workitem_create` while writing `validate`. Pinned by
`test_an_auto_generated_id_is_a_usable_active_context`.

---

## Preserved behavior / invariants

| # | Invariant | Evidence |
|---|---|---|
| P1 | §9's ambiguity rule is absolute — `0 → create/ask`, `1 → use`, `>1 → ASK` | `test_two_workitems_on_one_branch_never_tie_break`, `test_the_ladder_has_no_tie_break_operator` (an `ast` proof that `resolve_decision` calls no `min`/`max`/`sorted`), `test_no_rung_ever_returns_an_unregistered_workitem` |
| P2 | T02's refuse-over-guess ladder unweakened | all five baseline `workitem_*` reasons still present (`workitem_name_invalid`, `workitem_exists`, `workitem_required`, `workitem_unknown`, `workitem_ambiguous`); `workitem_ambiguous` keeps its `workitems` data key and only *gains* `candidates` |
| P3 | Invariant 8 — gates stay in the parent | rungs 5/6 are prompt-layer text only; no engine code infers or asks; `SKILL.md` states "never delegated to a subagent" |
| P4/P5 | Invariant 6 — single writer; `bind_workitem` stays pure | `test_bind_workitem_writes_nothing_and_prints_nothing` (recursive SHA map + empty streams across bind, explicit, unknown, ambiguous and legacy paths); `test_the_active_context_is_written_only_by_the_declared_setters` (`ast` proof) |
| P6 | Exit codes 0/1/2/3 | `branch_mismatch` and `workitem_unregistered` are exit 1; `workitem_validation_failed` is exit 3; no new code |
| P7 | JSON on stdout, text on stderr | all new commands emit through `emit`; `header`'s `rendered` byte-identical (`test_header_reports_the_mismatch_without_changing_rendered`) |
| P8 | SpecKit opacity | no `speckit-*` name or `/speckit.*` command touched |
| P9 | One source of truth | one ladder (`resolve_decision`) with two consumers; `workitem_id_wellformed` is the single id predicate; prompt files reference behaviour and restate no membership list |
| P10 | Legacy dual-read and `migrate-workflow` keep working | `test_the_legacy_dual_read_rung_still_binds`, `test_init_still_refuses_a_legacy_workflow_unconditionally`, every pre-existing `migrate-workflow` test green |
| P11 | No `workflow_version` bump | `CURRENT_VERSION = "1.14"`; `lint-skill` reports `14 migration rows`; `templates/state.json` byte-identical to `ab889a1` |
| P12 | Fail safe | no new path advances a phase; `branch_guard` refuses before any phase change |
| P13 | No distributed locking | no lock, lease or cross-worktree coordination added |
| — | NB-1 left in place for T04 | `resolve_artifact_path`'s `legacy_prefix = ".workflow/"` bridge is untouched |

---

## Test changes and TP-003 classification

| Test | Category | Rationale |
|---|---|---|
| `tests/test_hooks.py::test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` → `test_dirty_tree_resolves_a_workitem_the_same_way_the_engine_does` | **2 — genuinely superseded behaviour** | Its premise was T02 finding NB-3: the dirty-tree guard could not fire in a multi-WorkItem repository. T03's rungs 4 and 5 close that, inside `bind_workitem`, with **zero** edits to `.claude/hooks/hooks.py`. The rewrite is strictly stronger: fires with a valid context, silent with none, silent when branch-invalidated — so the fail-safe posture is still proven. `started_git` replaces `started` because the branch-invalidated case is unreachable without git. |
| `tests/conftest.py::Project.init_git` | **2 — mirrors a product configuration change** | One `.gitignore` line (`workitems/.active-context.json`) plus the adjacent comment. The plan's anti-contradiction clause names this as the single permitted `conftest.py` edit. No fixture semantics changed. |
| `tests/test_units_workitem_runtime.py::test_runtime_free_commands_need_no_workitem` | **additive coverage — not a modification of an assertion** | One parametrize row `("validate",)`. The test asserts per-command behaviour, not the frozenset's membership. |
| `tests/test_units_workitem_resolution.py` | **new file** | 96 cases. |

**No test was weakened, skipped, xfailed or deleted.**
`grep -rn "pytest.mark.skip\|pytest.skip(\|xfail" tests/` → **no matches** across the
whole suite.

### A17's `skip`/`xfail` grep, every returned line classified

`git diff ab889a1 -- tests/` returns **no** matching added line (the new file is
untracked, so it is not in the diff). Grepping the new file directly for `skip|xfail`
returns 18 lines, **none a pytest marker**:

- `def sha_map(root, skip=(".git",))` and `if any(part in skip …)` — a local helper's
  excluded-paths parameter.
- test *names* `…_is_skipped_never_fatal`, `…_whose_directory_vanished_is_skipped`,
  `…_branch_stale_context_is_skipped`, `…_detached_head_skips_the_branch_rung`,
  `…_no_git_skips_the_branch_rung` — describing a resolution *rung* being skipped by the
  engine.
- `("skip",)`, `mismatched.run("skip", …)`, `== "skip"` — the SDLE `skip` **CLI
  subcommand** and its `pending_confirm_action` token, in the N7 double-acknowledgement
  tests.
- three prose comments about *not* skipping (`"the suite keeps zero skips"`,
  `"Fails loudly rather than skipping"`).

`xfail` appears nowhere in the repository's tests.

---

## Commands actually run

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy python -m pytest -q -rsxX` (resume baseline, pre-M7) | **`341 passed in 356.37s (0:05:56)`, RAW EXIT 0** | no short-summary section → zero skips/xfails |
| `rtk proxy python -m pytest -q --collect-only` (resume) | `341 tests collected in 0.18s` | proved the new test file did not exist |
| `python -c "ast.parse(open('scripts/sdle.py').read())"` | `syntax ok` | after the M7 edits |
| `python scripts/sdle.py --project-root . validate` | exit 0, one `active_workitem_unresolved` warning | this repository registers no WorkItem |
| `rtk proxy python -m pytest -q tests/test_units_workitem_runtime.py -k runtime_free` | `5 passed` | the additive `validate` row |
| `rtk proxy python -m pytest -q -rsxX tests/test_units_workitem_resolution.py` | **`96 passed in 118.90s (0:01:58)`, RAW EXIT 0** | no short-summary section |
| **`rtk proxy python -m pytest -q -rsxX` (final, full suite)** | **`438 passed in 479.49s (0:07:59)`, RAW EXIT 0** | no short-summary section |
| **`rtk proxy python -m pytest -q --collect-only` (final)** | **`438 tests collected in 0.33s`** | collected **==** passed → zero skips, xfails, errors |
| **`python scripts/sdle.py lint-skill`** | **RAW EXIT 0**, `grep -c '"passed": true'` = **22**, `grep -c '"passed": false'` = **0** | `Parsed 19 phases, 8 gates, 14 migration rows`; re-run after M7 and again after every prompt-file edit |
| **`python tools/transition/validate.py`** | `TRANSITION_VALID: complete=3/12 next=T03`, **RAW EXIT 0** | |
| `git diff --exit-code ab889a1 -- .claude/hooks/hooks.py .claude/settings.json .claude/skills/sdle/templates/state.json .claude/skills/sdle/modules/ scripts/sdle.sh scripts/sdle.ps1 .github/ requirements/ docs/dry-runs/` | **exit 0** | A4 |
| `grep -n 'CURRENT_VERSION = ' scripts/sdle.py` | `CURRENT_VERSION = "1.14"` | A5 |
| `git diff --name-status ab889a1 -- tests/` | three `M`, no `D`, no `A` | see A17 note below |
| `git status --porcelain tests/` | three `M` + one `??` (the new file, untracked) | A17 |
| `grep -rn "pytest.mark.skip\|pytest.skip(\|xfail" tests/` | no matches | |
| `grep -rn "\.sdle/policies\|baseline\.\|risk\|classification\|flow_type\|subagent" scripts/sdle.py` | **2 hits**, both pre-existing: `baseline.lower()` in the drift comparison and the `drift rebaseline` help string. `git show ab889a1:scripts/sdle.py \| grep -c …` = **2**, the same two lines | A18 |
| `ls -d .sdle` | no repository-root `.sdle/` | A18 |
| `grep -n "def resolve_artifact_path" -A 20 scripts/sdle.py` | `legacy_prefix = ".workflow/"` still present | NB-1 left for T04 |
| Python 3.11 | **NOT_RUN** | no 3.11 interpreter on this host |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN** | the branch has never been pushed; **no outcome is predicted** |

**A17 nuance, declared rather than glossed:** the plan expects exactly one `A` under
`tests/`. Nothing in T03 is committed, so `tests/test_units_workitem_resolution.py` is
still **untracked** and appears as `??` in `git status --porcelain`, not as `A` in
`git diff --name-status`. The set is otherwise exactly as the plan predicts: three `M`
(`conftest.py`, `test_hooks.py`, `test_units_workitem_runtime.py`), zero `D`.

---

## Git evidence

- **HEAD:** `767b657009d9631c3a10a7fee3b87f4e0c549558` on `transition/workitem-v1`.
- **Product baseline / rollback point:** `ab889a1` (the T02 implementation commit).
- **Working tree — nothing committed by this phase:**

```
git diff --numstat
 19    7   .claude/commands/sdle-start.md
  3    1   .claude/settings.local.json      <- pre-existing, OUT OF SCOPE
 10    2   .claude/skills/sdle/SKILL.md
  1    0   .gitignore
  3    1   CLAUDE.md
 33    6   README.md
 89    9   docs/SDLE-Reference-Guide.md
1001   46  scripts/sdle.py
  5    2   tests/conftest.py
 38    15  tests/test_hooks.py
  1    0   tests/test_units_workitem_runtime.py

untracked:
  tests/test_units_workitem_resolution.py
  docs/transition/phases/T03-checkpoint-a01-01.md … -06.md
  docs/transition/phases/T03-handoff-a01.md
```

- `.claude/settings.local.json` is the user's permission allowlist. It was already
  modified before this phase began and was **not** touched; it is on the plan's scope
  exclusion list.
- All 46 deleted lines in `scripts/sdle.py` were read and accounted for: the old
  `resolve_paths` root computation (replaced by the marker walk), the inline detached-HEAD
  check in `cmd_workitem_create` (extracted to `current_branch`), the old `bind_workitem`
  body (replaced by `resolve_decision` + refusal mapping), and one reflowed `CONFIRMABLE`
  line. No existing function was silently altered.
- **Not committed.** The orchestrator owns committing; per §24.3 this implementer stops
  at the handoff.

---

## Known limitations / risks

1. **`_own_confirm_token` has one narrow window that cannot be closed without extra
   state, and it is declared rather than fixed.** If a user runs `skip` on a *matched*
   branch (setting `pending = "skip"`), then checks out a different branch, then runs
   `skip --confirm`, the guard sees `pending == own` and passes through — so that one
   critical action runs with no `branch_mismatch` acknowledgement ever audited. The
   mechanism cannot distinguish this from the legitimate three-invocation flow without
   recording the acknowledgement stickily, which plan D5 considered and rejected because
   it changes the per-command semantics. The window is a branch switch *between* a
   command's two steps. Not fixed in T03; recorded so the fail-open hunt finds a
   declaration rather than a surprise.
2. **`cmd_workitem_use` reuses the reason string `workitem_required` for a
   `UsageError` (exit 2)** when neither `--workitem` nor `--clear` is given. A caller
   matching on `reason` alone could confuse it with the resolution refusal (exit 1). The
   exit code is the contract and it is unambiguous; left as M2 shipped it and pinned by
   `test_workitem_use_without_a_target_is_a_usage_error`.
3. **The symlink path-escape case degrades on a Windows host without the symlink
   privilege.** `test_validate_detects_a_symlinked_workitem_directory` then asserts the
   `resolve()`-based escape rule directly instead of skipping (plan F13). The
   traversal-shaped index id has its own always-run test, so the `path_escape` check has
   deterministic coverage on every host. On this host the symlink branch was taken —
   which one ran cannot be told from the pass count alone.
4. **`validate` is a diagnosis, not a gate.** Nothing calls it automatically; a broken
   registry still refuses at resolution time, which is the guardrail.
5. **Python 3.11 and CI are NOT_RUN.** T03 is standard-library-only and adds no syntax
   beyond what `sdle.py` already used, but **no outcome is predicted**.
6. **The resume-baseline suite run overlapped the first M7 edits.** `conftest` imports
   `sdle.py` once at collection, so the in-process tests ran pre-M7 code; the handful of
   subprocess-based cases in `test_units_cli.py` may have picked up partially-edited
   code. The authoritative figure is the **final** full-suite run (438 passed, raw exit 0)
   made after all edits.

---

## Claims for verifier to independently check

1. **A1** — `rtk proxy python -m pytest -q -rsxX` gives `438 passed`, raw exit 0, and
   `--collect-only` gives `438 tests collected`; collected == passed, so zero skips,
   xfails or errors. `438 = 341 (baseline) + 96 (new file) + 1 (parametrize row)`.
2. **A2** — `lint-skill` raw exit 0, 22 PASS / 0 FAIL, `19 phases, 8 gates, 14 migration
   rows`, v1.14 at all four locations.
3. **A3** — `python tools/transition/validate.py` raw exit 0.
4. **A4** — the must-not-change list is byte-identical to `ab889a1`, including
   `.claude/hooks/hooks.py` (which is what makes A15's "zero hook edits" claim checkable).
5. **A5** — `CURRENT_VERSION == "1.14"`, 14 migration rows, `templates/state.json`
   unchanged, no new `state.json` field (`git diff ab889a1 -- .claude/skills/sdle/templates/state.json` empty).
6. **A6–A8** — the §9 matrix tests, each ambiguous row asserting a recursive SHA map is
   unchanged; `workitem_unregistered` binds nothing.
7. **A9–A10** — the purity proof and the context lifecycle, including the `ast` proof
   that only `cmd_init`, `cmd_migrate_workflow` and `cmd_workitem_use` write it.
8. **A11–A14** — `execution.json` git block; the nine `BRANCH_CRITICAL_ACTIONS`;
   `workitem resolve`; `validate`'s per-rule findings and exit codes.
9. **A15** — NB-3 closed with `.claude/hooks/hooks.py` byte-identical to `ab889a1`.
10. **A16** — `test_two_worktrees_drive_two_workitems_with_no_flag`: two `git worktree`s,
    no `--workitem` anywhere, byte-unchanged neighbours, per-WorkItem locks, no
    `.workflow/`.
11. **A17** — the modified-test set, with the untracked-file nuance above.
12. **A18–A19** — no future-phase leakage; the `.workflow/` bridge and the legacy rung
    intact.
13. **A20** — Python 3.11 and CI recorded NOT_RUN, no outcome predicted.
14. **The seven declared divergences above** — in particular divergence 2
    (`_own_confirm_token`) together with **Known limitation 1**, and divergence 7 (the
    auto-generated-id defect fix), which is the one place T03 changed behaviour that no
    failing test demanded.

## Blocker

None. No material architecture, contract or baseline decision was required.
