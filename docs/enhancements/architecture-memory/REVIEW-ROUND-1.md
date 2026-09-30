# Independent Review — Round 1

Produced by a separate agent instance with a fresh context, tool grant
`Read` / `Grep` / `Glob` only, reviewing the committed diff
(`git diff main...HEAD`, 70 files, 6123 insertions, 536 deletions) written out
to a patch file because the reviewer cannot run commands. It received
Appendix B's prompt, the fixed design decisions D1–D15 and the frozen
contracts document, and nothing the implementer wrote about its own work.

**The reviewer's output below is verbatim and unedited.** The implementer's
dispositions are in a separate section at the end.

---

## Findings

**R1-001 · CRITICAL · `scripts/sdle.py` — `cmd_architecture_realize` (patch 6726-6748)**
`cmd_architecture_apply` refuses `gate_required` when `state.approvals["gate_architecture"]` is unset (patch 6703-6710); `cmd_architecture_realize` has no equivalent check on `gate_implement` and calls `architecture_realize` → `write_architecture_catalog` unconditionally.
*Why it matters:* contract §7 says `realize` is the "`gate_implement`-approval path only", and ADR-013's stated guarantee is "no placement enters the catalog without a human". Anyone holding the shell — including the orchestrator — can flip `PLANNED → IMPLEMENTED`, close superseded `dataOwnership` rows and mark the decision `IMPLEMENTED` before any implementation is accepted. This is a catalog mutation with no human decision behind it.
*Fix:* mirror `cmd_architecture_apply`: refuse `gate_required` unless `(state.get("approvals") or {}).get("gate_implement")` is set.
*Test:* no. `test_units_architecture.py::test_realize_turns_a_planned_service_into_an_implemented_one` calls `sdle.architecture_realize(paths, …)` directly at `spec_draft`, encoding the absence of the guard as expected behaviour.

**R1-002 · HIGH · `scripts/sdle.py:5524` and `:5740` — `introducesTechnologyDecision` read from the wrong object**
`evaluate_architecture_proposal` stores `bool(placement.get("introducesTechnologyDecision"))` and `_enforce_constitution_rule` reads `placement.get("introducesTechnologyDecision")`. Contract §5 places the field at the **envelope** level, a sibling of `bootstrapDelta` and `placement`.
*Why it matters:* D12. A contract-conformant proposal sets it at top level, the engine sees `None`, `bool(None)` is `False`, and the `architecture_constitution_required` refusal for `EXTEND_EXISTING_SERVICE` / `KEEP_EMBEDDED_AND_MONITOR` never fires. Fail-open on the one D12 input the engine cannot derive. Compounding it: `cmd_architecture_schema` (patch 6413-6453) never names the field, and `modules/architecture-placement.md` never mentions it — the contracts document is the only place its location is stated, so an agent following `architecture schema` will never emit it at all.
*Fix:* read it from `document`, not `placement`; add it to the `architecture schema` output so the location has one source of truth.
*Test:* no. `test_but_not_when_it_introduces_a_technology_decision` calls `_enforce_constitution_rule("EXTEND_EXISTING_SERVICE", absent, {"introducesTechnologyDecision": True}, …)` — it passes the flag in the *placement* position, so it encodes the code's reading. No end-to-end test sets the field; `conftest.record_architecture` never emits it.

**R1-003 · HIGH · `scripts/sdle.py:9583-9593` — realize runs after the first audit append**
`architecture_apply` is deliberately placed before the first ledger write (9535-9544, with a comment explaining exactly why). `architecture_realize` for `gate_implement` is called *after* `append_audit(event="gate_approved")` at 9553-9563, and it can raise: `read_architecture_record` (`IntegrityError`), `read_architecture_catalog` (`architecture_catalog_invalid`, exit 3), the status branch (`architecture_decision_unresolved`, patch 6675-6681) and `write_architecture_catalog`'s outgoing validation.
*Why it matters:* the engine's own rule, restated at 9519-9527 — a refusal must leave `audit.md` byte-identical. Here a refusal leaves a `gate_approved` entry in the append-only ledger for an approval `save_state` never persisted: `state.json` and `audit.md` disagree and `audit verify` reports an approval that did not happen (invariants 5 and 6).
*Fix:* hoist `architecture_realize` next to `architecture_apply`, before the approvals write, keeping the audit append where it is.
*Test:* no. No test corrupts the catalog between approval and realize, and no test asserts `audit.md` is unchanged after a failed `gate_implement` approval.

