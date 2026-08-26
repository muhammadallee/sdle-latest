# T06 Independent Verification — Attempt a01

**Phase:** T06  
**Attempt:** 01  
**Verifier context:** fresh/isolated  
**Result:** FAIL

> The handoff is a claim set, not proof. Every figure below was produced by a command run in **this** context. Nothing is copied from `T06-handoff-a01.md` or from any checkpoint.

**Commit under verification:** `ccb9835` (HEAD, `transition/workitem-v1`).
**Rollback/prior-phase baseline:** `475795a` (T05, verified PASS). Product baseline `f8fdaa0`.
**Working tree:** only ` M .claude/settings.local.json`, which is out of scope and was neither staged, reverted nor edited.

**Headline.** The four subsystems §12 asks for are present, deterministic and genuinely enforced: the risk floor cannot be talked past by any route I could construct, the monotone policy override refuses all six weakening shapes, staleness blocks downstream consumption in both the normal and the drift path, and the A17 traversal differential is real and non-vacuous. One blocking defect stands against it: **a T06 refusal on the `gate approve` path writes a false `Gate Decision: APPROVED` entry into the append-only audit ledger and leaves the hash chain broken**, because `cmd_gate_approve` appends the audit entry *before* it calls `apply_advance`, and E1 is the first refusal ever reachable there. That is a fail-safe and audit-integrity violation (invariants 5 and 6), it is reachable through an ordinary user action, and no test in the 786 detects it.

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** full suite | PASS | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` run to completion in this context: **`786 passed in 990.27s (0:16:30)`**, **`RAW_EXIT=0`** read with no pipe between. Captured output is 15 lines; `short test summary` occurs **0** times, so zero skips, xfails and errors. `--collect-only -q` = **`786 tests collected`**, so collected == passed. |
| **A2** suite arithmetic | PASS | Baseline re-derived from a pristine `git archive 475795a` extracted to scratch and collected there: **`569 tests collected`**. Node-id set diff pristine→HEAD: **0 removed**, 217 added. 569 + 175 (`test_units_governance.py`) + 40 (`test_units_artifact_review.py`) + 2 = **786**. The +2 is the only per-file delta in a modified file and is exactly `test_units_repo_config.py::test_lifecycle_state_under_the_repository_boundary_is_an_error[governance.json]` and `[reviews.json]` — a parametrisation expansion from anti-contradiction row 3, not a new test function. Every other per-file count is identical to baseline (hooks 44, integration_01 8, 02_to_05 42, 06_to_09 38, lint_skill 17, cli 9, infra 28, speckit_binding 55, state 37, transitions 24, workitem 57, resolution 96, runtime 45). |
| **A3** `lint-skill` | PASS | `python scripts/sdle.py lint-skill` → **raw exit 0**, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15`, `"failed": []`. |
| **A4** `validate.py` | PASS | `python tools/transition/validate.py` → **raw exit 0**, `TRANSITION_VALID: complete=6/12 next=T06`. |
| **A5** must-not-change set | PASS | `git diff --exit-code 475795a ccb9835 -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .claude/skills/sdle/modules/security-review.md .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ ADR-001 ADR-002 .sdle/ tools/` → **raw exit 0**. |
| **A6** no constant table changed | PASS | All **175** markdown table rows in `SKILL.md` byte-identical to `475795a` (read via `git show` as bytes, rows extracted and compared programmatically). `templates/state.json` byte-identical via A5. `CURRENT_VERSION = "1.15"` in both revisions by AST extraction. `lint-skill` reports 15 migration rows and v1.15 in four locations. |
| **A7** `RUNTIME_FREE_COMMANDS` | PASS | Both definitions AST-extracted and read side by side: the `475795a` seven members are all present, `"governance"` added, nothing removed. 8 members. |
| **A8** `.sdle/` untouched | PASS | `find .sdle -type f` → `config.json`, `implementation-state/.gitkeep`, `policies/.gitkeep`, `templates/.gitkeep`. `ls -a .sdle/policies` → `.gitkeep` only. `cmd_config_init`, `cmd_config_show`, `read_repo_config`, `repo_config_findings` all byte-identical (A9). |
| **A9** guardrails byte-identical | PASS | AST extract-and-compare against `475795a`: **24/24 identical, 0 differ, 0 missing** across the 19 named functions plus `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`, `INJECTION_PATTERNS`, `SECRET_PATTERNS`. Additionally verified identical: `gate_precondition_hook`, `cmd_artifact_record`, `sha256_file`, `resolve_artifact_path`, `cmd_workitem_create`, `cmd_skip`, `cmd_advance`, `branch_guard`, `write_completion_summary`. `cmd_gate_approve` **+1 / −0** (one `review_precondition` call), `_approve_drift` **+1 / −0** (same). `read_repo_config` byte-identical, so T05 NB-4 was not inherited and stays T09's. Only new import: `copy` (stdlib). |
| **A10** §12 exit criterion, real CLI | PASS | Driven as subprocesses in a throwaway project. Fresh WorkItem: `init` exits 0, first `advance` refuses **`governance_missing`**, state byte-identical across the refusal. After `governance assess`, `governance.json` carries all seven §12 evidence items — `quality.result`, `classification{type,flow,advisory}`, `risk.signals`, `risk.score`, `risk.floorsApplied`, `risk.deterministicLevel`/`finalLevel`, `risk.uncertainty` — plus `wouldBeRequiredGates` and `policy{source,sha256}`. `governance policy` resolves with no WorkItem bound and reports `source: "builtin"`. |
| **A11** audit integrity | **FAIL** | Positive half holds: `audit verify` exits 0 after a pre-`init` assessment + `init`, after a blocked-then-remediated assessment, after PASS/FAIL reviews, after a gate approval, after a drift re-approval, and across the four complete 18-phase runs in the differential. **Negative half fails:** after a refused `gate approve` (`governance_missing` or `governance_stale`) `audit verify` returns **exit 3 `audit_chain_broken`** and the ledger has grown by one false `**Gate Decision:** APPROVED` entry. See Finding B1. |
| **A12** Claude cannot lower a floor | PASS | Live, four independent routes. `proposedLevel LOW` + signal `payment_or_financial` → `deterministicLevel=HIGH`, `finalLevel=HIGH`, `loweringAttempted=True`, **exit 0**. `proposedLevel LOW` + `uncertainty CRITICAL` → `deterministicLevel=CRITICAL`, `finalLevel=CRITICAL`, `loweringAttempted=True`, exit 0. A proposal *above* the deterministic level still wins (`final=CRITICAL`, `loweringAttempted=False`) — it is a true lattice maximum, not a clamp. Unknown signal → exit 1 `unknown_risk_signal` rather than a silent drop. See the deterministic guardrail section for the four attack routes I constructed. |
| **A13** fail safe | **FAIL** | Every reason refuses at exit 1 and freezes `current_phase`, `status`, `approvals`, `artifact_shas` and `state["audit_sha"]` — verified live for `governance_missing`, `governance_blocked`, `governance_stale`, `review_missing`, `review_stale`, `review_failed`, `policy_malformed`, `policy_weakens_baseline`, `unknown_risk_signal`, `quality_malformed`, `quality_unknown_check`, `quality_not_applicable_refused`, `governance_input_malformed`, `reviews_malformed`. All three E2 refusals additionally leave `audit.md` **byte-identical**. But the three E1 refusals reached through `gate approve` and `skip` do **not**: `audit.md` grows by one entry. `state["audit_sha"]` staying unchanged is precisely what makes the defect invisible to the suite. Finding B1. |
| **A14** exit-code contract | **FAIL (with the declared divergence separately accepted)** | The declared new exit-3 path (`governance_record_invalid` in `read_governance_record`) is argued on the merits and pinned by a 3-case parametrised test; I accept it — a corrupt record is a different fact from an absent one, and the precedent (`state_unreadable`, `legacy_state_invalid`, `index_malformed`) is real. However **a second, undeclared exit-3 outcome is newly reachable**: `audit verify` → `audit_chain_broken` after an ordinary T06 refusal at `gate approve`. Finding B1. |
| **A15** invariant 7 | PASS | Independent content search over `README.md`, all of `docs/` except `docs/transition/`, all of `.claude/` and all of `.sdle/`, using a needle set derived by importing `GOVERNANCE_POLICY_BUILTIN` (12 risk-signal ids + the underscored check ids): **zero hits**. No policy default value is restated outside `scripts/sdle.py`. Grep over the 4,334 added lines in the product corpus: `PHASE_SEQUENCE` 0, `PROGRESS_MAP` 0, `PHASE_TO_GATE_KEY` 0, `rate_limits` 0, `baseline_file` 0, `implementation_state_dir` 0. |
| **A16** T02–T05 guarantees | PASS | All named guardrail tests pass unmodified inside the 786. Independently re-driven live: the legacy `.workflow/` dual-read rung still binds with zero WorkItems registered; `init` with a `.workflow/state.json` present still refuses **`legacy_workflow_present`**; `governance assess` under the legacy binding refuses `governance_workitem_required` and writes nothing. `.claude/hooks/` and `SDLE_OWNED_PREFIXES` byte-identical (A5, A9), so `.sdle/` is still not SDLE-owned. |
| **A17** non-behaviour-change proof | PASS | `test_governance_changes_no_lifecycle_behaviour` inspected line by line, not merely observed green. Four repositories cloned **before** any run. Anti-vacuity clause 0 is genuine: it asserts `finalLevel` is LOW/LOW/CRITICAL/CRITICAL and that three distinct classification types were recorded, so the variants demonstrably took effect. All four traversals equal `EXPECTED_TRAVERSAL`; ordered lifecycle audit events identical modulo a **narrow** two-member exclusion set (`governance_recorded`, `artifact_reviewed`); approvals 8/8 `approved`; `artifact_shas` key sets identical at 8. The variant is injected by overriding the *fixture* method; no engine function is patched. |
| **A18** would-be gate set inert | PASS | Re-derived by my own AST pass over `scripts/sdle.py`: the only functions referencing `required_gate_set` / `wouldBeRequiredGates` are `cmd_governance_assess` and `cmd_governance_gates`; the only readers of `finalLevel` are `evaluate_risk`, the two governance commands and `record_governance_audit`; the only references to `flow` are `evaluate_classification` and `record_governance_audit`. Not one phase-movement function (`apply_advance`, `cmd_advance`, `cmd_gate_*`, `cmd_skip`) touches any of them. The differential's clause 3 shows the would-be set genuinely differs across risk and across classification while the traversal does not move. |
| **A19** staleness enforcement real | PASS | Live, through the real CLI. PASS review → append one byte to the artifact → `gate approve` refuses **`review_stale`** with `reviewed_sha != current_sha` both present in `data` → re-review → approval succeeds. Drift path: approve Gate 2, drift the spec, `drift check --queue`, `gate approve` refuses **`review_stale`** → review the drifted content → re-approval succeeds and re-baselines. `review_missing` and `review_failed` each reproduced. All four E2 refusals leave state **and** `audit.md` byte-identical. |
| **A20** invariants 3 and 8 | PASS | Grep over all 4,334 added lines in `scripts/`, `tests/`, `.claude/`, `README.md`, the Reference Guide and `ADR-003`: `speckit-` **0**, `/speckit.` **0**. `sdle-architect` matches 9 lines, every one a recorded actor *string* in T06's own tests or one descriptive sentence in ADR-003; `subagent` matches 6, all inside `test_t06_creates_no_subagent`, its docstring and ADR-003's statement that none is created; `Task(` matches 1, inside that test's forbidden-token list. `.claude/agents/` byte-identical via A5. |
| **A21** invariant 4 | PASS | `modules/gate-protocol.md` diff is +3 / −1: steps 1–3 (which display artifact content) are untouched, the old step 4 is renumbered to 5, and the review status is a **new** step 4 plus a **new** `Review:` line in the prompt format. Added alongside the content, never substituted for it. |
| **A22** no future-phase leakage | PASS | Over the same corpus: `conditional gate` matches 1 line, ADR-003's prose "eight **unconditional** gates" — a substring hit, not a mechanism. `gate_policy` 0, `flow_selection` 0, `flow routing` 0, `baseline.json` 0, `risk_tier` 0, `adaptive` 0. `brownfield`/`discovery` match 2 lines each, both the `BROWNFIELD_DISCOVERY` **enum value** in the §12 classification vocabulary, which is validated and recorded and read by nothing on any transition path (A18). No gate became conditional; the fixed 18-phase sequence is intact (`lint-skill`); the `.workflow/` rung, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal all still work (A16); `implementation-state/` is still empty. |
| **A23** TP-003 | PASS | `git diff --name-status 475795a ccb9835 -- tests/` → **10 M, 0 D, 0 R, 2 A**. `git diff --numstat` shows **0 removed lines in every test file except `tests/test_units_repo_config.py` (4)**. I read every hunk of all ten files: in nine of them every hunk is purely additive (`review_for_gate` / `record_governance()` setup calls and six cross-module imports); no assertion was relaxed, removed or reordered. The 4 removed lines in `test_units_repo_config.py` are row 4's docstring plus one `for` line. `grep -rn "xfail" tests/ --include=*.py` matches **nothing** (exit 1). `grep -rn "skipif|pytest.mark.skip|pytest.skip" tests/ --include=*.py` matches exactly one line, the pre-existing `tests/test_units_infra.py:49: @pytest.mark.skipif(SH is None, reason="POSIX sh not available")`. Quoted, not asserted empty. |
| **A24** Python 3.11 / CI | NOT_RUN | Host is Python **3.13.0**; the branch is local-only. **Python 3.11: NOT_RUN. CI: NOT_RUN / UNKNOWN.** No outcome predicted. |

