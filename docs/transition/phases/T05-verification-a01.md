# T05 Independent Verification — Attempt a01

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary (contract §11)
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Everything below was re-derived by a command run in **this** context. Where a figure disagrees with the handoff, the figure here is the one that was observed.

Commit under verification: **`475795a`** ("T05: introduce the repository .sdle boundary (IMPLEMENTED, NOT YET VERIFIED)"), which is HEAD on `transition/workitem-v1`.
Rollback / prior-phase baseline: **`7b054ee`**. Product baseline: `f8fdaa0`.
Host interpreter: **Python 3.13.0**. Python 3.11 and CI: **NOT_RUN / UNKNOWN**; no outcome predicted.

## Why this phase needed a different verification shape

§11's exit criterion is *"repository-global configuration exists independently from WorkItem runtime state, with no lifecycle behavior change"*, and §11 forbids moving lifecycle rules yet. Most of the correctness argument is therefore the **absence** of change, which admits two opposite failure modes. Both were checked separately:

1. **Something changed that should not have.** Covered by the byte-identity, AST, diff-scope and `lint-skill` evidence below.
2. **Nothing changed because nothing works.** A green suite would also be green for scaffolding nothing reads. So `config init` / `config show` were driven **through the real CLI as a subprocess**, both leak detectors were fired on **planted violations built by this verifier** (not by the shipped tests), and the four source-level containment detectors were **mutation-tested** against deliberately broken copies of `sdle.py` held in memory. A green suite was treated as necessary and not sufficient.

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** full suite | **PASS** | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` in the actual working tree, unpiped, raw exit read directly: **`569 passed in 645.35s (0:10:45)`, `RAW_EXIT=0`**. `grep -c "short test summary"` over the captured run = **0**, so zero skips, xfails and errors. `--collect-only` = **`569 tests collected in 0.52s`**, so collected == passed. |
| **A2** suite arithmetic | **PASS** | Pristine `git archive 7b054ee` extracted to a scratch tree: `--collect-only` = **`500 tests collected in 2.79s`**. New file `tests/test_units_repo_config.py` = **69**. 500 + 69 = **569**. `tests/test_units_workitem_resolution.py` = **96** at pristine `7b054ee` and **96** now, so the one authorised edit added no test. |
| **A3** `lint-skill` | **PASS** | Raw exit **0**; `grep -c "PASS"` = **22**, `"failed": []`; `Parsed 19 phases, 8 gates, 15 migration rows`; `all four locations report v1.15`. All 22 check names enumerated and none is new. |
| **A4** `validate.py` | **PASS** | `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** (this also re-verifies `control-plane.sha256`). |
| **A5** must-not-change set | **PASS** | `git diff --exit-code 7b054ee HEAD -- .claude/ .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ docs/architecture/ADR-001-deterministic-core.md tools/ tests/conftest.py` → **exit 0**. Note this is *wider* than A5 as written: the whole of `.claude/` and `tests/conftest.py` were included. |
| **A6** no schema change | **PASS** | `sdle.CURRENT_VERSION == "1.15"`; `len(sdle.MIGRATIONS) == 15`; `templates/state.json` inside the A5 exit-0 set; `lint-skill` reports 15 migration rows and v1.15 at all four locations. |
| **A7** byte-identity of the guardrails | **PASS** | AST `get_source_segment` extract-and-compare of `git show 7b054ee:scripts/sdle.py` against the working file: all **19** named definitions byte-identical — `write_atomic`, `append_audit`, `save_state`, `read_state`, `touch_lock`, `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, `cmd_migrate_workflow`, `cmd_init`, `cmd_workitem_use`, `cmd_implement_preflight`, `cmd_manifest_build`, `_validate_runtime_state`, `discover_project_root`, `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`. See non-blocking finding **NB-2** on the "exactly three changed" wording. |
| **A8** `RUNTIME_FREE_COMMANDS` | **PASS** | `sorted(...)` = `['config','constants','lint-skill','migrate-workflow','sha','validate','workitem']` — **7** members, `7b054ee`'s six plus exactly `"config"`, nothing removed. |
| **A9** the repository's own `.sdle/` | **PASS** | `os.walk('.sdle')` lists exactly `config.json` plus `implementation-state/`, `policies/`, `templates/`, each holding only `.gitkeep`. No `baseline.json`. `.sdle/config.json` parses to exactly `{"configVersion": "1", "policyFormat": "json"}` and is **53 bytes**. `git check-ignore -v` over all four files exits **1** — everything is versioned. |
| **A10** reproducible boundary | **PASS** | `config init` driven as a subprocess into a fresh scratch root produced the identical relative file list and an equal parsed `config.json`. |
| **A11** §11's exit criterion, real CLI | **PASS** | Scratch repository with two registered WorkItems and no `--workitem`: `config show` exit **0**, `config init` exit **0**, `state get` exit **1** reason `workitem_ambiguous`. Zero-WorkItem repository: `config show` / `config init` exit 0 while the runtime command refuses. This is the criterion, demonstrated rather than asserted. |
| **A12** the leak detector fires both ways | **PASS** | Fired by this verifier on planted violations, outside the shipped tests. Direction 1: each of the seven derived runtime member names (`state.json`, `audit.md`, `execution.json`, `lock`, `evidence`, `implementation-manifest.md`, `completion-summary.json`) planted under `.sdle/` → `validate` exit **3**, exactly one `lifecycle_state_in_repository_config` finding, severity `error`. Direction 2: each of the five configuration member names planted under `workitems/alpha/.sdle/` **with no `state.json`** → exit **3**, exactly one `repository_config_in_workitem` finding. |
| **A13** purity | **PASS** | Covered by the shipped N13 tests (passing) and by A20's independent reproduction: the configured project's `.sdle/` is byte-identical across an entire 18-phase run, and the audit event sequence is identical to the unconfigured project's. |
| **A14** fails closed | **PASS** | Real CLI: second `config init` → exit **1** `config_exists` with nothing created; `--project-root <repo>/workitems` and `<repo>/workitems/<id>` → exit **1** `config_root_inside_workitem` for both `init` and `show`; `policyFormat: "yaml"` → exit 1 `config_malformed` naming the explicit-dependency requirement. |
| **A15** healthy repositories stay clean | **PASS** | `test_validate_stays_clean_with_no_repository_boundary`, `test_validate_stays_clean_after_config_init` and the **unmodified** `test_validate_is_clean_in_a_healthy_repository` all pass in the full run. |
| **A16** T02/T03/T04 guarantees | **PASS** | The named tests are byte-unchanged (`git diff 7b054ee HEAD -- tests/test_units_workitem_resolution.py` is a single three-line hunk at line 1346) and pass in the full run: rebinding closed set, active-context setters, healthy-repository validate, unconditional `legacy_workflow_present` refusal, `test_the_legacy_dual_read_rung_still_binds`, the five marker tests, all of `test_units_workitem.py`, all of `test_hooks.py`, all nine integration transcripts. |
| **A17** invariant 7 | **PASS** | `grep -rE 'rate_limits\|approvals\|project_name\|verbose\|max_remediation_attempts\|PHASE_SEQUENCE\|NEXT_PHASE\|PROGRESS_MAP\|ARTIFACT_OWNERSHIP\|PHASE_TO_GATE_KEY\|phase\|gate' .sdle/` → **exit 1, no matches** (the term list was widened beyond A17's to include bare `phase` and `gate`). `REPO_CONFIG_DEFAULTS` holds only the two new keys. See **NB-3** for a low-grade drift surface. |
| **A18** invariant 3 | **PASS** | `grep -E 'speckit-\|/speckit\.'` over the added (`^+`) lines of the whole T05 diff for `scripts/ tests/ README.md CLAUDE.md docs/SDLE-Reference-Guide.md ADR-002 .sdle/` → **no matches**. |
| **A19** no future-phase leakage | **PASS, one declared match confirmed** | The same grep for `risk_tier\|flow_id\|classification\|quality_gate\|risk evaluate\|gate status\|baseline validate\|discovery` matched **exactly one added line**, and it is the one the handoff declares: `tests/test_units_repo_config.py`, the docstring *"discovery returns exactly what it returned at `7b054ee`"* inside `test_the_new_marker_is_a_no_op_for_every_pre_t05_tree`. That is **project-root** discovery, not T08 brownfield discovery. Reading confirmed. |
| **A20** the differential proof | **PASS, reproduced from scratch** | Not read — re-executed. See "Regression evidence" below. |
| **A21** TP-003 | **PASS** | `git diff --name-status 7b054ee HEAD -- tests/` = **one `M`** (`test_units_workitem_resolution.py`), **zero `D`**, **zero `R`**, one `A` (`test_units_repo_config.py`). `--numstat` for the `M` is `3 0`, and the full hunk is the literal `"config"` plus a two-line comment inside `test_runtime_free_commands_is_a_closed_enumerated_set`. `tests/conftest.py` is inside the A5 exit-0 set. The other three closed-set assertions are byte-identical by construction. |
| **A22** 3.11 / CI | **RECORDED** | Python 3.11 **NOT_RUN** (host is 3.13.0); CI **NOT_RUN / UNKNOWN**. No outcome predicted. |

## Regression evidence

### A20 reproduced independently, and the declared N10 divergence pinned

The shipped differential test was **not** trusted. A standalone harness was built in this context that replicates `conftest`'s `git_project` fixture manually, imports `run_happy_path` and `EXPECTED_TRAVERSAL` from `tests/test_integration_01_happy_path.py`, and drives **three** identical scratch repositories through the full 18-phase workflow:

- `plain` — no `.sdle/`;
- `committed` — `config init`, then `git add -A` + `git commit`;
- `uncommitted` — `config init`, left untracked (the plan's literal N10 wording).

Observed:

```
traversal plain == EXPECTED:            True
traversal committed == EXPECTED:        True
traversal uncommitted == EXPECTED:      True
audit events committed == plain:        True   counts 21 21 (uncommitted 22)
scrubbed state committed == plain:      True
scrubbed state uncommitted == plain:    True
boundary identical after run (committed):    True
boundary identical after run (uncommitted):  True
uncommitted-vs-plain audit diff: ["+('implement', 'dirty_tree_bypassed')"]
```

Three conclusions:

1. **A20 holds.** Identical traversals, identical ordered audit event sequences, identical scrubbed state, and the configured project's `.sdle/` byte-identical before and after the whole run. Clause 4 — the strongest statement that no lifecycle rule moved into `.sdle/` — is true.
2. **The declared divergence is exactly what the handoff says it is, and no more.** Handoff claim 6 asked to be checked by removing the commit; done. The *only* difference is one extra `('implement', 'dirty_tree_bypassed')` audit event. Traversal, scrubbed state and `.sdle/` byte-identity **still hold even uncommitted**. The divergence is caused by an untracked file in the working tree, not by anything reading configuration.
3. **Committing `.sdle/` in the test is therefore not a dodge.** The question posed to this verifier was whether it quietly evades what N10 was written to catch. It does not: N10 exists to catch a lifecycle rule migrating into `.sdle/`, and clauses 1, 3 and 4 — the clauses that would detect that — are unaffected by the commit. The commit only removes a working-tree-cleanliness artefact, and `.sdle/` is versioned by D7 so "committed" is the true steady state. The implementer additionally pinned the uncommitted direction with a separate test rather than hiding it, which is the right disposition.

### The fail-closed property the N10 decision rests on

Verified directly, not via the shipped test. Git-backed scratch project, `init`, then `config init` left uncommitted, then `implement preflight`:

```
exit: 1   reason: dirty_tree
entries: ['?? .sdle/config.json', '?? .sdle/implementation-state/.gitkeep',
          '?? .sdle/policies/.gitkeep', '?? .sdle/templates/.gitkeep']
