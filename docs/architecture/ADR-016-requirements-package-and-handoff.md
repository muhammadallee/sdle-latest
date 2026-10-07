# ADR-016 — A requirements package is approved at a digest, and a WorkItem starts from it

**Status:** Accepted
**Date:** 2026-10
**Builds on:** ADR-012 (requirements binding), ADR-013 (repository-level knowledge), ADR-015 (refinement). It changes none of their rules.

---

## 1. The decision

SDLE starts from supplied requirements. For a large source document (an SRS) that is not enough: a developer should not have to re-read and re-interpret the source, and a Solution Architect (SA) should approve exactly what the developer starts from. So:

- A **requirements package** is a uniform, engine-validated rendering of a source document: a manifest (`package.json`) plus markdown files, under `requirements/packages/<package-id>/`.
- The **SA approves the package at an exact digest**. The approval is an engine-written, hash-chained, append-only ledger at repository level, outside the package directory.
- **One package work item (`WI-nnn`) is one SDLE WorkItem.** `package intake` creates and binds them; a full SRS never authorises implementation in a single WorkItem. (Documentation says "package work item" for the requirement unit and "WorkItem" only for the runtime unit.)
- `init` refuses a WorkItem whose package is unapproved or stale, or whose work item is NOT READY. A started WorkItem is **pinned** to the revision it began under.

This ADR adds no phase, no gate and no `state.json` field; `CURRENT_VERSION` is unchanged.

## 2. The contract

`package.json` carries the package id, the source documents (path, SHA-256, the version or date the source states), the **id grammar declared once**, the file list (role and digest per file), the work items (readiness, own file, shared files they cite), the requirements (id, kind, statement, status, a source reference or a clarification reference, an assignment or an exclusion), retired ids, open issues and the supporting files deliberately left out.

- Ids are immutable once approved and never reused. A split, merge or move retires the old id; the replacement says what it `supersedes`. The engine extracts ids **by the declared grammar only**, never by matching wording.
- `package validate` names **every** offender in one refusal (`package_invalid`, one `rule` per offender).
- Supporting files are generated only when the source warrants them; the overview names each absent one with its reason; an empty file is a refusal.
- Nothing is invented: a detail the source does not support becomes an open issue, and a work item with a blocking open issue cannot be READY.

## 3. Where things live, and who writes them

| Thing | Location | Writer |
|---|---|---|
| Source documents | wherever they are | nobody; never modified |
| Draft | `package-staging/<id>/` (unfenced, git-ignored) | the orchestrator |
| Imported package | `requirements/packages/<id>/` (fenced and scanned) | `package import`, `package reseal` |
| Approval ledger and approved revisions | `.sdle/package-approvals/<id>/` (fenced) | `package approve` |
| A WorkItem's pin | `workitems/<id>/.sdle/package-binding.json` | `init`, `package adopt` |

The fence is not weakened. `requirements/` and the ledger are written only by the engine; staging is the one place a model may draft, and `package import` is the only thing that moves a draft into place, after scanning it for injected instructions and validating it. The ledger sits outside the package so an approval never changes the digest it approves.

**Approved revisions are stored.** `package approve` builds the package's copy beside its destination in `.sdle/package-approvals/<id>/revisions/`, verifies it reproduces the digest it will be filed under, and moves it into place in one step, so a crash never leaves a revision that is present and incomplete; an existing revision is verified before it is trusted. That makes `package show --diff` work without Git and gives ID history something to be checked against: an approved id may not silently disappear, move to another work item or change kind; a retired id may never come back, and the retired set only grows across approved revisions. A requirement's *statement* may be edited under the same id: whether an edit changes what a requirement means is the fidelity review's judgement, not something the engine can decide.

**Import publishes what it validated.** Staging is unfenced, so `package import` reads it once, writes that snapshot to a private directory, scans and validates the snapshot, and replaces the package by moving the validated directory into place (never by editing the old one). A link inside a package, in staging or in the package already imported, is refused: a link could point anywhere, and the engine never follows one. Every package and approval directory is proved to be inside the repository with no link in its path before it is read, copied or replaced. A manifest cannot name a path outside the package (or, for a source document, outside the repository), and an id pattern is a small deterministic language (literals, `\d`, classes, groups of same-length alternatives, exact `{n}` repetition) so no manifest can hand the engine a pattern that backtracks.