---

## Regression evidence

Everything below was driven through the real CLI as subprocesses in throwaway projects outside pytest, so nothing depends on a fixture that could mask the behaviour.

**E1 is at the choke point and all three movers inherit it.** `governance_precondition` is called from `apply_advance` and nowhere else (my own AST pass); `apply_advance` has exactly three callers. Reproduced individually:

- `advance --to gate_constitution` with no record → exit 1 `governance_missing`, state byte-identical.
- `gate approve` from a workflow already standing at the gate, with E2 satisfied, record removed → exit 1 `governance_missing`, `current_phase` still `gate_constitution`, `approvals["gate_constitution"]` still `None`.
- `skip --confirm` with `requirements/` edited underneath → exit 1 `governance_stale`, phase unchanged.

E1 fires **after** `forward_jump` and `gate_not_approved`, so no pre-existing refusal is masked.

**A blocking finding stops progression and the record survives.** `governance assess` with `acceptance_criteria: FAIL` → exit 1 `requirements_quality_blocked`, and `governance.json` exists with `quality.result == "BLOCKED"`, `blocking == ["acceptance_criteria"]`. `init` then succeeds; the first `advance` refuses `governance_blocked` with the finding text in `data`; the whole state tuple is frozen; re-assessing with the check passing lets the same `advance` through.

