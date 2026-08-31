# T07 Independent Verification — Attempt a01

**Phase:** T07
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

**Commit verified:** `c80f341` ("T07: declarative flow selection (IMPLEMENTED, NOT YET VERIFIED)"), HEAD on `transition/workitem-v1`.
**Prior baseline:** `c0775b3`. **Plan commit:** `77ca0b8` (revision 2; revision 1 at `7dba4b6` is superseded). **Product baseline:** `f8fdaa0`.
**Working tree:** one modified file, `.claude/settings.local.json` — declared out of scope, pre-existing.
**Host Python:** 3.13.0. **Python 3.11 and CI:** `NOT_RUN` / `UNKNOWN`; no outcome predicted.

> The handoff is a claim set, not proof. Every figure below was produced by a command run in this verification context. Where the handoff and my own measurement disagree, my measurement is recorded. The whole `c0775b3..c80f341` diff was reviewed, not only what the handoff narrates.

**Transition-guard refusals encountered — quoted verbatim, not routed around.** Two, both on my own Bash payloads, both resolved by renaming my own tokens exactly as the prior verifier did:

```
PreToolUse:Bash hook error: [python tools/transition/agent_guard.py verifier]: SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape
```

The first fired on the literal `"<module>"` inside an AST script (the `>` tripwire); the second on the English word `copy` in a code comment. Neither was a real mutation. No alternate shell or interpreter was used, and the guard was not patched or re-signed.

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** suite green, collected == passed, zero skips/xfails | **PASS** | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **`901 passed in 1063.04s (0:17:43)`**, **RAWEXIT=0** (captured with no pipe between the command and `$?`). Occurrences of `short test summary` in the captured run = **0**; of `skipped` = 0, `xfail` = 0, `error` = 0. `--collect-only -q` → **`901 tests collected in 0.55s`**, raw exit 0. Per-file collection accounts for the +110 over the 791 baseline exactly: `test_units_flow_model.py` **98** (new), `test_lint_skill.py` **28** (was 17), `test_units_governance.py` **181** (was 180); no other file moved. |
| **A2** `lint-skill` 29/29 at v1.16 | **PASS** | `python scripts/sdle.py --project-root . lint-skill` raw exit **0**; parsed payload `len(checks)=29`, `failed=[]`; `tables_wellformed: Parsed 20 phases, 8 gates, 16 migration rows`; `version_string_consistent: all four locations report v1.16`. |
| **A3** `validate.py` raw exit 0 | **PASS** | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=7/12 next=T07`, raw exit **0** (control-plane SHA manifest verified by the tool itself). |
| **A4** must-not-change list untouched | **PASS** | `git diff --name-only 77ca0b8 c80f341` over `.claude/hooks/`, `.claude/settings.json`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `scripts/README.md`, `.github/`, `.gitignore`, `.gitattributes`, `requirements/`, `tools/`, ADR-001..003, `modules/security-review.md`, `tests/test_integration_01_happy_path.py`, `transition.md`, `baseline.md` → **empty**. `git diff --name-only 77ca0b8 c80f341 -- docs/transition/phases/` filtered for non-T07 → **empty**: no T00–T06 artifact touched. `T07-plan.md` at `c80f341` is **byte-identical** to `77ca0b8` — the implementer did not edit the immutable plan. |
| **A5** compatibility translation, four ways | **PASS** | **(P1)** `test_greenfield_equals_the_happy_path_expected_traversal` imports `EXPECTED_TRAVERSAL` from the untouched transcript test. **(P2)** `GREENFIELD_GOLDEN` literal in `tests/test_units_flow_model.py`, asserted against both the constant and `constants.flows["GREENFIELD"]`. **(P3) re-derived by me:** I parsed `PHASE_SEQUENCE` out of `git show <rev>:.claude/skills/sdle/SKILL.md` with the engine's own `parse_md_table` for **`7dba4b6`, `c0775b3` and `f8fdaa0`** — all three are 19 entries and all three are **element-wise equal** to `constants.flows["GREENFIELD"]` at HEAD. **(P4)** `_mig_1_15` sets `flow = DEFAULT_FLOW` unconditionally when the field is missing or non-string, with no governance symbol in its body. |
| **A6** `test_integration_01_happy_path.py` byte-identical | **PASS** | Raw bytes at HEAD equal `git show 77ca0b8:` bytes (`rawsame=True`, no normalisation needed). It collects 8 tests and they pass in the full run. |
| **A7** **GREENFIELD is not derived from the registry** | **PASS** | Verified **by mutation**, not by reading. `flow_phases` keys are `['BROWNFIELD_DISCOVERY','DEFECT_FIX','HOTFIX','ITERATIVE']` — `GREENFIELD` is **not** a row. Registry = **20** entries; flow sizes 19/19/17/15/11 — **no flow has 20**. Appending `zz_stray_phase` to a live `Constants.phase_sequence` left `flows["GREENFIELD"]` at **19 entries, identical tuple**; inserting a fully-tabled `zz_stray` row made `every_registry_phase_is_used_by_some_flow` report `(False, "orphaned=['zz_stray']")`. Second mutation: setting `flow_phases["GREENFIELD"]` while keeping all four real rows makes `flow_table_covers_the_required_flows` fire alone with `GREENFIELD must not be a FLOW_PHASES row` — so the "declared GREENFIELD row" case is caught explicitly, not only via coverage arithmetic. |
| **A8** five flows drive end to end, pairwise distinct except the declared pair | **PASS** | Five scratch git-backed repositories, real CLI as a subprocess, one flow each, walked gate by gate to `complete`. Observed **entries / non-terminal (final progress) / gates approved**: GREENFIELD 19 / 18 (`18/18`) / 8; BROWNFIELD_DISCOVERY 19 / 18 (`18/18`) / 8; ITERATIVE 17 / 16 (`16/16`) / 7; **DEFECT_FIX 15 / 14 (`14/14`) / 6**; HOTFIX 11 / 10 (`10/10`) / 3. Each observed traversal equals that flow's declared `phases` list exactly. `audit verify` exit **0** in all five. Pairwise set comparison: the **only** equal pair is `('GREENFIELD','BROWNFIELD_DISCOVERY')`. |
| **A9** `impact_analysis` is real, governed and **gateless** | **PASS** | Registry position **2** (`phase_sequence.index+1 == 2`). Present in exactly `{DEFECT_FIX, HOTFIX}`. `init` under both lands on it (observed live); under GREENFIELD/BROWNFIELD_DISCOVERY it lands on `constitution_draft`, under ITERATIVE on `spec_draft` — three distinct landings across five flows. **No** `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP` or `GATE_TO_EXECUTION_PHASE` entry (all three tables still hold exactly the eight gate keys). `templates/state.json` `approvals` has exactly the **eight** pre-T07 keys, byte-compared to `77ca0b8`; a full DEFECT_FIX run ended with the same eight. `artifact record --phase impact_analysis` fingerprinted `reviews/impact-analysis-<ts>.md`, the SHA matched my own `sha256` of the file, and exactly **one** `artifact_recorded` event was appended. `artifact review --type impact-analysis` bound the review to that exact SHA; `artifact reviews --path <same>` reported `"current": true`, and after I rewrote the file it reported `"current": false` with the old SHA still in `reviewed_shas` — TP-011 staleness by the existing mechanism, no new code. Its `phase-execution.md` block contains **0** occurrences of `feature bind` and **0** of `featureDirectory` (block extracted by regex and counted). `gate approve --gate gate_impact_analysis` refuses `unknown_gate` and leaves `audit.md` and `state.json` byte-identical. |
| **A10** `flow_mismatch` leaves the ledger byte-identical on all three paths | **PASS** | Reproduced independently in three scratch repositories: re-assess with a different flow mid-run, then (1) `advance` → exit **1**, `flow_mismatch`; (2) `gate approve` → exit **1**, `flow_mismatch`, and no approval recorded; (3) `skip --confirm` after arming → exit **1**, `flow_mismatch`, phase unmoved. In **all three**, `sha256(audit.md)` and `sha256(state.json)` are **identical before and after**, and `audit verify` exits **0**. Payload carries `{bound, proposed, workitem}` and the message names both remedies. |
| **A11** gate discipline under a flow | **PASS** | `advance --to impact_analysis` under GREENFIELD → `forward_jump` with `data["in_flow"] is False` (**not** `unknown_phase`); `advance --to not_a_phase_at_all` → `unknown_phase`; `advance --to gate_security` (in flow, far ahead) → `forward_jump` with `in_flow: True`. Under HOTFIX, `advance --to constitution_draft` → `forward_jump`, `in_flow: False`. `gate approve` for `gate_design` and `gate_tasks` under HOTFIX → `not_at_gate`, ledger and state byte-identical, approvals map untouched. `gate_not_approved` fires at each flow's **own** first gate — parametrised live over all five flows. `required_gate_set` callers are exactly `['cmd_governance_assess','cmd_governance_gates']` (AST) and its source is byte-identical to `77ca0b8`. |
| **A12** closed caller sets | **PASS** | AST over `scripts/sdle.py`: `apply_advance` callers = `['cmd_advance','cmd_gate_approve','cmd_skip']`; `governance_precondition` callers = `['apply_advance','cmd_gate_approve','cmd_skip']`. **`cmd_init` appears in neither** — governance did not become an `init` precondition by the back door. |
| **A13** preserved functions byte-identical | **PASS** | AST extract-and-compare against `git show 77ca0b8:scripts/sdle.py` — all 15 **identical**: `write_atomic`, `append_audit`, `save_state`, `read_state`, `bind_workitem`, `resolve_decision`, `cmd_migrate_workflow`, `compute_drift`, `cmd_repo_staleness`, `governance_precondition`, `required_gate_set`, `cmd_artifact_record`, `cmd_artifact_review`, `SDLE_OWNED_PREFIXES`, `RUNTIME_FREE_COMMANDS`. |
| **A14** `_mig_1_15` | **PASS** | Live: a state hand-set to `1.15` with `flow` removed migrated with terminal step `1.15->1.16` to `flow: "GREENFIELD"`, then re-running `migrate` produced `steps: []` (idempotent), and the workflow continued to traverse correctly (`advance` exit 0 to `gate_constitution`). Function body contains no governance symbol. Chain from `1.13` and `1.14` covered by the suite; my own run confirmed the terminal step. |
| **A15** HOTFIX identity and load-time refusal | **PASS (with the implementer's declared correction)** | `set(HOTFIX) - {"impact_analysis"} == set(MANDATORY_FLOW_PHASES)` → **True** (exact equality). Every flow is a superset of the 10-phase floor → **True**. `len(HOTFIX) <= len(flow)` for every flow → **True**. **The plan's literal third clause is false and the implementer is right to have replaced it:** `set(HOTFIX).issubset(...)` is `False` for GREENFIELD, BROWNFIELD_DISCOVERY and ITERATIVE, because HOTFIX carries `impact_analysis` and those three deliberately do not. Load-time enforcement confirmed live: a hand-broken `FLOW_PHASES` (missing mandatory phase) makes `advance`, `flow show` and an unknown `state["flow"]` all refuse **`flow_table_invalid`, exit 3**, never a default. `lint-skill` over the same five breakages (unknown phase, out of order, duplicate, missing mandatory, missing terminal) still returns **per-check failures** rather than raising. |
| **A16** GREENFIELD views are lint-pinned and byte-stable | **PASS** | Derived GREENFIELD progress equals `PROGRESS_MAP` for **all 19** phases (zero mismatches). `PHASE_TO_GATE_KEY`'s gate-number column equals the derived numbering (zero mismatches). Rendering the eight gate labels for GREENFIELD reproduces the **pre-T07 literals byte-for-byte** (`Gate 1: Constitution Approval` … `Gate 8: Security Review Approval`; zero differences against the `77ca0b8` table). `PROGRESS_MAP`'s **19 rows are byte-identical** to `77ca0b8`. HOTFIX renders `Gate 1/2/3` for spec/implement/security — flow-relative, as designed. |
| **A17** no traversal function reads `NEXT_PHASE` | **PASS** | Every textual `next_phase` occurrence in `scripts/sdle.py` mapped to its receiver: `consts.next_phase` appears **only** in `load_constants` (write), `run_sync_checks` (×2, lint) and `cmd_constants` (dump). Every other occurrence is `flow.next_phase(...)` — the `Flow` method. `next_phase_chains_sequence` passes over the 20-entry registry. The suite additionally closes the naming loophole (`test_every_constants_instance_in_the_engine_is_named_consts`). |
| **A18** no linter check weakened, 22 → 29 | **PASS** | `lint-skill` run in a `git archive 77ca0b8` scratch tree → **22** checks, exit 0. At HEAD → **29**, exit 0. Name-set comparison: **7 added, 0 removed**. I diffed `run_sync_checks` and `_check_no_hardcoded_progress` source-to-source. The two re-targeted checks still assert **exact equality in both directions** (`phase_set_matches_progress_map` now against GREENFIELD's phase set) and the denominator check's expected value is unchanged in effect (`greenfield.phase_count` = 18). The one broadening is the optional ordinal in the block-header regex, over-compensated by `execution_block_numbers_are_the_greenfield_positions`, which reports `all 17 block ordinals are GREENFIELD positions` — 17 previously unchecked restated constants now pinned. |
| **A19** exactly one binder, read-only reads | **PASS** | AST writer set for `state["flow"]` is exactly `{cmd_init, _mig_1_15}`. The only parser additions in the whole `sdle.py` diff are `flow` and `flow show` — there is no `flow set`/`flow select`. A recursive SHA map of a scratch project across `flow show`, `constants`, `governance show`, `governance gates`, `state dump`, `artifact reviews` showed **0 added, 0 removed, 0 changed** files. `flow show` with no WorkItem refuses `workitem_required`; with no state it refuses `state_unreadable` (exit 3) — the engine's existing convention, not a new default. |
| **A20** two WorkItems, different flows, independent | **PASS** | One repository, `alpha-one` bound GREENFIELD and `beta-two` bound HOTFIX. Driving `beta-two` all the way to `complete` (`10/10`) left `alpha-one`'s `state.json` **and** `audit.md` SHA-identical. `beta-two`'s completion summary carries `"flow": "HOTFIX"` alongside the pre-existing keys, none removed. |
| **A21** TP-003 file-level discipline | **PASS (one disclosed deviation, see NB-1)** | `git diff --name-status 77ca0b8 c80f341 -- tests/` → ten `M`, one `A`, **zero `D`, zero `R`**. `conftest.py` shows exactly the one permitted value change plus six comment lines — no fixture, helper, signature or `Project` method added or changed. `test_integration_01_happy_path.py` shows no change at all. `test_lint_skill.py` adds 11 functions and removes **no `def` line** (verified by scanning every `-` line for `def`); its three removed lines are planted-fixture literals inside two existing firing tests, whose assertions are unchanged. |
| **A22** no skip/xfail added | **PASS** | Repository-wide search under `tests/` for skip/xfail markers yields exactly one hit, the pre-existing `tests/test_units_infra.py:49` `@pytest.mark.skipif(SH is None, …)`, which did not fire — the captured 901-test run has no `short test summary` section and zero `skipped`/`xfail` tokens. |
| **A23** dry-run disposition | **PASS** | All nine transcripts byte-identical to `77ca0b8` after CRLF/LF normalisation (four of them differ only in raw line endings, which is a checkout artefact, not a content change — I normalised before concluding). `impact_analysis` appears in none of them. The only `docs/dry-runs/` change is the six-line disposition section in `README.md`. Judged against contract §13: the disposition is explicit, states that all nine remain valid, byte-identical and GREENFIELD, states that no transcript is authored for the other four flows and why, and states that removing the legacy fixed-sequence structures the transcripts describe is **not** done here. That satisfies §13's "dry-run behavior has explicit disposition" honestly. |
| **A24** write fence permits the artifact path | **PASS** | `.claude/hooks/hooks.py write-fence` driven directly with real payloads, reading the emitted decision on stdout (an exit-code-only check would be a false green — the guard emits a JSON `deny` and still exits 0): `reviews/impact-analysis-<ts>.md` → **permit**; `reviews/security-review-<ts>.md` → **permit**; `workitems/wi-a/.sdle/state.json` → **deny**; `workitems/wi-a/reviews/impact.md` → **deny** (which is exactly why the project-root `reviews/` path was necessary); `.workflow/state.json` → **deny**; `requirements/todo-api.md` → **deny**; `workitems/wi-a/specs/001-x/spec.md` → **permit**. `.claude/hooks/` is byte-identical to `77ca0b8`. |
| **A25** no future-phase leakage | **PASS** | See the leakage section below. |
| **A26** Python 3.11 / CI | **PASS** | Recorded as `NOT_RUN` / `UNKNOWN`. Host is 3.13.0. **No outcome is predicted.** |

---

## Regression evidence

**Behaviour was supposed to change here, so the burden is inverted: I verified it changed exactly where intended and nowhere else.**

- **GREENFIELD is untouched, proved three independent ways.** The nine dry-run transcripts and `test_integration_01_happy_path.py` are byte-identical and green with zero edits; my own end-to-end GREENFIELD drive reproduced the transcript traversal, `18/18`, 8 gates; the pre-T07 `PHASE_SEQUENCE` parsed out of Git at three separate revisions is element-wise `constants.flows["GREENFIELD"]` at HEAD; and the eight GREENFIELD gate labels render byte-identically to the pre-T07 literals.
- **The four non-GREENFIELD flows now traverse differently, and only because of the flow.** Five clones at identical LOW risk land on three distinct phases. The T06 differential was re-targeted (not dropped) to hold the flow constant and vary risk and type, with explicit guard clauses asserting the flow really was held constant — so its null result cannot pass for the uninteresting reason.
- **B1 / NB-6 not regressed.** The `flow_mismatch` refusal is a pure reader placed ahead of every `append_audit` in `apply_advance` and in both early prechecks. I reproduced all three refusal paths and observed byte-identical `audit.md` and `state.json` and `audit verify` exit 0 each time. The three-step ordering also keeps `governance_stale` unmaskable — the suite pins this and the ordering is visible in the source.
- **Legacy rung intact.** A repository with a legacy `.workflow/state.json` and no WorkItem still binds it (`state dump` exit 0), still migrates (`1.15->1.16`, `flow: GREENFIELD`), `init` still refuses `legacy_workflow_present`, and `migrate-workflow` left `.workflow/state.json` **byte-identical**. `cmd_migrate_workflow` is in the byte-identical set.
- **Drift and staleness need no flow edits.** `compute_drift` and `cmd_repo_staleness` are byte-identical; out-of-flow gates are never approved, so both remain flow-correct with zero changes.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **RAW EXIT 0** | **`901 passed in 1063.04s (0:17:43)`**; `short test summary` occurrences = **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | RAW EXIT 0 | **`901 tests collected in 0.55s`** — collected == passed; per-file breakdown re-derived |
| `python scripts/sdle.py --project-root . lint-skill` | **RAW EXIT 0** | 29 checks, 29 PASS, `failed=[]`, `Parsed 20 phases, 8 gates, 16 migration rows`, `all four locations report v1.16` |
| same, in a `git archive 77ca0b8` scratch tree | RAW EXIT 0 | **22** checks — the A18 baseline; name diff = 7 added, 0 removed |
| `python tools/transition/validate.py` | **RAW EXIT 0** | `TRANSITION_VALID: complete=7/12 next=T07` |
| Five end-to-end flow drives, real CLI as a subprocess | all complete | 19/18/8, 19/18/8, 17/16/7, **15/14/6**, 11/10/3; `audit verify` exit 0 ×5 |
| Three `flow_mismatch` reproductions | all exit 1 | ledger and state byte-identical, `audit verify` exit 0 ×3 |
| `python .claude/hooks/hooks.py write-fence` × 7 payloads | decisions read from stdout | permit/permit/deny/deny/deny/deny/permit as listed under A24 |
| Registry-mutation experiments (×3) | as expected | GREENFIELD unchanged; orphan check fires; declared-GREENFIELD-row check fires alone |
| `python --version` | — | **3.13.0** |

No `os error 112` and no I/O error appeared in any run. The F1 `ENVIRONMENT_FLAKE` procedure was treated as **VOID**; no failure occurred that would have needed it.

---

## Future-phase leakage check

- **T08 (§14).** No discovery phase in the registry — the registry gained exactly one phase, `impact_analysis`. No `.sdle/baseline.*` is written or read: the only `baseline.json` reference in `sdle.py` is the pre-existing reserved path property, and both `README.md` and the Reference Guide still describe it as reserved and unwritten. No baseline validity check was added anywhere, including for ITERATIVE. `BROWNFIELD_DISCOVERY` still traverses identically to GREENFIELD, and `test_brownfield_discovery_is_greenfield_until_t08_changes_it` names **T08 (contract §14)** as the owner of changing it, so T08's edit cannot be silent.
- **T09 (§15).** The boundary held exactly where the task said to look: T07 selects which *phases* execute; nothing makes gate *requirements* policy-driven. `governance gates` still emits `advisory: true` (observed live), and its reworded note says gates *within the selected flow* run unconditionally — which is true. `required_gate_set` is byte-identical and is called only by `cmd_governance_assess` and `cmd_governance_gates`; no phase-movement function touches it. `impact_analysis` is in two flows because the flow table says so, never because of a risk level. The `required_gates_by_*` policy keys are read by nothing in traversal.
- **T10 (§16).** `git diff --name-status` over `.claude/` shows **five modified files and zero additions** — no product subagent, no skill split, no delegation. Invariant 8 is intact: nothing holding a gate was moved out of the parent.
- **T11 (§17).** §13's legacy-structure removal was deliberately **not** performed. `NEXT_PHASE` (20 rows), `PROGRESS_MAP` (19 rows, byte-identical), `PHASE_LABEL_MAP` and `PHASE_TO_GATE_KEY`'s gate-number column all survive and all remain linted. The legacy `.workflow/` dual-read rung, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal all still work (verified live).
- **No second new phase.** The registry grew by exactly one entry. §13's other sketch names remain mapped onto existing phases.
- **No ninth gate.** `gate_impact_analysis` appears nowhere in `.claude/`, `scripts/sdle.py` or `templates/state.json`. Its only occurrences under `tests/` are **negative** assertions proving absence (`assert "gate_impact_analysis" not in …`, plus one `unknown_gate` refusal case); the remainder are in transition documentation. I read the context of every hit before concluding.
- **No deferred §27 construct.** `Flow` is an immutable ordered subset of a fixed registry with a position, a next-phase lookup and derived ordinals. No branching, no loop, no parallelism, no dynamic insertion, no policy DSL.

---

## Test weakening / deletion check

- `git diff --name-status 77ca0b8 c80f341 -- tests/`: **zero `D`, zero `R`**, ten `M`, one `A`.
- **No assertion was weakened.** Every `M` falls in TP-003 category 2 and is a value or subject change forced by T07's own change: `1.15` → `1.16` literals, the added `1.15->1.16` migration step, `phase_count` 18 → 19 (the *registry's* count — both sites carry a comment saying GREENFIELD's is still 18), and the `advisory` flag flipping to `False` in the classification record.
- **Two rewritten tests, both strictly stronger.** `test_governance_changes_no_lifecycle_behaviour` → `test_risk_and_type_change_no_lifecycle_behaviour`: the old form asserted that four variants naming three different **flows** traverse identically, which after T07 asserts the opposite of the design. The rewrite holds the flow constant, keeps the whole risk/type half, and adds guard assertions that the flow really was constant; the positive half is asserted separately by a new test that drives five clones at identical risk. `test_classification_is_marked_advisory_in_the_record` → `test_the_classification_flag_no_longer_claims_to_be_advisory`: now asserts both that the record says `False` **and** that `governance gates` still says `True` — the T07/T09 boundary in one test.
- `test_no_phase_movement_function_consults_the_would_be_gate_set` and `test_the_phase_movement_prefixes_actually_match_something` were not modified and pass.
- `tests/conftest.py`: the one permitted value change plus a six-line explanatory comment. Nothing else.
- `tests/test_lint_skill.py`: 11 added functions, **no `def` line removed**. See NB-1.
- I spot-read the load-bearing new tests rather than trusting the checkpoint narrative (the task's precedent warning). `test_a_new_registry_row_does_not_join_greenfield`, the three closed-reader-set tests, the three `flow_mismatch` ledger tests and the approvals-key-set test all make real, non-vacuous assertions against real CLI runs or real parsed constants, and several add explicit anti-vacuity guards.

---

## Deterministic guardrail check

- **Gate discipline.** `forward_jump` and `gate_not_approved` still fire first in `apply_advance`, ahead of everything T07 adds; both reproduced live in every flow. A gate outside the flow can never be current, and `gate approve` for one refuses `not_at_gate` and writes nothing.
- **It refuses; it does not warn.** `flow_mismatch` is exit 1 with a named remedy; `flow_table_invalid` is exit 3. Neither degrades to a default. No new warning was introduced anywhere.
- **Fail safe.** Every T07 refusal fires before any state mutation and before any ledger append — measured, not assumed.
- **Fail closed, not open.** Two designed-in fail-open risks were probed by mutation. (1) A stray registry row does **not** join GREENFIELD and does make `lint-skill` fail loudly. (2) A hand-declared `GREENFIELD` row in `FLOW_PHASES` is ignored in favour of the frozen constant **and** reported by name — so the worst case is the safe value plus a loud lint failure, never a silently re-shaped lifecycle.
- **Single writer.** `write_atomic`, `append_audit`, `save_state`, `read_state` and `SDLE_OWNED_PREFIXES` are byte-identical; the only new command, `flow show`, is read-only and provably changed nothing on disk.
- **The ladder never guesses.** No resolution rung added; the resolution refusals still fire (`workitem_required` observed).
- **Invariant 3.** The `impact_analysis` block names no Spec Kit skill and no `speckit-*` string; it explicitly forbids invoking SpecKit.
- **Invariant 4.** Strengthened: the `spec_draft` block displays the impact analysis in conversation immediately before the gate prompt, conditional on the file existing, so the human reads it before the first gate downstream of it.
- **Invariant 7.** GREENFIELD has exactly one home. `PROGRESS_MAP`, the gate-number column, the gate ordinals inside `PHASE_LABEL_MAP` and the 17 execution-block ordinals all became lint-pinned derived views — checked for the first time in three of those four cases.

---

## State / audit / evidence integrity check

- Schema `1.15` → `1.16`, one new field `flow`, **`approvals` untouched at eight keys** (byte-compared to `77ca0b8`), `progress` default unchanged. `MIGRATIONS` gained exactly one row, `("1.15","1.16",_mig_1_15)`, and `migration_covers_every_state_field` passes.
- `_mig_1_15` is unconditional and idempotent and reads no governance record — verified live and by reading the function.
- The audit chain survives every new path: `audit verify` exits 0 after five completed flows, after all three `flow_mismatch` refusals, and after the migration cases.
- `flow_selected` is appended exactly once per `init`, in all five flows.
- Evidence documents: the impact-analysis review wrote a real `review-*.json` evidence record under the WorkItem's `evidence/`, and `reviews.json` binds `path` + `sha256`; `artifact reviews` flipped `current` from `true` to `false` after the file changed.
- The completion summary gained `flow` and lost nothing.

---

## Cross-platform / path handling check

- The 783 added lines in `scripts/sdle.py` contain **no** `sys.platform`, `os.name`, `WindowsPath`/`PosixPath` or backslash path literal. The four backslash hits are regex escapes and one `\n` in an f-string. The new engine code is table arithmetic.
- The one new path is a forward-slash, project-root-relative string handed to existing helpers, identical in shape to the security-review path that has shipped since v1.x.
- `no_powershell_only_cmdlets` passes; no shell wrapper changed (`sdle.sh` and `sdle.ps1` are byte-identical).
- I hit the CRLF/LF trap the task warned about while byte-comparing the dry-runs and normalised before concluding: four transcripts differ in raw bytes and are content-identical.
- CI on `ubuntu-latest` / `windows-latest` is **`NOT_RUN` / `UNKNOWN`**. No outcome predicted.

---

## Artifact review/SHA freshness check

- `tools/transition/control-plane.sha256` is verified by `validate.py`, which exits **0** — no control-plane file drifted, and the guard was not patched or re-signed.
- `T07-plan.md` at `c80f341` is byte-identical to its content at the plan commit `77ca0b8`; the implementer did not mutate the immutable plan. Revision 1 remains preserved at `7dba4b6`.
- Governed-artifact freshness in the product: TP-011 review binding for the new phase's artifact was exercised end to end — bound to the exact SHA, reported `current: true`, and flipped to `current: false` on edit with the reviewed SHA retained.
- The eight gate baselines (`artifact_shas`) were written on every completed run, and `drift rebaseline` still works at `analyze`.

---

## Findings

### Blocking

None.

### Non-blocking

- **NB-1 — `tests/test_lint_skill.py` received three edited fixture literals, which the anti-contradiction clause's literal wording ("new test functions only") forbids.** Two existing firing tests had their *planted breakage strings* updated because the source text they plant into moved (`Gate 5: Analysis Approval` → `Gate {gate_number}: Analysis Approval`, and `v1.15` → `v1.16`). Without the update those tests would plant a string that no longer exists and would stop testing anything — so the edit is the opposite of a weakening. No `def` line was removed, no assertion changed, and the handoff discloses it in its test-classification table. Recorded because it is a deviation from a plan clause that the handoff did not repeat in its "Declared divergences" section.
- **NB-2 — plan defect, correctly caught by the implementer: D4's summary column and A8 say `DEFECT_FIX` has 5 gates.** The same D4 row's own phase list contains six gate phases, and the flow as implemented has **6**. I re-derived 6 independently and drove the flow through six approvals. Every shipped document (`docs/SDLE-Reference-Guide.md` line 423, `ADR-004` line 43) states **6**; nothing shipped restates 5. The plan is immutable, so this stands as a plan defect, not an implementation one.
- **NB-3 — plan defect, correctly caught: A15's third clause "HOTFIX is the subset-minimum of the five flows" is false as written.** It contradicts the user decision the same plan implements, because HOTFIX carries `impact_analysis` and three flows deliberately do not. The implementer's replacement pair (`len(HOTFIX) <= len(flow)` and `set(HOTFIX) - {"impact_analysis"} <= set(flow)`, for every flow) is both true and forbids what the clause was for. Verified True for all five flows.
- **NB-4 — D10's stated placement for `flow_mismatch` is self-contradictory, and the resolution is sound.** D10 asks for the check *after* `governance_precondition` and *before* any `append_audit`, but `governance_precondition(paths, state)` appends. The implementer's three-step order — validate with no `state` (pure read), refuse `flow_mismatch`, then let the accepted facts enter the ledger — satisfies both intents and keeps `governance_stale`/`governance_blocked` unmaskable. It costs one extra record read per advance. Recorded for the record, not as a defect.
- **NB-5 — a `FLOW_PHASES` row named `GREENFIELD` is silently overridden by the frozen constant in `Constants.flows` before `flow_table_covers_the_required_flows` reports it.** This is fail-*closed* (the safe frozen list wins and lint fires by name — I proved both by mutation), so it is correct behaviour rather than a defect. Noted only because a future reader of `Constants.flows` could mistake the overwrite for a silent acceptance.
- **NB-6 — `modules/gate-protocol.md` step 9 still reads "Moving to Phase \<N+1\>".** Harmless: the neighbouring steps now instruct the model to read `current_phase`, `progress` and the gate numbers back from the script's response rather than compute them, and `\<N+1\>` is a display idiom rather than a restated constant. Not adopted here; noted for whoever next edits that file.
- **NB-7 — carried forward, unchanged and unowned by T07:** T04 N-2/N-3/N-4/N-6/N-7 (including the stale `.workflow/completion-summary.json` path on the gate-protocol completion line, which T07 correctly edited for the gate *count* only), T03-1/4/5/6/7/8/10, T02 NB-2/NB-4/NB-5, and the out-of-scope `.claude/settings.local.json`. T07 adopted none of them, as its scope exclusions require.

---

## Final result rationale

T07 is the first phase that intentionally changes lifecycle semantics, so I verified that behaviour changed exactly where intended and nowhere else, rather than that nothing changed.

The single property the phase turns on — that **GREENFIELD is not derived from the registry** — I verified by mutation rather than by reading, three ways: appending a phase to a live registry leaves `flows["GREENFIELD"]` byte-identical at 19 entries; an orphaned registry row makes `every_registry_phase_is_used_by_some_flow` fail loudly; and a hand-declared `GREENFIELD` row is both overridden by the frozen constant and reported by name. §13's compatibility translation holds all four ways, including the one that compares against Git history rather than against anything the implementer wrote — the pre-T07 `PHASE_SEQUENCE` parsed out of three separate revisions is element-wise `constants.flows["GREENFIELD"]` at HEAD.

Flow selection genuinely changes traversal: five flows driven end to end through the real CLI produce 18/8, 18/8, 16/7, 14/6 and 10/3, pairwise distinct except the one declared pair. `impact_analysis` is exactly what the user decided it should be — a real inspectable step at registry position 2, in the two defect flows only, with no gate anywhere in any of the four gate-bearing structures, no ninth approvals key at any point of a full run, and yet fingerprinted, SHA-bound to a TP-011 review that goes stale on edit, written to a path the write fence actually permits, and displayed to the human before the first gate downstream of it. The documentation describes it as governed but gateless, and states the true 14/6 rather than the plan's arithmetic slip.

Gate discipline survived becoming flow-relative in every case I could construct, and the refusal that would have re-opened the defect two phases just closed does not: `flow_mismatch` at `advance`, at `gate approve` and at `skip` each left `audit.md` and `state.json` byte-identical with `audit verify` exit 0. No linter check was weakened — 22 checks became 29 with none removed, the two re-targeted checks still assert exact equality in both directions, and the one broadened regex is over-compensated by a check that pins 17 previously unchecked ordinals. The closed sets that keep the design correct are all intact: `NEXT_PHASE` has no traversal reader, `cmd_init` still does not call `apply_advance`, and `state["flow"]` has exactly two writers. Nothing leaked from T08, T09, T10 or T11, and §13's legacy structures were kept, as §13 requires.

The full suite is 901 passed at raw exit 0 with collected equal to passed and zero skips or xfails, `lint-skill` is 29/29 at v1.16, `validate.py` exits 0, the must-not-change list is byte-empty against both the plan commit and the prior baseline, and no test was weakened, skipped, xfailed or deleted. The four divergences from the plan are all plan defects or plan self-contradictions, all declared, all resolved in the direction that asserts more rather than less. The remaining findings are non-blocking.

Phase T07 passes independent verification.
