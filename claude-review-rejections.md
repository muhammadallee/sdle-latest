# Independent Review Rejections

Findings the isolated reviewer agent raised that the implementer rejected after
counter-review. Accepted findings are implemented, not listed.

---

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