**R1-004 · HIGH · `scripts/sdle.py` — `realize_architecture_decision` (patch 6290-6292)**
```python
for capability in catalog["capabilities"]:
    if capability.get("status") == "EXTRACTING":
        capability["status"] = "ESTABLISHED"
```
The loop is unfiltered: it flips **every** capability in the repository catalog, not the one this decision concerns.
*Why it matters:* the catalog is shared state (D2). WorkItem A realizing its extraction silently marks WorkItem B's in-flight `EXTRACTING` capability `ESTABLISHED`, so B's later placement reasons from a false state. This breaks cross-WorkItem isolation in the one place it is hardest to notice — nothing refuses, nothing is audited.
*Fix:* the catalog `Decision` row carries no capability id, but `architecture_realize` holds the WorkItem record; pass `record["placement"]["capability"]["id"]` into `realize_architecture_decision` and match on it. The candidate loop immediately above already filters on `decisionReference` and is correct.
*Test:* no. There is no two-WorkItem realize test; `test_a_second_workitem_sees_the_first_ones_architecture` only reads.

**R1-005 · HIGH · `scripts/sdle.py` — `architecture_realize` returns `None` in three places (patch 6661-6670); `cmd_architecture_assess` has no phase precondition (patch 6490-6499)**
Contract §12: "a missing decision at realization is an integrity failure (`architecture_placement_missing`), not a tolerated no-op." The code returns `None` for a missing record, a missing catalog and a missing decision, and `cmd_gate_approve` continues silently.
*Why it matters:* it is reachable, not theoretical. `cmd_architecture_assess` never checks `state["current_phase"]`, so re-running it after `gate_architecture` has been approved rebinds `architecture-placement.json` to a freshly minted `AP-<wi>-002` (patch 5899-5910 counts catalog decisions, so the applied `001` forces a new number). At `gate_implement`, `architecture_realize` looks up `002`, finds nothing, returns `None` — `AP-<wi>-001` stays `APPROVED_PENDING_IMPLEMENTATION` and its service stays `PLANNED` for ever, with no refusal and no audit entry. `cmd_discovery_assess` has no phase check either, but discovery has no downstream apply/realize coupling, so the sibling precedent does not carry here.
*Fix:* raise `architecture_placement_missing` instead of returning `None`, and refuse `architecture assess` once `approvals["gate_architecture"]` is set (remediation goes through gate reject, which clears it).
*Test:* no. No test re-runs `assess` after approval, and no test drives `gate_implement` with a decision absent from the catalog.

**R1-006 · MEDIUM · `scripts/sdle.py` — `_upsert` (patch 6025-6032) combined with `abandon_or_supersede_prior` (patch 6224-6234)**
`_upsert` unconditionally `entry.update(fields)` on a pre-existing entity, and every call site writes `decisionReference: decision_id` — candidates (6142), services (6106), bootstrap rows (6041/6060), and the ACTIVE `dataOwnership` branch (6159). The abandonment cascade then selects by `decisionReference in touched`.
*Why it matters:* contract §11 says candidates and `dataOwnership` rows "introduced **solely** by it" are disposed of. Here an `OPEN` candidate that WorkItem A created and WorkItem B's `KEEP_EMBEDDED_AND_MONITOR` merely re-stated becomes `ABANDONED` when B restarts — B's restart rewrites A's history, which is precisely what D14 forbids. The same applies to an `ACTIVE` ownership row B touched.
*Fix:* record `introducedBy` (set only on creation) separately from `decisionReference`, and cascade on `introducedBy`.
*Test:* no. `test_restart_to_the_placement_phase_abandons_the_decision` has a single WorkItem and a single decision.

**R1-007 · MEDIUM · `scripts/sdle.py` — `_enforce_constitution_rule` (patch 5718-5746)**
D12 / contract §6 permit `EXTEND_EXISTING_SERVICE` and `KEEP_EMBEDDED_AND_MONITOR` without a constitution only when the proposal introduces "no new service boundary, no ownership transfer and no new technology choice". The function receives only `outcome`, `constitution` and `placement`; it checks the technology flag and nothing else.
*Why it matters:* an `EXTEND_EXISTING_SERVICE` proposal whose `dataOwnership` delta names a datum currently `ACTIVE`-owned by a *different* service is an ownership transfer — `realize_architecture_decision` will `SUPERSEDE` the old owner — and it is permitted in a repository with no constitution. Two of the three D12 conditions are unenforced.
*Fix:* pass the validated `ownership` list and `known` catalog in; refuse `architecture_constitution_required` when any delta datum has a different current `ACTIVE` owner, or when the proposal names a `targetOwner` not already in the catalog.
*Test:* no. The three constitution tests call `_enforce_constitution_rule` directly with `{}` as the placement.

