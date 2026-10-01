# Independent Review Rejections

Findings the isolated reviewer agent raised that the implementer rejected after
counter-review. Accepted findings are implemented, not listed.

---

## Index

Round 1 and Round 2: nothing rejected. Round 3 (two reviewers — a Claude
subagent and Codex): nine findings rejected (RR-001 to RR-009), every one of
them a defect or choice that exists identically in the Stage 0 reference
(`65b75df`) or in `main`, and not introduced by the architecture enhancement.
Everything the Codex review found in the architecture code itself, including
its one CRITICAL, was accepted and fixed.

## Round 1 — nothing rejected

All twenty-two findings from
[`docs/enhancements/architecture-memory/REVIEW-ROUND-1.md`](docs/enhancements/architecture-memory/REVIEW-ROUND-1.md)
were **accepted and implemented**. One CRITICAL (`R1-001`, an unguarded
`architecture realize`), four HIGH and seventeen MEDIUM/LOW; the dispositions
table in that file records what each fix was.

Two findings were accepted with a deliberate choice about *how*, recorded here
because "accepted" alone would understate the decision:

- **R1-012** asked the implementation either to align with the contract
  (`ABANDONED` for a rerun supersession) or to amend it. The contract was
  amended: a decision replaced by a later placement for the same WorkItem
  records `SUPERSEDED`, because `architecture show` distinguishes "walked away
  from" and "replaced" and the second is the truthful one. The half of the
  finding that was not a choice — the missing `architecture_decision_abandoned`
  ledger entry — was fixed as raised.
- **R1-022** asked either to narrow the change-manifest exclusion alongside the
  dirty-tree guard or to state why the two boundaries differ. It was narrowed.
  Leaving them different would have meant a `.sdle/policies/` edit during an
  implementation trips the preflight and then disappears from the evidence a
  reviewer reads, which is the asymmetry the finding named.

This file exists from the start of Round 1 so that an empty section is itself a
record: nothing was rejected, rather than nothing having been reviewed.

---

## Round 3 — rejected

Round 3 reviewed the reconciliation that restored Stage 0 (OPEN-01/02) after
the architecture tree was found to have reverted it. Findings R3-001, R3-006
and R3-008 were accepted. The five below were not, and none is a CRITICAL or
HIGH finding, so §8.7 does not require stopping — but R3-003 and R3-004 are
real, so they are surfaced to the owner rather than left to sit here.