**E2 is at both approval sites.** `review_precondition` is called from `cmd_gate_approve` and `_approve_drift` only. `review_missing`, `review_failed`, `review_stale` each reproduced; the drift re-approval path refuses `review_stale` against a review of the pre-drift content and succeeds after the drifted content is reviewed. `audit verify` exits 0 afterwards.

**Legacy carve-out is bounded and behaves as declared.** With `.workflow/` present and zero WorkItems registered, a full `gate approve` runs with no governance record and no review and is not refused; with a WorkItem bound the same sequence refuses. `governance assess` under the legacy binding refuses `governance_workitem_required` and creates nothing. T11 removes the rung.

**Purity and pre-`init` operation.** A recursive SHA map of the whole project root before and after `governance assess` differs by exactly two added files — `workitems/<id>/.sdle/governance.json` and `workitems/<id>/.sdle/evidence/governance-<execution-id>.json` — and **zero** changed files. No `state.json`, no `audit.md`. `governance policy`, `governance show` and `governance gates` leave the SHA map byte-identical. `audit verify` exits 0 after the subsequent `init`, so the pre-`init` write does not disturb the chain. The `governance_recorded` ledger entry lands at the first phase movement and is de-duplicated by `executionId` (1 entry after two movements), and it names the lowering attempt verbatim: `proposed LOW, final HIGH; Claude proposed a lower level and it had no effect.`

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | PASS | **`786 passed in 990.27s (0:16:30)`**, **`RAW_EXIT=0`**, 15 output lines, `short test summary` count **0**. |
| `python -m pytest --collect-only -q` (HEAD) | PASS | **`786 tests collected`** — collected == passed. |
| `python -m pytest --collect-only -q` (pristine `git archive 475795a`) | PASS | **`569 tests collected`** — baseline re-derived, not inherited. |
| `python scripts/sdle.py lint-skill` | PASS | raw exit 0, 22 PASS / 0 FAIL, `Parsed 19 phases, 8 gates, 15 migration rows`, v1.15 in four locations. |
| `python tools/transition/validate.py` | PASS | raw exit 0, `TRANSITION_VALID: complete=6/12 next=T06`. |
| `git diff --exit-code 475795a ccb9835 -- <A5 list>` | PASS | raw exit 0. |

