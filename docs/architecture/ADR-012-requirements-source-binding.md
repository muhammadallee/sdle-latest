# ADR-012 — A WorkItem declares the requirements it is about

**Status:** Accepted
**Date:** 2026-09
**Amends:** ADR-008 TR25, which deferred the question of which repository-level directories are
genuinely WorkItem-scoped. This answers it for `requirements/`: neither, and the question was the wrong
shape.

---

## 1. The decision

A WorkItem holds a **requirements binding**: an explicit, recorded list of the requirement documents
that WorkItem is about. The binding is established before `preflight`, and every consumer — `preflight`,
the untrusted-content scan, the governance proposal, `governance assess`, `init`'s project-name
inference, and the discovery and impact-analysis phases — reads that one list.

`requirements/` stays at the repository root. Nothing moves.

Freshness compares the **bound** documents. A document that a WorkItem never bound cannot stale it.

## 2. The defect

F-101. `requirements_sources` globs the root directory and hashes everything in it; `governance_freshness`
re-globs and compares. So adding a document for WorkItem B refuses WorkItem A's next `advance` with
`governance_stale`, reproduced end to end.

The record already stores the exact source set with per-file SHAs. The comparison discards it and
re-enumerates. **The record is right; the comparison is wrong** — but fixing only the comparison is not
enough, because assessment still *selects* by globbing a directory, so two unrelated documents that both
exist at assess time stay coupled from the start.

## 3. Why not move the directory

The obvious fix is `workitems/<id>/requirements/`. It was rejected on evidence:

- **Repository-wide requirements would have nowhere to live.** A regulatory constraint, a product-wide
  availability target, or a common API invariant can legitimately govern several WorkItems.
  `BASELINE_REFERENCE_KINDS` is `("constitution", "architecture", "adrs")` — the baseline holds no
  requirements — so there is no other home. Putting such a document under the first WorkItem lies about
  ownership; copying it into each is what §10 forbids.
- **It assumes one WorkItem per flow.** It does not:
  `test_two_workitems_complete_independent_runs` drives two full default runs in one repository.
- **It would not deliver the isolation it promises.** F-102 and F-103: another WorkItem's changes reach
  this one's manifest through a repository-wide diff, whatever directory the requirements sit in.

A two-scope variant — root means shared, WorkItem-local means owned, effective set is the union — was
also rejected. Its cardinality is all-or-one: it cannot express *this constraint governs A and B but not
C*.

## 4. Binding, not layout

The ontology the directory layout was being asked to encode — shared versus owned — is not a property of
a document. It is a property of the **relationship** between a document and a WorkItem, and it is
many-to-many. A filesystem path cannot hold a many-to-many relationship; a declaration can.

| Case | Binding |
|---|---|
| A document about one change | Bound by that WorkItem alone. Editing it stales only that WorkItem |
| A constraint governing several WorkItems | Bound by each. Editing it stales exactly those, which is correct dependency tracking |
| A document nobody bound | Governs nothing, and stales nothing. It is a file in a directory |

Nothing is copied, so §10 is satisfied. Sharing is visible because two records name the same path, not
inferred because two WorkItems happen to sit above the same directory.

## 5. The binding is itself governed

Declaration has a failure mode that structure does not: a document can be **forgotten**. Omitting the
regulatory constraint from a binding yields a lower risk classification, and the engine cannot
distinguish a deliberate exclusion from an oversight.

The binding is therefore a recorded, inspectable decision and not a command-line detail:

- it is written by the engine, into the WorkItem's runtime, and never hand-edited (invariant 6);
- `requirements show` reports it, and the orchestrator displays it before the governance proposal;
- the governance **record** carries the binding's digest, so a recorded assessment is tied to the set it
  analysed. The digest is computed by the engine at assess time; the model's proposal does not and cannot
  supply it (§7);
- re-binding is explicit, and re-binding to a **different set** makes the existing assessment stale
  (`governance_stale`, with `rebound: true`).

