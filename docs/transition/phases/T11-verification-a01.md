# T11 Independent Verification — Attempt 01

**Phase:** T11
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

**Range verified:** `4b1aa71..53b0733` — five commits: `97100e2` (plan), `a25c930` (M1),
`17f7ea2` (M2), `90e52d0` (M3), `42c7d5b` (M4), `53b0733` (M5–M8, HEAD).
**Prior-phase baseline:** `11363d9` (T10 implementation, verified PASS at `4b1aa71`).
**Product baseline:** `f8fdaa0`. **Branch:** `transition/workitem-v1`.
**Working tree at verification:** only `.claude/settings.local.json` dirty (out of scope,
pre-existing, and byte-identical across the range — `git diff --name-only 4b1aa71 53b0733 --
.claude/settings.local.json` is empty).

> The handoff is a claim set, not proof. Everything below was reconstructed from the
> repository, the contract, the Git diff and command output obtained in **this** context.
> No figure is inherited. Where the handoff and the repository disagreed, the repository won.

---

## 0. The declared evidence gap — CLOSED

The handoff declared one outstanding gap: **a single-process full-suite run was NOT_RUN**,
because the Bash tool caps a foreground command at 600 s, the suite takes ~26 min, and four
prior backgrounded attempts truncated mid-flight. It ran six foreground segments instead and
proved them exhaustive, but stated plainly that six segments are not one process and that its
1710-test corroborating figure was **inherited, not re-observed**.

**I obtained the single-process run.** Backgrounding `rtk proxy "python -m pytest -q
-p no:cacheprovider --junitxml=<scratch>/full_v01.xml"` and waiting on the output file rather
than on a completion signal:

```text
1731 passed in 1599.58s (0:26:39)
RAWEXIT=0
```

Independently parsed from the run's own `--junitxml` (not from the summary line, and with no
pipe between the command and `$?`):

```text
tests=1731  failures=0  errors=0  skipped=0
unique testcase ids = 1731
suite time = 1599.184 s
```

`1731 tests == 1731 unique ids == 1731 passed`, zero skips, zero xfails, raw exit 0, **one
process, one ordering**. The cross-file-ordering residual the handoff named is therefore
resolved, and the segmented evidence is no longer load-bearing. I did **not** inherit the 1710
figure and make no claim about it.

