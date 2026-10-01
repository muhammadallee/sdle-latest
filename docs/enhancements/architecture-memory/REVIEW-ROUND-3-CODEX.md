# Independent Review — Round 3, second reviewer (Codex)

Round 3 was reviewed twice, by two different reviewers, because the first
(`REVIEW-ROUND-3.md`, a read-only Claude subagent) found one regression and
the user asked for a Codex pass as well. This file is the second reviewer's.

Produced by the `codex:codex-rescue` agent through the shared Codex runtime,
instructed to review only — no edits, no test runs, no writing SDLE command —
over the committed patch `git diff d1b203a..HEAD` at `ac97c8e` (three commits),
with the same read-only reference copies of the engine before and after each
line of work. It was told that the first reviewer had already found the stale
`2/18` in dry-run 05, and not to limit itself to that reviewer's areas.

**The findings below are the reviewer's report, transcribed.** Each finding's
text is kept as written; nothing was trimmed or reworded. The implementer's
dispositions are in a separate section at the end.

---

## Findings

### C3-001 — CRITICAL

**File:line:** `scripts/sdle.py:8286`, `scripts/sdle.py:8322`

**What is wrong:** `cmd_architecture_apply` and `cmd_architecture_realize` test whether the approval entry is truthy, not whether its decision is `"approved"`. `cmd_gate_reject` writes a truthy `{"decision": "rejected", ...}` record. After rejecting `gate_architecture`, `architecture apply` still writes the rejected placement into the shared catalog. After rejecting `gate_implement`, `architecture realize` still promotes the decision and planned entities to implemented.

**Why it matters:** This bypasses the universally human-required architecture gate. It breaks the invariant that shared architecture mutations happen only behind an explicit approval. It also overrides an explicit human rejection.

**Concrete fix:** Replace both truthiness checks with `approval_decision(state, gate_key) == "approved"`. Refuse omitted, rejected, malformed or absent decisions. Consider one shared "requires an approved gate" helper so assess, apply and realize cannot drift apart.

**Test that would have caught it:** Reject `gate_architecture`, invoke `architecture apply`, and assert `gate_required` with a byte-identical or absent catalog. Separately, reject `gate_implement`, invoke `architecture realize`, and assert the decision and service remain `APPROVED_PENDING_IMPLEMENTATION` / `PLANNED`.

### C3-002 — HIGH

**File:line:** `scripts/sdle.py:8170`, `8211`, `8259`, `7752`

**What is wrong:** Catalog revision checking is a non-atomic read/check/write. Two WorkItems can both read revision N and both pass `baseRevision == N`. Each then produces revision N+1 and atomically replaces the catalog, so the last replacement silently loses the other decision. Realization and abandonment have the same race.

**Why it matters:** This breaks D11's optimistic-concurrency invariant. It can erase durable architecture history even though every individual write uses `write_atomic`.

**Concrete fix:** Put every catalog mutation through one short-lived repository-level transaction primitive. Acquire an exclusive catalog lock, re-read and validate the catalog under that lock, do the revision/replay check, then replace the file and release. This is not a lifecycle-wide lock.

**Test that would have caught it:** Run two base-revision-equal applies with a barrier after their initial read. Assert exactly one succeeds, the other gets `architecture_catalog_stale`, and the catalog holds the successful decision without lost history. Add equivalent apply-versus-realize and apply-versus-abandon cases.

### C3-003 — HIGH

**File:line:** `scripts/sdle.py:9995`, `10013`, `10200`

**What is wrong:** `cmd_gate_approve` returns into `_approve_drift` before reaching `gate_precondition_hook`, `governance_precondition`, or the flow, discovery, impact and architecture preconditions. It also skips omission revalidation. `_approve_drift` only resolves the artifact and checks its PASS review. It can therefore write audit and state and resume the pending phase in any of these situations:
- the acknowledgement store is malformed;
- governance is stale or blocked;
- required placement evidence is missing;
- a changed implementation manifest fails the deterministic test-evidence rules.

