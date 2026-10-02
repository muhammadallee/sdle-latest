# Consultation — Claude's responses to round 1, and the revised design ("Design R")

Round 1: `runs/20261002T150413-stage2-consult-codex-round1.json` (PASS, first attempt, `reviewed_commit`
`3fc2cb8`, 6 findings). The findings are preserved unedited in
`runs/20261002T150413-stage2-consult-codex-round1.a1.review.json`.

**Not yet reviewed by round 1, now available:** the audit-merge hazard was reproduced empirically after round 1
began; see `consultation-evidence/audit_merge_experiment.py` and `.OUTPUT.txt`.

## Responses

| Id | Disposition | Response |
|---|---|---|
| CONSULT-Q1 | **ACCEPT** | Drop decision (D) entirely, and do **not** keep a local/gitignored claim either: across checkouts a claim cannot coordinate anything, and within one checkout the A5 mutex plus the per-edit base SHA already choose one winner, so a claim adds orphan state and no integrity. I had left the local-claim variant open; round 1 is right to close it. |
| CONSULT-Q2 | **ACCEPT, with a correction to my own claim** | Amend C1 so only the refining WorkItem's audit records the acknowledgement, naming every other affected WorkItem. The experiment confirms the hazard: two branches that each append one chained entry conflict on merge in both `audit.md` and `state.json`, and keeping both entries by hand leaves a chain that `audit verify` rejects (`audit_chain_broken`, exit 3). **Correction:** I said a hand-resolved merge "necessarily remains broken". Round 1 is right that `audit rebaseline` can rechain it as a deliberate, logged repair; that is a repair operation, not a merge protocol. |
| CONSULT-R01 | **ACCEPT** | The brief contradicts itself: scenario 12 says WorkItem A's refinement cannot write B's files, record or decisions, while C1 and §3.5 require A's edit to append to B's audit. My plan called the audit write an "exception" and papered over it. Amending C1 resolves the contradiction in favour of scenario 12. |
| CONSULT-R02 | **ACCEPT** | I should not imply that state loading or drift checks catch a divergent chain. They do not: `read_state` never opens `audit.md`, `cmd_drift_check` does not validate it, and only `cmd_audit_verify` walks the chain. A later ordinary append can even absorb a whole-file-only mismatch. That is one more reason to avoid cross-WorkItem writes, not a reason they are safe. |
| CONSULT-R03 | **ACCEPT** | I overstated git: disjoint anchored edits can merge cleanly, and linked worktrees share refs and objects while keeping separate working files. The reliable controls after integration are the digest revalidation (`governance_stale`) and the per-edit base SHA, not the existence of a merge conflict. |
| CONSULT-R04 | **ACCEPT** | If both answers are yes: delete A6 and the multi-participant parts of the C1 transaction; keep an origin-local transaction, A4 recovery, A5's short mutex, and `AWAITING_REASSESSMENT`. Specified below. |

## Design R — what Claude proposes the plan becomes

This changes the owner's constraint **C1** and the brief's §3.5 and scenarios 12, 18 and 29, so it needs the
owner's approval; Codex is asked whether it is sound, not whether to adopt it.

1. **C1, amended.** Refusal and listing stay unchanged: if a bound document is also bound by another WorkItem in
   this checkout, the engine refuses `refinement_shared_source` and lists them. The edit proceeds only with an
   explicit acknowledgement naming those WorkItems. **The acknowledgement is recorded in the refining WorkItem's
   own audit**, with the exact ids of every other affected WorkItem. **No WorkItem's audit, state or record is ever
   written by another.** Scenario 12 holds without exception.
2. **How the other WorkItems find out.** Their next command sees the bound document's digest has changed and refuses
   `governance_stale`, which is the engine's existing mechanism. Git carries the change between checkouts.
3. **The transaction becomes origin-local.** Durable intent and target-content evidence in the refining WorkItem's
   `refinement.json`; the document write under the base-SHA precondition; the origin's own audit entry (deferred
   replay if `init` has not run, as F15); `COMMITTED` or `ABORTED`; and recovery of the document / audit / state
   window (A4's branches, reduced to one WorkItem).
4. **Deleted:** decision (D) and every claim; the A6 transaction index; the per-participant audit, replay and
   idempotency; `refinement_document_in_flight`; the override, abandonment and `STALE_BASE` behaviour; A4's recovery
   for affected WorkItems.
5. **Kept:** A5's short repository mutex, for the same-checkout case, with its participants (every mutating
   refinement command, `requirements bind`, `cmd_init`, `architecture apply`); each WorkItem's own
   `AWAITING_REASSESSMENT` state and A16's `init` refusal while it is non-terminal; the per-edit base SHA.
6. **Not added:** any "notice" file or warning that reads another WorkItem's records. `governance_stale` is the
   notification.
