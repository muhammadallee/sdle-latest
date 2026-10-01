# Independent Review — Round 2

Produced by a separate agent instance with a fresh context, tool grant
`Read` / `Grep` / `Glob` only, reviewing the committed diff at that point
(`git diff main...HEAD`, 73 files, 7006 insertions, 542 deletions) written out
to a patch file. It received the Round-1 findings and dispositions and was
asked to verify them, and it read the frozen contracts as the specification.

**The reviewer's output below is verbatim and unedited.** The implementer's
dispositions are in a separate section at the end.

---

## Part 1 — Verification of the 22 Round‑1 dispositions

| R1 | Claim | Verdict | Evidence / pointer |
|---|---|---|---|
| R1-001 | realize needs `gate_implement` | **landed** | `sdle.py:8158-8165`; `test_the_realize_command_needs_the_implementation_gate` |
| R1-002 | tech flag read from envelope | **landed** | `sdle.py:6645-6651` reads `document`, refuses it inside `placement`; emitted by `architecture schema:7816-7827`; stated in `modules/architecture-placement.md` Step F.1 |
| R1-003 | apply/realize before first audit append | **landed** | `sdle.py:9771-9780` precede `append_audit` at `:9789` and `save_state` at `:9876` |
| R1-004 | capability loop filtered | **landed** | `sdle.py:7659-7662`; `test_realize_closes_only_its_own_extraction` |
| R1-005 | realize raises; assess refused after approval | **REGRESSED** — see **R2-001** | `sdle.py:7900`; new predicate is truthiness, not `"approved"` |
| R1-006 | `introducedBy`, cascade on it | **landed** | `sdle.py:7369-7387`, `:7586-7596`; unenforced in the catalog validator — see **R2-011** |
| R1-007 | 3 D12 conditions checked | **landed** | `sdle.py:6978-6999` |
| R1-008 | drift re-approval refused | **incomplete** — see **R2-003** | `_approve_drift:9919` guarded; `cmd_drift_rebaseline:10350-10388` not |
| R1-009 | disposed record reads as missing | **incomplete** — see **R2-005** | `require_architecture_record:7231` yes, but `architecture_precondition:7767` still calls `read_architecture_record` |
| R1-010 | `reserve_evidence` first | **landed** | `sdle.py:7925` precedes `write_atomic:7951` |
| R1-011 | bootstrap references validated | **landed** | `sdle.py:7099-7127` |
| R1-012 | `SUPERSEDED` + audit event | **landed in code, contract half-amended** — see **R2-010** | `sdle.py:7568`, `:9812-9822`; contract §11 bullet still says `ABANDONED` |
| R1-013 | delete the scratch proposal | **landed** | `modules/architecture-placement.md` Step F.1 |
| R1-014 | two equality checks | **landed, one path skips it** — see **R2-012** | `:7209`, `:7690`; `cmd_architecture_apply:8120` passes no `resolved` |
| R1-015 | dead code removed | **landed, new instance** — see **R2-009** | `architecture_apply` lost its `state` param; `service_ids` now unused in `_validate_outcome_requirements` |
| R1-016 | status sets match contract | **landed** | `sdle.py:6880-6906` |
| R1-017 | adjacency, not order | **landed** | `sdle.py:13031` `(gate, spec) != (placement + 1, placement + 2)` |
| R1-018 | path containment | **landed** | `_inside_repository:7134-7149` |
| R1-019 | contract §4 amended | **landed** | contracts §4 *(R1-019)*, *(R1-006)* |
| R1-020 | service → capability check | **landed** | `sdle.py:7413-7421` |
| R1-021 | relative path from `Paths` | **landed, same class recurs** | `:6503-6506`; `implementation_exclusions:12199` rebuilds the literal |
| R1-022 | manifest exclusion narrowed | **landed** | `sdle.py:12188-12200` |

---

## Part 2 — Findings