`ENVIRONMENT_FLAKE` is VOID; no failure occurred, so the procedure was never reachable.

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** integration files, `.claude/settings.json`, `.gitignore` byte-identical to `4b1aa71` | **MET** | `git diff --stat 4b1aa71 53b0733 -- <5 paths>` prints nothing |
| **A2** no `"legacy"` rung; `bind_workitem` returns only a bound `Paths` | **MET** | Regex over `sdle.py`: `0` occurrences of `"legacy"`/`'legacy'`. AST walk of `bind_workitem` finds **exactly one** `Return`: `return dataclass_replace(paths, workitem=decision.workitem)`; every other exit is a `raise` |
| **A3** no `paths.workitem is None` guard survives outside `Paths` and `collect_validation_findings` | **MET** | AST/line scan: `workitem is None` appears **twice** — `sdle.py:141` (`Paths.workitem_root`) and `sdle.py:3920` (`collect_validation_findings`' speculative-resolution warning, P5). Down from 14 |
| **A4** legacy-only repo recovers via `workitem create` → `migrate-workflow` | **MET, reproduced end-to-end** | Built a legacy-only tree (`.workflow/state.json` at `workflow_version 1.13`, no `workitems/`), drove the real CLI as a subprocess: `workitem create` → id `recovered-work` (exit 0); `migrate-workflow --workitem recovered-work` → exit 0, `migration_steps ["1.13->1.14","1.14->1.15","1.15->1.16","1.16->1.17"]`, target `workitems/recovered-work/.sdle/state.json`, migration evidence written |
| **A5** every non-`RUNTIME_FREE` command refuses `workitem_required` naming both steps in order | **MET, reproduced** | `header`, `drift check`, `doctor` on the legacy-only tree: exit **1**, `reason=workitem_required`, message names `` `workitem create --name <name>` `` as step 1 and `` `migrate-workflow --workitem <id>` `` as step 2 **in that order**, and `data.legacy_state` carries the path |
| **A6** `.workflow/` SHA-256-identical after any `migrate-workflow` | **MET** | SHA-256 map of every file under `.workflow/` taken before and after a successful migration — identical. Interruption at all nine write points covered by `test_t11_n7_an_interruption_at_any_write_point_is_recoverable`, passing in my full-suite run |
| **A7** `PROJECT_ROOT_MARKERS` keeps `(".workflow","state.json")`; `.workflow` in `FENCED` and `SDLE_OWNED_PREFIXES`; `.gitignore` unchanged | **MET** | `PROJECT_ROOT_MARKERS` = `("workitems","index.md"), (".workflow","state.json"), (".git",), (".sdle","config.json")`. `FENCED` byte-identical to baseline. `SDLE_OWNED_PREFIXES` = `.workflow/`, **`.sdle/`**, `workitems/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/`. `.gitignore` in A1's empty diff |
| **A8** all 16 §17 hardening tests exist and pass | **MET** | §17's mandatory list parsed programmatically = **16 bullets** (confirmed; the plan's E31 is right and an earlier "17" claim was wrong). N1–N11, N13–N16 are named `test_t11_n*` functions in `tests/test_units_hardening.py`; **N12 lives in `test_units_governance.py`** (eight `test_n12_*` functions), declared at the top of the hardening file. All pass in the single-process run |
| **A9** new refusals leave `audit.md` byte-identical | **MET, with the handoff's declared PD-F exception, which I confirmed is pre-existing** | Reproduced live on a real WorkItem runtime: `gate approve` ×4 real gate keys (`not_at_gate`, exit 1), `skip` (`not_failed`, exit 1), `gate omit`, `advance` — `audit.md` SHA-256 unchanged after every one; `audit verify` exit **0**. PD-F: `branch_guard`'s stale-ack path appends `branch_ack_stale` then refuses. I compared against `git show 4b1aa71:scripts/sdle.py` — the **baseline already** appended `branch_mismatch_guard`, saved state, then raised. The shape is pre-existing, not introduced |
| **A10** `lint-skill` = 43 checks, `failed: []` | **MET** | `python scripts/sdle.py lint-skill` → exit **0**, `ok true`, `data.checks` length **43**, `data.failed` `[]`, every check `passed: true`, including the new `documentation_set_is_present` |
| **A11** v1.17 everywhere; 17 migration rows | **MET** | `version_string_consistent` passes: *"all 7 locations report v1.17"*. `MIGRATIONS` has **17** rows ending `("1.16","1.17",_mig_1_16)`; `constants.version_chain` length **17**; `CURRENT_VERSION = "1.17"` |
| **A12** nine documentation targets exist and are non-empty | **MET** | All nine present and non-empty; the six new directories each hold a README of 4.9–10.0 KB. `documentation_set_is_present` message: *"all 9 documentation targets present"* |
| **A13** no hard risk floor changed | **MET** | `test_n9_no_built_in_floor_was_lowered_or_removed` and `test_n9_the_first_six_floor_rules_keep_their_positions` pass in the full run; the governance downgrade path adds evidence only (see A16/B3 below) |
| **A14** every §18 PRESERVE row has a named passing test | **MET** | Extracted all 45 `file.py::test_name` references from handoff §4.1 and resolved each by AST against the test tree: **0 missing**. All pass in the single-process run |
| **A15** 21 registry phases, 5 flows, GREENFIELD unchanged | **MET** | `sdle.py constants` → `phase_sequence` 21, `flows` 5, `gate_phases` 8 |
| **A16** exit codes 0/1/2/3 keep their meanings | **MET** | Observed live: refusals exit **1** (`workitem_required`, `not_at_gate`, `not_failed`, `workitem_ambiguous`, `workitem_exists`, `workitem_unknown`); usage errors exit **2** (`workitem_flag_required`, argparse); integrity exit **3** (`index_malformed` per N3, `legacy_state_missing`/`legacy_state_invalid` in `cmd_migrate_workflow`). Reason-string diff vs baseline below |
| **A17** `no_powershell_only_cmdlets`; both launchers intact | **MET** | Check passes inside the 43; `test_t11_n16_both_launchers_agree_on_the_interpreter_contract` passes |
| **A18** no product subagent gained a write tool | **MET** | The three `product_agents_*` checks pass inside the 43 |
| **A19** ADR-008 carries all 26 findings | **MET, re-derived by parsing, not by reading prose** | Parsed ADR-008 §7's table: **26 rows**, ids `TR1…TR26` with **no duplicate and no gap**; dispositions **20 FIXED / 4 DEFERRED / 2 NOT-A-DEFECT**. Matches §9 of the plan exactly |
| **A20** both transcript pins non-vacuous | **MET, proven by my own mutation, on a different transcript** | See "Regression evidence" below |
| **A21** no transition control-plane file modified/deleted | **MET** | `git diff --name-only 4b1aa71 53b0733 -- docs/transition/transition.md docs/transition/phases/T0* docs/transition/phases/T10* docs/transition/baseline.md docs/transition/templates/` is **empty**. `tools/transition/` and `.claude/agents/sdle-transition-*` untouched. Only `RESUME.md`, `progress.md` and new `T11-*` artifacts moved; the four modified `.claude/agents/sdle-{code,design,security}-review.md` / `sdle-discovery.md` are **product** agents (TR4) |
| **A22** full suite green, `collected == passed`, junit-captured, raw exit read with no pipe | **MET, single process** | §0 |

---

## Regression evidence

### 1. The migration path still works after the legacy runtime was removed (§17's gate)

Driven end to end through the real CLI as subprocesses, not through fixtures:

* `PROJECT_ROOT_MARKERS` still contains `(".workflow", "state.json")` — read directly out of
  the source. Without it the legacy-only repository cannot be *discovered* and the recovery
  path dies; this is the single most dangerous "cleanup" a later reader could make.
* A tree containing **only** `.workflow/state.json` (`workflow_version 1.13`) plus `.git`:
  * `header` / `drift check` / `doctor` → exit **1**, `workitem_required`, message naming
    `workitem create` then `migrate-workflow`, **in that order**, with `data.legacy_state`;
  * `workitem create --name "Recovered Work"` → exit 0, id `recovered-work`;
  * `migrate-workflow --workitem recovered-work` → exit 0, chain `1.13→1.14→1.15→1.16→1.17`,
    runtime at `workitems/recovered-work/.sdle/state.json`, migration evidence written;
  * every file under `.workflow/` **SHA-256-identical** before and after;
  * afterwards `validate` reports `runtime_state_outside_workitem` (P5) naming the archive and
    the remedy.

`validate` on the *pre*-migration legacy-only tree reports `active_workitem_unresolved` and
does not mention the legacy runtime — see NB-4.

### 2. The fence fix — three claims checked, then attacked

**Claim (a): `in_dir` unchanged.** Its `return` expression is unchanged; a 15-line docstring
was added. Proven by AST: with docstrings stripped from both sides, `ast.dump` of the baseline
and current `in_dir` bodies are **identical**. The handoff's phrase "character for character"
is therefore imprecise (NB-5), but the property that matters — behaviour — holds, and
`test_n28` asserts exactly that stronger structural property itself
(`_without_docstring(before["in_dir"]) == _without_docstring(defs["in_dir"])`).