The structural test at `tests/test_units_governance.py:1128-1158` only checks that the guard's source line precedes `append_audit`. It does not establish that the guard dominates the drift return.

**Why it matters:** This violates governance-at-every-progression and refusal-before-first-write. It also bypasses gate-specific deterministic controls during re-approval.

**Concrete fix:** Run the applicable pure-reader precondition stack before dispatching to drift mode. Have `_approve_drift` run `gate_precondition_hook` for the queue head before changing baselines or appending.

**Test that would have caught it:** Queue drift, corrupt `scan-acknowledgements.json`, then attempt re-approval. Assert an integrity refusal with byte-identical state and audit. Also drift an implementation manifest to forged or failed test evidence, add a current PASS review, and assert the same deterministic implementation-evidence refusal as initial approval.

### C3-004 — HIGH

**File:line:** `scripts/sdle.py:9621`, `9646`, `9670`

**What is wrong:** `governance_precondition` validates the structure of the acknowledgement store but never re-scans the current bound bytes. It also never verifies that flagged content still has a matching acknowledgement. Suppose flagged content was acknowledged and assessed, then its acknowledgement entry is lost or deleted without changing the requirements. Governance freshness stays true, so `advance` and ordinary `gate approve` proceed.

**Why it matters:** This violates the required `governance_content_unacknowledged` enforcement at assess, advance and gate approve. After assessment, the durable acknowledgement no longer works as a progression precondition.

**Concrete fix:** Have the progression precondition obtain the bound bytes and hashes once, then call `unacknowledged_flagged_sources` before any replay or audit write. Share the same snapshot with freshness evaluation to avoid a second source read.

**Test that would have caught it:** Acknowledge flagged content, assess successfully, initialize, then remove only the matching acknowledgement while leaving requirements unchanged. Assert both `advance` and `gate approve` refuse `governance_content_unacknowledged` with byte-identical state and audit.

### C3-005 — HIGH

**File:line:** `README.md:489`, `docs/dry-runs/01-happy-path.md:128`, `docs/SDLE-Reference-Guide.md:1103`

**What is wrong:** All three canonical GREENFIELD walkthroughs approve `gate_constitution` and jump directly to `spec_draft`. They omit `architecture_placement`, its structured assessment and review, and the universally required `gate_architecture`. README shows Phase 6 while saying "Moving to Phase 4", and its approval table omits `gate_architecture`.

**Why it matters:** This contradicts the universal architecture-before-specification invariant and the engine's actual next-phase transition. These are user-facing execution instructions, and the dry run is described as behavioural specification.

**Concrete fix:** Insert the complete architecture placement and Gate 2 segment between constitution approval and specification in all three walkthroughs. Include the architecture review, catalog mutation, status headers, approval table and engine-command narration.

**Test that would have caught it:** A documentation transcript test that extracts ordered phase/gate transitions. It should require each GREENFIELD example to be an ordered subsequence of the engine flow and specifically reject `gate_constitution → spec_draft`.

### C3-006 — MEDIUM

**File:line:** `scripts/sdle.py:8088`, `docs/architecture/architecture-memory-contracts.md:548`

**What is wrong:** `proposalDigest` hashes only `evaluation["placement"]` and excludes `bootstrapDelta`. Bootstrap content is part of the validated proposal and is applied to the catalog. Two proposals with identical placement but different bootstrapped services, capabilities or ownership get the same proposal digest.

**Why it matters:** D11 relies on decision ID plus proposal/content digest to tell an identical replay from different content. The current digest does not identify the full catalog mutation.

**Concrete fix:** Digest a canonical object containing at least both the validated `placement` and `bootstrapDelta`, using the same normalized representation that is later applied.

**Test that would have caught it:** Validate two proposals differing only in `bootstrapDelta` and assert different digests. Also simulate a same-ID replay with changed bootstrap content and require `architecture_decision_conflict`.

### C3-007 — MEDIUM

**File:line:** `scripts/sdle.py:8233`, `8247`