**ID R2-001 · CRITICAL · `scripts/sdle.py:7900` (with `:10223`)** · `cmd_architecture_assess` refuses whenever `approvals["gate_architecture"]` is *truthy*, but `cmd_gate_reject:10223` writes `{"decision": "rejected", …}` — a truthy dict — and nothing ever clears it (`remediate begin/finish` do not; only `cmd_restart:11565` sets `None`). After any rejection of `gate_architecture`, `architecture assess` refuses `architecture_decision_conflict` with the message *"gate_architecture has already been approved"*, which is false. · **Why it matters:** this breaks gate discipline (invariant 2) in reverse and contradicts three documents that describe the same path — `modules/gate-protocol.md` step 5 ("Re-execute `architecture_placement`… produces a new proposal"), `modules/architecture-placement.md` ("Rejection re-runs the phase"), and `docs/troubleshooting/README.md` ("Rejection returns the WorkItem to `architecture_placement` through the ordinary remediation path"). Three consequences: (a) documented remediation is unreachable; (b) `ARCHITECTURE_REVIEW_REQUIRED` — contract §8's escape hatch, whose only documented exit is *reject then re-run* — becomes a hard dead end; (c) the stale record still satisfies `architecture_precondition`, the PASS review still binds the unchanged SHA and `gate_precondition_hook` still passes, so `gate approve` succeeds — **the only forward path is approving the artifact the human just rejected**, or `restart`. · **Fix:** make the guard test the decision, not the presence: refuse only when the entry's `decision` is `approved` (or is in `BASELINED_GATE_DECISIONS`). · **Test:** no. `test_reassessing_after_approval_is_refused:665` drives only the approved branch; no test rejects `gate_architecture` and re-assesses. Add one that rejects, re-assesses and expects exit 0 with a new `decisionId`.

**ID R2-002 · HIGH · `README.md:470-533` (against `README.md:25-47`)** · The "Try It" walkthrough still prints `Phase 2/18`, `Phase 4/18 — Generate Specification`, `Phase 5/18`, `Gate 1/8`, `Gate 2/8: Specification Approval`, `gate_plan (7/18)`, and `Phase 4 only` for clarify at `:324` — while the phase table 400 lines above it now reads 20 phases and "9 approval gates total", and `:550` already uses the new Gate 5–9 numbering. · **Why it matters:** the README is the product's front door and a lint-enforced member of the documentation set; the rule in CLAUDE.md is "where a document and the engine disagree, the document is the defect". It now disagrees with itself on the same page. · **Fix:** re-derive the walkthrough's fractions and gate ordinals from `sdle.sh flow show`/`gate show` for GREENFIELD (spec_draft `6/20`, gate_spec `7/20` Gate 3/9, gate_plan `9/20`), and change `:324` to `spec_draft` as SKILL.md:442 already did. · **Test:** no — `doc_flow_counts_match_engine` checks only three claim shapes, and `no_hardcoded_progress_outside_progress_map` runs over `_skill_files` only, not `docs/` or `README.md`.

**ID R2-003 · HIGH · `scripts/sdle.py:10350-10388` — `cmd_drift_rebaseline`** · The R1-008 guard was added to `_approve_drift:9919` only. `drift rebaseline --gate gate_architecture` re-baselines `artifact_shas["gate_architecture"]` to whatever is on disk, with no `architecture_binding_precondition`, no re-apply and no refusal. · **Why it matters:** identical consequence to R1-008 — the catalog decision's `renderedSha256`/`renderedArtifact` permanently disagree with the file, and because the gate is already approved no later check re-reads the binding. D15's cryptographic binding is silently broken through the sibling door. Both doors are reachable from the same shell; guarding one is not guarding the artifact. · **Fix:** refuse `gate_architecture` in `cmd_drift_rebaseline` with the same pointer `_approve_drift` gives. · **Test:** no.

**ID R2-004 · HIGH · `docs/SDLE-Reference-Guide.md:151-159, 474-492, 505, 513, 697, 763, 1266, 125`** · The phase-by-phase sections were correctly renumbered to the 20/9 lifecycle, but the artifact table, the glossary, the misconceptions table and the command reference were not: `spec.md | Phase 4`, `checklist.md | Phase 8`, `tasks.md | Phase 9 (refined Phase 11)`, `app-design.md | Phase 13`, `implementation-manifest.md | Phase 15`, `security-review | Phase 17`, "Gates 1–6 … Only Gate 7 involves reviewing actual code", "written only when Gate 8 is approved", "Loaded only at Phase 17". · **Why it matters:** the same document states "### Phase 6 — Generate Specification" and "spec.md | Phase 4". A derived view that contradicts itself is worse than one that is merely stale. · **Fix:** renumber from the engine's GREENFIELD view: spec 6, checklist 10, tasks 11 (refined 13), design 15, manifest 17, security review 19, code gate 8, completion gate 9. · **Test:** no.