**Claim (b): `untrusted_read` still calls `in_dir`.** Confirmed by AST call-graph:
`in_dir` is called by `{fenced_target, untrusted_read}`. `untrusted_read`, `SCANNED`, `FENCED`
and `SPECS_CARVE_OUT` are all **byte-identical** to `4b1aa71`.

**Claim (c): only `write_fence` calls `fenced_target`.** Confirmed:
`fenced_target` ← `{write_fence}`; `normalized` ← `{write_fence}`.
Definition-level delta of `hooks.py` vs `4b1aa71`: changed `{FENCE_REASONS, in_dir,
write_fence}`, added `{fenced_target, normalized}`, removed `{}` — exactly the declared set.

**Driving the registered hook as a subprocess** (`python .claude/hooks/hooks.py write-fence`,
`CLAUDE_PROJECT_DIR` = repo root), 27 cases:

| Path shape | Result |
|---|---|
| `workitems/wi-1/.sdle/state.json`, `.workflow/state.json`, `requirements/…`, `guidance/…` — and each of the first two in absolute form | **DENY** (all 6) |
| `docs/workitems/README.md` — relative **and** absolute | **PERMIT** (both) |
| `docs/requirements/x.md`, `src/guidance/x.py`, `workitems-archive/x.md`, `README.md` | **PERMIT** |
| `workitems/wi-1/specs/001-x/spec.md` (carve-out) | **PERMIT** |

**Routing-around attempts, all repelled:**

| Attack | Result |
|---|---|
| `workitems/wi-1/specs/../.sdle/state.json` (the T04 N-3 bypass) | **DENY** — was `PERMIT(carve-out)` at `4b1aa71`; D7 genuinely closes it |
| same, absolute form | **DENY** |
| `docs/../workitems/wi-1/.sdle/state.json` | **DENY** |
| `workitems/wi-1/../../workitems/wi-2/.sdle/state.json` | **DENY** |
| `./workitems/wi-1/.sdle/state.json`, `workitems/wi-1/specs/./../.sdle/state.json` | **DENY** |
| backslash forms of both the absolute and relative owned paths | **DENY** |
| lower-case drive letter `d:/…/workitems/…` and fully upper-cased root | **DENY** (falls through to the loose test — fail-closed) |
| `C:/other/workitems/wi/.sdle/state.json`, `/tmp/other/workitems/wi/x` | **DENY** (loose fallback preserved) |
| `WorkItems/wi-1/.sdle/state.json` | PERMIT — but **also PERMIT at `4b1aa71`**; pre-existing case-sensitivity, not a T11 delta |
| `../otherrepo/workitems/wi/.sdle/state.json` | PERMIT — **DENY at `4b1aa71`**. A genuine, undeclared narrowing: see NB-3 |

Each negative was re-derived against the baseline module (`git show 4b1aa71:.claude/hooks/hooks.py`,
executed in-process) so that "narrower" and "pre-existing" are distinguished by observation
rather than by argument.

### 3. §17's removals happened, and its Preserve list survived

**Removed** — `.workflow/` as a *runtime* (rung 6 gone, no `"legacy"` literal, no bound
`Paths` with `workitem is None`); the repo-global runtime lock (`Paths.lock_file` is
`runtime/lock`, and `runtime` is WorkItem-scoped for every bound `Paths`); WorkItem-less
initialization (`for_init` → `legacy_workflow_present`; reproduced: a plain command refuses);
`current_feature_id` as identity (survives only in migration rows); the fixed-18-phase and
fixed-8-gate assumptions (21-phase registry, 5 flows, policy-derived gates — pinned, not
re-removed); the obsolete constant `ACTIVE_CONTEXT_SETTERS`, now **enforced** by
`write_active_context` rather than deleted; all 12 dual-path carve-outs.

**Preserved** — the §18 matrix: all 45 named tests resolve and pass (A14). `.workflow` still a
project-root marker, still fenced, still in `SDLE_OWNED_PREFIXES`, still gitignored;
`cmd_migrate_workflow` intact with every refusal; `legacy_state_present`;
`runtime_state_outside_workitem`.

**Silent-guardrail-loss sweep.** I diffed every `raise Refused/IntegrityError/UsageError`
reason string against `4b1aa71`:

* **Added:** `active_context_unwritable` (D8's `OSError` hardening), `workitem_flag_required` (D8).
* **Removed:** `discovery_workitem_required`, `governance_workitem_required` (both folded into
  the ladder's `workitem_required` by D4 — verified live: `governance show` and `discovery show`
  on a zero-WorkItem repository both refuse `workitem_required` at exit **1**, while
  `governance policy` and `discovery schema` still succeed at exit 0), and the `UsageError`
  variant of `workitem_required` (renamed to `workitem_flag_required` by D8, which is the point).

No refusal was converted to a warning. No exit code changed meaning. The two retired reason
strings are declared in the handoff §3 M1 — but ADR-008 does not record them and ADR-005 still
lists one: NB-2.

### 4. The 16 mandatory hardening tests, and whether the 38 pass vacuously

§17's list parsed programmatically = **16 bullets**, each mapped to a named, passing test
(A8). `tests/test_units_hardening.py`: **38 collected** (31 functions, 2 parametrised),
**178 assertions**, minimum **1** per test, **zero** assertions of a vacuous shape
(`assert True`, bare `isinstance`, no-assert bodies). I read every test with ≤2 assertions —
each asserts a real property (exact write-sequence equality; `EXIT_INTEGRITY` + `index_malformed`;
the `os.sep` needle guarded by `assert occurrences`; the lint-check delegation).

Four scenarios are implemented differently from §17's wording. Each is declared in its own test
docstring **and** in ADR-008 §5.1, with the property asserted instead — corrupt-audit locates
the tamper rather than re-verifying per command; a partial temp is proven *inert* rather than
swept; a *materially invalid* baseline blocks ITERATIVE while a *stale* one can never be relied
on silently (sweeping invalidation would violate §26 item 22); execution-ids are not globally
unique by contract, so isolation is asserted against the WorkItem id, which is. I accept all
four: each names the true property rather than narrowing to a weaker one, and the fourth
explicitly retired an assertion whose outcome turned on the clock.

`test_t11_n16_every_emitted_path_uses_posix_separators` deliberately skips absolute paths; I
observed a native-separator absolute path in a real payload (`data.legacy_state`), consistent
with the test's declared scope but broader than the plan's wording — NB-6.

### 5. Refusals leave `audit.md` byte-identical

Reproduced on a real initialised WorkItem runtime (see A9). Every refusal left the ledger's
SHA-256 unchanged and `audit verify` exited **0** afterwards.

### 6. The transcript pins — converted, and verified by my own mutation

The conversion is `apply_dry_run_substitutions(at_baseline(f)) == here(f)`, with a **17-pair
enumerated literal list** in `conftest.py` (no regex, no computed rewrite), consumed by both
pins from one place.

I re-executed the comparison **outside pytest**, in-process, against both baselines:

| Pin | Files | Match | Pairs used |
|---|---|---|---|
| `test_n20_…` vs `adbdc5e` | 10/10 | **True** | 17/17, set-equal |
| `test_n27_…` vs `e1cf341` | 10/10 | **True** | 17/17, set-equal |

Both baselines independently produce the **identical** current bytes — a joint constraint
strictly stronger than either pin alone.

**My own mutation, on a transcript the implementer did not use**
(`docs/dry-runs/07-audit-integrity-and-session-lock.md`, whereas the handoff used `01`), and
performed **in memory** so no repository file was touched:

* equality holds before mutation: **True**;
* appending one undeclared line: **fails**;
* a single-token change (`audit.md` → `audit.MD`, one occurrence): **fails**;
* removing one pair from the declared set: the file comparison **fails**.

**No relaxation on the current-file side.** `here(f)` is still compared by exact equality
against one fixed, deterministic target string; only the target moved, once, by an enumerated
amount. This is a real conversion, not a re-baseline, and it is not vacuous. The plan's F7
failure mode (a wildcard absorbing a real edit) is structurally impossible here.

I applied T10's lesson — a replacement called "stronger" whose coverage had actually narrowed —
and looked for narrowing specifically: the file-list comparison, the `len(numbered) == 9` guard,
the "baseline must be reachable" non-vacuity guard and the whole-directory glob are all still
present, and the `used == {…}` exact-set equality is a property the byte pin never had.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --junitxml=<scratch>/full_v01.xml"` (single process, backgrounded, waited on the output file) | **1731 passed in 1599.58s**, `RAWEXIT=0` | Summary line **located** in the output, not trusted from a completion signal |
| The same run's junit XML, parsed independently | `tests=1731 failures=0 errors=0 skipped=0`; **1731 unique testcase ids** | `collected == run == passed`; nothing hidden in a skip or xfail |
| `python -m pytest tests/test_units_hardening.py --collect-only -q` | **38 tests collected** | Confirms the handoff's 38 |
| `python scripts/sdle.py lint-skill` | exit **0** | Raw exit read with no pipe |
| The same output parsed | **43 checks**, all `passed: true`, `failed: []` | Includes `documentation_set_is_present` |
| `python tools/transition/validate.py` | exit **0** | `TRANSITION_VALID: complete=11/12 next=T11` |
| `python scripts/sdle.py constants` | `phase_sequence` **21**, `flows` **5**, `gate_phases` **8**, `version_chain` **17** | A11, A15 |
| `git diff --stat 4b1aa71 53b0733 -- <A1's five paths>` | **empty** | A1 |
| ADR-008 §7 table parsed | **26 rows**, 20/4/2, no duplicate, no gap | A19 |
| Live CLI reproductions (legacy migration, refusal ledger, ambiguity, kebab-case, auto-generate) | as tabulated above | Subprocesses against the real `scripts/sdle.py` |
| Registered write-fence hook driven as a subprocess | 27 cases | Tabulated above |
| **Python 3.11** | **NOT_RUN** | No 3.11 interpreter on this host. Observed: CPython **3.13.0**, win32. No outcome predicted |
| **CI (`ubuntu-latest` / `windows-latest`)** | **UNKNOWN** | Never executed at any point in this migration. No platform result claimed that I did not obtain |

**Guard refusals, declared verbatim, not routed around.** `tools/transition/agent_guard.py
verifier` refused three of my Bash calls with:

```text
SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape
```

The cause each time was a token inside my **own** analysis payload, not an attempt to mutate
anything: `v>1` and `len(cells)>1` (read as output redirection by the tripwire) and a local
variable named `rm`. I renamed my own tokens and re-ran. I did not patch, re-sign or bypass the
guard, and I used pytest's own `--junitxml` rather than `>` throughout.

---

## Future-phase leakage check

There is no T12; the risk is the inverse — the §1.4 post-transition control-plane cleanup
leaking *into* T11. **It did not.** `docs/transition/transition.md`, `docs/transition/baseline.md`,
`docs/transition/templates/`, every `T00…T10-*.md`, all of `tools/transition/` and every
`.claude/agents/sdle-transition-*` are untouched across `4b1aa71..53b0733`. The control plane
did not delete itself while the transition was executing.

Scope exclusions hold: no new lifecycle phase, no ninth gate (`gate_phases` = 8, template
`approvals` = 8), no `sdle.py` module split, no YAML dependency, no §27 item. `sdle.py` imports
are standard-library only (`argparse, copy, dataclasses, datetime, hashlib, json, os, pathlib,
re, shutil, subprocess, sys, tempfile, time`) — no DB, no MCP, no web framework.

---

## Test weakening / deletion check

Assertion delta per test file, computed from `git diff --unified=0` over `tests/`:

| File | `assert` removed | `assert` added |
|---|---:|---:|
| `test_units_hardening.py` (new) | 0 | 203 |
| `test_units_transitions.py` | 1 | 69 |
| `test_units_governance.py` | 3 | 59 |
| `test_units_gate_policy.py` | 14 | 49 |
| `test_units_workitem_runtime.py` | 7 | 43 |
| `test_units_speckit_binding.py` | 7 | 39 |
| `test_units_capabilities.py` | 7 | 25 |
| `test_units_flow_model.py` | 14 | 24 |
| `test_units_workitem_resolution.py` | 3 | 21 |
| `test_lint_skill.py` | 0 | 14 |
| `test_hooks.py` | 0 | 11 |
| `test_units_repo_config.py` | 3 | 11 |
| `test_units_artifact_review.py` | 2 | 5 |
| `test_units_state.py` | 4 | 4 |
| `conftest.py` | 0 | 2 |

**Fifteen test functions disappeared by name.** Every one maps to a declared X row and has a
successor: X1 (2), X2 + PD-1 (5), X3 (3), X4 (1), X6 (1), X10 (2), X11 (1), PD-B (1).
**No function that survived lost a single assertion** — I compared per-function assertion counts
between `4b1aa71` and HEAD across the five most-affected files and found **zero** regressions.

Two successors read in full to check for narrowing:

* `test_n22_the_legacy_rung_and_migrate_workflow_are_untouched` →
  `test_n22_migrate_workflow_still_leaves_the_legacy_tree_untouched`. The B9 half (`after ==
  before`, "migrate-workflow must never mutate .workflow/") is kept **verbatim**; the inverted
  half gained an assertion (it now checks `EXIT_REFUSED` **and** `reason == "workitem_required"`
  where the original only checked `EXIT_OK`).
* `test_n28_the_hooks_are_byte_identical`. `_hooks_top_level` now captures `ast.Import`,
  `ast.ImportFrom` and the module docstring, with `assert "__doc__" in before` and
  `assert any(k.startswith("import:") …)` guarding vacuity — this is T10 NB-1's own written
  remedy and a **strict** strengthening. The three exempted definitions are pinned by explicit
  property assertions instead of bytes: `FENCED` frozen to its four names, `FENCE_REASONS`
  set-equal to `FENCED` with per-reason content assertions, `write_fence` required to call
  `normalized(` and `fenced_target(` and **forbidden** to call `in_dir(`, `fenced_target`
  required to keep both the anchor and the fallback, `in_dir` proven changed only in prose, and
  `untrusted_read` asserted still loose.

`.gitignore` and `.claude/settings.json` unchanged, so the byte-identity pins that ride on them
are untouched. No assertion anywhere was relaxed to an `in` / `>=` shape. **No test was weakened
to make T11 pass.**

---

## Deterministic guardrail check

* **The core refuses; it does not warn.** Every new failure path is a `Refused`/`UsageError`/
  `IntegrityError` with reason, message and structured `data` — observed live for
  `workitem_required`, `workitem_ambiguous`, `workitem_flag_required`, `feature_ambiguous`,
  `not_at_gate`, `not_failed`, `workitem_exists`, `workitem_unknown`.
* **Single writer.** No new `write_atomic` caller exists: the set of functions calling
  `write_atomic` is **identical** to `4b1aa71`. `append_audit` gained call sites, not
  competitors. No second writer of `state.json` or `audit.md`.
* **Claude cannot lower a deterministic floor.** `governance_downgrade` and
  `_record_governance_downgrade_audit` contain **no `raise` at all** — they emit evidence
  (`governance_downgraded`, `governance_sha256`, `governance_downgrade` in the omission
  record) and never grant permission. No floor value moved. T09 NB-2 therefore stays **fixed as
  evidence, not as refusal**, exactly as required.
* **The ladder never guesses.** D1 removed a rung and added no tie-break. D10 extends
  no-guessing into Spec Kit discovery: more than one candidate in a tier now refuses
  `feature_ambiguous` and lists them.
* **Fail-open sweep.** The one declared fail-open with no other owner (T03-1) is now closed:
  `pending_branch_ack` records *which* branch was acknowledged and the second step must match;
  a mismatch re-arms and refuses instead of proceeding. The `branch_ack_stale` audit-then-refuse
  shape is PD-F, and I confirmed against the baseline source that it is the guard's
  **pre-existing** shape, not a new one.
* **Exit codes / JSON on stdout** — unchanged, observed.
* **Invariants 1–8** hold: no gate delegated to a subagent (the three `product_agents_*` lint
  checks pass), no second writer, gate content still displayed in conversation, SpecKit opacity
  untouched.

---

## State / audit / evidence integrity check

* State schema moved by **exactly one field**: `pending_branch_ack` added, nothing removed,
  `approvals` still 8 keys, `workflow_version` `1.16 → 1.17`. The `templates/state.json` diff is
  precisely those two lines.
* `test_t11_the_state_template_changed_only_as_declared` pins it by declared substitution
  against `4b1aa71` with `assert expected.count(old) == 1` per pair plus a structural
  cross-check — a **third** change anywhere in the file still fails. Strictly more auditable
  than a re-baseline.
* Migration chain: 17 rows, `1.16 → 1.17` present with a matching `MIGRATIONS` step; the
  1.13→1.17 chain executed live during the legacy-migration reproduction.
* Audit chain: refusals leave `audit.md` byte-identical; `audit verify` exit 0 after the whole
  refusal sequence; the migrated WorkItem's ledger verifies.
* Evidence: `migrate-workflow` wrote `workitems/<id>/.sdle/evidence/migration-<exec>.json` with
  `legacy_state_sha` and the legacy audit fingerprint.

---

## Cross-platform / path handling check

* Emitted **repository-relative** paths use `/`; every `os.sep` occurrence in the engine is a
  normalisation *into* `/`, asserted with a non-vacuity guard.
* `write_atomic` is the only text writer and pins `newline="\n"`; the test additionally asserts
  no `.write_text(` / `.write_bytes(` exists anywhere in `sdle.py`.
* `no_powershell_only_cmdlets` passes; both launchers exist and agree on `SDLE_PYTHON`, the
  3.11 floor, `uv` and the target, and neither hard-codes the other platform's interpreter.
* Baseline comparisons in tests normalise CRLF→LF (`git show` emits LF, the working tree is
  CRLF) — I confirmed this in `at_t11_hooks_baseline`, `at_t11_template_baseline` and the
  transcript helpers, and my own out-of-pytest re-derivation applied the same normalisation and
  matched.
* **Python 3.11 NOT_RUN; CI UNKNOWN.** `test_t11_n16_what_this_host_could_not_observe_is_not_asserted`
  encodes the absence in the suite itself. The honest V1 statement in ADR-008 §6 — written to be
  cross-platform, mechanically checked for platform-only constructs, executed only on Windows /
  CPython 3.13 — matches what I observed and must not be softened.

---

## Artifact review/SHA freshness check

* `governance_sha256` now fingerprints the governance record an omission was derived from, and
  `governance_downgrade` carries the whole downgrade block — both flow into the omission
  evidence and the audit event. Neither adds a writer, a command, a state field or a gate
  (verified: command set **identical** to `4b1aa71`; state fields +1, and that one is D13's;
  `gate_phases` 8; `write_atomic` callers identical).
* `baseline_commit` added to the baseline refusal `data` — same class, same conclusion.
* Artifact SHA / stale-review invalidation rows of the §18 matrix each have a named passing
  test (A14), including
  `test_a_one_byte_edit_after_review_blocks_approval_until_re_review`.
* Governed transition artifacts: `docs/transition/transition.md`, `baseline.md`, `templates/`
  and every T00–T10 artifact are byte-unchanged across the range; no re-signing occurred; no
  `control-plane.sha256` exists in this repository (pre-existing, out of T11's scope).

---

## §26 definition of done — the migration's terminal claim

Checked item by item against the shipped engine. Live observations are marked **[obs]**.

| # | Item | Status |
|---|---|---|
| 1 | `start workflow` entry point | HOLDS — `SKILL.md` bootstrap intact; integration 01 byte-identical |
| 2 | WorkItem is the primary V1 orchestration unit | HOLDS — **[obs]** every non-`RUNTIME_FREE` command binds one or refuses |
| 3 | Names become unique kebab-case directories | HOLDS — **[obs]** `"  Payment   API!!  "` → `payment-api`; a re-use refuses `workitem_exists` |
| 4 | `auto generate` mints `WI-<name>-<datetime>` | HOLDS — **[obs]** `WI-login-flow-20260907T193444Z`, matching `AUTO_ID_RE` |
| 5 | `workitems/index.md` append-only by behavior | HOLDS — **[obs]** rows accumulate; `read_index` refuses `index_malformed` (exit 3) and never rewrites |
| 6 | State/audit/evidence isolated per WorkItem | HOLDS — N2 asserts byte-identity of WI-B's whole `.sdle/` across a full WI-A run |
| 7 | Repository-global `.workflow/` is no longer normal runtime | **HOLDS — the phase's core claim, reproduced.** Rung 6 gone; no `"legacy"` literal; every bound `Paths` names a WorkItem; `.workflow/` is a migration source and a root marker only |
| 8 | Two WorkItems on different branches/worktrees | HOLDS — N1 drives both worktrees to completion with independent verifying ledgers |
| 9 | Same-WorkItem parallel development unsupported | HOLDS — WorkItem-local session lock |
| 10 | Launch from WorkItem, `workitems/`, repo root or elsewhere | HOLDS — resolution rungs 1–5 intact; `workitem_unregistered` still refuses rather than binding a neighbour |
| 11 | Ambiguity asks instead of guessing | HOLDS — **[obs]** two registered, none named → exit 1, `workitem_ambiguous`, both candidates listed, **no pick** |
| 12 | Spec Kit operates in the active WorkItem context | HOLDS — tier 1 is `workitems/<id>/specs/` and takes precedence |
| 13 | Native Spec Kit artifacts not duplicated | HOLDS — `SPECS_CARVE_OUT` preserved byte-identical |
| 14 | Requirements quality explicit | HOLDS — T05 |
| 15 | Flow classification explicit | HOLDS — 5 flows, `flow_selected` audited |
| 16 | Risk hybrid: AI proposes, policy decides | HOLDS — T06/T09 |
| 17 | Hard floors cannot be lowered by the model | HOLDS — A13; the downgrade path **cannot raise** |
| 18–20 | Greenfield / iterative / defect+hotfix flows work | HOLDS — 5 flows element-wise unchanged; integration files byte-identical |
| 21–22 | Brownfield baseline reusable, not repeated by default | HOLDS — and N11's declared divergence exists **because** item 22 forbids sweeping invalidation |
| 23 | Design/security gates policy-driven | HOLDS — T09 |
| 24 | Human gates evidenced | HOLDS — omission evidence now also carries `governance_sha256` |
| 25–27 | Review/validation bound to the exact SHA; stale review invalidated | HOLDS — A14 rows, each with a passing test |
| 28 | Audit append-only / tamper-evident | HOLDS — **[obs]** `audit verify` exit 0; N5 locates a tamper at entry 2 |
| 29 | Drift functional | HOLDS — integration 04 |
| 30 | Secrets / test evidence functional | HOLDS — `test_hooks.py`, integration 06 |
| 31 | Resume after fresh Claude context | HOLDS — N14/N15 reconstruct from disk alone through a fresh subprocess, with `audit.md` byte-identical across the reconstruction |
| 32–35 | No DB, no MCP, no release model, no web UI | HOLDS — **[obs]** stdlib-only imports; no `sqlite`/`mcp`/`flask`/`fastapi`/release tokens |
| 36 | Deterministic guardrails not **silently** lost | **HOLDS, with one recorded qualification.** The fence narrowed deliberately, is documented in three places, and is pinned by 21 subprocess-driven cases — not silent. One sub-case of that narrowing is undeclared: NB-3 |
| 37 | Suite green on supported platforms | **PARTIAL, and honestly stated.** Green in a single process on Windows / CPython 3.13.0: 1731/1731. Linux and Python 3.11 **NOT_RUN**; CI **UNKNOWN**. The engine asserts the absence rather than implying coverage |
| 38 | Core suitable for a future MCP adapter | HOLDS — JSON on stdout, exit-code contract, no I/O coupling introduced |
| 39 | Every completed phase has plan + handoff + PASS verification | HOLDS — `validate.py` exit 0 at `complete=11/12`; this artifact closes the twelfth |
| 40 | Transition resumes from repository evidence only | HOLDS — eight checkpoints plus `RESUME.md`, now current (TR26) |
| 41 | Migration agents never substitute for human approvals or core authority | HOLDS — and demonstrated: the implementer hit a permission wall at M7, **wrote a blocker and stopped** rather than writing the file with another tool |

Item 37 is the only one not fully evidenced, it is not evidenceable on this host, and it is
declared rather than glossed. Every other item holds.

---

## Findings

### Blocking

**None.**

### Non-blocking

**NB-1 — six new unchecked restatements of the version constant (invariant 7).**
Each of the six new documentation READMEs carries `**Applies to:** SDLE v1.17` on line 3.
`_check_version_consistency` reads seven locations and **none of them is one of these six**, so
at the next bump all six go stale silently. T11 fixed exactly this class twice in the same phase
(TR3's "four hooks", TR4's restated tool grant) and then created six new instances. The rule
already reads the Reference Guide header by the same regex shape, so the remedy is a
one-expression extension of `found` in `_check_version_consistency` (or deleting the header
line). Other `v1.1x` mentions in those files are historical ("since v1.17", "before v1.17") and
are fine.

**NB-2 — an architecture document made false by T11's own change, unrecorded.**
D4 retired `discovery_workitem_required` and `governance_workitem_required` (folded into
`workitem_required`; verified live). `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`
lines 393–397 still list `discovery_workitem_required` among "nine new refusals" and assert
"No existing refusal is removed or renamed." ADR-008 records neither retirement. The handoff
does declare them (§3 M1), so this is documentation drift, not a hidden change — but it is the
same class as TR3, which this phase fixed. Remedy: one line in ADR-008 §2 naming the two retired
reason strings and superseding ADR-005's clause.

**NB-3 — one undeclared narrowing in the write fence.**
`fenced_target` anchors every **non-absolute** path against the repository root. A relative path
that escapes the repository — `../otherrepo/workitems/wi/.sdle/state.json` — was DENIED at
`4b1aa71` and is PERMITTED now (reproduced against both module versions). The handoff's
replacement-safety statement says what is lost is "only the accidental coverage of unrelated
directories that merely share a name"; a `..`-relative path into a genuine second SDLE
repository's `workitems/` is not that. Impact is low — Claude Code delivers `file_path` as an
absolute path, the absolute form of the same target is still denied, and the engine's
choke-point refusal is the guarantee — but a guardrail change at the final milestone should have
this case in its declared set. Remedy: either treat a normalised path beginning `../` as
outside the repository and fall back to `in_dir`, or add the case to ADR-008 §5.3's
replacement-safety paragraph and to the 21 pinned cases.

**NB-4 — `validate` is silent about a legacy-only repository.**
`runtime_state_outside_workitem` is guarded by `indexed and legacy_state_present(paths)`
(`sdle.py:3845`), so with **zero** registered WorkItems and a legacy `.workflow/state.json` on
disk, `validate` reports only `active_workitem_unresolved` and never names the archive or the
two-step recovery. Plan P5 called that finding "the only automated way a user learns a legacy
runtime is still on disk". Well mitigated — every non-`RUNTIME_FREE` command refuses with the
full ordered message (reproduced) — but `validate` is precisely the command a stuck user runs.
Remedy: emit the finding whenever `legacy_state_present`, with the WorkItem count in `data`.

**NB-5 — handoff wording: `in_dir` "kept, character for character".**
A 15-line docstring was added. Behaviour is provably unchanged and `test_n28` asserts the
correct, stronger property structurally. Record-keeping only; no product impact.

**NB-6 — N16's shipped scope is narrower than the plan's wording.**
Plan N16 says "every emitted JSON path uses `/`"; the test excludes absolute paths, and I
observed a native-separator absolute path in a real payload (`data.legacy_state`). The narrowing
is declared in the test docstring and guarded against vacuity (`checked > 50`). Recorded so the
plan's wording is not later read as the shipped guarantee.

None of the six changes an acceptance criterion, weakens a test, loses a guardrail, or affects
the exit criterion. All are documentation/coverage hygiene with precise remedies, suitable for
the post-transition cleanup §1.4 permits.

### Judgements recorded, not re-opened

* **The 26-finding triage.** Re-derived by parsing ADR-008 §7: 26 rows, TR1…TR26, no duplicate,
  no gap, **20 FIXED / 4 DEFERRED / 2 NOT-A-DEFECT**. I checked **every** FIXED row against the
  code rather than the prose — the failure mode this phase already produced once, when ADR-008
  asserted TR26 FIXED while `RESUME.md` was still stale. All 20 verified in the source or by
  live reproduction: TR1 (`_hooks_top_level` captures imports + docstring, with vacuity guards),
  TR2 (no `modules/*.md` path remains in `sdle-approve.md`), TR3 (ADR-001 now says four "when
  this ADR was written, and a fifth"), TR4/TR6 (the caveat clause and the authority pointer are
  present), TR7 (audited, never refused — no `raise` on the downgrade path), TR9/TR11 (`.sdle/`
  in `SDLE_OWNED_PREFIXES`; `cmd_manifest_build` carries the ownership exclusion), TR10 + TR12
  (both reproduced through the CLI and the hook), TR13/TR14 (the only surviving `.workflow`
  mentions are a dirty-tree filter list, a migration-row description, the migration instruction
  itself and a `workflow_version` JSON key — all legitimate; zero stale runtime paths remain),
  TR15/TR16/TR17/TR18/TR21/TR22/TR24 verified in source or live, TR26 (`RESUME.md` now describes
  `complete=11/12 next=T11` and T11 as `IMPLEMENTED, NOT YET VERIFIED`).
* **Deferrals respected.** TR8 (§15's documentation review) stays **DEFERRED** as the single
  named V1 gap, with a two-step proposed shape in ADR-008 §8 — confirmed no ninth gate exists.
  TR20 was correctly resolved to DEFERRED after verification rather than assumed to fall out of
  D13, with a pinning test. TR23 and TR25 carry reasons.
* **Nine plan deviations, both claimed plan defects confirmed.**
  **PD-B: plan E15 undercounts.** At `4b1aa71`, **three** test files pin `.sdle/` as absent from
  `SDLE_OWNED_PREFIXES` — `test_units_flow_model.py:1721`, `test_units_gate_policy.py:1594` and
  `test_units_repo_config.py:1060` — not two. E15 is wrong; PD-B is correct.
  **PD-D: D10's named escape hatch does not exist.** `feature bind` registers exactly one flag,
  `--require-feature` (a `store_true`), and cannot name a feature id. The substitute remedy —
  tier 1 (`workitems/<id>/specs/`) takes precedence, so moving the directory the WorkItem owns
  resolves the ambiguity **by precedence, with SDLE still choosing nothing** — is named in the
  refusal text and in `data.remedy_tier`, and is *performed* end-to-end by
  `test_n21_the_named_remedy_is_a_real_one`. Rejecting a new `--feature-id` override was the
  right call: §9 forbids making "SDLE will not guess" negotiable.
* **The out-of-plan fence correction.** Escalated as `T11-blocker.md` with the model declining
  to write the file by another tool ("stepping around a guardrail to make the phase go green
  would be the worst possible precedent"), and recorded as decided by the user (Option A) in
  `T11-checkpoint-a01-08.md`. I cannot verify a human utterance from the repository, and I note
  that plainly; what I can verify is that the change is correct on its merits, that the fence
  now equals `SDLE_OWNED_PREFIXES` inside the repository, that `FENCED` is unchanged so
  `.workflow/` stays fenced (P6), and that 21 subprocess-driven cases pin both halves. NB-3 is
  the one sub-case not covered.
* **The two M6 product changes** add no writer, command, state field or gate — verified by
  diffing the registered command set (identical), the state template (+1 field, D13's), the
  gate count (8) and the `write_atomic` caller set (identical) against `4b1aa71`.

---

## Final result rationale

T11 was the migration's only destructive phase and its last chance to close every finding. I
verified it as if it were wrong, and it holds.

The removal is real and complete — rung 6 gone, no `"legacy"` rung literal, every bound `Paths`
names a WorkItem, all twelve dual-path carve-outs deleted, `workitem is None` down from fourteen
sites to two — and it did **not** brick the recovery path, which is the specific catastrophe
§17's own gate exists to prevent. I did not take that on trust: I built a legacy-only repository
and drove `workitem create` → `migrate-workflow` through the real CLI to a working v1.17 WorkItem
runtime, with `.workflow/` SHA-256-identical afterwards and the refusal on every other command
naming both steps in order.

The four things most likely to be wrong were each attacked rather than read. The fence fix was
driven through the registered hook as a subprocess across 27 paths, including `..` traversal,
absolute forms, case variants and foreign trees, with every negative re-derived against the
baseline module so that "narrowed" and "pre-existing" were separated by observation; it closes a
real bypass and denies exactly what the engine owns. The transcript pins were converted, not
re-baselined, and I proved them non-vacuous by my own in-memory mutation of a transcript the
implementer did not use — there is no relaxation on the current-file side at all, and the
conversion adds two properties the byte pin never had. The hardening set is 16 bullets, all
covered, 38 tests, 178 assertions, none vacuous, with four scenario divergences declared in
their own docstrings rather than silently narrowed. And every one of the 20 FIXED rows was
checked against the code, not the prose — the precise failure this phase produced once already.

The evidence gap the implementer declared is closed: I obtained the single-process full-suite
run it could not, and 1731/1731 passed with zero failures, errors and skips, raw exit 0, parsed
from the run's own junit XML.

Six non-blocking findings remain. Every one is documentation or coverage hygiene with a named
one-line remedy; none touches an acceptance criterion, weakens a test, loses a guardrail, or
bears on the exit criterion. Two of them (NB-1, NB-2) are the "one source of truth" class this
phase itself worked to close, which is worth recording precisely because a later editor will
read those documents as normative.

Item 37 of §26 — "test suite is green on supported platforms" — is the only definition-of-done
item not fully evidenced, and it is not evidenceable on this host. It is stated honestly
everywhere it appears, and the suite asserts the absence rather than implying coverage. I
predict no Linux or Python 3.11 outcome and claim no platform result I did not obtain: Python
3.11 is **NOT_RUN**, CI is **UNKNOWN**.

§17's exit criterion — *"Latest WorkItem-based requirements are the only normal runtime model
and all V1 definition-of-done checks pass"* — is met.

The single top-level result line for this artifact is declared once, in the header above: PASS.
T11 is therefore COMPLETE, and the migration closes at 12/12.