The last point is narrower than it first appears, and the narrowness is deliberate. `binding_digest`
hashes the sorted list of source paths and nothing else, so:

| What changed | Stales the assessment? | Why |
|---|---|---|
| A bound document's **content** | Yes | The sources digest hashes each file's SHA-256 |
| **Which documents** are bound | Yes, `rebound: true` | The binding digest changes |
| A bound document is deleted or renamed | Yes | Its hash becomes absent, so the sources digest moves |
| The **primary** alone, same set | **No** | The primary is not in the binding digest |
| The `boundAt` timestamp | **No** | Not in the digest either |
| An unbound file appears or changes | **No** | Only bound documents are hashed — this is the point of ADR-012 |

Re-binding the same set with a different primary is therefore silent. That is defensible — the primary
selects the project name and does not change what was analysed — but it means "I re-bound, so the record
must be stale" is not a safe assumption. `governance show` reports the facts; do not infer them.

## 6. No implicit default

Omitting a binding **refuses**. It does not fall back to "everything in the root directory".

That fallback has unstable semantics: a WorkItem bound implicitly to `{a.md}` and re-assessed later, for
an unrelated reason, silently acquires `{a.md, b.md}` from the identical command. Each alternative is
equally bad — reusing the previous set silently excludes newly intended documents; re-expanding silently
includes unrelated ones.

There is no compatibility obligation, so the fail-closed choice is available and is taken.
`requirements bind --all-current` exists for convenience and records an **exact snapshot** of the files
present at that moment, never a live glob.

## 7. Order in the lifecycle

```
workitem create
  → requirements bind --source <path> [--source <path> …]
  → preflight            (checks the binding, not a directory listing)
  → untrusted scan       (over exactly the bound sources)
  → governance proposal  (the model's 4-key input; it does NOT carry the digest)
  → governance assess
  → init                 (project name from the binding's primary source)
```

The proposal a model writes has exactly four top-level keys — `governanceInputVersion`, `quality`,
`classification`, `risk` — and a fifth is refused `governance_input_malformed` rather than ignored. So
the binding digest cannot travel in the proposal even in principle: `governance assess` reads the
binding from the WorkItem's runtime itself and writes `requirements.sources`, `requirements.digest` and
`requirements.bindingDigest` into the record. The tie between an assessment and the set it analysed is
made by the engine, which is what makes it evidence rather than a claim.

`preflight` before this ADR reported `requirements_missing` from a bare listing of the root directory,
which under a binding would be wrong in both directions: passing because some unrelated document exists,
or failing because the root is empty while the bound sources live elsewhere. It reads the binding
instead.

**The project name** comes from the binding's primary, but only as the second link in a chain:
`--project` if given, else the primary document's first `#` heading, else the WorkItem's title, else the
project root's directory name. Naming a primary is what makes the second link deterministic, which is
why `requirements_primary_required` refuses rather than defaulting to the alphabetically first
document (§10).

## 8. Refusals

Exit codes are the engine's contract (`0` success · `1` refused · `2` usage · `3` integrity). The codes
below were read from the running CLI, not from intent.

One reason carries **two** exit codes, because it covers two different failures: `requirements_binding_empty`
is a usage error when the command names no selector at all, and a refusal when `--all-current` is a
well-formed request that the repository cannot satisfy. Reading the reason without the exit code
conflates them.