**ID R2-005 · MEDIUM · `scripts/sdle.py:7767` — `architecture_precondition`** · Uses `read_architecture_record`, which does not consult disposal, while `gate_precondition_hook:11072` uses `require_architecture_record`, which does. · **Why it matters:** R1-009's finding was *"a human is shown a stale rendering and approves it"*. After `restart --to architecture_placement`, the record and rendering survive and the WorkItem can still `advance --to gate_architecture`; the orchestrator displays the voided placement for a decision (invariant 4), and only the `approve` call refuses. · **Fix:** call `require_architecture_record` in `architecture_precondition`. · **Test:** no.

**ID R2-006 · MEDIUM · `docs/dry-runs/01-happy-path.md` and 02, 06, 10–15** · The pre-existing transcripts were updated only where `test_dry_run_contracts.py` parses them. Prose was not: DR‑01 shows "Gate 3/9: Specification Approval" and "Gate 2 approved" for the same approval; "All 8 gates passed" (nine); "exactly the 18 phases above" (twenty) beside "All 9 gates approved"; `Phase: implement (15/18)`. DR‑02's starting conditions (`5/18`, "Gate 1 approved") are wrong in both the fraction and the gate set. DR‑10/11/12/13 close with "All 8 / 7 / 6 / 3 gates passed" against the new 9 / 8 / 7 / 4. · **Why it matters:** CLAUDE.md calls `docs/dry-runs/` "the behavioural specification". · **Fix:** sweep the prose ordinals; then add a scan for `Gate \d+ approved`, `All \d+ gates` and `\(\d+/\d+\)` over `docs/` to `test_dry_run_contracts.py`. · **Test:** no.

**ID R2-007 · MEDIUM · `.claude/skills/sdle/modules/phase-execution.md:9-18` — the Guidance File Map** · There is no `architecture_placement` row, yet `modules/architecture-placement.md` Step A.7, ADR-014 and contracts §15 all state that `guidance/architecture-placement.md` "flows through the existing Guidance File Map". `cmd_guidance_path` parses exactly that table, so `guidance path --phase architecture_placement` returns `path: null` and the file is never discovered. · **Why it matters:** a prompt/engine semantic disagreement with a silent failure mode — steering input read by nothing, and the untrusted-content scan never runs on it. · **Fix:** add the row, or delete the claim from all three documents. · **Test:** no.

**ID R2-008 · MEDIUM · `scripts/sdle.py:7198, 7205, 7211` — `architecture_placement_invalid` exit code** · `read_architecture_record` raises this reason as `IntegrityError` (exit 3). Contract §14 lists `architecture_placement_invalid | 1`, and the troubleshooting guide repeats exit 1. · **Why it matters:** "exit codes are the contract". One reason with two exit codes means a caller branching on the code gets a different answer depending on which raise site fired. Same class, undocumented: `architecture_decision_conflict` now has a third trigger (re-assess after approval) and `architecture_decision_unresolved` a second (`realize` on a non-pending decision) that §14 omits. · **Fix:** give the record-corruption case its own reason at exit 3, or amend §14 and troubleshooting. · **Test:** no.

**ID R2-009 · MEDIUM · `scripts/sdle.py:11113` and `:12449`** · Two user-visible strings still carry pre-1.18 ordinals: `"Cannot approve Gate 7: {resolved} is missing …"`, and the manifest body's `f"Phase: implement ({state.get('progress', '15/18')})"` — a hardcoded fallback that writes `15/18` into a governed artifact. · **Fix:** render the refusal from `flow.gate_number(gate_key)`; drop the `'15/18'` default. · **Test:** no.

**ID R2-010 · LOW · `docs/architecture/architecture-memory-contracts.md` §11** · The trigger row records the rerun disposition as `SUPERSEDED` *(R1-012)*, but the cascade bullet below still reads "decision → `ABANDONED`". · **Fix:** amend the cascade bullet to distinguish status from `abandonedBy`.