**What is wrong:** `architecture_realize` matches only `decisionId`. It does not verify that the catalog decision belongs to the current WorkItem or that its `proposalDigest` equals the WorkItem record. Even the `IMPLEMENTED` replay branch returns success without the "same digest" condition the frozen contract requires.

**Why it matters:** This breaks D1 WorkItem isolation and D11 replay identity. A mismatched or restored record can be reported as a successful replay. It can also drive realization using capability data from a different record.

**Concrete fix:** Before either the replay or the mutation branch, require a matching `workItem` and `proposalDigest`. Otherwise refuse with `architecture_decision_conflict` or an integrity-specific reason.

**Test that would have caught it:** Change only the WorkItem record's digest while keeping its decision ID, and assert realization refuses and leaves the catalog byte-identical. Repeat with a decision ID belonging to another WorkItem.

### C3-008 — MEDIUM

**File:line:** `scripts/sdle.py:7487`, `7529`

**What is wrong:** The governed rendering shows only bootstrap service IDs and paths, capability IDs and statuses, and evidence. It omits bootstrap `dataOwnership` entirely. It also omits material service and capability fields such as owned data, dependencies, capability ownership and descriptions. `apply_bootstrap_delta` nevertheless writes all of those hidden values into the shared catalog.

**Why it matters:** This weakens D15 and the exact-artifact gate invariant. The human-reviewed Markdown does not disclose the full structured catalog delta being approved.

**Concrete fix:** Render the complete normalized bootstrap delta, including every field `apply_bootstrap_delta` can mutate. Alternatively, make a canonical full structured delta a displayed and gated companion artifact.

**Test that would have caught it:** Assess a bootstrap containing ownership, dependencies, owned data and capability ownership. Assert every applied value appears in the rendered gate artifact before approval.

### C3-009 — MEDIUM

**File:line:** `scripts/sdle.py:12347`, `12349`

**What is wrong:** The post-init `accept-content --path` route writes the durable acknowledgement before reading and validating existing state. If `state.json` exists but is malformed or unsupported, the command returns an integrity refusal after already changing `scan-acknowledgements.json`.

**Why it matters:** This violates refusal-before-first-write. State and audit stay unchanged, but the security decision store is mutated by a refused command.

**Concrete fix:** If state exists, read and validate it before writing the acknowledgement. Do all other refusing checks before either store is changed.

**Test that would have caught it:** Plant malformed state and preserve the acknowledgement bytes. Invoke `accept-content --path` on flagged content and assert the integrity refusal leaves the acknowledgement store byte-identical or absent.

### C3-010 — MEDIUM

**File:line:** `docs/SDLE-Reference-Guide.md:470`, `520`, `1078`; `docs/dry-runs/README.md:32`; `docs/tutorials/greenfield.md:339`; `docs/tutorials/brownfield-discovery.md:14`

**What is wrong:** Current documentation still publishes the pre-architecture registry, flow sizes, gate totals, positions and completion text.
- The Reference Guide says 21 registry rows, GREENFIELD 18/8 and a ten-phase mandatory floor. Its example uses `/18` and Gate 1–8 throughout.
- The dry-run index still says DR-01 is 18 phases / 8 approvals and DR-06 uses Gate 7.
- The greenfield and brownfield tutorials still say eight gates.

**Why it matters:** This violates lint-skill cross-file synchronization and gives incompatible lifecycle instructions. The correct values are a 23-row registry (`phase_count` 22), GREENFIELD 20/9, and a twelve-phase mandatory floor.

**Concrete fix:** Re-derive all current-document counts and positions from `flow show` and the constant tables. Exclude genuinely historical ADR and review statements from the sweep, but update present-tense guides, tutorials and scenario indexes.

**Test that would have caught it:** Extend documentation-count validation to cover quoted Markdown tables, narrative "contains N gates" forms, scenario-index prose, and progress/gate fractions in current guides. The existing check covers only three claim shapes.

### C3-011 — MEDIUM

**File:line:** `tests/conftest.py:652`, `tests/test_units_capabilities.py:643`

