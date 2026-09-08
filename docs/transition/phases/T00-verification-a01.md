# T00 Independent Verification — Attempt a01

**Phase:** T00 — Baseline Freeze and Transition Safety Net  
**Attempt:** 01  
**Verifier context:** fresh/isolated  
**Result:** PASS

> The handoff is a claim set, not proof. Every number below was re-derived in
> this verifier context from `scripts/sdle.py`, `.claude/`, `tests/`,
> `docs/transition/transition.md` and re-run commands. Where my observation
> differs from the handoff's (the pytest flake victims), my own observation is
> recorded, not the handoff's.

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| A1 — `baseline.md` has exactly the 7 top-level sections in plan order | PASS | `grep -n "^## "` returns `1. Frozen baseline identity`, `2. Environment record`, `3. Baseline verification results`, `4. Capability inventory`, `5. Transition regression matrix`, `6. Known baseline conditions`, `7. Explicitly preserved by decree` — 7, in order |
| A2 — §4 has exactly 14 subsections in contract §6 item 3 order, no blank cell | PASS | Parsed §4: 14 `### 4.x` headings matching the contract list verbatim in order; 14 header rows; **183 data rows**; 0 rows with a cell count other than 5; **0 blank cells** |
| A3 — §3 records lint-skill and pytest with exit codes; lint-skill 22 PASS / 0 failed; pytest zero failures or every failure dispositioned under F1 | PASS | Re-ran both. `lint-skill` exit 0, 22 `[PASS]` lines, `"ok": true`, `"failed": []`. `pytest -q --tb=line -rf` exit 1, `2 failed, 228 passed in 389.46s`; both failures carry the F1 signature and all three targeted re-runs passed (see Regression evidence) |
| A4 — no tracked file modified or deleted | PASS | `git status --porcelain` = 7 lines, all `??`; `git status --porcelain -uall` = 25 lines, **0** not beginning with `??`; `git diff HEAD --stat` produces **no output** |
| A5 — §5 carries every contract §18 capability exactly once with a valid disposition and a changing phase on every non-PRESERVE row | PASS | Parsed contract §18: **31** capability rows. Parsed §5 matrix: **47** data rows = 31 §18 labels each present exactly once (0 missing, 0 duplicated, 0 invented) + **16** `NOT_IN_S18`. Every §4 row disposition is in {PRESERVE, ADAPT, SUPERSEDE_LATER}; **0** violations of the "PRESERVE implies phase `-`, non-PRESERVE implies a named phase" rule across all 183 §4 rows |
| A6 — every §4 Item maps to a §5 row | PASS (by declared rule) | §5 states an explicit family-mapping rule and names the two non-obvious Items (`security-review begin`, `accept-state`). Spot-checked all 14 categories: each has a family row (exit codes, state schema, audit chain, lock, rate limits, drift, hooks, dirty-tree, untrusted scan, secrets scan, test evidence, base-ref, migration chain, plus the CLI family rows) |
| A7 — §1 records observed HEAD SHA with an explicit MATCH verdict | PASS | `git rev-parse HEAD` = `f8fdaa048b9a9a35d317224eddd191318ccdd7f6`; §1 records that value, the contract value, and **MATCH**; branch `transition/workitem-v1`; `git branch -a --contains HEAD` = `transition/workitem-v1` + `remotes/origin/wave-a-deterministic-core`, exactly as recorded |
| A8 — both CI rows `NOT_RUN` with a reason; no predicted CI result anywhere | PASS | §3.4 and §3.5 are `NOT_RUN` with the local-only-branch reason. Case-insensitive sweep of `baseline.md`, the handoff and all three checkpoints for `CI` returned only: the workflow pin/matrix/steps quoted from `git show`, the skew statement, and explicit "No CI outcome is predicted" lines. No predicted outcome found |
| A9 — §6 carries the four required known conditions | PASS | §6.1 `write_atomic` flake, §6.2 19-vs-18, §6.3 `.github/` Read restriction, §6.4 `agent_guard.py` defect (RESOLVED) |
| A10 — §7 reproduces all five contract §6 explicit-preserve items with the phase permitted to change each | PASS | 18-phase sequence/T07, 8 gates/T09, `.workflow/` location/T02, lock behavior/T02, Spec Kit feature behavior/T04 — all five, each with file:line evidence |
| A11 — validator exits 0; T00 row well-formed | PASS | `python tools/transition/validate.py` exit **0**, `TRANSITION_VALID: complete=0/12 next=T00` (pre-verification state). T00 row parses to 9 columns, Plan = `docs/transition/phases/T00-plan.md`, Handoff resolves to an existing file, no pipe inside any cell |
| A12 — no new top-level directory; `workitems/` and `.sdle/` absent | PASS | `ls -a` top level: `.claude .git .github .gitignore .pytest_cache CLAUDE.md README.md SDLE-*.md docs requirements scripts tests tools`. `ls -d workitems .sdle` → "No such file or directory" for both |
| A13 — control-plane files unchanged / manifest intact | PASS | Validator exit 0 raises no `control-plane hash mismatch`; all 15 manifest lines verify. See the guard-change verification below for the one authorized exception |
| A14 — nothing under `tests/` added, deleted or modified; 230 collected | PASS | `git diff HEAD --stat` empty (covers `tests/`); `python -m pytest -q --collect-only` = **230 tests collected** |

