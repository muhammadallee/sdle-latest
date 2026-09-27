# Round 2 dispositions

Codex output: `runs/20260927T224128-round2-codex-open-items-round2.a2.review.json` (the `a2` attempt;
`a1` is kept too — both are schema-valid, `a2` did more exploration per its own events log). Candidate
note on the run record explains the `reviewed_commit` mismatch (bookkeeping only, empty product diff).

Overall closure verdict returned: `open_01_closed: false`, `open_02_closed: false`. Every disposition and
new finding below is answered, then closure is reassessed at the end.

## Dispositions on my round-1 responses

**R1-D01 — REVISED.** Accepted in full. Verified directly against the live CLI: `init` succeeds with a
flagged, never-assessed, unacknowledged bound document (no governance record at all), while `advance`
then refuses `governance_missing` and a genuine assessment attempt still refuses
`governance_content_unacknowledged`. This is exactly the accepted consequence of two decisions already
made — O1 (governance is not an `init` precondition) and shape (a) (check at assess, not at init) — not
a new gap. **Partial challenge, evidence-backed:** "cannot reach `init` unexamined" was my own overclaim,
now corrected in three places (GETTING-STARTED, Reference Guide, dry-run 05) to "cannot pass a governed
assessment unexamined". Not escalated to the owner: the chain holds exactly as shape (a) implies, and
correcting the wording closes the gap between what is promised and what is true.

**R1-D02 — RESOLVED.** No response needed; agreed.

**R1-D03 — RESOLVED**, with the brittleness caveat about raw-string matching noted and accepted — the
static test is a regression guard for the specific omission reported, not a semantic parser, and does
not claim to be.

**R1-D04 — REVISED.** Accepted in full. Both original end-to-end tests started from `_bound`, so `reset`
preserved an existing binding rather than exercising the unbound branch. Two new tests added
(`test_registered_and_never_bound_runs_the_full_step_2b_sequence`,
`..._with_a_flagged_false_positive`) that start from `_registered` (create only), assert
`requirements show` reports `bound: false`, then actually run `requirements bind` before continuing
through preflight, scan, assess, init.

**R1-D05 — REVISED.** Accepted. `SKILL.md`'s scan-handling paragraph (lines 333-338, a section I had not
touched — my earlier fix only edited the governance-refusals paragraph) still told the orchestrator
"there is nowhere to record an acknowledgement... Never tell the user to say `accept content` here",
which is now false. Rewritten to describe both routes accurately. The Reference Guide's command table
row for `accept content` also updated to mention `--path`.

**R1-D06 — REVISED.** Accepted. The module docstring's "every other test begins from an already bound
WorkItem" overstated the gap — fourteen other modules also use `bare_project` — and was corrected to
name what those modules actually cover (narrower purposes, never the full documented sequence) versus
what this module now adds.

**R1-P01 — UPHELD.** No response needed; agreed, no change.

**R1-Q01 — REVISED.** Accepted; folded into the SKILL.md rewrite above, which now defines
`acknowledgeable` precisely ("whether the *bare* form will find something pending", not "whether any
acknowledgement route exists").

**R1-CLOSURE — UPHELD.** Agreed at round 2 time; see "Closure, reassessed" below for the position after
this round's fixes.

## New findings from round 2

**R2-D01 (high) — ACCEPTED, fixed.** Verified: `cmd_accept_content --path` called `read_text()` then a
separate `sha256_file()` (a second disk read); `unacknowledged_flagged_sources` compared a fresh scan
against `entry["sha256"]` computed by an earlier, separate call to `requirements_sources`. Both fixed to
read bytes once and derive both the hash and the decoded scan text from that single buffer;
`unacknowledged_flagged_sources` now compares acknowledgements against the hash of what it actually just
scanned, never a stale one from an earlier read.

**R2-D02 (medium) — ACCEPTED, fixed. This was a real regression.** Verified directly: after a post-init
flag, bare `accept-content` cleared `pending_confirm_action` and audited, but never wrote a content
acknowledgement — the next `governance assess` refused anyway, exactly as Codex predicted, reproduced
before the fix. `cmd_accept_content` rewritten so both forms converge: bare form now also writes the
acknowledgement (from one read of the file's current bytes); `--path` form now also clears a matching
`pending_confirm_action` when state exists. Re-verified after the fix: the same reproduction now passes
assessment.

**R2-D03 (low) — ACCEPTED, and it went deeper than reported.** Grepped every `raise Refused(` /
`raise IntegrityError(` site for these five strings before rewriting, per this repository's own
"don't guess APIs" rule. Confirmed: `governance_missing`, `governance_blocked` and `governance_stale` are
raised only by `governance_precondition` (the advance-time check) and, for `governance_missing`, also by
`governance show`/`governance gates` — never by `cmd_governance_assess`. `governance assess` itself raises
only `requirements_quality_blocked` (not `governance_blocked` — a different reason code for a related but
distinct fact) and the new `governance_content_unacknowledged`. SKILL.md's refusal list rewritten a third
time to state this split correctly, with the right reason codes attributed to the right commands.

**R2-D04 (low) — PARTIALLY ACCEPTED, deferred by design, pinned by a test.** Confirmed:
`write_content_acknowledgement` is an unlocked read-modify-write, and two concurrent acknowledgements for
different paths can race. Not serialised here: it fails closed (a lost acknowledgement is reported
unacknowledged again, never silently treated as accepted), and real serialisation belongs with the
refusing lock primitive the requirements-refinement work introduces for its own shared-document
transaction (D2 in that plan), not duplicated for this one file ahead of it. Documented in the function's
own docstring and pinned by
`tests/test_units_governance.py::test_a_lost_concurrent_acknowledgement_fails_closed`, which simulates the
race and asserts the lost acknowledgement is caught, not silently honoured.

## Closure, reassessed

With R2-D01 and R2-D02 fixed and R2-D03's attribution corrected: OPEN-01's engine mechanism is closed —
independently verified by direct CLI reproduction of every scenario Codex named — and every surface that
misdescribed it is corrected. OPEN-02's remaining gap (the unbound step 2b branch) is closed by the two
new tests. R2-D04 is an accepted, documented, tested-as-fail-closed limitation, not an open defect.

No disagreement survived reconciliation; nothing here needed the owner. A targeted Codex verification of
this round's changed material (not a full round 3 — the brief reserves exactly two rounds) follows before
this closes.