The `rtk` false-green trap was avoided on every run: the suite went through `rtk proxy "..."` with the raw exit read by `echo $?` with no pipe in between.

---

## Future-phase leakage check

No leakage found.

- **T07 (flow selection).** No gate is conditional. `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP`, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE` and `templates/state.json` are byte-identical. `classification.flow` is validated by `evaluate_classification`, recorded with `advisory: true`, named in the audit line by `record_governance_audit`, and read by nothing else — proved by an AST reference scan, not by grep alone. The would-be gate set is reachable only from `cmd_governance_assess` and `cmd_governance_gates`.
- **T08 (brownfield / baseline).** `baseline.json` written by nothing; `baseline_file` and `implementation_state_dir` appear 0 times in the added lines; `implementation-state/` still holds only `.gitkeep`. `BROWNFIELD_DISCOVERY` appears only as a §12 classification enum value.
- **T09 (risk-adaptive gates).** Risk is computed and recorded and consulted by no gate. `read_repo_config` is byte-identical, so T05 NB-4 was not adopted; no README lint rule was added.
- **T10 (subagents).** No agent is created, registered or invoked; `.claude/agents/` byte-identical; `sdle-architect` is a recorded actor string only.
- **T11 (legacy removal).** The dual-read rung, `migrate-workflow` and the unconditional `legacy_workflow_present` refusal all still work (re-driven live).

---

## Test weakening / deletion check

Zero deletions, zero renames, zero skips, zero xfails.

- `git diff --name-status 475795a ccb9835 -- tests/`: **10 M, 0 D, 0 R**, plus 2 A.
- Removed lines per test file (`--numstat`): `test_units_repo_config.py` 4; **every other test file 0**.
- I read every hunk of the nine other modified test files. All are inserted setup calls (`review_for_gate(...)`, `record_governance()`) plus six `from test_units_artifact_review import review_for_gate` imports. No assertion text changed anywhere.
- `tests/conftest.py` gained only `Project.record_governance()` and one call inside `started`. `bare_project`, `project`, `git_project`, `started_git` and `isolated_git_identity` keep their bodies. `grep -c review_for_gate tests/conftest.py` = **0**.
- **Row 4's rewrite is genuinely stronger, and I proved it rather than reading it.** I re-implemented the three clauses and ran them against the unmodified source (all PASS) and against three planted mutations of `scripts/sdle.py` held in memory. Planting a policy read in a helper named `_quietly_consult_policy` — outside every old prefix — is caught by clause (a) and by `test_the_repository_configuration_members_have_a_closed_reference_set`, while the **original prefix clause (c) still passes**, which is exactly the silent-guardrail-death the plan's F6 warned about. Planting the same read inside `apply_advance` is likewise caught by (a) and (c) misses it. Planting a `config_file` read in `cmd_advance` is caught by (b), (b2) and (c). The rewrite supersedes; it does not evade.
- The declared enumeration divergences (setup calls in `test_units_workitem.py`, `test_units_workitem_resolution.py`, `test_units_transitions.py`) are all inserted calls with no assertion touched, and the reasoning — E1 sits at *phase movement*, not at `approve`, so the plan's "49 approve literals" bound was the wrong bound — is correct.

---

## Deterministic guardrail check

**The risk-floor asymmetry is enforced by the core, and I could not talk past it.** Four attack routes, all closed:

1. **Model-supplied proposal.** `proposedLevel: LOW` against a `payment_or_financial` floor → `finalLevel HIGH`, `loweringAttempted True`, exit 0. Against an `uncertainty: CRITICAL` floor → `finalLevel CRITICAL`, `loweringAttempted True`, exit 0. `final = max(deterministic, proposed)` over an index-ordered lattice; there is no branch in `evaluate_risk` that can return below `deterministicLevel`.
2. **Smuggling policy into the input.** An input carrying `"severity": "advisory"` on a failing blocking check → exit 1 `quality_unknown_check`. An input carrying a top-level `blocking_checks` or `policy` key → exit 1 `governance_input_malformed`. Severity is read from the policy only.
3. **Hand-edited policy override.** All **eight** weakening shapes I could construct are refused **`policy_weakens_baseline`** with the offending key named: drop a blocking check, widen `optional_checks`, lower a signal weight, raise a level threshold, delete hard floors, lower a hard floor's level, empty `hard_floors` entirely, remove a would-be required gate. All **nine** malformed shapes are refused **`policy_malformed`**: invalid JSON, JSON array, JSON scalar, unknown top-level key, wrong value type, negative weight, boolean weight, phantom gate key, and a *directory* in place of the file. Nothing returns a default from an exception handler; presence and readability are correctly treated as different questions. Strengthening works and is observably stricter: adding a `CRITICAL` floor on `external_api_surface` moved that assessment's `finalLevel` to `CRITICAL`.
4. **Silent signal drop.** An unrecognised signal id → exit 1 `unknown_risk_signal`, not a silent zero-weight.

**Freshness and staleness are derived, never stored.** The emitted review record's key set is `{actor, comments, evidenceId, path, result, reviewType, sha256, timestamp}` — no boolean. Hand-planting `"fresh": true` and `"current": true` into `reviews.json` and then mutating the artifact still produces `review_stale`. A malformed `reviews.json` is refused `reviews_malformed` rather than read as "nobody reviewed it".

**The two SHA mechanisms stay separate.** After a full approval, `artifact_shas` holds only gate keys and `reviews.json` holds only review records; no gate key appears in the ledger and no review data appears in `artifact_shas`. `cmd_artifact_record`, `sha256_file`, `resolve_artifact_path`, `compute_drift`, `cmd_drift_rebaseline` are all byte-identical, so no parallel SHA registry was forked. Invariant 7 holds.

**Cross-platform.** `review_key` normalises backslashes and resolves absolute paths to a repo-relative POSIX key; a review recorded with `workitems\...\spec.md` lands under the same single key as its POSIX spelling (ledger shows 2 distinct keys for 2 distinct artifacts, not 3). `requirements_sources` sorts by repo-relative POSIX path and digests `"<path> <sha>"` pairs, so the digest is order- and platform-stable. Paths outside the project root are refused `review_path_outside_project`.

---

## State / audit / evidence integrity check

This is where the phase fails. See Finding **B1** for the full reproduction.

Everything else in this area is sound: `write_atomic`, `save_state`, `read_state`, `verify_audit_chain` and `touch_lock` are byte-identical; `append_audit` renders byte-identically when `review`/`evidence_id` are absent and inserts the two new lines **before** `**Prev:**`, which remains the last rendered line of every entry; evidence documents follow the existing `<kind>-<execution-id>.json` convention under `evidence/`; `governance.json` and `reviews.json` have one writer each; `state.json` and `audit.md` keep exactly their prior writer set.

---

## Cross-platform / path handling check

Covered under the deterministic guardrail section. No PowerShell-only cmdlet was introduced (`lint-skill` check `no_powershell_only_cmdlets` passes). `sdle.sh` and `sdle.ps1` byte-identical. `SKILL.md` remains CRLF in the working tree with a 10-insertion / 0-deletion diff, so the existing convention was preserved rather than renormalised.

---

## Artifact review/SHA freshness check

Bound to the exact current SHA, verified behaviourally rather than by reading the code:

- "Currently reviewed" is recomputed on every call from `sha256_file` of the artifact as it stands, matched against `record["sha256"]` lowercased. No stored flag exists and a planted one has no effect.
- A one-byte append after a PASS review blocks `gate approve` with `review_stale`, carrying both `reviewed_sha` and `current_sha` in `data`, until the current content is re-reviewed.
- The same rule governs drift re-approval through `_approve_drift`, which is the case TP-011's staleness diagram is drawn for.
- A `FAIL` review of the current content blocks approval; a later `PASS` on the same SHA clears it.
- The audit linkage carries every §12 minimum field: `event = artifact_reviewed`, `**Artifact:**`, `**Artifact SHA (SHA-256):**`, `**Review:** <type> | <result> | <actor_type>:<actor_name>`, `**Evidence:** …/evidence/review-<execution-id>-<n>.json`.

---

## Findings

### Blocking

**B1 — A T06 refusal on the `gate approve` path writes a false approval into the append-only audit ledger and leaves the hash chain broken.**

`cmd_gate_approve` appends its `gate_approved` audit entry — including `**Gate Decision:** APPROVED` — and only *then* calls `apply_advance`. T06 puts `governance_precondition` inside `apply_advance`. At `475795a` `apply_advance` had **no reachable raise** from `cmd_gate_approve` (the target is always `NEXT_PHASE[gate_phase]` so `forward_jump` cannot fire; the approval is written `"approved"` two statements earlier so `gate_not_approved` cannot fire; a `None` current phase is caught earlier by `not_at_gate`). E1 is therefore the **first refusal ever reachable there**, and it lands downstream of an irreversible append to `audit.md`.

Reproduced twice through the real CLI, once by an entirely ordinary user action:

```
# standing at gate_constitution, artifact reviewed PASS,
# the user edits a file under requirements/ (a normal thing to do)
gate approve --gate gate_constitution
  -> exit 1  governance_stale
  audit.md entries 5 -> 6
  ledger now contains 1x "**Gate Decision:** APPROVED"  for an approval that was refused
  state["audit_sha"] unchanged  (state.json was never saved)
  audit verify -> exit 3  audit_chain_broken