Contract §6 exit criteria, checked directly rather than only through the plan:

| Contract §6 exit criterion | Result | Evidence |
|---|---|---|
| complete baseline inventory exists | MET | 14 subsections, 183 rows, all 5 cells populated; every countable minimum met exactly (below) |
| baseline suite is green | MET WITH RECORDED CAVEAT | Suite exit 1 in this context from two `WinError 5` flakes; F1 applied by me, 3/3 targeted re-runs passed; the caveat is recorded, the raw exit code is not restated as 0 |
| no runtime behavior has changed | MET | `git diff HEAD --stat` empty; `git status --porcelain -uall` has 0 non-`??` lines |
| every current guardrail has a disposition | MET | 183/183 §4 rows and 47/47 §5 rows carry a disposition; 31/31 contract §18 capabilities covered exactly once |

## Full-suite / lint evidence

Every row below was executed by me in this verifier context and its output observed.

| Command | Result | Evidence/summary |
|---|---|---|
| `python scripts/sdle.py lint-skill` | **exit 0** | 22 `[PASS]` checks, no `[FAIL]`; JSON envelope `"ok": true`, `"failed": []`. Includes `tables_wellformed: Parsed 19 phases, 8 gates, 13 migration rows` and `progress_denominator_matches_phase_count: denominators=['18'] expected={18}` |
| `python -m pytest -q --collect-only` | exit 0 | `230 tests collected in 0.15s` |
| `python -m pytest -q --tb=line -rf` | **exit 1** | `2 failed, 228 passed in 389.46s (0:06:29)` |
| `python tools/transition/validate.py` | **exit 0** | `TRANSITION_VALID: complete=0/12 next=T00` |
| `git rev-parse HEAD` | exit 0 | `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` |
| `git diff HEAD --stat` | exit 0 | no output |
| `python scripts/sdle.py constants` | exit 0 | `version_chain` = 13 rows, `1.0→1.1` … `1.12→1.13` — corroborates the 13 migration rows |
| `git show HEAD:.github/workflows/ci.yml` | exit 0 | `fail-fast: false` (l.13), `os: [ubuntu-latest, windows-latest]` (l.15), `python-version: "3.11"` (l.22), steps `lint-skill` (l.36), `pytest -q --tb=line -rf` (l.45), `sh scripts/sdle.sh lint-skill` (l.59), `./scripts/sdle.ps1 lint-skill` (l.64) — every CI fact in baseline §2 confirmed verbatim |
| Linux CI (`ubuntu-latest`) | **NOT_RUN** | Not observable from this context; branch is local-only. No outcome predicted here or anywhere in the T00 evidence |
| Windows CI (`windows-latest`) | **NOT_RUN** | Same |