**ID R2-011 · LOW · `scripts/sdle.py:6345-6431` and `:7383`** · Contract §4 states every entity carries `introducedBy`; `validate_architecture_catalog` never checks for it, and `_upsert`'s `setdefault` silently adopts any entity lacking the key into whichever decision touches it first — the exact defect R1-006 was raised for. · **Fix:** require it in the validator, or state in §4 that it is advisory.

**ID R2-012 · LOW · `scripts/sdle.py:8120`** · `cmd_architecture_apply` calls `architecture_binding_precondition(paths, record)` without `resolved`, so R1-014's path-equality check is skipped on the standalone replay path. · **Fix:** resolve and pass it.

**ID R2-013 · LOW · `scripts/sdle.py:6718, 6873`** · `service_ids` is passed to `_validate_outcome_requirements` and never read. A new instance of what R1-015 flagged. · **Fix:** drop the parameter.

**ID R2-014 · LOW · `.claude/skills/sdle/SKILL.md:446`** · "The write fence denies direct edits to `workitems/`, `.workflow/`, `requirements/` and `guidance/`" — `hooks.py` now also fences `.sdle/architecture`. · **Fix:** add it and its carve-out note.

**ID R2-015 · LOW · `CLAUDE.md:121`** · Still reads "`docs/dry-runs/01..16` … All sixteen are pinned by their claims", and the contract test now asserts twenty. · **Fix:** extend to `01..20` and name the 17–20 group.

**ID R2-016 · LOW · `docs/dry-runs/19-architecture-catalog-stale-revision.md`, Parts 3–4** · The transcript claims Session A's re-assessment mints `AP-wi-a-002`. `next_decision_id` counts only decisions **already in the catalog**; `AP-wi-a-001` was refused and never reached it, so the engine re-mints `AP-wi-a-001` — the function's own docstring says so. · **Fix:** correct the transcript to reuse `AP-wi-a-001`.

**ID R2-017 · LOW · `scripts/sdle.py:11562` / contracts §11 / troubleshooting** · `cmd_restart` calls `abandon_architecture_decisions`, which can raise `architecture_catalog_invalid` (exit 3). So an unreadable catalog blocks `restart` as well as `reset`, but only the `reset` consequence is stated. · **Fix:** state it for `restart` too.

**ID R2-018 · LOW · `.claude/skills/sdle/guidelines/service-design.md`** · Thirteen sections are presented as "Sections to add" once *any* placement is approved. `service-planning.md` gets this right ("including 'no change', which is an answer"); `service-design.md` has no equivalent. · **Why it matters:** for `EXTEND_EXISTING_SERVICE` in a single-deployable repository, mandating "API contracts", "Published/consumed events" and "Deployment impact" makes a distributed shape the default vocabulary of the design. · **Fix:** add the same sentence and mark the event/deployment rows conditional. (The rest of the guideline set is clean: `architecture-placement.md` defaults to extending, names nanoservices and one-service-per-WorkItem as anti-patterns, and `implementation.md` rejects premature abstraction.)

**ID R2-019 · LOW · `scripts/sdle.py:12199`, `:11919`** · `implementation_exclusions` and `SDLE_OWNED_PREFIXES` both spell `architecture/` as a literal while `Paths.architecture_dir` owns the name — the class R1-021 fixed elsewhere. · **Fix:** derive from `Paths`, or note why these stay literal.

**ID R2-020 · LOW · `scripts/sdle.py` — many comment and `--help` sites** · Comments, docstrings and help strings still name old ordinals: "The N in 'N/18'", "Gate 7's verification evidence", "Phase 8's checklist", "Phase 17 support.", "HOTFIX's `gate_implement` is Gate 2, GREENFIELD's is Gate 7" (now 3 and 8), and a comment arguing from `modules/security-review.md` cross-referencing "Phase 17", which it no longer does. · **Fix:** sweep, and prefer phase ids to ordinals in help strings.