**R1-008 · MEDIUM · `scripts/sdle.py:9661-9721` — `_approve_drift` bypasses `gate_precondition_hook`**
The drift re-approval path calls `required_gate_artifact` and `review_precondition` but not `gate_precondition_hook`, which is where `architecture_binding_precondition` and `architecture_outcome_precondition` now live (patch 6879-6883).
*Why it matters:* D15. Once `gate_architecture` is approved and the decision applied, an edit to `placement.md` enters the drift queue; re-approval re-baselines `artifact_shas["gate_architecture"]` to the new SHA with no binding check and no re-apply. The catalog's `renderedSha256` and `renderedArtifact` then permanently disagree with the file on disk, and the cryptographic binding the whole design rests on is silently broken.
*Fix:* refuse drift re-approval for `gate_architecture` with a pointer to restore the generated file (re-running `assess` is not the remedy — see R1-005).
*Test:* no. `test_a_hand_edited_rendering_fails_the_binding` edits *before* approval, which is the path that is guarded.

**R1-009 · MEDIUM · `scripts/sdle.py` — `architecture_precondition` (patch 6387-6389) vs. the abandonment cascade**
After `restart --to <placement>` or `reset`, `abandon_architecture_decisions` marks the catalog decision `ABANDONED`, but `architecture-placement.json` and `placement.md` are untouched. The precondition only asks "does a record exist".
*Why it matters:* gate discipline (invariant 4). The workflow advances to `gate_architecture` on the strength of a record the engine has already disposed of, the human is shown a stale rendering, approves it, and only then does `architecture_apply` refuse `architecture_decision_conflict` (patch 6616-6622). No corruption, but a human is asked to approve a decision the engine has already voided.
*Fix:* treat a record whose `decisionId` resolves to an `ABANDONED`/`SUPERSEDED` catalog row as missing, or delete the record and rendering as part of the cascade.
*Test:* no. Neither restart test advances to the gate afterwards.

**R1-010 · MEDIUM · `scripts/sdle.py` — `cmd_architecture_assess` (patch 6533-6540)**
`write_atomic(architecture_placement_rendering, …)` runs *before* `reserve_evidence`, which can raise `execution_id_collision` (exit 3, `sdle.py:3087`). `cmd_discovery_assess` — the sibling this docstring claims to mirror — calls `reserve_evidence` first (`sdle.py:6077`), before any `write_atomic`.
*Why it matters:* the docstring asserts "every refusal fires before the first write". After this refusal `placement.md` has been replaced while `architecture-placement.json` still holds the old `renderedSha256`, so the next gate approval fails `architecture_artifact_binding_invalid` for a reason unrelated to what the operator did. Dry-run 16 exists precisely for this collision.
*Fix:* move `reserve_evidence` above the rendering write, as discovery does.
*Test:* no. `test_a_refused_assess_writes_nothing` refuses at validation, long before this point.

**R1-011 · MEDIUM · `scripts/sdle.py` — `_validate_bootstrap_delta` (patch 5805-5842)**
Bootstrap `capabilities[].ownerService` and `services[].capabilities` are copied into the record with no reference check; only evidence paths are validated.
*Why it matters:* contract §5 lists "every referenced capability/service either exists in the catalog or is introduced by this same proposal" as **enforced** at `assess`. A bootstrap capability naming an unknown `ownerService` passes `assess`, the human approves the gate, and then `write_architecture_catalog` → `validate_architecture_catalog` (patch 5196-5202) raises `architecture_catalog_invalid` — **exit 3, an integrity failure** — for what is a malformed proposal the engine should have refused with exit 1 before anyone read the artifact.
*Fix:* validate bootstrap references in `_validate_bootstrap_delta` and raise `architecture_capability_unknown` / `architecture_service_unknown`.
*Test:* no. `test_a_legacy_repository_bootstraps_from_evidence` uses a bootstrap with no cross-references.