Verifier environment: Python 3.14.6, pytest 9.1.1, Windows 11 (10.0.26200) —
identical skew to the implementer's, and equally not evidence about CI's
CPython 3.11 on either platform.

## Regression evidence

### F1 applied independently (scrutiny item 1)

My full-suite run failed differently from both the plan's and the implementer's:

```text
FAILED tests/test_integration_01_happy_path.py::test_completion_summary_written_exactly_once
FAILED tests/test_units_state.py::test_migrate_adds_implementation_base_ref
2 failed, 228 passed in 389.46s (0:06:29)
```

Both carry the identical signature:

```text
C:\workspace\ai\cc\sdle-git-repo\sdle-latest\scripts\sdle.py:463: PermissionError: [WinError 5] Access is denied:
  '...\pytest-10\test_completion_summary_writte0\target\.workflow\.audit.md.kgky0py8.tmp'
  -> '...\pytest-10\test_completion_summary_writte0\target\.workflow\audit.md'
```

`scripts/sdle.py:463` is `os.replace(handle.name, path)` inside `write_atomic`
(function spans 446-469, no retry, no backoff) — confirmed by reading the source.

F1 procedure run by me, both node ids together, three times:

```text
F1 re-run 1: 2 passed in 12.87s   exit 0
F1 re-run 2: 2 passed in 11.51s   exit 0
F1 re-run 3: 2 passed in 39.31s   exit 0
```

Classification `ENVIRONMENT_FLAKE` is **independently confirmed, not accepted on
trust**. The victim set has now moved across three unrelated contexts:

| Context | Victim node id(s) | Victim file(s) |
|---|---|---|
| Plan | `test_integration_02_to_05.py::test_04_unapproved_gates_are_never_drift_checked` | `audit.md`, then `state.json` |
| Implementer a01 | `test_integration_01_happy_path.py::test_traversal_matches_the_transcript` | `state.json` |
| This verification | `test_integration_01_happy_path.py::test_completion_summary_written_exactly_once` **and** `test_units_state.py::test_migrate_adds_implementation_base_ref` | `audit.md` both times |

A deterministic defect does not migrate across four unrelated tests in three
runs while every targeted re-run passes. The plan's mismatch prediction was
correct and the implementer's handling was correct. Not a T00 failure.

### Countable minimums, re-derived from source

| Minimum | Required by plan | Re-derived by me | Baseline §4 rows | Verdict |
|---|---|---|---|---|
| CLI subcommands | every `add_parser` name incl. nested | `grep -c "add_parser("` = **65**: 33 on `subparsers`, 32 on 17 nested group objects (16 distinct group parsers) | 65 | EXACT |
| — set equality | — | Resolved every registration to its full command path and diffed against §4.1's Item column: **0 missing, 0 extra** (the only textual difference is the cosmetic `(group)` suffix on the 16 group rows) | — | EXACT, no padding |
| Exit codes | all four | `EXIT_OK/EXIT_REFUSED/EXIT_USAGE/EXIT_INTEGRITY` at `scripts/sdle.py:37-40` | 4 | EXACT |
| State fields | 25 top-level + 8 `approvals` | `json.load(templates/state.json)`: **25** top-level keys, **8** approvals keys | 33 | EXACT |
| Hooks | all four wired | 4 wired entries | 8 (4 wired + 4 cross-cutting) | MET |
| Migrations | 13 rows lint-skill parses | lint-skill `13 migration rows`; `constants.version_chain` = 13 | 15 (13 chain + 2 chain-level behaviors) | MET |
| Total §4 rows | — | — | **183** | matches claim |

### Regression matrix completeness (scrutiny item 4)

Parsed contract §18 (31 capability rows) and baseline §5 programmatically:

- 31/31 §18 labels present, **verbatim**, each **exactly once**; 0 missing, 0 duplicated;
- 0 values in the "Contract §18 row" column that are neither a real §18 label nor `NOT_IN_S18`, so **nothing was invented**;
- **16** `NOT_IN_S18` rows; 31 + 16 = **47** total, matching the claim;
- 0 blank cells across the matrix.

(The naive line count is 52; five of those lines belong to the two-column
"Vocabulary mapping rule" table above the matrix, not to the matrix itself.)

**The five `NO_ANCHOR` rows are genuine findings, not filler.** Verified by
searching `tests/`, `scripts/sdle.py` and `templates/state.json`:

| `NO_ANCHOR` row | Claim | My check |
|---|---|---|
| Artifact review/validation against exact SHA | capability absent at baseline | `grep -rni "stale_review\|stale-review\|review_sha\|reviewed_sha\|governed"` across `tests/`, `scripts/sdle.py`, `state.json` → **zero hits**. Genuine |
| Review evidence + audit linkage | same | same search, zero hits. Genuine |
| Stale-review invalidation after artifact change | same | same search, zero hits. Genuine |
| `.gitignore` content | no test | Only hit for `gitignore` in `tests/` is `conftest.py:180`, which *writes* a fixture `.gitignore`; nothing asserts the repository's `.gitignore` content. Genuine |
| `checkpoint set/get/clear` | no dedicated test | Only `checkpoint` hit in `tests/` is `test_integration_06_to_09.py:322` — an incidental `assert state["phase_checkpoint"] is None`, not a test of the subcommands. The row's wording ("no dedicated test") is precise. Genuine |

Note the existing `security-review` subcommand is a Phase-17 artifact helper and
is **not** the §18 governed-review capability; treating them as distinct is
correct, and T06 will have no regression net to inherit for those three rows.

### Anchor integrity — no invented test node ids

Extracted every pytest node id cited anywhere in `baseline.md` and matched it
against the live collection (230 ids):

- 118 fully-qualified node ids cited; 4 initially unmatched, all four resolved as
  **parametrized** tests whose collected ids carry a `[param]` suffix
  (`test_write_fence_denies_governance_files`, `test_05_every_injection_pattern_fires`,
  `test_state_set_refuses_engine_owned_fields`, `test_advance_refuses_forward_jumps`
  — each confirmed by its `def` line in `tests/`);
- 25 `::shorthand` citations, all 25 resolved against the file named on the same line.

**Zero fabricated anchors.** The matrix's regression anchors are real.

## Future-phase leakage check

PASS. No leakage found.

- `workitems/` and `.sdle/` do not exist (`ls -d` errors for both).
- No new top-level directory: `.claude .git .github .gitignore .pytest_cache CLAUDE.md README.md SDLE-TRANSITION-KICKOFF.md SDLE-TRANSITION-KIT-FILES.txt SDLE-TRANSITION-KIT-README.md SDLE-WAVE-A-KICKOFF.md docs requirements scripts tests tools`.
- `git status --porcelain -uall` = 25 entries, **0** not `??`; every untracked path belongs to the transition kit or to T00's own evidence (`docs/transition/baseline.md`, `phases/T00-*`, `progress.md`).
- No `workitem` CLI subcommand exists: the 65 re-derived `add_parser` names contain none.
- No `RepositoryContext`/`WorkItemContext`, no `.sdle/` config, no flow-model change, no `.gitignore` edit — all impossible given the empty `git diff HEAD`.
- The `sdle-transition-*` agents and `apply-sdle-transition` skill are migration control-plane scaffolding from the kit, not T10 product skills (contract §1.4), and predate this attempt (mtime 11:49, before T00 started).

## Test weakening / deletion check (scrutiny item 6)

PASS. **TP-003 is genuinely an empty set.**

`git diff HEAD --stat` produces no output at all, which proves every tracked
file — including all nine test modules and `conftest.py` — is byte-identical to
`f8fdaa04`. Nothing under `tests/` was added, deleted, modified, skipped or
xfailed, because nothing under `tests/` was touched. Collection is still 230.

