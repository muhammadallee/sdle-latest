# Independent Review Rejections

Findings the isolated reviewer agent raised that the implementer rejected after
counter-review. Accepted findings are implemented, not listed.

---

## Index

Round 1 and Round 2: nothing rejected. Round 3: five findings rejected (RR-001
to RR-005), all of them defects or choices that exist identically in the Stage 0
reference (`65b75df`) and were not introduced by the architecture enhancement.

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