**R1-012 · MEDIUM · `scripts/sdle.py` — `abandon_or_supersede_prior` (patch 6208) and `apply_architecture_delta` (patch 6095-6096)**
The rerun-supersession path sets `status = "SUPERSEDED"`, and no `architecture_decision_abandoned` audit event is emitted for it. Contract §11 specifies decision → `ABANDONED` with `abandonedBy` in `restart|reset|superseded`, plus the audit event, for all three triggers.
*Why it matters:* it is a divergence from the frozen contract, and the concrete loss is the missing audit event — the supersession of a prior approved-but-unrealized decision leaves no ledger entry at all, only a field change inside the catalog. (`SUPERSEDED` is arguably the better status; the missing event is not arguable.)
*Fix:* either align with the contract or amend the contract, and in both cases emit `architecture_decision_abandoned` on the supersession path.
*Test:* no. No test performs a rerun placement that supersedes a prior applied decision.

**R1-013 · MEDIUM · `.claude/skills/sdle/modules/architecture-placement.md` — Step F.1 (patch 665)**
"Write the proposal JSON to a scratch path (the WorkItem's runtime is engine-owned; put it somewhere ordinary such as the repository root)." Nothing tells the agent to delete it.
*Why it matters:* `SDLE_OWNED_PREFIXES` does not cover repository-root files, so the leftover `*.json` is an untracked file that trips `dirty_tree` at the implementation preflight several phases later, with a diagnostic that points nowhere near the cause. `conftest.record_architecture` unlinks the file in a `finally` — the test fixture knows the rule the prompt does not state.
*Fix:* add "delete the scratch proposal once `assess` succeeds" to Step F.

**R1-014 · LOW · `scripts/sdle.py` — `architecture_binding_precondition` (patch 6304-6351), `read_architecture_record` (patch 6857-6882)**
The hook receives `resolved` (the `ARTIFACT_OWNERSHIP` path the gate fingerprinted) but never asserts `record["renderedArtifact"] == resolved`; `read_architecture_record` never asserts `record["workitem"] == paths.workitem`.
*Why it matters:* the gate fingerprints one path and the binding verifies another. Both are write-fenced, so this needs a hand-edit — but the binding check exists for exactly the hand-edit case.
*Fix:* two one-line equality checks.
*Test:* no.

**R1-015 · LOW · `scripts/sdle.py` — dead and misleading code in the new module**
`_validate_outcome_requirements` re-checks `current_owner not in service_ids` at patch 5656 and 5697, after `_require_known_services` (5483) has already refused that case — both branches are unreachable. `implemented` (5647) holds services with status `PLANNED` **or** `IMPLEMENTED`; the name says otherwise. `architecture_apply`'s `state` parameter (patch 6588) is never read — `test_a_stale_base_revision_is_refused_and_writes_nothing` passes `{}`.
*Why it matters:* dead branches and a lying local name are what the next reader mis-trusts; the unused parameter invites a caller to think state is consulted.
*Fix:* delete the two branches and the parameter, rename `implemented` to `claimed`.

**R1-016 · LOW · `scripts/sdle.py:5647-5671, 5650-5661` — outcome floors diverge from contract §5**
`CREATE_NEW_SERVICE` refuses a `targetOwner` that is merely `PLANNED`; the contract says "not already `IMPLEMENTED`". `EXTEND_EXISTING_SERVICE` checks only membership in `service_ids`, so a `WITHDRAWN` or `SUPERSEDED` service is an acceptable extension target; the contract says "an existing `IMPLEMENTED` or `PLANNED` service".
*Why it matters:* the first is stricter than specified and blocks the D14 reclaim path `apply_architecture_delta` (patch 6104-6105) explicitly supports; the second is looser and lets a WorkItem extend a boundary that was withdrawn.
*Fix:* match the contract's status sets in both branches.
*Test:* no test covers either status.

**R1-017 · LOW · `scripts/sdle.py` — `architecture_phase_precedes_spec_in_every_flow` (patch 7032)**
`if not placement < gate < spec` checks ordering, not adjacency. Contract §2.5 requires "immediately precedes" twice.
*Fix:* compare indices for `gate == placement + 1` and `spec == gate + 1`.