**What is wrong:** The restatement-search exemption now excludes two complete implementation-state directories, not just generated run logs. Those directories contain authored `PLAN.md`, `BRIEF.md`, prompts, replies, dispositions, Python prototypes and ledgers. The updated test explicitly blesses skipping all of them.

**Why it matters:** This weakens the lint-skill cross-file-sync invariant. Authored material that could restate engine facts is hidden from the invariant-7 search.

**Concrete fix:** Exempt only generated or raw evidence paths such as `runs/` and specifically justified ledger files. Keep authored plans, prompts, replies and prototypes searchable.

**Test that would have caught it:** Put a forbidden engine-fact restatement in `requirements-refinement/PLAN.md` and `open-items-01-02/review-rounds/round1.prompt.md`. Assert both stay in `searchable_files`, while raw event logs remain excluded.

### C3-012 — LOW

**File:line:** `tests/test_units_invariants.py:239`

**What is wrong:** The write-primitive call-site pins use raw substring counts. At HEAD, `write_atomic(` has 30 syntactic occurrences including its definition, while `"write_atomic"` appears 32 times. `append_audit(` has 51 syntactic occurrences including its definition, while `"append_audit"` appears 56 times. Comments and docstrings therefore satisfy part of the asserted totals, and the patch's own explanatory comments contain the pinned primitive names.

**Why it matters:** The test can stay green after a real writer is removed or added, if a comment changes to match. It does not reliably enforce the single-writer / call-site invariant it claims to pin.

**Concrete fix:** Parse the AST and count actual `Call` nodes by resolved function name. Assert the primitive definitions separately.

**Test that would have caught it:** Rewrite `test_the_engine_writes_through_a_known_number_of_call_sites` as an AST-based call inventory, and show that comments containing primitive names do not affect the count.

### C3-013 — LOW

**File:line:** `scripts/sdle.py:247`, `scripts/sdle.py:3504`

**What is wrong:** `Paths` defines `scan_acknowledgements_file`, but `workitem_runtime_member_names` omits it. The repository-boundary leak detector therefore does not flag a misplaced repository-global `.sdle/scan-acknowledgements.json`. Its docstring promises that new runtime members inherit the check.

**Why it matters:** This weakens WorkItem / requirements isolation and the single-writer ownership boundary for the acknowledgement store.

**Concrete fix:** Add `bound.scan_acknowledgements_file` to the derived runtime member tuple.

**Test that would have caught it:** Place `.sdle/scan-acknowledgements.json` at repository scope and assert `validate` reports `lifecycle_state_in_repository_config`.

### C3-014 — LOW

**File:line:** `scripts/sdle.py:4525`, `4532`, `12252`

**What is wrong:** The Windows-alias loop treats `.` and `..` as components ending in a dot. `./requirements/x.md` is therefore refused instead of canonicalized as the later `cmd_scan` comment promises. A leading `../` is classified with the misleading cross-platform-alias message before the traversal check can run.

**Why it matters:** Path containment fails closed, but the diagnostics and documented canonicalization disagree with the engine. That increases the chance of unsafe workarounds.

**Concrete fix:** Do `.`/`..` normalization and the traversal check before the Windows trailing-dot rule, or exempt those two components from the alias check.

**Test that would have caught it:** Assert `scan --path ./requirements/x.md` uses the canonical key, while `../x.md` refuses through the traversal branch with the repository-escape message.

### C3-015 — LOW

**File:line:** `.claude/skills/sdle/modules/gate-protocol.md:172`, `scripts/sdle.py:7382`

**What is wrong:** The gate prompt says architecture remediation produces a new `decisionId` and that the previous placement is superseded, never edited. The engine deliberately reuses the same number for an unapplied or rejected placement and overwrites the fixed record and rendering paths. Only the evidence copy preserves the prior proposal.

**Why it matters:** This is a direct prompt-versus-engine disagreement. It violates lint-skill synchronization and makes audit interpretation ambiguous.

**Concrete fix:** Either change the prompt to describe ID reuse and evidence preservation accurately, or change ID minting and artifact retention to implement the promised semantics.