The handoff's reasoning is also sound: T00 changes no behavior, so TP-003's three
categories have no applicable member. That is an empty set, not an invented
fourth category. The one suite failure was dispositioned under the *plan's* F1
failure mode, which is correctly labelled as a plan classification rather than a
TP-003 category.

## Deterministic guardrail check

PASS.

- All 22 lint-skill checks pass, including the cross-file sync checks that would
  detect any tampering with PHASE_SEQUENCE, NEXT_PHASE, PHASE_LABEL_MAP,
  PROGRESS_MAP, the 8 gate registrations, the single state template, and the
  four version-string locations.
- No fail-open behavior introduced: T00 adds no executable code. The one
  executable control that *was* changed (`agent_guard.py`) moved strictly from
  fail-open to fail-closed for the implementer role — verified below.
- No duplicated source of truth created. `baseline.md` quotes contract §18 labels
  into a dedicated column and quotes two PHASE_SEQUENCE rows as evidence; neither
  is machine-read by anything, and no product constant was copied to a second
  location. lint-skill `single_state_template` and
  `no_hardcoded_progress_outside_progress_map` still pass.

### 19-vs-18 phase count (scrutiny item 3)

PASS — **RESOLVED, no defect**, and the cited line numbers are correct.

| Cited | What is actually there |
|---|---|
| `SKILL.md:110-111` | Line 110 is `\| 19 \| ` + backtick-`complete`-backtick + ` \|`, the 19th and final PHASE_SEQUENCE row, immediately after line 109 `\| 18 \| gate_security \|`. Line 111 is the table's end |
| `scripts/sdle.py:322-325` | Exactly the `@property def phase_count` block: docstring "The N in 'N/18' — every phase except the terminal ``complete``", body `return len([p for p in self.phase_sequence if p != "complete"])` |
| `scripts/sdle.py:3144-3155` | Exactly the denominator check: `expected_denominator = str(consts.phase_count)` compared against the PROGRESS_MAP denominator set |
| `scripts/sdle.py:2338` | Exactly `total = len(consts.phase_sequence) - 1  # ` + backtick-`complete`-backtick + ` is not restartable` |

So 19 is a raw PHASE_SEQUENCE row count that includes the terminal pseudo-phase,
18 is the phase count excluding it, and the denominator check compares against
18. Both lint-skill messages are correct and non-contradictory. Plan unknown U3
is properly closed. Nothing to fix; recording it as a known condition rather than
a defect is the right disposition.

## State / audit / evidence integrity check

PASS.

- `python tools/transition/validate.py` exits **0** and validates all 15
  control-plane manifest lines with the canonical-LF hash.
- `progress.md` parses to 12 rows T00..T11 in order, 9 columns each, no pipe
  character inside a cell.
- The three checkpoint files are consistent with the final artifacts: every count
  they claim (65 / 4 / 33 / 8 / 7 / 6 / 10 / 8 / 4 / 8 / 5 / 5 / 5 / 15 = 183;
  47 = 31 + 16) matches what I independently parsed out of `baseline.md`.
- No audit or state file was written by T00; `.workflow/` does not exist in this
  repository outside test temp dirs.

### Authorized `agent_guard.py` modification — blocker §9 execution (in scope)

**PASS. §9 describes the change accurately, and nothing beyond it was touched.**
I verified the execution, not the decision.