**ID R2-021 · LOW · `scripts/sdle.py:7489` — `OUTCOME_CAPABILITY_STATUS`** · `EXTEND_EXISTING_SERVICE` writes `ESTABLISHED` unconditionally. A second WorkItem extending a capability currently `EMBEDDED` with an `OPEN` candidate flips the capability while the candidate stays `OPEN`. · **Fix:** confirm whether intended; if so, say so in the table's comment.

**ID R2-022 · LOW · `docs/tutorials/*`** · Tutorial transcripts still carry `/18` fractions, `progress: "2/18"`, `Phase 18 is a gate phase … did you mean phase 17`, "Gate 2: Specification Approval", and `DEFECT_FIX` "`gate_spec` reports as Gate 1 of 6 … in GREENFIELD it is Gate 2 of 8". The index headline counts were updated; the bodies were not. · **Fix:** same sweep as R2-006.

---

**22 findings · 1 CRITICAL, 3 HIGH, 5 MEDIUM, 13 LOW.** Of the 22 Round-1 dispositions: 15 landed, 1 regressed (R1-005 → R2-001), 3 incomplete (R1-008, R1-009, R1-014), 1 half-amended in the contract (R1-012), 2 recur as new instances of the same class (R1-015, R1-021).

Direct answers to the parent's focus list: **cross-file consistency** — the constant tables, `FLOW_PHASES` (all four re-verified by hand: 21/9, 18/8, 16/7, 12/4), `NEXT_PHASE`, `PHASE_TO_GATE_KEY`, `PROGRESS_MAP`, `CAPABILITY_MAP`, `phase-execution.md` block ordinals, `gate-protocol.md` and the new dry runs 17/18/20 agree with the engine; 19 does not (R2-016); the prose in README, the Reference Guide, the old dry runs and the tutorials does not (R2-002/004/006/022). **Unreachable or undocumented refusals** — every contract §14 reason has a raise site and a troubleshooting entry; three reasons have triggers the documents do not name and one has two exit codes (R2-008). **Prompt instructing what the engine refuses** — yes, R2-001, and R2-007 the reverse. **`{workitem_root}`** — safe: every `resolve_artifact_path` caller reaches it only after `read_state`, so the WorkItem is always bound. **Incremental mode** — genuinely supported; `bootstrapDelta` is optional, `architecture show` invents nothing, and DR-20 is the HOTFIX/no-constitution case. The only pressure toward an SRS-shaped repository is R2-018. **Premature decomposition** — no; the guideline set argues the other way, with the one caveat in R2-018. **Anything the job does not need** — nothing found; the command surface is three new verbs, the state change is one key, and `architecture apply`/`realize` earn their place as replay paths.

### Areas inspected
- `scripts/sdle.py` in the current file: the whole ADR-013 block `6183-8181`; `cmd_gate_approve`, `_approve_drift`, `cmd_gate_reject`, `cmd_gate_omit`, `gate_precondition_hook`, `required_gate_artifact`, `resolve_artifact_path`, `compute_drift`, `cmd_drift_rebaseline`, `cmd_remediate_begin/finish`, `cmd_skip`, `cmd_restart`, `cmd_reset`, `cmd_gate_show`, `cmd_guidance_path`, `gate_requirements`, `terminal_gate_key`, `MANDATORY_FLOW_PHASES`, `SDLE_OWNED_PREFIXES`, `implementation_exclusions`, `Paths`, `capability_directories`, and the two new lint checks plus `execution_block_numbers_are_the_greenfield_positions`.
- `.claude/skills/sdle/SKILL.md` (all constant tables, header example, fence sentence), `modules/architecture-placement.md`, `modules/gate-protocol.md`, `modules/phase-execution.md` (Guidance File Map and every renumbered block), `modules/security-review.md`, `templates/state.json`, `.claude/hooks/hooks.py` diff.
- All six `guidelines/*.md` in full — R1 did not reach these.
- `docs/architecture/architecture-memory-contracts.md` in full as the specification; ADR-013's §"This amends ADR-002" and its header.
- Dry runs 17–20 in full, arithmetic recomputed per flow from `FLOW_PHASES`; every cited node checked against `tests/test_units_architecture.py`; `docs/dry-runs/README.md` and `verification-matrix.md` diffs; the prose of 01, 02, 06, 10–15 by targeted grep.
- `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md`, `docs/troubleshooting/README.md`, `docs/tutorials/*` by ordinal/fraction grep.
- `tests/test_units_architecture.py` in full; `test_dry_run_contracts.py` regexes and scenario count; `test_units_invariants.py`, `test_hooks.py` diffs.

