# T06 Independent Verification — Attempt a02

**Phase:** T06  
**Attempt:** 02 (remediation under §24.5 after `T06-verification-a01.md` = FAIL on one blocking finding)  
**Verifier context:** fresh/isolated  
**Result:** PASS

> `T06-handoff-a02.md` and `T06-checkpoint-a02-01.md` are claim sets, not proof. Every figure below was produced by a command run in **this** context. Nothing is copied from the handoff, from a01's handoff, or from `T06-verification-a01.md` — that artifact was read only to know what B1 was, and was **not edited**.

**Commit under verification:** `0a9b8c7` ("T06 a02: no audit entry survives a refused gate approval"), HEAD of `transition/workitem-v1`.
**Attempt a01 commit:** `ccb9835`. **Prior-phase baseline:** `475795a` (T05, PASS). **Product baseline:** `f8fdaa0`.
**Working tree:** only ` M .claude/settings.local.json` — out of scope, neither staged, reverted nor edited.

**Headline.** B1 is genuinely fixed, and the fix is minimal, structurally honest and pinned by a regression that I confirmed fails against the defect. Through the real CLI, a `gate approve` refused for `governance_stale`, `governance_missing` or `governance_record_invalid` now leaves `audit.md` **byte-identical**, writes **zero** `Gate Decision: APPROVED` lines, leaves `state.json` byte-identical, and leaves `audit verify` at **exit 0** — where `ccb9835` grew the ledger by a false approval and returned exit 3. The engine delta from `ccb9835` is exactly **two** top-level definitions out of 326: `cmd_gate_approve` (one inserted statement) and `governance_precondition` (docstring only). `apply_advance`, `_approve_drift`, `cmd_skip` and `read_repo_config` are byte-identical to the revisions they must match. One residual is carried, not fixed: `cmd_skip`'s pre-existing append-then-move ordering, which I reproduced **at `475795a`** as well as at HEAD.

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **B1 defect actually gone** (the reason this attempt exists) | PASS | Reproduced end-to-end as **subprocesses** (`python scripts/sdle.py …`) in a throwaway project built in this context, outside pytest: WorkItem created → `governance assess` → `init` → artifact written → `advance --to gate_constitution` → `artifact review … --result PASS` → an ordinary edit to `requirements/todo-api.md` → `gate approve --gate gate_constitution` = **exit 1 `governance_stale`**, `audit.md` **byte-identical** (2017 → 2017 bytes), `**Gate Decision:** APPROVED` count **0 → 0**, `state.json` **byte-identical**, `audit verify` **exit 0** with `matches: true`. Repeated with the record deleted: **exit 1 `governance_missing`**, ledger byte-identical, `audit verify` exit 0. |
| **The fix did not move the problem** | PASS | AST enumeration of every `raise` in the transitive callee closure of every statement at or after the first `append_audit` in `cmd_gate_approve`: exactly 8 — `apply_advance`'s `state_unreadable`/`forward_jump`/`gate_not_approved`, `governance_precondition`'s three, and `read_governance_record`'s two `governance_record_invalid`. The last five are now all pre-evaluated at the new call (source line 5214) which precedes the first append (5222); nothing between those two statements touches disk. The first three are unreachable from this command (`not_at_gate` catches a `None` phase; `target` is always `NEXT_PHASE[gate_phase]`; the approval is written `"approved"` before `apply_advance`). **`governance_record_invalid` re-driven live at both revisions:** HEAD exit 3, ledger byte-identical, `audit verify` exit 0; `ccb9835` exit 3, ledger **+1 APPROVED**, `audit verify` **exit 3**. `_approve_drift` never calls `apply_advance`, so E1 is not reachable there; its only refusals (`drift_pending`, the three E2 reasons) precede its append — verified live, all four leave `audit.md` byte-identical. |
| **The early call is side-effect free** | PASS | `governance_precondition`'s only side effect is `record_governance_audit(paths, state, record)` guarded by `if state is not None:` — read from the source, and the body-without-docstring is **AST-identical to `ccb9835`**. A transitive side-effect scan of `read_governance_record` and `governance_freshness` finds **no** writer (`write_atomic`, `save_state`, `append_audit`, `record_governance_audit`, `touch_lock`, `mkdir`, `replace`, `write_text`, `write_bytes`); the single `open` reached is `sha256_file`'s read. The AST of the inserted call is `governance_precondition(paths)` — **one positional argument, zero keywords**. Behaviourally: `state.json` is byte-identical across the refusal, and a successful gate approval produces the **identical ordered audit event sequence** at `ccb9835` and HEAD (`workflow_initialized, phase_complete, governance_recorded, phase_advance, artifact_reviewed, gate_approved`), identical resulting state (`spec_draft`/`pending`) and exactly one `APPROVED` line — so the facts still enter the ledger once, from `apply_advance`. |
| **`apply_advance` byte-identical to `ccb9835`** (invariant 7) | PASS | AST extract-and-compare with explicit UTF-8 decoding: identical, 2515 bytes both sides. Whole-module comparison of **326** top-level definitions: **0 added, 0 removed, exactly 2 changed** — `cmd_gate_approve` and `governance_precondition` (docstring only). The E1 rule therefore still lives in exactly one function. |
| **E2-before-E1 precedence unchanged** | PASS | Source line order in `cmd_gate_approve`: `gate_precondition_hook` (5192) → `review_precondition` (5204) → `governance_precondition` (5214) → `append_audit` (5222). Statement-level AST dump shows exactly one statement inserted, at index 13 of 24. Behaviourally re-driven: with **both** a missing review and a stale record, the refusal reported is `review_missing` — E2 still fires first. |
| **The strengthened `frozen()` genuinely catches a ledger append** | PASS | Proved two ways. (1) **Plant:** both helpers imported and driven directly against a live project — appending a forged `gate_approved`/`APPROVED` block to `audit.md` makes `test_units_governance.frozen` and `test_units_artifact_review.frozen` both return a different tuple, and restoring the bytes restores equality. Tuple length 6 in both. (2) **Retro-run:** with a02's two test files overlaid on `ccb9835`'s product tree, the **pre-existing, otherwise unmodified** `test_gate_approve_inherits_the_same_clause` now **FAILS** ("At index 5 diff", the ledger member) where it passed at a01 — the a01 blind spot demonstrated rather than argued. |
| **The regression actually regresses** | PASS | a02's `tests/test_units_governance.py` + `tests/test_units_artifact_review.py` run against a pristine `git archive ccb9835` tree: **`5 failed, 213 passed in 148.76s`**, raw exit 1. Failures: `test_a_refused_gate_approval_leaves_the_ledger_byte_identical[stale]` and `[missing]` (`AssertionError: a refused gate approval appended to the append-only ledger`), `test_gate_approve_inherits_the_same_clause`, `test_the_clause_has_exactly_one_enforcement_site`, `test_the_gate_approval_precheck_runs_before_the_first_audit_write`. All five pass at HEAD inside the full suite. |
| **A1** full suite | PASS | Run **twice**. (1) `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **`789 passed in 845.19s (0:14:05)`**, 13 output lines, `short test summary` count **0**. (2) Independently, pytest invoked as a **direct subprocess from Python** (no `rtk`, no shell, no pipe) → **`RETURNCODE: 0`**, `789 passed in 841.44s (0:14:01)`, 12 stdout lines, `short test summary` occurrences **0**. Zero skips, xfails, errors. |
| **A2** suite arithmetic | PASS | Node-id sets collected in this context: HEAD **789**, pristine `git archive ccb9835` **786**, pristine `git archive 475795a` **569**. HEAD − `ccb9835` = exactly the 3 new ids (`…leaves_the_ledger_byte_identical[stale]`, `[missing]`, `…precheck_runs_before_the_first_audit_write`); `ccb9835` − HEAD = **∅**; `475795a` − HEAD = **∅**. Collected == passed. |
| **A3** `lint-skill` | PASS | `rtk proxy "python scripts/sdle.py lint-skill"` → **raw exit 0**, **22 PASS / 0 FAIL**, `"failed": []`, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15`, `progress denominators=['18']`, all eight gates `registered everywhere`. |
| **A4** `validate.py` | PASS | `python tools/transition/validate.py` → **raw exit 0**, `TRANSITION_VALID: complete=6/12 next=T06`. |
| **A5** must-not-change set | PASS | `git diff --exit-code 475795a 0a9b8c7 -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .claude/skills/sdle/modules/security-review.md .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ ADR-001 ADR-002 .sdle/ tools/` → **exit 0**. |
| **A6** no constant table changed | PASS | `git diff --name-status ccb9835 0a9b8c7` touches **no** prompt file: `scripts/sdle.py`, `docs/architecture/ADR-003-…md`, the two T06 test files, and control-plane docs only. `lint-skill` re-confirms 19 phases / 8 gates / 15 migration rows / v1.15 in four locations; `templates/state.json` byte-identical via A5. |
| **A9** guardrails byte-identical | PASS | AST extract-and-compare of 36 named definitions vs `475795a`: **31 identical**, **5 differ** — exactly T06's declared deltas `append_audit`, `apply_advance`, `_approve_drift`, `cmd_gate_approve`, `RUNTIME_FREE_COMMANDS`. **`cmd_skip` byte-identical to `475795a`** (1755 bytes) and **`read_repo_config` byte-identical to `475795a`** (796 bytes), so the pre-existing defect was not adopted and T05 NB-4 stays T09's. Also identical to `475795a`: `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, `write_atomic`, `save_state`, `read_state`, `_entry_digest`, `verify_audit_chain`, `touch_lock`, `compute_drift`, `cmd_drift_rebaseline`, `cmd_artifact_record`, `sha256_file`, `resolve_artifact_path`, `gate_precondition_hook`, `cmd_init`, `cmd_advance`, `cmd_workitem_create`, `branch_guard`, `write_completion_summary`, `cmd_config_init`, `cmd_config_show`, `repo_config_findings`, `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`, `INJECTION_PATTERNS`, `SECRET_PATTERNS`. Whole-module delta `475795a` → HEAD: 49 added definitions, **0 removed**, 8 changed. |
| **A11** audit integrity — a01's failing half | PASS | See the B1 row and the state/audit section. Positive half re-driven too: `audit verify` exit 0 after a successful approval, after a PASS→stale→re-review→approval cycle, after a drift re-approval, and after the legacy-binding run. |
| **A12** Claude cannot lower a floor | PASS | Re-driven live. `proposedLevel LOW` + `payment_or_financial` → `deterministicLevel HIGH`, `finalLevel HIGH`, `loweringAttempted True`, **exit 0**. A proposal *above* the deterministic level still wins (`deterministic LOW`, `final CRITICAL`, `loweringAttempted False`) — a true lattice maximum, not a clamp. Unknown signal id → exit 1 `unknown_risk_signal`. **Eight** hand-built weakening overrides all refused **`policy_weakens_baseline`** with the offending key and detail named (drop a blocking check, widen `optional_checks`, zero a signal weight, raise every threshold, empty `hard_floors`, lower every floor to LOW, drop an always-gate, drop a HIGH risk gate). **Eight** malformed shapes all refused **`policy_malformed`** with a recursive SHA map of the project root showing **zero** files changed (JSON array, JSON scalar, invalid JSON, unknown top-level key, wrong value type, negative weight, boolean weight, phantom gate key). Strengthening works and is observably stricter: adding a `CRITICAL` floor on `external_api_surface` moved that assessment's `finalLevel` to `CRITICAL` and `policy.source` to `.sdle/policies/governance-policy.json`. |
| **A13** fail safe — a01's failing half | PASS | Every refusal I drove leaves `audit.md` byte-identical: `governance_stale`, `governance_missing`, `governance_record_invalid`, `review_missing`, `review_failed`, `review_stale` (normal path), `review_stale` (drift path). `state.json` byte-identical across the E1 refusals. Both `frozen()` helpers now carry the ledger bytes, so T06's own suite asserts this rather than merely `state["audit_sha"]`. |
| **A14** exit-code contract — a01's failing half | PASS | The undeclared exit-3 outcome is closed: `audit verify` after a T06 refusal at `gate approve` is **exit 0** for `governance_stale`, `governance_missing` and `governance_record_invalid`. The one **declared** exit-3 divergence, `governance_record_invalid` from `read_governance_record`, is unchanged, still argued on the merits, and now fires ahead of the first irreversible write. |
| **A15** invariant 7 | PASS | Needle set derived by parsing `GOVERNANCE_POLICY_BUILTIN` out of the source; restricted to the 17 underscored risk-signal and check ids so ordinary English words cannot produce false hits. **Zero** occurrences anywhere under `docs/` (excluding `docs/transition/`), `.claude/`, `.sdle/` or `README.md`. The 11 lines a02 added to ADR-003 contain **0** needle hits. |
| **A16** T02–T05 guarantees | PASS | Re-driven live at HEAD: with a `.workflow/` runtime present and **zero** WorkItems registered, `state get` exits 0, `advance` exits 0 with **no** governance record, and `gate approve` exits 0 with **no** governance record and **no** review — the declared bounded carve-out, unchanged by the new early call, which returns immediately when `paths.workitem is None`. `init` with `.workflow/state.json` present still refuses **`legacy_workflow_present`**. Hooks, `SDLE_OWNED_PREFIXES` and `.gitignore` byte-identical (A5, A9). |
| **A17 / A18** non-behaviour-change, would-be gate set inert | PASS | `tests/test_units_governance.py::test_governance_changes_no_lifecycle_behaviour` (four repositories, `EXPECTED_TRAVERSAL`, anti-vacuity clause) is byte-unchanged from `ccb9835` and passes in both full runs. `apply_advance` and `cmd_skip` byte-identical; the only phase-movement function touched is `cmd_gate_approve`, whose inserted call references neither `required_gate_set` nor `wouldBeRequiredGates`. The eight gates are still unconditional (`lint-skill` `registered everywhere` ×8; `gate_precondition_hook` byte-identical to `475795a`). |
| **A19** staleness enforcement real | PASS | Re-driven end to end: PASS review → append to the artifact → `gate approve` refuses **`review_stale`** with both `reviewed_sha` and `current_sha` in `data` → re-review → approval succeeds. Drift path: drift the approved artifact, `drift check --queue`, `gate approve` refuses **`review_stale`** against the pre-drift review → review the drifted content → re-approval succeeds. `review_missing` and `review_failed` each reproduced. `audit verify` exit 0 afterwards. |
| **A20 / A22** invariants 3, 8 and future-phase leakage | PASS | Over all **154** lines a02 added to `scripts/`, `tests/` and `docs/architecture/`: `speckit-` 0, `/speckit.` 0, `sdle-architect` 0, `subagent` 0, `Task(` 0, `conditional gate` 0, `gate_policy` 0, `flow_selection` 0, `flow routing` 0, `baseline.json` 0, `risk_tier` 0, `adaptive` 0, `brownfield`/`BROWNFIELD` 0, `PHASE_SEQUENCE` 0, `PROGRESS_MAP` 0, `PHASE_TO_GATE_KEY` 0, `rate_limits` 0, `baseline_file` 0, `implementation_state_dir` 0. `.claude/agents/` byte-identical via A5. |
| **A23** TP-003 | PASS | `git diff --name-status 475795a 0a9b8c7 -- tests/` → **10 M, 2 A, 0 D, 0 R**. `--numstat`: the only pre-existing test file with removed lines is still `tests/test_units_repo_config.py` (4, from a01's authorised row-4 rewrite); a02 removed lines only from files T06 itself added (`test_units_governance.py` 108/6, `test_units_artifact_review.py` 12/2). `grep -rn "xfail" tests/ --include=*.py` → **no match, exit 1**. `grep -rnE "skipif\|pytest.mark.skip\|pytest.skip" tests/ --include=*.py` → exactly one line, pre-existing: `tests/test_units_infra.py:49:@pytest.mark.skipif(SH is None, reason="POSIX sh not available")`. |
| **A24** Python 3.11 / CI | NOT_RUN | Host is Python **3.13**; the branch is local-only and unpushed. **Python 3.11: NOT_RUN. CI: NOT_RUN / UNKNOWN.** No outcome predicted. |

---

## Regression evidence

All of the following was driven through the real CLI as **subprocesses** in throwaway projects built in this context, so nothing depends on a pytest fixture that could mask behaviour.

**The B1 scenario, both causes, both revisions.** At HEAD a refused `gate approve` is inert: exit 1, ledger byte-identical, zero `APPROVED` lines added, `state.json` byte-identical, `audit verify` exit 0. At `ccb9835` the same corrupt-record scenario gives exit 3, ledger **+1 `**Gate Decision:** APPROVED`**, `audit verify` **exit 3** — the defect reproduced against the old code, so the fix is demonstrated rather than asserted.

**The success path is unchanged.** Same scenario without the requirements edit, run at `ccb9835` and at HEAD: identical ordered audit event sequence, identical `current_phase`/`status`, one `APPROVED` line each, `audit verify` exit 0 both. The early call adds nothing to the ledger.

**E2 still fires first and still refuses ahead of every write.** `review_missing`, `review_failed`, `review_stale` (normal) and `review_stale` (drift queue) each leave `audit.md` byte-identical; each clears after a PASS review of the current bytes; the drift queue then re-baselines and `audit verify` exits 0.

**The legacy rung is untouched.** Zero WorkItems + `.workflow/state.json` → `state get`, `advance` and `gate approve` all exit 0 with no governance record and no review; `init` still refuses `legacy_workflow_present`.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | PASS | **`789 passed in 845.19s (0:14:05)`**, 13 lines, `short test summary` count **0**. |
| pytest as a direct Python subprocess (no `rtk`, no shell, no pipe) | PASS | **`RETURNCODE: 0`**, **`789 passed in 841.44s (0:14:01)`**, 12 lines, `short test summary` occurrences **0**. This is the authoritative raw exit: the `rtk` false-green trap is structurally impossible here. |
| `python -m pytest --collect-only -q` (HEAD) | PASS | **789 tests collected** — collected == passed. |
| `--collect-only -q` on pristine `git archive ccb9835` | PASS | **786** — a01's baseline re-derived, not inherited. |
| `--collect-only -q` on pristine `git archive 475795a` | PASS | **569** — T05 baseline re-derived. |
| a02 tests vs `ccb9835` product tree | PASS (as required) | **`5 failed, 213 passed in 148.76s`**, raw exit 1 — the regression fails against the defect. |
| `rtk proxy "python scripts/sdle.py lint-skill"` | PASS | raw exit 0, 22 PASS / 0 FAIL, 19 phases / 8 gates / 15 migration rows, v1.15 in four locations. |
| `python tools/transition/validate.py` | PASS | raw exit 0, `TRANSITION_VALID: complete=6/12 next=T06`. |
| `git diff --exit-code 475795a 0a9b8c7 -- <A5 list>` | PASS | exit 0. |

Disk was checked before trusting any run: `D:` 21 GB free, `C:` 9.4 GB free. No `os error 112` or any I/O error appeared in either full run.

---

## Future-phase leakage check

None found. a02's product delta is one statement plus two docstring paragraphs and eleven ADR lines; the leakage needle scan over all 154 added lines returns zero on every T07–T11 token (table row A20/A22). `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP`, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE` and `templates/state.json` are byte-identical to `475795a`; the eight gates remain unconditional and the fixed 18-phase sequence intact (`lint-skill`); no flow-type routing exists on any transition path; the `.workflow/` rung, `migrate-workflow` and `init`'s unconditional `legacy_workflow_present` refusal all still work; `.sdle/implementation-state/` still holds only `.gitkeep`.

---

## Test weakening / deletion check

Zero deletions, zero renames, zero skips, zero xfails; **no assertion was relaxed**.

- a02 removed exactly **14** lines across `scripts/`, `tests/` and `docs/architecture/`. I read every one: two ADR sentences, four `governance_precondition` docstring lines, two one-line `frozen()` docstrings, two `return` continuation lines, three docstring lines of `test_the_clause_has_exactly_one_enforcement_site`, and one `assert callers == ["apply_advance"]`. That single assertion is the **only** assertion touched anywhere in a02.
- **`frozen()` (TP-003 category 3, "defect in the assertion") — judged genuinely strengthening, not merely changed.** The tuple gained a sixth member and lost nothing, so every pre-existing `frozen(p) == before` assertion now additionally requires `audit.md` bytes to match. Proved two independent ways (planted append; retro-run against `ccb9835` making the previously-green `test_gate_approve_inherits_the_same_clause` fail). This is the opposite of weakening: it converts a helper that provably could not observe the defect into one that does.
- **`test_the_clause_has_exactly_one_enforcement_site` (category 2) — judged correct.** `assert callers == ["apply_advance"]` → `assert callers == ["apply_advance", "cmd_gate_approve"]` is still an **exact equality on a closed, sorted, explicitly named set**, not a subset, membership or `in` check; a third caller still fails loudly. The widening is compensated by a **new** structural test that pins the ordering (`guards[0] < min(appends)`), the argument count (one positional, zero keywords, i.e. no `state`), and carries an explicit anti-vacuity guard (`assert appends, …`). I confirmed that guard is real: `cmd_gate_approve` does contain `append_audit` calls, so the test cannot pass by matching nothing.
- **Row 4's containment rewrite re-proved load-bearing in this context**, not merely read. Using the test module's own `functions_outside_paths` / `names_referenced` helpers against three in-memory mutations of `scripts/sdle.py`: a policy read planted in a helper named `_quietly_consult_policy` — outside every old name prefix — is caught by clause (a) (`policy_readers` becomes a two-member set); the same read planted inside `apply_advance` is caught by clause (a); a `config_file` read planted in `cmd_advance` is caught by clause (b) **and** by the retained prefix clause (c). The unmutated source yields exactly `{"read_governance_policy"}` and the declared five config readers.
- `tests/test_units_repo_config.py`, `tests/conftest.py` and the seven other pre-existing modified test files are **byte-identical to `ccb9835`** — a02 changed no pre-existing test file at all.

---

## Deterministic guardrail check

The security property that matters most survives the remediation intact, re-derived here rather than inherited: **Claude cannot lower a deterministic policy floor.** `final = max(deterministic, proposed)` over an index-ordered lattice; a lowering attempt is recorded and has no effect and does not deadlock the workflow; an unrecognised signal refuses rather than silently weighing zero; the repository override is monotone in all eight weakening directions I could construct and fail-closed against all eight malformed shapes, writing nothing in every malformed case; strengthening is admitted and observably changes the outcome. Because `evaluate_risk`, `read_governance_policy`, `required_gate_set` and `review_precondition` are byte-identical to `ccb9835`, a01's wider exploration of this surface still applies, and my spot-checks agree with it.

"Currently reviewed" remains a derived predicate — the emitted record carries no boolean, and freshness is recomputed from `sha256_file` on every call. The two SHA mechanisms stay separate: `cmd_artifact_record`, `sha256_file`, `resolve_artifact_path`, `compute_drift` and `cmd_drift_rebaseline` are byte-identical to `475795a`.

---

## State / audit / evidence integrity check

This is the section that failed at a01, and it now holds.

- `write_atomic`, `save_state`, `read_state`, `verify_audit_chain`, `touch_lock` and `_entry_digest` are **byte-identical to `475795a`**. `write_atomic` was not touched, as required.
- `append_audit` is byte-identical to `ccb9835` and still renders `**Prev:**` last.
- A refused `gate approve` now writes **nothing**: ledger byte-identical, `state.json` byte-identical, `audit verify` exit 0. Invariant 5 (freeze on any failure) and invariant 6 (single writer, consistent chain tail) are restored on that path.
- A successful `gate approve` produces the same ledger it produced at `ccb9835`, byte-for-byte in event sequence and `APPROVED` count, so the fix bought integrity without changing the record.
- The rule still lives in exactly one function (invariant 7). It now has two call sites; the second is a pure reader whose only side effect is guarded out, and the enforcement site is unchanged.

---

## Cross-platform / path handling check

a02 introduces no path handling, no new I/O and no new string parsing: the engine delta is one call, two docstrings. `sdle.sh`, `sdle.ps1` and all prompt files are byte-identical to `475795a` (A5). `lint-skill`'s `no_powershell_only_cmdlets` passes. `review_key`'s separator normalisation and `requirements_sources`' sorted repo-relative POSIX digest are byte-identical to `ccb9835`. All reproductions in this context ran on Windows through `subprocess` with explicit UTF-8.

---

## Artifact review/SHA freshness check

Bound to the exact current SHA, verified behaviourally at HEAD: a one-byte append after a PASS review blocks `gate approve` with `review_stale` carrying `reviewed_sha`, `reviewed_shas` and `current_sha`; a `FAIL` review of the current content blocks approval; the same rule governs drift re-approval through `_approve_drift`; every one of those refusals leaves `audit.md` byte-identical. The `artifact_reviewed` audit linkage is unchanged from `ccb9835` and appears in the success-path event sequence in the correct position.

---

## Findings

### Blocking

None.

### Non-blocking

**NB-6 (carried, correctly declared by the handoff; needs an owning phase).** `cmd_skip` has the same append-then-move ordering `cmd_gate_approve` had: `append_audit(..., decision="SKIPPED")` then `apply_advance`. I reproduced both halves in this context:

- **At `475795a`, before T06 existed** — `status = failed` at a gate phase, `skip` then `skip --confirm` → exit 1 `gate_not_approved`, `audit.md` grew by 415 bytes, `audit verify` **exit 3**. So the orphan is **pre-existing product behaviour**, not a T06 regression.
- **At HEAD** — `status = failed`, an ordinary `requirements/` edit, `skip --confirm` → exit 1 `governance_stale`, `audit.md` grew by 417 bytes, `audit verify` **exit 3**. So T06 widens its *reachability*.

I judge this non-blocking and consistent with the finding set this attempt answers: `T06-verification-a01.md` examined the same ordering, reproduced it at `475795a`, and scoped its blocking finding to `cmd_gate_approve` where the refusal is new. `cmd_skip` is **byte-identical to `475795a`** here, so the remediation neither adopted the defect nor widened its own diff to chase it. Two facts bound the severity: `skip` is reachable only after a genuinely failed step (`status != "failed"` refuses `not_failed`), and the orphaned entry carries `**Gate Decision:** SKIPPED`, not a false `APPROVED`. It should still be fixed: the general shape is the one applied here — refuse before the first irreversible write — and the test shape is the one added here, comparing `audit.md` bytes rather than `state["audit_sha"]`. **T11 hardening is a reasonable home; an owner must be recorded, because this is now the second time it has been observed and deferred.**

**NB-1…NB-5 from `T06-verification-a01.md` are carried unchanged and remain unadopted**, and I re-confirmed each is still accurate at HEAD: NB-1 `reviews_malformed` is an undeclared refusal reason; NB-2 `governance_freshness` compares only the `requirements/` digest and never re-checks the recorded `policy.sha256`, so installing a stricter override does not invalidate an assessment made under the built-in (owner **T09**); NB-3 the governance record has no integrity binding beyond JSON shape (owner: whichever phase first *acts* on the recorded risk); NB-4 `docs/dry-runs/` shows no governance assessment or pre-gate review and `docs/transition/RESUME.md` remains stale relative to `validate.py` (owner **T11**); NB-5 is answered by `T06-handoff-a02.md`.

**NB-7 — handoff accuracy.** Every quantitative claim I re-derived was accurate: 789/786/569, the +3 node ids, `789 = 786 + 3`, `10 M / 2 A / 0 D / 0 R`, numstat `23/4` for `scripts/sdle.py`, `108/6` and `12/2` for the two test files, `11/2` for ADR-003, `cmd_skip` and `read_repo_config` identical to `475795a`, `apply_advance` identical to `ccb9835`, the two greps quoted verbatim, and the pre-fix failure of the regression. One clarification rather than an error: the A9 row reports "35 identical / 1 differs" over its own 36-name guardrail set, which is true, but the whole-module delta from `ccb9835` is **two** definitions — `cmd_gate_approve` and `governance_precondition`, the latter docstring-only. The handoff states that docstring change elsewhere, so nothing is concealed.

**NB-8 — ADR-003's rewritten sentence is true of the shipped code.** "The rule is written in exactly one function, so there is exactly one place to audit", followed by the explicit statement that `cmd_gate_approve` calls that function a second time, earlier, without `state`. Both halves check out against the source and against `test_the_clause_has_exactly_one_enforcement_site`'s two-member closed set. The prior wording ("There is exactly one enforcement site") would have been false after the fix, so correcting it was required, not optional.

---

## Final result rationale

The one blocking defect T06 returned on is gone, and I established that by reproducing the original scenario against both revisions rather than by reading the patch: at `ccb9835` an ordinary refusal grows the append-only ledger by a false `Gate Decision: APPROVED` and leaves `audit verify` at exit 3; at `0a9b8c7` the same command, the same project, the same edit leaves `audit.md` byte-identical, `state.json` byte-identical, zero `APPROVED` lines added and `audit verify` at exit 0. The same now holds for `governance_missing` and for the declared exit-3 `governance_record_invalid` path, which was orphaning entries at a01 too.

The fix is the smallest one that closes the class. It moves no rule: `apply_advance` is byte-identical, so E1 is still written in exactly one function and all three movers still funnel through the enforcement site. The early call is a pure reader — its only side effect is guarded by `if state is not None`, it is invoked with one positional argument and no keywords, and a transitive scan reaches no writer — which is why the success path's ledger is byte-for-byte what it was before. E2 still precedes E1. Nothing else in the engine changed: 2 of 326 top-level definitions, one of them a docstring.

The test changes are strengthening, and I refused to take that on the word of the handoff. The retro-run against `ccb9835`'s product tree makes the point better than any argument: with the strengthened helper in place, the *pre-existing* test that a01 wrote to prove the refusal freezes everything now fails, because it can finally see the ledger. The new regression fails against the defect in both parametrisations and passes here. The one widened assertion stays an exact closed-set equality and gained a companion test that pins the ordering and the missing `state` argument with an anti-vacuity guard.

Everything a01 had already passed still holds where I re-checked it: the risk floor could not be talked past by any of the eight weakening or eight malformed override shapes I built, staleness blocks consumption in both the normal and the drift path, row 4's containment rewrite demonstrably catches the exact evasion the plan warned about, the legacy rung and `legacy_workflow_present` still behave, the eight gates are still unconditional, and the traversal differential is byte-unchanged and green. The full suite is 789 green with the raw exit code read directly from pytest's own process, zero skips and zero xfails, across two independent runs; `lint-skill` is 22/0 and `validate.py` exits 0; the must-not-change set diffs clean against `475795a`.

One residual is carried rather than fixed, and I am satisfied that is the right call: `cmd_skip`'s identical ordering is pre-existing product behaviour that I reproduced at `475795a` itself, it is byte-identical here, and the finding set this attempt answers deliberately scoped its blocking half to `cmd_gate_approve`. It is recorded as NB-6 with an owner recommendation so it is not lost a third time.

Exactly one final result is valid: `PASS` or `FAIL`.