**R1-018 · LOW · `scripts/sdle.py:5796` — bootstrap evidence path check**
`(paths.project_root / item).exists()` — an absolute `item` discards `project_root` entirely, and `../..` walks out of the repository. The refusal message says "not in this repository", which is not what is checked.
*Fix:* reject absolute paths and any resolved path outside `project_root`.

**R1-019 · LOW · `scripts/sdle.py:5048, 5053, 6192` — enum and field additions absent from the frozen contract**
`EXTRACTING` added to `CANDIDATE_STATES`, `PLANNED` added to `DATA_OWNERSHIP_STATUSES`, `supersedes` added to the `Decision` object. All three look deliberate and `PLANNED` is load-bearing for the one-ACTIVE-owner invariant, but §4 of `docs/architecture/architecture-memory-contracts.md` is frozen and still lists the old sets.
*Fix:* amend §4; the contracts document is meant to be the place no stream invents these independently.

**R1-020 · LOW · `scripts/sdle.py:5196-5216` — one dangling-reference check from contract §4 is missing**
The contract names three: candidate → capability, **service → capability**, dataOwnership → service. The code checks candidate → capability, capability → ownerService and dataOwnership → service. `services[].capabilities` is never validated, so a bootstrap service can carry capability ids nothing defines.
*Fix:* add the service → capability check.

**R1-021 · LOW · `scripts/sdle.py` — `architecture_catalog_relative` (patch 5291-5293)**
Builds `f"{config_root_relative}/architecture/{…}"` with a second literal `"architecture"`, while `Paths.architecture_dir` already owns that name.
*Why it matters:* invariant 7, one source of truth per fact, in a project that enforces it by lint everywhere else.
*Fix:* `paths.architecture_catalog_file.relative_to(paths.project_root).as_posix()`.

**R1-022 · LOW · `scripts/sdle.py:11931` — the manifest exclusion was not narrowed alongside the guard**
`implementation_exclusions` still excludes `paths.config_root_relative + "/"` — all of `.sdle/`. D10's narrowing applied only to `SDLE_OWNED_PREFIXES`.
*Why it matters:* answering the parent's question directly — the narrowing weakens nothing; it only adds `.sdle/config.json` and `.sdle/policies/` to the dirty-tree guard. But those same two files remain invisible to the change manifest and the secrets scan, so a policy edit during an implementation trips the preflight and then vanishes from the evidence a reviewer sees. Worth a deliberate decision rather than an accident of two lists.
*Fix:* either narrow the manifest exclusion the same way or state in the comment why the two boundaries differ.

---

**22 findings · 1 blocking-severity CRITICAL, 4 HIGH.**