**One writer at a time.** Every command that changes a package or its approvals holds an operating-system lock for its whole run; the operating system releases it if the holder dies, and nothing ever breaks it by age. The approval also re-reads the ledger and the package digest immediately before it writes, and refuses rather than overwrites if either moved.

## 4. Approval

An approval is a record of package id, digest, approver, role, timestamp, the approver's wording and the previous record's hash. A package is **approved iff its current digest equals the digest of the latest record**; any later change makes it *stale*, and earlier records are immutable history. The approval is not a lifecycle gate: the SA is not in the developer's session, and no existing gate approves requirements.

Approval display (ADR-016's one deliberate, scoped relaxation of invariant 4): the overview, every work item's `requirements.md`, the open issues and the readiness verdicts are shown in the conversation; a re-approval also shows the diff since the last approved revision. Supporting files are listed with their digests and shown on request.

## 5. Handoff, pin and change

- `init` runs `package_handoff_precondition`, a pure reader ahead of the first write: `package_approval_missing`, `package_approval_stale`, `package_workitem_not_ready`, `package_binding_invalid`, `package_binding_mixed`. It is **inert for any binding that names no package file**, so every legacy WorkItem is unaffected.
- `init` writes `package-binding.json`: package id, work item, digest, the approval record's hash. Governance freshness (ADR-012) sees only the *bound* files, so a change to the manifest or to a shared file the work item does not bind would be invisible to it; the pin covers the whole package. `package_pin_precondition` refuses `package_revision_changed` ahead of the first write at every site that already runs `governance_precondition` (`advance`, `gate approve`, `gate omit`, `skip`), at the first call of `skip` (which saves a pending confirmation before it gets there), at drift re-approval, at `gate reject` and at `remediate begin`.
- **Before `init`**, refinement (ADR-015) may edit a package file; the approval becomes stale and `package reseal` recomputes the file digests, keeping the ledger. **After `init`**, refinement is refused (ADR-015) and a changed package goes through staging, `package import --replace`, SA approval and `package adopt` (which re-checks that the new revision is approved and that this work item is still present, READY and exactly bound, re-pins, audits, and records the assessment it was made against: progression is refused `package_reassessment_required` until a different assessment exists, and adopting again never forgets a reassessment that is still owed). Reassessment alone never re-pins.
- `requirements bind --all-current` excludes `requirements/packages/`: a package is bound deliberately, work item by work item.

## 6. What this does not do

- It does not verify that a requirement says what its source says. That is a review (`sdle-requirements-review`, source-fidelity mode), put to the SA in the conversation.
- It does not verify who the approver is.
- It does not trace requirements into the specification, tasks or tests; that is the traceability work (ADR-017).

## 7. Enforcement split

Written out as ADR-007 §3 does, and not to be softened.

**The engine guarantees:** package validity by the declared rules; the digest; the approval ledger's hash chain and its fail-closed read; that an approval is bound to the digest it recorded; the handoff refusals at `init`; the pin and its refusal ahead of the first write; ID history across approved revisions; that `requirements/` and the ledger are written only by the engine (together with the write fence); that source documents are never written.

**The Claude Code runtime guarantees, not SDLE:** that the write-fence hook fires and that a subagent's `tools:` grant and `PreToolUse` fence are honoured. SDLE checks the declaration, not the runtime's honouring of it; project hooks load only from the launch directory.

**Convention only:** that the approver named is the person who approved (the ledger records a name it is given); that a human rather than the orchestrator approved; that the source-fidelity review was delegated at all and its findings reported faithfully; that `--actor-name` truthfully names a reviewer. The recommendation, in documentation only, is to protect `requirements/packages/` and `.sdle/package-approvals/` with CODEOWNERS and branch protection, so the Git host supplies real identity.

## 8. Rejected alternatives

- **An SA approval as a lifecycle gate.** The SA is not in the developer's session; a gate needs the artifact in conversation for a human decision (invariant 8), and nothing in this flow holds one open for a person who is not there.
- **Writing the package through the model's file tools.** `requirements/` is fenced precisely so a model cannot edit what it is told to treat as ground truth; weakening it to admit packages would weaken it for everything.
- **The ledger inside the package.** An approval would change the digest it approves.
- **Matching ids by wording.** A requirement id is a declared grammar, not a guess.