```

The same shape with the record removed yields `governance_missing` and an identical outcome. `header`, `state get`, `gate show` and `drift check` still exit 0, so nothing surfaces the breakage; and after the *next* successful state-writing command the chain re-links and `audit verify` returns to exit 0 — which means **the false approval entry becomes permanent and undetectable**.

Why this is blocking:

- It violates non-negotiable invariant **5** ("on any failure, freeze") and invariant **6** (the audit chain and drift detection assume a single writer and a consistent tail), and the plan's own preserved-invariant 5, "Every new failure path refuses and freezes".
- It makes **exit 3 newly reachable from an ordinary refusal**, which A14 forbids and which the handoff does not declare. The one declared exit-3 divergence (`governance_record_invalid`) is separate and is accepted.
- An audit ledger that records approvals that did not happen is a correctness failure of the product's central evidence artifact, not a cosmetic one.
- **No test detects it.** `frozen()` in `tests/test_units_governance.py` compares `state["audit_sha"]`, and `state.json` is never saved on the refusal path, so `test_gate_approve_inherits_the_same_clause` asserts `frozen(project) == before` and passes while `audit.md` has grown by an entry. The E2 refusals, which fire *before* the append, do leave `audit.md` byte-identical — I verified that separately, which is what isolates the defect to E1's placement relative to the audit write.

The same ordering exists in `cmd_skip`. **There the orphan is pre-existing** — I reproduced it at `475795a` by forcing `status = failed` at a gate phase, where `gate_not_approved` produces the identical `audit_chain_broken` — so `skip` is a widening, not a regression: T06 moves it from a contrived state to any `requirements/` edit. The `gate approve` case has no such precedent and is the blocking half.

This was **partially seen and wrongly dismissed**. `T06-checkpoint-a01-04.md` line 71 records the `cmd_skip` ordering, calls it "pre-existing … and is not T06's to change", and moves on. That reasoning does not transfer to `cmd_gate_approve`, where the refusal is new; and the observation was never carried into `T06-handoff-a01.md`'s declared divergences, so it was not surfaced for verification.

**Remediation direction (for a fresh implementer — I did not change any product code).** Evaluate the governance precondition before any audit write on every phase-movement path, while keeping a single structural enforcement site. The obvious shape is a pre-write guard invoked at the top of `cmd_gate_approve` and `cmd_skip` (and harmlessly again inside `apply_advance`, which is idempotent — `record_governance_audit` already de-duplicates by `executionId`), or hoisting the check out of `apply_advance` into a helper all three commands call before they touch the ledger. The fix must be pinned by a test that compares `audit.md` bytes — not `state["audit_sha"]` — across every refusal on every one of the three movers, because the existing `frozen()` tuple provably cannot see this class of defect. `write_atomic` must not be touched.

### Non-blocking

**NB-1 — `reviews_malformed` is an undeclared refusal reason.** Behaviourally correct and fail-closed (an unreadable ledger is not an empty one), exit 1, but it is not in D9's enumeration nor in A13's list, so it carries no frozen-state assertion. Worth adding to A13's set in a future phase.

**NB-2 — Governance freshness does not cover the policy.** `governance_freshness` compares only the `requirements/` digest. `governance.json` records `policy.sha256`, but nothing ever re-checks it, so installing a *stricter* `.sdle/policies/governance-policy.json` does not invalidate assessments made under the built-in. Inert at T06 because nothing consumes the risk level, but **T09** (risk-adaptive gates) must own it — otherwise a repository could tighten its policy and keep running under a record scored by the looser one.

**NB-3 — The governance record has no integrity binding.** `read_governance_record` validates JSON shape only. A hand-forged `governance.json` would produce a truthful-looking `governance_recorded` audit line naming a risk level that was never computed. Mitigated in practice: `workitems` is in `hooks.py`'s `FENCED` tuple so the write fence blocks a model edit, and the record is git-versioned. Inert at T06 for the same reason as NB-2. Flagged for whichever phase first *acts* on the recorded risk.

**NB-4 — Documentation debt, as declared.** `docs/dry-runs/` shows no governance assessment and no review before a gate (owner T11, alongside T04 N-6). `docs/transition/RESUME.md` remains stale relative to `validate.py`. Both correctly declared and correctly not adopted.

**NB-5 — Handoff accuracy.** Every quantitative claim I re-derived was accurate: 786/569/175/40/+2, 24/24 byte-identical definitions, 175 SKILL.md table rows, `cmd_gate_approve` and `_approve_drift` at +1/−0, `read_repo_config` byte-identical, `grep -c review_for_gate tests/conftest.py` = 0, 10 M / 0 D / 0 R in `tests/`. The single accuracy failure is the omission described in B1: a defect noted in checkpoint 04 did not reach the handoff.

---

## Final result rationale

T06's positive claim is largely proved. The four §12 subsystems are real and deterministic; the security property that matters most — *Claude cannot lower a deterministic policy floor* — held against every route I could construct, including a hand-edited monotone policy override, a crafted proposal, smuggled severity and an unknown signal, and it is enforced by the core rather than by prompt instruction. Staleness genuinely blocks downstream consumption in both the normal and the drift path. The negative claim is proved too: the traversal, the eight unconditional gates, the approvals, the `artifact_shas` key sets and the ordered lifecycle audit events are identical across four repositories differing only in governance, and the anti-vacuity clause makes that identity meaningful rather than trivial. Row 4's containment rewrite is strictly stronger and I demonstrated it catches the exact evasion the plan warned about. The full suite is green at 786 with zero skips, `lint-skill` and `validate.py` both exit 0, and no future-phase leakage or test weakening exists.

Against that stands one defect that the phase cannot ship with. T06 introduced the first refusal reachable in `apply_advance` from `cmd_gate_approve`, and placed it downstream of an audit append that had never previously been followed by a possible failure. The result is that an ordinary, expected refusal — one a user will hit simply by editing a requirements file while standing at a gate — writes an approval that never happened into the append-only ledger and leaves the integrity command reporting exit 3. That is a direct violation of the two invariants this engine exists to guarantee, it is invisible to the test that was written to prove the opposite, and the one place it was noticed it was reasoned away with an argument that does not apply to the path where it is new.

The defect is an ordinary implementation defect — a statement-ordering error with a small, well-understood fix and no architectural, contract or baseline question attached. It does not warrant a blocker. T06 stays `IMPLEMENTED` and returns to a fresh implementer under §24.5.

Exactly one final result is valid: `PASS` or `FAIL`.