### Areas inspected
- `scripts/sdle.py` — the whole ADR-013 block (patch 4974-6748), `resolve_artifact_path`, `apply_advance`, `cmd_gate_approve`, `_approve_drift`, `cmd_gate_omit`, `gate_precondition_hook`, `cmd_skip`, `cmd_restart`, `cmd_reset`, `SDLE_OWNED_PREFIXES`, `implementation_exclusions`, the two new lint checks, `_check_capability_map`, `_skill_files`, `capability_directories`, the new sub-parsers; plus current-state reads of `read_state`/`save_state`/`touch_lock`, `reserve_evidence`, `cmd_discovery_assess`, `Flow.index`, `main`.
- `docs/architecture/architecture-memory-contracts.md` — in full, used as the specification.
- `.claude/skills/sdle/SKILL.md` diff (registry, `FLOW_PHASES`, `NEXT_PHASE`, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`, `CAPABILITY_MAP`, header example) — internally consistent with the engine at 20/9 and with contract §2; no number disagreement found.
- `.claude/skills/sdle/modules/architecture-placement.md`, `modules/gate-protocol.md` diff, `.claude/hooks/hooks.py` diff.
- `tests/test_units_architecture.py` in full, `tests/conftest.py` additions, `tests/test_dry_run_contracts.py` diff.
- `docs/troubleshooting/README.md` — all twelve refusal reasons from contract §14 have entries with deterministic remedies; no gap.

Direct answers to the parent's questions: **catalog written without human approval — yes, R1-001.** **Every refusal before the first mutation — no, R1-003 and R1-010.** **Replay rule — correct** (patch 6605-6640 distinguishes identical-digest replay, same-id-different-digest conflict and genuine staleness, and refuses a re-apply of a disposed decision). **Abandonment cascade — loses no decision history, but over-reaches onto other decisions' entities, R1-006; an unreadable catalog correctly blocks `reset` as §11 intends.** **One-ACTIVE-owner — structurally holds** through apply (new rows enter `PLANNED`) and realize (supersede-then-activate); the soft spots are `_upsert` keyed on `data` silently last-wins inside a single bootstrap delta, and hand-edits. **`SDLE_OWNED_PREFIXES` narrowing weakens nothing** (R1-022 notes the asymmetry it leaves).

### Areas not reached
- The four new dry-run transcripts (17-20, patch 3367-4243) and `docs/dry-runs/verification-matrix.md` — not read; I cannot confirm their cited test nodes exist or that their claimed refusals match the engine.
- `tests/test_lint_skill.py`, `test_units_flow_model.py`, `test_units_invariants.py`, `test_units_capabilities.py`, `test_units_state.py`, `test_units_transitions.py`, `test_units_workitem_runtime.py`, `test_units_repo_config.py`, `test_hooks.py` and the five integration drivers — diffs not read; `WRITE_PRIMITIVE_COUNTS`, `COMMANDS` and `GREENFIELD_PHASES` updates unverified.
- The six new `guidelines/*.md` files, ADR-013, ADR-014, `docs/enhancements/architecture-memory/PROGRESS.md`, and the README / Reference Guide / lifecycle / risk-and-gates / brownfield / tutorials prose diffs — flow-count and phase-table claims there are lint-enforced, and I did not check them by hand.
- `modules/phase-execution.md` (patch 723-900) — the new `architecture_placement` block and the renumbering of later blocks were not read.
- No test evidence: I cannot run the suite or `lint-skill`, so every "would a test have caught it" answer is from reading the test source, not from a run. The manifest is the parent's.

---

## Implementer disposition

Every finding gets exactly one disposition. **All twenty-two are ACCEPTED**;
nothing was rejected, so `claude-review-rejections.md` records no entry from
this round.

| ID | Disposition | What was done |
|---|---|---|
| R1-001 | ACCEPT | `cmd_architecture_realize` refuses `gate_required` without an approved `gate_implement`; the unit test now drives the gate instead of calling the function at `spec_draft` |
| R1-002 | ACCEPT | `introducesTechnologyDecision` is read from the envelope, reported by `architecture schema`, documented in `modules/architecture-placement.md`, and covered end to end |
| R1-003 | ACCEPT | `architecture_realize` hoisted beside `architecture_apply`, before the first `append_audit` |
| R1-004 | ACCEPT | the capability loop filters on the decision's own capability id, passed in from the record |
| R1-005 | ACCEPT | `architecture_realize` raises `architecture_placement_missing` rather than returning `None`; `architecture assess` refuses once `gate_architecture` is approved |
| R1-006 | ACCEPT | entities carry `introducedBy`, set only at creation; the abandonment cascade selects on it |
| R1-007 | ACCEPT | the constitution rule receives the ownership delta and the catalog, and refuses an ownership transfer or a new boundary with no constitution |
| R1-008 | ACCEPT | drift re-approval of `gate_architecture` is refused `architecture_artifact_binding_invalid` |
| R1-009 | ACCEPT | a record whose decision is `ABANDONED` or `SUPERSEDED` reads as missing |
| R1-010 | ACCEPT | `reserve_evidence` runs before the first `write_atomic`, as `discovery assess` does |
| R1-011 | ACCEPT | bootstrap references are validated at `assess` |
| R1-012 | ACCEPT | `architecture_decision_abandoned` is emitted on the supersession path; the contract is amended to record `SUPERSEDED` as that path's status |
| R1-013 | ACCEPT | Step F says to delete the scratch proposal |
| R1-014 | ACCEPT | both equality checks added |
| R1-015 | ACCEPT | dead branches, the unused parameter and the misleading name removed |
| R1-016 | ACCEPT | both status sets match the contract |
| R1-017 | ACCEPT | the lint check asserts adjacency |
| R1-018 | ACCEPT | absolute paths and paths outside the repository are refused |
| R1-019 | ACCEPT | contract §4 amended to carry `EXTRACTING`, `PLANNED`, `supersedes` and `introducedBy` |
| R1-020 | ACCEPT | service → capability added to the catalog's reference checks |
| R1-021 | ACCEPT | the relative path is derived from `Paths`, not rebuilt |
| R1-022 | ACCEPT | the manifest exclusion is narrowed the same way, so the two boundaries agree |