## RR-001 — MAINTENANCE_RECORDS exempts whole directories
**Round:** 3  **Finding id:** R3-002  **Severity as raised:** MEDIUM
**Reviewer finding:** the restatement-search exemption names three whole
directories, two of which hold authored prose next to raw event streams.
**Affected files:** `tests/conftest.py`, `tests/test_units_capabilities.py`
**Counter-analysis:** the enumerated three-entry set is Stage 0 / Stage 1's
reviewed design (its docstring says widening is "a reviewed decision each
time"), and CI proved the widening necessary. The merge carried it across
unchanged.
**Evidence:** `git diff main 65b75df -- tests/conftest.py`; commits `e5af3a4`, `84925f2`.
**Disposition:** REJECTED  **Reason:** not introduced here; narrowing is the owner's call.
**Residual risk:** Low — authored prose under those directories is exempt from the invariant-7 scan.

## RR-002 — `_lexically_safe_path` refuses `./x` and mis-messages it
**Round:** 3  **Finding id:** R3-003  **Severity as raised:** MEDIUM
**Reviewer finding:** the alias check rejects `.` and `..` components, so
`./requirements/x.md` is refused `path_invalid` with a misleading message, the
`traversal` branch is unreachable for a leading `..`, and the `cmd_scan`
comment contradicts the code.
**Affected files:** `scripts/sdle.py`
**Counter-analysis:** identical in the Stage 0 reference `65b75df`. It is
refusal-side (fails closed), so it costs a user a retry, not a bypass.
**Evidence:** the Stage 0 reference; the `DEF-RR-006` scoping precedent.
**Disposition:** REJECTED for this change, **recommended as a separate fix**.
**Residual risk:** Low — misleading refusal, no bypass.

## RR-003 — no troubleshooting entries for the Stage 0 refusals; no way out of `scan_acknowledgements_invalid`
**Round:** 3  **Finding id:** R3-004  **Severity as raised:** MEDIUM
**Reviewer finding:** `governance_content_unacknowledged`,
`scan_acknowledgements_invalid` (exit 3), `path_invalid` and `content_flagged`
are undocumented, and an invalid store has no documented or engine-provided
recovery, with the write-fence blocking the parent session from editing it.
**Affected files:** `docs/troubleshooting/README.md`, `scripts/sdle.py`
**Counter-analysis:** Stage 0's own documentation never had these entries. The
missing recovery route is an engine design question, not a documentation gap.
**Disposition:** REJECTED for this change, **recommended as a separate fix**.
**Residual risk:** Medium — an integrity-failed store has no in-band repair.

## RR-004 — `workitem_runtime_member_names` omits the acknowledgement store
**Round:** 3  **Finding id:** R3-005  **Severity as raised:** LOW
**Counter-analysis:** identical omission in the Stage 0 reference.
**Disposition:** REJECTED for this change.  **Residual risk:** Low.

## RR-005 — registry phase count pinned by literal
**Round:** 3  **Finding id:** R3-007  **Severity as raised:** LOW
**Counter-analysis:** the pin was already a literal (`== 20`) with a
comment; `CLAUDE.md` says such pins change "on purpose and in the same
commit". Only the value moved.
**Disposition:** REJECTED.  **Residual risk:** None.

---

## Round 3, second reviewer (Codex) — rejected

Codex's report is in
[`docs/enhancements/architecture-memory/REVIEW-ROUND-3-CODEX.md`](docs/enhancements/architecture-memory/REVIEW-ROUND-3-CODEX.md).
Of its sixteen findings, nine were accepted and fixed (C3-001 CRITICAL, C3-002
HIGH, C3-005 HIGH, and six more); C3-011, C3-013 and C3-014 duplicate RR-001,
RR-004 and RR-002. The four below are new, all inherited, and the first two are
HIGH as raised — so, as with RR-002 and RR-003, they are surfaced to the owner
rather than left to sit here.

## RR-006 — drift re-approval runs before the precondition stack
**Round:** 3 (Codex)  **Finding id:** C3-003  **Severity as raised:** HIGH
**Reviewer finding:** `cmd_gate_approve` returns into `_approve_drift` before
`gate_precondition_hook`, `governance_precondition` and the flow, discovery,
impact and architecture preconditions, so a drift re-approval can proceed past
a malformed acknowledgement store, stale governance, or a drifted
implementation manifest that fails the test-evidence rules.
**Affected files:** `scripts/sdle.py`
**Counter-analysis:** the ordering is Stage 0's: `cmd_gate_approve` in
`sdle.py.at-65b75df` already dispatches to `_approve_drift` first. The only
change the architecture work made to `_approve_drift` is a new refusal for
`gate_architecture`, which is stricter. Each listed scenario fails the same
way in the Stage 0 reference.
**Evidence:** function-body comparison against the Stage 0 reference.
**Disposition:** REJECTED for this change, **recommended as a separate fix**.
**Residual risk:** Medium — a governance and evidence bypass on the drift path.

## RR-007 — an acknowledgement removed after assessment is not re-checked at advance
**Round:** 3 (Codex)  **Finding id:** C3-004  **Severity as raised:** HIGH
**Reviewer finding:** `governance_precondition` validates the acknowledgement
store's structure but does not re-scan the bound bytes or check that flagged
content still has an acknowledgement, so deleting the entry after assessment
leaves `advance` and `gate approve` free to proceed.
**Affected files:** `scripts/sdle.py`
**Counter-analysis:** `governance_precondition` is byte-identical to
`sdle.py.at-65b75df`. A gap in Stage 0's gate, which the owner closed as
VERIFIED; the store is also inside the write-fence, so closing it is not a
bypass available to the parent session.
**Disposition:** REJECTED for this change, **recommended as a separate fix**.
**Residual risk:** Medium.

## RR-008 — post-init `accept-content --path` writes before it validates state
**Round:** 3 (Codex)  **Finding id:** C3-009  **Severity as raised:** MEDIUM
**Counter-analysis:** `cmd_accept_content` is byte-identical to the Stage 0
reference. State and audit are left unchanged; only the acknowledgement store
is touched by a refused call.
**Disposition:** REJECTED for this change.  **Residual risk:** Low.

## RR-009 — write-primitive pins are raw substring counts
**Round:** 3 (Codex)  **Finding id:** C3-012  **Severity as raised:** LOW
**Counter-analysis:** the pin is `ENGINE.count(needle)` on `main`. The AST
rewrite the reviewer proposes is sound and is worth doing, but as its own
change to the test's method. This change did not make it worse: the one
docstring that named a pinned primitive was reworded instead of bumping the
count.
**Disposition:** REJECTED for this change.  **Residual risk:** Low.