'.sdle/' in SDLE_OWNED_PREFIXES: False
```

The §18 Wave A dirty-tree guard genuinely still fires on an uncommitted boundary. The decision not to extend `SDLE_OWNED_PREFIXES` fails **closed**, and `SDLE_OWNED_PREFIXES` itself is byte-identical to `7b054ee`.

### The two leak detectors fire on violations built by this verifier

Not inherited from the shipped parametrisation — planted by hand through the real CLI. All twelve plantings produced exit **3** with exactly one correctly-named error finding (table row A12). This is the direct answer to the "inert scaffolding" failure mode: the detectors are reachable and they fire.

### The source-level containment detectors have teeth

The N1 and N11 predicates were re-implemented from the test file and run against mutated copies of `sdle.py` held in memory (product code was never modified):

| Mutation | Detector | Outcome |
|---|---|---|
| baseline, unmutated | N1 / N11(1) / N11(3) | PASS / PASS / PASS |
| `config_root` changed to `self.project_root / (self.workitem or ".sdle")` | N1 | **FAIL** `config_root leaks ['workitem']` — caught |
| `cmd_advance` given `_ = paths.config_file` | N11(3) and N11(1) | **FAIL** `['cmd_advance']` — caught by both |
| `cmd_validate` given `_ = paths.policies_dir` (a sixth reference site) | N11(1) | **FAIL** `extra=['cmd_validate']` — caught |

### The `.sdle` collision surface, probed through launch-directory discovery

| Case | Observed |
|---|---|
| Launch from `workitems/<id>/` in a healthy repository | project root resolves to the repository root; `config show` exit 0 reporting `root: ".sdle"` |
| Launch from `workitems/<id>/` after planting `config.json` in that WorkItem's `.sdle/` (so `workitems/<id>/` now carries the new marker) | `config show` and `config init` both exit **1** `config_root_inside_workitem` — fails closed |
| `validate` from the repository root, same leak present | exit **3**, `repository_config_in_workitem` |

The new marker's worst case is therefore a refusal, not a misplaced write.

### The anti-over-scrub question, judged rather than accepted

The implementer added `phase_history[*].completed_at` to N10's run-varying set. The scrub was applied to a real completed `state.json` and inspected:

- kept: 20 of 26 top-level keys, including `current_phase`, `progress`, `workflow_version`, `workitem`, `status`, `rate_limits`, `attempt_counts`, `drift_queue`, `specKit`, `project_name`, `verbose`;
- dropped: exactly `artifact_shas`, `audit_sha`, `current_artifact_sha`, `implementation_base_ref`, `last_updated`, `security_review_artifact`, plus nested `timestamp` / `completed_at`;
- all **18** `phase_history` entries survive with `phase` and `outcome` intact; all **8** approvals survive with their `decision`.

`test_the_scrubbed_state_comparison_still_has_teeth` is a real constraint, not a blessing: it would fail if `current_phase`, `workflow_version`, `workitem`, `progress`, `phase_history`, `approvals` or `specKit.featureId` were added to the scrub set. Independently, clause 2 (ordered audit events) is **not** scrubbed at all, so over-scrubbing clause 3 could not hide a behavioural difference on its own. Not over-scrubbed.

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (working tree, HEAD `475795a`, nothing in flight) | **`569 passed in 645.35s (0:10:45)`, `RAW_EXIT=0`** | `grep -c "short test summary"` = **0** — zero skips, xfails, errors. Run backgrounded without redirection, exit read from the process. |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **569 tests collected in 0.52s** | collected == passed |
| `--collect-only` on pristine `git archive 7b054ee` | **500 tests collected in 2.79s** | baseline re-derived, not copied from the handoff |
| `--collect-only tests/test_units_repo_config.py` | **69** | 500 + 69 = 569 |
| `--collect-only tests/test_units_workitem_resolution.py`, pristine `7b054ee` and now | **96** and **96** | the authorised edit adds no test |
| `rtk proxy "python scripts/sdle.py lint-skill"` | raw exit **0**, **22 PASS / 0 FAIL** | `Parsed 19 phases, 8 gates, 15 migration rows`; `all four locations report v1.15`; `"failed": []` |
| `rtk proxy "python tools/transition/validate.py"` | raw exit **0** | `TRANSITION_VALID: complete=5/12 next=T05` |
| `git diff --exit-code 7b054ee HEAD -- <widened must-not-change list>` | **exit 0** | includes all of `.claude/` and `tests/conftest.py` |
| AST extract-and-compare vs `7b054ee` | 19 named definitions identical | `Paths` members purely additive; `build_parser` purely additive; `collect_validation_findings` purely additive (48 added lines, **0** removed) |
| `git diff --numstat 7b054ee HEAD -- scripts/sdle.py` | **`341  0`** | zero deletions confirmed |
| Real-CLI subprocess probes (A9–A14, collision surface) | as tabulated | not in-process |
| Standalone three-project differential harness | as tabulated | three full 18-phase runs |
| Python 3.11 | **NOT_RUN** | host is 3.13.0 |
| CI | **NOT_RUN / UNKNOWN** | branch is local-only; no outcome predicted |

## Future-phase leakage check

**No T06+ leakage found.**

- The A19 grep over added lines matched exactly one line, confirmed benign (project-root discovery docstring).
- `.sdle/policies/` contains **only** `.gitkeep` (`os.walk` confirms).
- No code path writes `baseline.json`: `baseline_file` is referenced only for `.name` in the leak detector and as a reported relative path in `config show`. `os.walk('.sdle')` shows no `baseline.json`.
- Nothing is written under `implementation-state/` except its `.gitkeep`.
- The T11-owned surfaces are all still present and passing: the legacy `.workflow/` dual-read rung (`test_the_legacy_dual_read_rung_still_binds`), `cmd_migrate_workflow` (byte-identical), `cmd_init`'s unconditional `legacy_workflow_present` refusal (byte-identical, and `test_init_still_refuses_a_legacy_workflow_unconditionally` passes).
- **The explicitly-not-adopted items were not quietly adopted.** `cmd_manifest_build`, `cmd_workitem_use`, `ACTIVE_CONTEXT_SETTERS` and `_validate_runtime_state` are byte-identical; `.claude/hooks/hooks.py` and `.claude/skills/` are byte-identical (A5). So T04 N-3, N-4, N-6, N-7 and T03-4/5/6/7/8/10 are untouched, as declared.
- No new state field, no migration row, no version bump, no gate, no phase.

## Test weakening / deletion check

**No test was weakened, skipped, xfailed or deleted.**

- `git diff --name-status 7b054ee HEAD -- tests/`: one `M`, zero `D`, zero `R`, one `A`.
- The one `M` is `3 0` in `--numstat` — a pure addition of the literal `"config"` plus a two-line explanatory comment inside `test_runtime_free_commands_is_a_closed_enumerated_set`. The assertion remains a **closed** frozenset comparison; it still fails if any other member is added or removed. TP-003 category 2 (genuinely superseded), correctly classified: `config` in `RUNTIME_FREE_COMMANDS` *is* §11's exit criterion in executable form.
- `tests/conftest.py` byte-identical, so no fixture was re-scoped.
- The three other closed-set assertions (`sites`, `writers`, `ACTIVE_CONTEXT_SETTERS`) are byte-identical; `test_workitem_rebinding_happens_only_at_the_declared_sites` still asserts the same six-name set, and the new `dataclass_replace(paths, workitem="_probe")` sits **inside** `collect_validation_findings`, already a declared member. `workitem_runtime_member_names` takes an **already-bound** `Paths` and contains no `dataclass_replace` call at all — verified by reading the function.
- `-rsxX` produced no short-summary section, so the suite has zero skips, xfails and errors. (Per the plan's own warning, a naive `grep "skip\|xfail"` over `tests/` was not used as evidence.)
- The new file is not vacuous: it carries four explicit anti-vacuity guards (`test_the_lifecycle_command_prefixes_actually_match_something`, `test_the_runtime_member_names_are_derived_from_paths`, `test_the_scrubbed_state_comparison_still_has_teeth`, and the `assert boundary_before` inside the differential test), and the containment predicates were independently mutation-tested above.

## Deterministic guardrail check

- **Exit-code contract intact.** Observed in this context: `config show`/`config init` success `0`; refusals `1` (`config_exists`, `config_malformed`, `config_root_inside_workitem`); `validate` integrity failures `3`.
- **It refuses; it does not warn.** All four new checks are `VALIDATE_ERROR`, and both new commands raise `Refused` before any write.
- **Refusal reason namespace.** A regex scan of `Refused(`/`UsageError(`/`IntegrityError(` string literals: **56 → 57**, added `{'config_exists'}`, removed `{}`. No pre-existing reason contained `config`. `config_malformed` and `config_root_inside_workitem` are raised through `_refuse_config_findings` from the finding's own `check`, so the refusal reason and the `validate` check name are the *same string by construction* — a genuine invariant-7 improvement, not a fork.
- **One predicate, two consumers.** `repo_config_findings` is the sole soundness implementation. The shipped N6 test asserts `config show`'s refusal message and `validate`'s finding `detail` are the same string across all eight malformed cases; this passed in the full run.
- **Derivation is real, not a comment over a hardcoded list.** Read at source: the runtime name set comes from `workitem_runtime_member_names(probe)`, which returns `tuple(member.name for member in (bound.state_file, bound.audit_file, bound.execution_file, bound.lock_file, bound.evidence_dir, bound.manifest_file, bound.completion_file))`; the configuration name set comes from `paths.config_file.name`, `paths.policies_dir.name`, `paths.shared_templates_dir.name`, `paths.baseline_file.name`, `paths.implementation_state_dir.name`. No file-name string literal appears on either side. A future phase adding a member on either side inherits the check.
- **No name collision between the two sets:** `{state.json, audit.md, execution.json, lock, evidence, implementation-manifest.md, completion-summary.json}` versus `{config.json, policies, templates, baseline.json, implementation-state}` — disjoint, verified at runtime.
- **Write fence untouched.** `hooks.py` byte-identical; `FENCED = (".workflow", "workitems", "requirements", "guidance")` — `.sdle` is absent, so the `in_dir` hazard is genuinely **deferred to T09**, not half-implemented. `.gitignore`'s only `.sdle` reference is `workitems/*/.sdle/lock`, anchored to `workitems`, so it cannot match the repository-root boundary.
- **Invariant 6 (single writer).** `config init` writes only inside `config_root`, via `write_atomic`, and appends no audit entry — verified by the shipped N13/N14 tests, by N11 clause 2 at source level, and at runtime by the differential run's byte-identical `audit.md` sequences.
- **Invariant 3.** No `speckit-` or `/speckit.` string in anything T05 added.
- **Invariant 8.** No subagent, no delegation, nothing that holds a gate; `.claude/agents/` byte-identical.
- **Resolution ladder.** `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence` byte-identical; `>1 plausible -> ASK` demonstrated live (`workitem_ambiguous` with two WorkItems while `config` succeeds).

## State / audit / evidence integrity check

- No state field added, removed or renamed; `templates/state.json` byte-identical; `CURRENT_VERSION == "1.15"`; `MIGRATIONS` has 15 rows; `migration_covers_every_state_field` PASS.
- `configVersion` is confirmed to be a separate namespace: it is not a state field, has no migration row, and nothing in the lifecycle reads it (N11 clause 3, mutation-tested).
- The audit hash chain is untouched — `append_audit` and `save_state` byte-identical, and the differential run produced identical 21-event ordered audit sequences in the configured and unconfigured projects.
- Evidence handling untouched: `evidence_dir` derives from `runtime` as before, and `evidence` is one of the seven names the repository-side leak detector rejects.
- `config init` creates the three directories before writing `config.json` last and atomically, so an interrupted run re-runs to completion rather than dead-locking on `config_exists` — pinned by `test_config_init_inherits_write_atomic`, which injects the failure into `write_atomic` itself (so it also proves the write is not hand-rolled).

## Cross-platform / path handling check

- All new path construction uses `pathlib` operators. Repo-relative strings are normalised: `config_root_relative` uses `str(...).replace(os.sep, "/")` and `cmd_config_init`/`cmd_config_show` use `.relative_to(project_root).as_posix()`. Detail strings are POSIX-form.
- `lint-skill`'s `no_powershell_only_cmdlets` PASS; no prompt file changed at all.
- `scripts/sdle.sh` and `scripts/sdle.ps1` byte-identical; the new `config` group is a plain subparser and needs no launcher change.
- Everything above was executed on **win32**, including the three full 18-phase runs, so the Windows path behaviour of the new code is directly observed. Linux and Python 3.11 remain **UNKNOWN**.
- `.gitattributes` untouched; `scripts/sdle.py` is LF in both index and working tree.

## Artifact review/SHA freshness check

- `tools/transition/validate.py` exits **0**, which re-verifies `control-plane.sha256` over the governed control-plane files. No control-plane file was modified by this phase (`tools/`, `docs/transition/transition.md`, `docs/transition/templates/`, `.claude/agents/sdle-transition-*`, `.claude/skills/apply-sdle-transition/` are all inside the A5 exit-0 set).
- **The plan is immutable and was not edited after planning:** `git diff --exit-code bf4ba5e 475795a -- docs/transition/phases/T05-plan.md` → exit 0, and `git log --all -- T05-plan.md` shows a single commit, `bf4ba5e`.
- The handoff and all four checkpoints exist on disk at the sizes the commit records.
- The commit under verification contains the whole product change; `git status --porcelain` shows only ` M .claude/settings.local.json`, which is the user's permission allowlist and explicitly out of scope — it was neither staged nor reverted.
- No governed artifact of the SDLE product (spec, plan, tasks, design, security review) is produced or consumed by T05, so §11 has no downstream SHA binding to check.

## Findings

### Blocking

None.

### Non-blocking

**NB-1 — The handoff overstates the `sdle.py` insertion count.** Handoff line 32 says "+436 added lines, **0 deleted lines**". The observed figure is **341** insertions (`git diff --numstat 7b054ee HEAD -- scripts/sdle.py` → `341  0`; `git diff -U0 | grep -c '^+'` = 342, one of which is the `+++` header). The "0 deleted" half is correct and independently confirmed. Narrative-accuracy defect in the handoff only; no product impact. Owner: none required — recorded so the figure is not propagated.

**NB-2 — "Exactly three named definitions changed" is imprecise.** An AST scan of *all* top-level definitions shows **five** changed: `PROJECT_ROOT_MARKERS`, `RUNTIME_FREE_COMMANDS`, `collect_validation_findings`, plus `Paths` and `build_parser`. The latter two are declared in the plan's "Files expected to change" (D1 and D5) and are **purely additive** — a `difflib` comparison of each shows zero removed lines, and every pre-existing `Paths` member is byte-identical. So this is wording, not scope creep. The claim is true of the *A7 named set*, which is what it was measuring; it should not be read as a statement about the whole module. Owner: none required.

**NB-3 — `REPO_CONFIG_DEFAULTS` is restated as a literal JSON block in `README.md`, and `lint-skill` has no check binding the two.** The 22 lint checks were enumerated; none covers this. It is a documentation restatement of a default, the same class as README's other examples, and the plan authorised it — but it is a real drift surface: changing `REPO_CONFIG_DEFAULTS` will not fail any mechanical check. Recommended owner: **T09**, the first phase likely to extend the configuration document; it should either drop the literal block from README or add a lint rule.

**NB-4 — `read_repo_config` is fail-open by construction.** It swallows `OSError` / `json.JSONDecodeError` / `ValueError` and returns `REPO_CONFIG_DEFAULTS`. This is safe **today** only because both call sites (`cmd_config_show`, and nothing else) run `repo_config_findings` first, which refuses. N11 clause 1 currently pins the reference set to five functions, which limits the blast radius. A future phase that calls `read_repo_config` directly would read a corrupt `config.json` as the defaults, silently. Recommended owner: **T09** — when policy reading becomes real, either fold the soundness check into the reader or document the precondition on the signature.

**NB-5 — `config_root_inside_workitem` is a name-based heuristic (implementer's known limitation 1, confirmed).** It fires on `project_root.name == "workitems"` or `project_root.parent.name == "workitems"`. A repository legitimately checked out at `…/workitems/<name>/` would have both `config` subcommands permanently refused **and** `validate` permanently at exit 3. This fails closed, which is the correct direction, and no cheaper alternative exists at T05 (the marker walk has already terminated by the time the predicate runs). Recorded as a false-positive surface. Owner: unassigned; revisit only if observed.

**NB-6 — `repo_config_findings` returns early on `config_root_inside_workitem`** so `config_malformed` can never co-occur with it. Deliberate and documented (implementer's known limitation 2). No action.

**NB-7 — Two carried hazards confirmed genuinely deferred, not half-implemented.** (a) `hooks.py::in_dir(path, name)` matches `/{name}/` anywhere, so adding `".sdle"` to `FENCED` would also match `workitems/<id>/.sdle/` and shadow the `workitems` reason text — `hooks.py` is byte-identical and `.sdle` is absent from `FENCED`, so **T09** inherits this intact, and a fence for the repository boundary must anchor to the start of the repo-relative path. (b) `SDLE_OWNED_PREFIXES` is not extended to `.sdle/`; verified byte-identical and verified fail-closed above. A later phase that writes `.sdle/` mid-run must revisit (b).

**NB-8 — Inherited open findings remain open**, as declared and as required by the plan's scope exclusions: T04 N-2, N-3, N-4, N-6, N-7; T03-1, T03-4/5/6, T03-7/8, T03-10; T02 NB-2/4/5. None was adopted; the byte-identity evidence above is the proof.

## Guard refusals encountered

Declared verbatim, as required. The `verifier` mode of `tools/transition/agent_guard.py` refused two command shapes, both times with:

```
SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape
```

1. `rtk proxy "git diff ... " > "$TMPDIR/sdle_diff.txt"` — output redirection to a file. Re-run by piping the diff through `sed -n` in ranges instead.
2. A `python - <<'PY'` heredoc containing a regex literal with named groups, `(?P<phase>...)`. The guard's redirection tripwire fires on `>` inside a quoted string, an accepted false positive it documents in its own comment. Re-run with numbered groups.

Neither was routed around with an alternate interpreter or shell, and the guard was neither patched nor re-signed. No product code, test, plan or handoff was modified by this verification; the only files written are this artifact and `docs/transition/progress.md`.

## Final result rationale

T05's exit criterion is that repository-global configuration exists **independently** from WorkItem runtime state with **no lifecycle behaviour change**, and §11 forbids moving any lifecycle rule into `.sdle/` at this phase. Both halves were checked in the two directions that matter.

**The boundary is real and reachable.** `config init` and `config show` were driven through the real CLI as subprocesses and behave as specified: `show` on a bare repository exits 0 reporting `present: false` and creates nothing; `init` creates exactly `config.json` plus three `.gitkeep`-bearing directories and no `baseline.json`; a second `init` refuses `config_exists` without touching anything. In a repository with two registered WorkItems and no `--workitem`, both `config` subcommands exit 0 while `state get` refuses `workitem_ambiguous` — §11's exit criterion demonstrated, not asserted. Both leak detectors were fired on twelve violations planted by this verifier outside the shipped tests, and all twelve produced exit 3 with the correct single error finding. The four source-level containment detectors were mutation-tested and all caught their mutation.

**No lifecycle rule moved.** `scripts/sdle.py` has **341 insertions and zero deletions**; nineteen named guardrail definitions are byte-identical by AST extraction; `Paths`, `build_parser` and `collect_validation_findings` changed additively with zero removed lines; the entire `.claude/` tree, `tools/`, `.gitignore`, `.gitattributes`, `docs/dry-runs/` and `tests/conftest.py` are byte-identical to `7b054ee`. No state field, no migration row, no version change, no gate, no phase, no prompt rule. The strongest evidence is the differential run reproduced from scratch in this context: two identical repositories, one configured, produce identical 18-phase traversals, identical 21-event ordered audit sequences, identical scrubbed state, and a `.sdle/` that is byte-identical before and after the entire run.

**The one declared divergence was judged, not accepted.** Removing the test's commit reproduces exactly one extra `('implement', 'dirty_tree_bypassed')` audit event and nothing else — traversal, scrubbed state and `.sdle/` byte-identity all still hold. That is the untracked-file behaviour of a §18 guardrail that was deliberately left byte-identical, and the guardrail was verified to still fire. The implementer pinned the uncommitted direction with its own test rather than hiding it. The call is correct.

The full suite is **569 passed, raw exit 0**, with zero skips, xfails and errors, and the arithmetic 500 + 69 = 569 was re-derived against a pristine `git archive 7b054ee`. `lint-skill` is 22/22 at v1.15 with 15 migration rows. `validate.py` exits 0. Exactly one existing test file changed, by three added lines, correctly classified TP-003 category 2, and the assertion remains closed. No T06+ concept appears anywhere in the diff.

Eight non-blocking findings are recorded above, of which two (NB-1, NB-2) are handoff-narrative inaccuracies with no product impact and the rest are hazards or limitations that the plan itself anticipated and that fail closed. None of them is a defect in what T05 shipped.

The single top-level result recorded for this phase is the `**Result:**` line in the header above, and it reads `PASS`.