**Test that would have caught it:** Reject and reassess architecture, then assert the documented ID and preservation behavior explicitly.

### C3-016 — LOW

**File:line:** `scripts/sdle.py:14347`, `tests/test_units_workitem_runtime.py:61`, `:381`, `tests/test_units_speckit_binding.py:105`

**What is wrong:** Source documentation still says GREENFIELD uses `N/18` and `18/18`. Test helpers construct `implement` as `15/18` and `security_review` as `17/18`. Another test describes a GREENFIELD driver as "All 18 phases." The current positions are `17/20` and `19/20`, and GREENFIELD has 20 phases.

**Why it matters:** This violates synchronization. It makes fixtures internally inconsistent, so tests can miss code that mistakenly trusts stale `progress`.

**Concrete fix:** Update the docstring and derive fixture progress from `flow.progress_for(phase)` instead of literals.

**Test that would have caught it:** Add a static sweep of current docs for legacy GREENFIELD denominators, excluding explicitly historical material. Also assert that every test-written state has progress matching its bound flow and current phase.

## Areas inspected

- Entire patch inventory and all changed-file hunks.
- Both supplied reference versions of `sdle.py`.
- Frozen D1–D15 contracts and architecture lifecycle/replay/abandonment sections.
- `cmd_init`, `apply_advance`, `cmd_advance`, `cmd_gate_approve`, `_approve_drift`, `cmd_gate_omit`, `cmd_skip`, `cmd_restart`, `cmd_reset`.
- Governance assessment, freshness, acknowledgement validation and replay, scanning, acceptance, and path containment.
- Architecture assessment, rendering, apply, realize, catalog validation and mutation, abandonment, and gate hooks.
- Argparse and runtime-free command wiring.
- Write-primitive pins and relevant governance and architecture tests.
- SKILL.md, sdle-start, phase execution, gate protocol, hooks, current guides, tutorials, and dry-run counts and transitions.
- Requirements isolation and runtime/configuration leak detection.

## Areas not reached

- No tests, lint-skill invocation or writing SDLE command was run, per instruction.
- No dynamic Windows junction/symlink race reproduction.
- No exhaustive semantic review of unrelated implementation, manifest, discovery, baseline and SpecKit commands outside the identified gate interactions.
- Historical ADR, review and progress prose was not exhaustively normalized. It was treated as historical unless it presented current instructions.
- Guideline heuristic quality was sampled for integration consistency, not reviewed line by line as architectural advice.

---

## Implementer disposition

Every finding was checked against the code before it was dispositioned. The
check that sorted them: for each function a finding names, the body was
compared against the two reference engines. Where it is byte-identical to the
Stage 0 reference (`sdle.py.at-65b75df`), the defect predates this
enhancement and is not the enhancement's to fix; where it exists only in the
architecture code, it is.