1. **The diff is exactly what §9.1 claims.** I removed from the current file
   precisely the block §9.1 documents (the four-line rationale comment plus
   `ROOT = ...`, the `if path.lower().startswith(ROOT.lower() + "/")` guard and
   its slice), restored the original single `path = str(raw_path).replace(...)`
   line, and hashed the result with `validate.py`'s own canonicalization:

   ```text
   reconstructed original : aa57c5881c86ca796e895136b5a751b0331e87d3a08c813a802ee9309101aa42
   §9.2 "before" value    : aa57c5881c86ca796e895136b5a751b0331e87d3a08c813a802ee9309101aa42
   current file           : 93afa04914005c18b64622485e42ff36f74382c4aaf523ae48bc8f310dff7f40
   §9.2 "after" value     : 93afa04914005c18b64622485e42ff36f74382c4aaf523ae48bc8f310dff7f40
   ```

   A byte-exact match in both directions proves the normalization block is the
   **only** difference. `CONTROL_PREFIXES`, the five phase-file regexes, `PROGRESS`,
   `allowed_write()` and both Bash filters are provably unaltered.

2. **Only the `agent_guard.py` manifest line changed.** Corroborated
   independently by mtime: every other control-plane file
   (`transition.md`, all four `templates/`, `phases/README.md`, `validate.py`,
   all four `.claude/agents/sdle-transition-*.md`, `apply-sdle-transition/SKILL.md`,
   `SDLE-TRANSITION-KICKOFF.md`, `SDLE-TRANSITION-KIT-README.md`) still carries
   the kit-extraction timestamp **11:49**, while `agent_guard.py` is **15:25** and
   `control-plane.sha256` is **15:26**. No third file was touched.

3. **`validate.py` exits 0**, printing `TRANSITION_VALID: complete=0/12 next=T00`,
   with no `control-plane hash mismatch`.

4. **Policy behavior re-tested by me, not accepted from §9.4.** I drove the guard
   with real `PreToolUse` JSON payloads across 10 role/target cases in **both**
   absolute and relative path form — 20 runs, **0 mismatches** against expectation:
   planner→plan ALLOW, verifier→verification ALLOW, planner/verifier→`progress.md`
   ALLOW (exact-string compare, the case that would expose an off-by-one in the
   prefix strip), planner→blocker ALLOW, implementer→handoff ALLOW,
   implementer→`scripts/sdle.py` ALLOW, verifier→`scripts/sdle.py` BLOCK,
   implementer→`transition.md` BLOCK, implementer→`agent_guard.py` BLOCK,
   implementer→`sdle-transition-planner.md` BLOCK. The fail-open half is closed
   and the fail-closed half is opened, with no policy drift.

## Cross-platform / path handling check

PASS. No migration and no path change is in T00's scope, and none occurred.

- lint-skill `no_powershell_only_cmdlets` passes; both launchers are untouched.
- The only cross-platform caveat is that the entire baseline was measured on
  Windows/CPython 3.14.6 against a CI pin of 3.11 on two platforms. Baseline §2
  states this explicitly and scopes the evidence to "this environment only",
  which is the honest treatment.
- The `WinError 5` flake is Windows-specific and is recorded as such, not
  generalized.

## Artifact review/SHA freshness check

PASS, with the correct scope.

Governed-artifact review bound to an exact SHA does not exist at this baseline —
it is one of contract §18's three `ADD / ENFORCE` rows, arriving at T06, and I
confirmed its absence by source search. The applicable SHA-bound control at T00
is the transition control plane itself, and it verifies clean (§9 above).
`artifact_shas` and the `audit_sha`/`prev_sha` chain are inventoried in §4.3/§4.4
with real test anchors and are untouched.

## Findings

### Blocking

**None.**

### Non-blocking