### Areas not reached
- ADR-013 and ADR-014 bodies beyond the ADR-002 amendment and the precedence chain; `DELIVERY.md`, `PROGRESS.md`, `claude-review-rejections.md`.
- `tests/conftest.py` additions, the five integration drivers, `test_lint_skill.py`, `test_units_flow_model.py`, `test_units_capabilities.py`, `test_units_state.py`, `test_units_transitions.py`, `test_units_workitem_runtime.py`, `test_units_repo_config.py`.
- `_skill_files` and `every_capability_file_is_linted`'s guideline globbing — `capability_directories` was read, the two call sites were not.
- `hooks.py`'s `fenced_target` normalisation for a Windows-separator path under `.sdle\architecture`; the test asserts list membership only.
- `docs/lifecycle/`, `docs/risk-and-gates/`, `docs/brownfield/`, `docs/workitems/`, `docs/spec-kit-integration/`, `docs/GETTING-STARTED.md` beyond the ordinal grep.
- **No test evidence.** I cannot run `pytest` or `lint-skill`; every "would a test have caught it" is read from test source. The manifest is the parent's.

---

## Implementer disposition

**All twenty-two accepted.** Nothing rejected; `claude-review-rejections.md`
records no entry from this round either.

The finding that matters most is **R2-001**, and it is worth naming plainly:
the Round-1 fix for R1-005 introduced a CRITICAL regression. Guarding on the
*presence* of an approvals entry rather than on its *decision* turned a
rejection into a dead end — the one path three separate documents describe as
the remedy. It is exactly the class of defect a second round exists to catch,
and it would not have been caught by the suite, because no test rejected that
gate and re-assessed. There is one now.

| ID | Disposition | What was done |
|---|---|---|
| R2-001 | ACCEPT | the guard tests `decision == "approved"`; a rejected gate reopens the phase. New test: reject, re-assess, expect success |
| R2-002 | ACCEPT | the README walkthrough's fractions and ordinals recomputed from the engine |
| R2-003 | ACCEPT | `cmd_drift_rebaseline` refuses `gate_architecture` with the same pointer `_approve_drift` gives |
| R2-004 | ACCEPT | the Reference Guide's four prose tables renumbered |
| R2-005 | ACCEPT | `architecture_precondition` uses `require_architecture_record` |
| R2-006 | ACCEPT | the prose ordinals in 01–15 swept, and a new contract check scans for them so the gap closes |
| R2-007 | ACCEPT | the Guidance File Map gains an `architecture_placement` row |
| R2-008 | ACCEPT | record corruption gets its own reason, `architecture_record_invalid` (exit 3); §14 and troubleshooting name the added triggers |
| R2-009 | ACCEPT | the refusal renders its gate number from the bound flow; the manifest's `15/18` default is gone |
| R2-010 | ACCEPT | the cascade bullet distinguishes status from `abandonedBy` |
| R2-011 | ACCEPT | `introducedBy` is required by the catalog validator |
| R2-012 | ACCEPT | `cmd_architecture_apply` resolves and passes the gate artifact |
| R2-013 | ACCEPT | the unused parameter dropped |
| R2-014 | ACCEPT | SKILL.md names the fifth fenced path and its carve-out |
| R2-015 | ACCEPT | CLAUDE.md reads `01..20` and names the new group |
| R2-016 | ACCEPT | DR-19 reuses `AP-wi-a-001`, as the engine does |
| R2-017 | ACCEPT | stated for `restart` as well as `reset` |
| R2-018 | ACCEPT | `service-design.md` carries the "no change is an answer" rule and marks the distributed rows conditional |
| R2-019 | ACCEPT | both lists derive the directory name from `Paths` |
| R2-020 | ACCEPT | the comment and `--help` ordinals swept |
| R2-021 | ACCEPT | not intended — extending a capability no longer clears an `EMBEDDED` status while its candidate is still open |
| R2-022 | ACCEPT | the tutorial transcripts swept with the same script as the dry runs |
