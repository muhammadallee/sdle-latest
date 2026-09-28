# Second targeted verification — dispositions

Codex output: `runs/20260928T021807-round2-codex-open-items-verify2.a1.review.json`. Candidate `ce8c02b`
(the run record's own `reviewed_commit` field says the same). Five new findings, `dispositions: []` (the
prompt asked to disposition nothing from round 1 — allowed via `codexrun_round2.py`'s new `allow-empty`
flag). All five verified directly (executed, against the live CLI or a fresh worktree) before acting —
several were themselves marked `evidence_type: "executed"` by Codex, meaning it ran code to confirm them,
not merely read the source.

## V2-01 (low) — Windows-alias key mismatch — ACCEPTED, fixed

Confirmed: `safe_repo_path` had none of `_binding_source`'s alias checks. Verified directly:
`requirements/todo-api.md.` (trailing dot) is now refused `path_invalid` by `scan --path`, matching
`_binding_source`'s existing rule exactly. Extracted the shared lexical checks into
`_lexically_safe_path`, used by both functions — the duplication that let `safe_repo_path` drift the day
it was written is now structurally impossible; a change to one rule changes both callers. Both functions
now return (or `safe_repo_path` returns) a canonical key, threaded through `pending_confirm_action`, the
acknowledgement record, the audit message and artifact, and emitted `data` — never the raw string a user
typed.

## V2-02 (medium) — bare route had no containment recheck — ACCEPTED, fixed

Confirmed: the bare `accept-content` route reconstructed `paths.project_root / flagged` directly,
never calling any path-safety function. Both routes now go through `safe_repo_path`, so a symlink
retargeted between `scan` and acceptance is caught rather than followed. Regression test simulates the
scenario by corrupting the pending confirmation to a spelling `safe_repo_path` refuses (standing in for
"the filesystem no longer agrees with what scan saw"); verified red against `ce8c02b`, green after.

## V2-03 (medium) — entry validator not total — ACCEPTED, fixed, and it was worse than one bug

Confirmed both halves directly: `a.get("sha256") or ""` passed a non-string sha256 straight to
`re.fullmatch`, raising `TypeError` (executed and reproduced); and a `path` containing `\n## AUDIT ` was
accepted by the old validator and would have been interpolated into `audit.md`, whose own parser treats
`## AUDIT ` as an entry boundary — a stored acknowledgement could forge a ledger entry. Fixed:
`isinstance(str)` checked before the regex; `path` re-validated through the same `_lexically_safe_path`
every write already uses; unknown keys rejected; `acknowledgedAt`/`session` type-checked. Both scenarios
reproduced end to end via the live CLI before the fix (a clean `governance_content_unacknowledged`-style
refusal is now impossible to get here — the file is rejected outright as `scan_acknowledgements_invalid`,
which is correct: a hand-tampered acknowledgements file is not a "content is unacknowledged" fact, it is
an integrity fact) and confirmed clean afterward.

## V2-04 (medium) — atomicity fix incomplete for gate approve/omit/skip — ACCEPTED, fixed

Confirmed by tracing the call graph, not just the reported line: `cmd_gate_approve`, `cmd_gate_omit` and
`cmd_skip` each call `governance_precondition(paths)` early with `state=None`, specifically so a refusal
precedes their own first irreversible audit append — but the V-04 fix gated *all* of
`record_scan_acknowledgement_audit` (validation and replay together) on `state is not None`, so those
early calls never validated at all. Split validation from replay: `record_scan_acknowledgement_audit` now
calls `read_scan_acknowledgements` (which raises on a malformed file) unconditionally, and returns before
replaying only when `state is None`. `governance_precondition` calls it before `record_governance_audit`
in every case, not only when `state` is given. Verified live for `gate approve` (malformed file → refused
`scan_acknowledgements_invalid`, `audit.md` byte-identical) before writing the test.

## V2-05 (low) — 12-hex marker + substring dedup — ACCEPTED, fixed

The marker now carries the full SHA-256, not a 12-character prefix. Replay de-duplication is now
structural (`_already_recorded`, parsing entries via the existing `split_audit_entries` and matching on
the entry's own `event` and `Artifact` fields, plus the marker within that same block) rather than a
substring search over the whole file — closing both the birthday-bound collision Codex described and the
cross-field suppression a crafted path or comment could otherwise cause.

## Closure

`closure_assessment.open_02_closed: true`. `open_01_closed: false`, on the basis of the five findings
above — all now fixed. No disagreement survived verification; nothing here needed the owner. This is the
third and final targeted-verification pass this session ran on this fix (the brief reserves the two
formal review rounds already used; every pass since has been a narrow check of changed material, per the
review protocol). The next step is one more Codex verification of this specific diff before treating
OPEN-01/02 as closed, per the stopping rule this session adopted: any further medium-or-higher invariant
violation goes to the owner rather than a further pass.
