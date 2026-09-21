# WorkItem isolation and requirements binding — findings

Opened 2026-09-21, off `main` at `cb9a183` (the merge of the repository stabilization iteration).
Branch `fix/workitem-isolation-and-requirements`.

These findings came out of a question from the owner — *"shouldn't the requirements be in the WorkItem
folder?"* — and a two-round design debate with Codex (`codex exec`, read-only). Both debate transcripts
are recorded beside this file.

Severity uses the previous iteration's scale. Every CONFIRMED finding below was reproduced by running
code, not by reading it.

---

## F-101 — one WorkItem's requirements document freezes another

**Severity:** medium. **Status:** CONFIRMED, open. **Fixed by:** ADR-012.

`requirements_sources` (`scripts/sdle.py`) globs `project_root / "requirements"` and hashes the whole
set into one digest, stored per WorkItem in `governance.json`. `governance_freshness` re-globs the same
directory and compares. Nothing records *which* documents a given WorkItem's assessment was about.

**Reproduction** (test harness, `git_project` fixture):

```
WorkItem A assessed against requirements/todo-api.md   digest 8d4a75d5…
→ add requirements/second-workitem.md   (a document for a different WorkItem)
→ A's next `advance`:  exit 1  governance_stale
```

A document that WorkItem A was never assessed against, and has no relationship to, stops A advancing.

**Why it matters.** ADR-008 carries a family of isolation guarantees, each with a test —
`test_two_workitems_complete_independent_runs`, `test_a_lock_on_one_workitem_never_blocks_another`,
`test_manifest_build_under_one_workitem_leaves_the_other_alone`. Governance freshness is not a member of
that family, and it should be.

**Not a defect in the digest.** The record already stores the exact source set with per-file SHAs. The
comparison throws it away and re-globs. The record is right; the comparison is wrong.

---

## F-102 — another WorkItem's runtime enters this WorkItem's Gate 7 manifest and security evidence

**Severity:** high. **Status:** CONFIRMED, open. **Found by:** Codex, round 1 of the debate.

`implementation_exclusions` returns only the *bound* WorkItem's runtime:

```
implementation_exclusions(paths, state)
→ ['workitems/fixture-workitem/.sdle/', '.sdle/', '.specify/']
```

`implementation_changes` diffs the whole working tree from the pinned base and filters through that
list. WorkItem records are **versioned by design**, so another WorkItem's `state.json`, `audit.md`,
`execution.json`, evidence files and manifests are tracked, changed by ordinary use, and *not* excluded.

**Consequence.** While WorkItem A is implementing, any advance, approval or artifact record on WorkItem B
lands inside A's Gate 7 implementation manifest and A's security-review diff. A reviewer approving A's
gate is shown another WorkItem's governed record as though it were A's implementation, and the secrets
scan runs over it.

This needs no layout change to hit. It is live on `main` today.

**Deliberate design being corrected, not overturned.** `implementation_exclusions` is narrow *on
purpose* — it is not `SDLE_OWNED_PREFIXES`, because that would drop `requirements/` and `design/` edits
from the manifest, which are genuinely part of an implementation. The list is right to be narrow; it is
simply missing the other-WorkItem case.

---

## F-103 — the concurrency promise is not backed by attribution

**Severity:** medium. **Status:** CONFIRMED (documentation overclaims), open. **Raised by:** Codex,
round 2.

`docs/workitems/README.md` states:

> A repository can carry as many WorkItems as you like, concurrently, on the same branch or on different
> ones, and they do not interact.

Fixing F-102 makes that true for *engine-owned* paths. It cannot make it true for ordinary source code.
`implementation_changes` measures a repository-wide working-tree diff from a pinned base; if WorkItems A
and B both edit application code after A's base, git cannot attribute those edits to either. A's manifest
will contain B's code changes.

**This is an architectural choice, not a bug to patch.** One of the following has to be true, and the
documentation must say which:

1. Concurrent implementation is supported only on separate branches or worktrees.
2. Implementation changes are explicitly attributed to a WorkItem.
3. Same-checkout concurrency is unsupported during the `implement` phase.

Option 2 is a large change. **Disposition for this iteration: narrow the promise (option 1/3) and record
the choice**, rather than claim an isolation that the engine does not compute. A path-prefix fix must not
be described as full WorkItem isolation.

---

## Decision record

The debate considered four shapes for F-101:

| | Shape | Outcome |
|---|---|---|
| A | Move `requirements/` to `workitems/<id>/requirements/` | **Rejected.** Leaves genuinely repository-wide requirements homeless: `BASELINE_REFERENCE_KINDS` is `("constitution", "architecture", "adrs")`, so the baseline holds no requirements, and §10 forbids copying shared artifacts into every WorkItem. Also rests on "GREENFIELD implies one WorkItem", which `test_two_workitems_complete_independent_runs` disproves |
| B | Compare only the recorded paths | **Insufficient alone.** Fixes the temporal case above, but two unrelated documents already present when both WorkItems are assessed stay coupled, because assessment still selects the whole directory |
| C | Two scopes, root shared and WorkItem-local, union | **Rejected.** All-or-one cardinality: it cannot express "this constraint governs A and B but not C", which is a case the repository already claims to support |
| **D** | **Explicit source binding** | **Adopted.** See ADR-012 |

Both parties changed position during the debate. The full exchange, including what each got wrong, is in
`debate-r1.out.md` and `debate-r2.out.md` beside this file.
