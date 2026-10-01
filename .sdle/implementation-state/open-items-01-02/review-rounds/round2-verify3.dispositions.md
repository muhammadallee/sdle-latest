# Third targeted verification — dispositions (stopping rule triggered)

Codex output: `runs/20260928T031813-round2-codex-open-items-verify3.a1.review.json`. Candidate `7935186`.
Four new findings, all rated medium. `closure_assessment` explicitly recommended owner escalation under
the stopping rule this session adopted before running this pass. Every finding verified before acting.

## V3-01 (medium) — control-character boundary bypass — ACCEPTED, fixed

**Confirmed by direct execution.** `_lexically_safe_path`'s `.strip()` runs before the control-character
check, so a path with a *leading or trailing* newline canonicalises cleanly — `entry_ok` only checked
that canonicalisation did not raise, never that the stored value already equalled its own canonical
form. Reproduced directly: `_lexically_safe_path(paths, "\n## AUDIT [forged]...")` returns
`"## AUDIT [forged]..."` (accepted, silently stripped) rather than raising. The *stored*, uncanonicalised
value is what `record_scan_acknowledgement_audit` interpolates into `audit.md`, so this reached the same
audit-chain-forgery class V2-03 closed for an *embedded* control character — via a *boundary* one
instead. Fixed: `entry_ok` now requires `a["path"] == canonical`, so nothing reaches replay that was not
already exactly what a trusted write produced. Regression test confirmed red against `7935186`, green
after.

## V3-02 (medium) — resolve-to-open race — PARTIALLY ACCEPTED, documented, not code-fixed

The underlying race is real: `safe_repo_path` reconstructs `target` from the canonical string rather
than returning the `resolved` handle `_lexically_safe_path` already opened. **But the suggested fix does
not close it**: Python's file APIs (`is_file()`, `read_bytes()`) re-resolve symlinks at the syscall that
actually opens the file, regardless of whether `.resolve()` was called on the `Path` object earlier — a
`Path` does not carry "already resolved" as an enforced property. Returning the resolved handle would
therefore behave identically to what ships today. Closing this for real needs a file-descriptor-anchored
open (`O_NOFOLLOW`/`openat`), which the earlier choke-point plan explicitly ruled out of scope ("don't
chase O_NOFOLLOW") — and which every other path-based read in this engine lacks too, including
`requirements_sources`, which `safe_repo_path` was built to mirror. This is a pre-existing, engine-wide
property of how the engine reads files, not a gap specific to `scan`/`accept-content`. Documented in
`safe_repo_path`'s own docstring rather than silently left unstated.

## V3-03 (medium) — cross-WorkItem acknowledgement transplant — ACCEPTED, fixed

**Confirmed by direct execution.** A fake acknowledgements file declaring `workitem-a` while
`paths.workitem` was `workitem-b` was accepted and honoured — `valid_shell` checked only the version and
the acknowledgements list, never the `workitem` field the writer always sets. The identical threat
`validated_binding` already guards against for the requirements binding (`owner != paths.workitem` →
refused) had no equivalent here. Fixed: `read_scan_acknowledgements` now requires
`doc.get("workitem") == paths.workitem`. Regression test confirmed red against `7935186`, green after.

## V3-04 (medium) — other path-taking commands lack containment — RECORDED, not fixed here, escalated

Confirmed by inspection: `cmd_governance_assess --input`, `cmd_discovery_assess`, `cmd_sha` and
`cmd_artifact_record` each join or open a user-supplied path with no containment check at all — an
absolute path or a `../` traversal reaches them unchecked. This is real, but it is **not** a DEF-RR-001
regression or something this session's changes introduced or touched: `cmd_governance_assess`'s `--input`
handling predates this entire body of work. It is a pre-existing, engine-wide characteristic well outside
OPEN-01/02's scope (which is specifically about the untrusted-content scan and its acknowledgement
mechanism, not a repository-wide audit of every CLI path parameter). Per the brief's own defect-scoping
rule, a pre-existing defect outside the mapped impact surface is recorded, not fixed in this change.
Escalated to the owner alongside this record, not fixed unilaterally.

## Closure

`closure_assessment.open_02_closed: true` (unchanged since the second pass). `open_01_closed: false`,
attributed specifically to V3-01/V3-03 (both now fixed) and V3-04 (out of scope, recorded). V3-02 is
accepted as a documented, engine-wide limitation, not an open defect this fix could close.

**Stopping rule invoked.** Codex's own summary called for owner escalation rather than a fourth targeted
pass. This is the third targeted-verification pass on this fix (after the formal two-round review); no
further Codex round runs without the owner's direction. Escalated in conversation alongside this record:
whether V3-04 should be triaged/fixed as its own piece of work, and whether the accumulated cost of four
verification passes on one defect fix changes the owner's view of shape (a) versus the alternatives
recorded in round1.reply.md's original "Design decision needed" section.