| Reason | Exit | When |
|---|---|---|
| `requirements_binding_empty` | 2 | A bind names neither `--source` nor `--all-current` |
| `requirements_binding_empty` | 1 | `--all-current` over a `requirements/` that holds no documents |
| `requirements_binding_ambiguous` | 2 | A bind passes both `--source` and `--all-current` |
| `requirements_primary_required` | 2 | More than one document is bound and none was named primary. Exit 2 but **not** early: every source is resolved and validated first, so a bind with two sources one of which is missing refuses `requirements_source_missing` (exit 1), not this |
| `requirements_unbound` | 1 | A consumer needs the binding and none exists |
| `requirements_source_missing` | 1 | A bound path is not a file, at bind time or later |
| `requirements_source_invalid` | 1 | A path is absolute, traverses out, names a directory, resolves through a symlink out of the tree, or uses a spelling that means different files on different platforms (a `:` stream, a trailing dot or space) |
| `requirements_source_duplicate` | 1 | The same file is named twice, including by a Windows case alias |
| `requirements_binding_invalid` | 3 | The binding on disk is not one the engine wrote: it does not parse, declares an unreadable version, carries a non-string or duplicate source, names a primary it does not bind, belongs to another WorkItem, or does not match its own digest. An integrity failure rather than a refusal, because the file is evidence rather than input |
| `governance_stale` | 1 | A bound document changed, was renamed or was deleted after the assessment; or the bound **source set** changed (`rebound` — see the §5 table for what does *not* count); or the record predates any binding. The refusal carries only the two digests; `governance show` is what reports which |

`--all-current` is how a directory becomes an exact file list; a directory named with `--source` is
refused.

**Precedence in `preflight`**, as observed. Two things are true at once and must not be confused:

- **`reason` names one problem** — Spec Kit and its skills first, then `requirements_unbound`, then
  `requirements_source_missing`. That is the headline, and it is what a caller branching on `reason`
  sees.
- **`data.problems` lists them all.** A WorkItem with neither Spec Kit nor a binding refuses
  `speckit_missing` with `problems: ["speckit_missing", "requirements_unbound"]`. So preflight does
  *not* hide the second problem behind the first; a reader who wants the whole picture reads
  `data.problems`, and a presenter should show it rather than making the user fix one thing to learn
  about the next.

**A malformed binding pre-empts all of it.** `requirements_binding_invalid` is an integrity failure
(exit 3) raised when the binding is read, which happens before the precedence above applies: `preflight`
with an unparseable `requirements.json` exits 3 even when Spec Kit is also absent. Integrity failures
are not ranked against ordinary refusals — the engine stops rather than reporting which of several
things is wrong with a record it no longer trusts.

## 9. Consequences

- Every flow gains a mandatory step between `workitem create` and `preflight`. The getting-started guide
  changes order, and its pre-launch inventory no longer includes a required `requirements/` directory
  staged before launch.
- `infer_project_name` stops taking the heading of whichever document sorts first and reads the
  binding's primary source, which is a correctness gain independent of isolation.
- A document in `requirements/` that no WorkItem binds is inert. That is intended: presence in a
  directory is no longer an implicit claim on anything.
- This closes F-101 only. F-102 and F-103 are cross-WorkItem isolation in the *implementation* change
  set and are addressed separately; a requirements binding must not be described as fixing them.

## 10. Amended by its own review

Two decisions changed after the implementation was reviewed independently, and the ADR records the
outcome rather than the first draft:

- **There is no default primary.** Binding more than one document without `--primary` is refused. The
  first draft took the alphabetically first source, which quietly made `00-regulatory.md` speak for a
  project whose product document was `product.md`. The primary names the project; that is a decision,
  and an arbitrary one is not better than asking.
- **A governance record with no `bindingDigest` is stale, not exempt.** Such a record predates the
  binding, so nothing says which documents it was assessed against. Treating a missing digest as
  "nothing to compare" would have let an existing WorkItem advance unbound — the implicit default §6
  refuses — so it is stale until re-assessed, and `governance show` reports that as its own fact
  because the remedy is to bind and re-assess rather than to restore a file.

Containment is rechecked on **every** read, not only at bind time: a symlink bound while it pointed
inside the repository can be retargeted afterwards. An escaping path is `requirements_source_invalid`
wherever it is found, including on the `advance` path, because "this is not where you said it was" is a
different fact from "it changed".