1. **`T00-plan.md` ledger error stands uncorrected on disk (scrutiny item 2).**
   The plan's evidence ledger says "The CLI exposes 21 top-level subcommands".
   I re-derived the truth from `scripts/sdle.py`: **33** registrations on the
   top-level `subparsers` object and **32** on 17 nested group objects (16
   distinct group parsers), **65** total; of the 33 top-level, 16 are groups
   requiring a nested subcommand, so 49 command paths are directly invocable.
   `21` matches none of 33, 49 or 65 and is simply wrong.
   **The implementer's handling was correct.** The plan's operative completeness
   rule ("every `add_parser` name, including nested subcommands, each as its own
   row") is unambiguous and independent of the ledger number; the implementer
   followed the rule, produced 65 rows that I confirmed are a *set-exact* match
   for the real registrations, and reported the divergence in the handoff and in
   checkpoint a01-02 without editing a planner-owned file. Contract §24.3 item 2
   asks the implementer to verify the plan against evidence, not to rewrite it,
   and `agent_guard.py` blocks an implementer write to `T00-plan.md` regardless.
   Reporting-not-absorbing was right. Recorded here only so a future reader of
   `T00-plan.md` is not misled by the stale figure.

2. **`write_atomic` has no retry and the flake is recurring, not a one-off.**
   It hit two different tests in my run and four distinct tests across three
   contexts. Any agent running the suite on this machine should expect it and
   apply F1 rather than reading it as a regression. Root cause remains `UNKNOWN`;
   a bounded retry around `os.replace` is product work requiring a separate human
   decision, correctly excluded from T00 by plan F2.

3. **CI remains `NOT_RUN` and will stay so.** Branch `transition/workitem-v1` is
   local-only, so no phase from T00 to T11 will produce CI evidence unless it is
   pushed. The local/CI version skew (3.14.6 vs 3.11, Windows-only vs a two-OS
   matrix) is correctly stated in baseline §2 and applies equally to every later
   phase's test evidence.

4. **Blocker §9.1 says "six lines added"; the added block is eight lines**
   (four comment lines plus `ROOT = ...`, the `if`, and the slice — the
   `path = str(raw_path)...` line already existed). Documentation imprecision
   only: the hash reconstruction above proves the substance is exactly what §9
   describes. No action needed.

5. **Residual from blocker §9.5 confirmed still open.** The planner/verifier Bash
   filter blocks redirection and mutation command shapes but not
   interpreter-mediated writes. Separately, that same regex is a usability
   friction for verifiers: it rejects observational commands merely for
   containing `>` anywhere in the text, including `2>/dev/null` and an ASCII
   arrow inside a Python comment. I worked around it without needing any
   mutation. Not a T00 defect; noted for whoever revisits the harness.

## Final result rationale

T00 is evidence-only, and the central acceptance check — that no SDLE product
behavior changed — is met absolutely: `git diff HEAD --stat` produces no output,
so every tracked file in `scripts/`, `tests/`, `.claude/`, `.github/` and the docs
tree is byte-identical to the frozen baseline `f8fdaa04`. Nothing was created,
modified or deleted outside the plan's declared file scope, and no future-phase
artifact appeared.

All fourteen plan acceptance criteria and all four contract §6 exit criteria are
met. Every completeness claim I could count, I counted from source rather than
from the handoff, and each landed exactly: 65 CLI rows set-equal to the real
`add_parser` registrations, 183 inventory rows with zero blank cells across 14
correctly ordered subsections, 47 matrix rows covering all 31 contract §18
capabilities exactly once plus 16 `NOT_IN_S18`, 33 state fields, 13 migration
rows, 22 lint checks, 230 collected tests. Every one of the 143 pytest anchors
cited in the matrix resolves to a real collected test, and the five `NO_ANCHOR`
rows are genuine gaps I confirmed by searching the source — the exercise produced
honest negative findings rather than padding.

The suite's exit code 1 is not a T00 failure. I reproduced it myself with a
*different* victim pair, applied the plan's F1 procedure independently, and got
three clean targeted re-runs; the victim has now moved across four unrelated
tests in three contexts, which is decisive against a deterministic defect. The
raw exit code is reported unaltered in the baseline rather than laundered into a
green claim, which is the correct treatment.

The one deliberate modification to a hash-locked control is verified in
execution: reconstructing the pre-change file from the documented patch
reproduces the recorded "before" hash byte-for-byte, mtimes show no third file
was touched, and my own 20-case payload matrix confirms the policy tables behave
identically in both path forms. The decision itself was the user's and is not
revisited here.

**T00 is COMPLETE.**