| ID | Disposition | What was done / why |
|---|---|---|
| C3-001 | **ACCEPT** | Reproduced first: both new tests failed before the fix (a rejected `gate_implement` actually promoted the service). `apply` and `realize` now require `approval_decision(...) == "approved"`. The `assess` side already tested the decision (`sdle.py`, comment at the `decided =` check); the two verbs now agree with it. Tests: `test_a_rejected_architecture_gate_cannot_be_applied_by_the_replay_verb`, `test_a_rejected_implementation_gate_cannot_realize_a_decision`. |
| C3-002 | **ACCEPT** (user decision) | A short-lived exclusive lock, `.sdle/architecture/catalog.lock`, around the three read-check-write cycles (`architecture_apply`, `architecture_realize`, the abandonment path). Not a lifecycle lock: a reader never waits for it, and a lock older than 60 s is broken. A fresh one that outlasts 10 s is the new refusal `architecture_catalog_locked`. Proved to bite: with the lock bypassed the concurrency test reports **two** `replayed: False` applies at revision 1 — the silent overwrite — and with it restored exactly one wins and the other is `architecture_catalog_stale`. Tests: `test_concurrent_applies_cannot_silently_overwrite_each_other`, `test_a_held_catalog_lock_is_a_refusal_not_a_hang`, `test_a_lock_left_by_a_dead_process_is_broken_once_stale`, `test_the_lock_is_released_when_the_guarded_work_refuses`. |
| C3-003 | **REJECT** (out of scope, surfaced) | The drift-first dispatch in `cmd_gate_approve` is Stage 0's own structure (`cmd_gate_approve` in `65b75df` already returns into `_approve_drift` before `governance_precondition`). The architecture work changed `_approve_drift` by exactly one thing — a refusal for `gate_architecture` — and that refusal is the *stricter* direction. Each scenario the reviewer lists (malformed acknowledgement store, stale governance, a drifted implementation manifest) fails identically in the Stage 0 reference. See RR-006. |
| C3-004 | **REJECT** (out of scope, surfaced) | `governance_precondition` is byte-identical to the Stage 0 reference. The reviewer's scenario — an acknowledgement entry removed after assessment without the requirements changing — is a gap in Stage 0's gate, which the owner closed as VERIFIED. Genuinely worth a separate fix. See RR-007. |
| C3-005 | **ACCEPT** | Confirmed: `dry-runs/01` never showed Gate 2, the Reference Guide's worked example was still `/18` with Gates 1–8, and the README said "Moving to Phase 4" at Phase 6. All three now walk `architecture_placement` and Gate 2 from the engine's real numbers; DR-01's flow listing and engine note follow. `test_dry_run_contracts` passes (186). |
| C3-006 | **ACCEPT** | `proposalDigest` now covers `{placement, bootstrapDelta}`. Test failed first: `test_the_proposal_digest_covers_the_bootstrap_delta`. Contracts §9 updated. |
| C3-007 | **ACCEPT** | `realize` now requires the catalog decision's `workItem` and `proposalDigest` to match this WorkItem's record before either the mutation or the `IMPLEMENTED` replay branch, refusing `architecture_decision_conflict`. Test failed first: `test_realize_refuses_a_decision_that_is_not_this_workitems_or_digest`. |
| C3-008 | **ACCEPT** | The gated rendering now shows every field `apply_bootstrap_delta` writes — service capabilities, owned data and dependencies; capability description, status and owner; and the whole `dataOwnership` list. Test failed first: `test_the_gated_rendering_discloses_every_bootstrap_value_it_applies`. |
| C3-009 | **REJECT** (out of scope, surfaced) | `cmd_accept_content` is byte-identical to the Stage 0 reference. See RR-008. |
| C3-010 | **ACCEPT** | Verified and fixed: the Reference Guide's flow table (it sat in a blockquote, so lint's table-row check never saw it), registry size and mandatory floor; `dry-runs/README.md` DR-01; and the `greenfield`, `greenfield-full-tour`, `brownfield-discovery`, `defect-fix` and `hotfix` tutorials. Every number was taken from the engine (`constants`, `Flow.gate_number`), not derived by hand. The reviewer's suggested test (widening the count-claim shapes) is a good follow-up and is listed under limitations. |
| C3-011 | **REJECT** | Duplicate of R3-002 / RR-001. |
| C3-012 | **REJECT** | A pre-existing weakness of the pin, present on `main` (`ENGINE.count(needle)`); the reviewer's AST proposal is sound and recorded as a follow-up. This change did not add to it: the one docstring that named a pinned primitive was reworded rather than letting it bump the count. See RR-009. |
| C3-013 | **REJECT** | Duplicate of R3-005 / RR-004. |
| C3-014 | **REJECT** | Duplicate of R3-003 / RR-002. |
| C3-015 | **ACCEPT** | The engine is deliberate (`next_decision_id`: nothing carrying a rejected placement's id ever reached the catalog, so the number is reused and the earlier proposal survives in its evidence file). The prompt and the troubleshooting page were wrong and now say so. |
| C3-016 | **ACCEPT** | The `sdle.py` docstring no longer hardcodes a denominator; the two test fixtures now use `17/20` and `19/20`; the driver docstring no longer claims a phase count. |
