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

**F-102's fix does not fix this, and must not be described as if it did.** Engine-owned paths are now
excluded; application code cannot be attributed by a repository-wide diff at all.

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


---

## F-102 — fixed

`implementation_exclusions` now excludes every *other* registered WorkItem's tree, plus the registry
file. Both consumers were driven through the real commands in the regression tests; before the fix the
leak was:

```
workitems/index.md
workitems/second-item/.sdle/{state,governance,execution}.json
workitems/second-item/.sdle/audit.md
workitems/second-item/.sdle/evidence/governance-<id>.json
workitems/second-item/workitem.json
```

Two decisions inside the fix are judgements rather than deductions, and each is pinned by a test:

- **Enumerated from the registry, not globbed.** A directory under `workitems/` that no row claims is
  an anomaly `validate` reports, so it stays *visible* in the manifest. Filtering it out would let an
  unregistered runtime be created during an implementation and never reach a reviewer.
- **`workitems/index.md` is excluded.** It changes whenever any WorkItem is created, so leaving it in
  shows every concurrent reviewer a row that is not theirs. The cost, stated plainly: a hand-edited
  registry during implementation no longer surfaces at Gate 7. Its controls are the write fence and
  `validate`, where a registry edit is a governance question rather than an implementation one.

---

## F-103 — proposal for the owner, not a decision taken

`docs/workitems/README.md` says concurrent WorkItems "do not interact". After F-102 that is true of
every engine-owned path and false of application code, which no repository-wide diff can attribute.

This is a user-visible contract change, so it is put rather than taken. Two candidate wordings:

**Option 1 — support concurrency, bound it to isolated checkouts.**

> A repository can carry as many WorkItems as you like. Two WorkItems may sit at any phase at once;
> their records never interact. **While two WorkItems are in the `implement` phase, give each its own
> branch or Git worktree.** The implementation change set is a diff of the working tree against a pinned
> commit, so two implementations in one checkout cannot be told apart, and each would list the other's
> code changes.

**Option 2 — declare same-checkout implementation unsupported.**

> A repository can carry as many WorkItems as you like, concurrently, and their records never interact.
> **Only one WorkItem may be in the `implement` phase in a given checkout at a time.** SDLE does not
> attribute application-code changes to a WorkItem; it measures them from a pinned commit.

Option 1 keeps the capability and tells the user how to get it. Option 2 is a narrower promise that
needs no new practice from the user. Option 1 is the better product if worktrees are an acceptable ask;
Option 2 is more honest if they are not.

A third option — attributing implementation changes to a WorkItem explicitly — is a substantial feature
and is not proposed here.

**Neither is written yet.** Until the owner chooses, the documentation keeps its current wording, which
is now wrong only about application code and which this finding records as wrong.

---

## F-102 — independent review, and what it changed

Reviewed by Codex (`codex exec`, read-only) against the first fix, then one round of discussion. Six
findings, **all accepted**; no disagreement survived the round. Packet and both outputs are beside this
file (`review-f102*.md`).

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | high | Exclusions read only the *current* registry, so deleting a WorkItem's row and directory during an implementation reported every one of its deletions as this WorkItem's work — the same leak in reverse, with the registry change that would explain it hidden by the rule below | **Accepted.** Owning ids are the union of the registry now and at the pinned base |
| 2 | medium | `workitems/index.md` was appended to a list matched with `startswith`, so it also hid `workitems/index.md.backup` | **Accepted.** Exact files and directory prefixes are now separate kinds, matched by equality and by prefix |
| 3 | medium | A rename was filtered on its destination alone, so moving application code *into* an excluded tree erased the fact that it left `src/` | **Accepted**, and shipped here rather than deferred: my change widened the excluded set, so it converts visible evidence into a silent omission. Four-way projection |
| 4 | medium | Registry cells reached git pathspecs unquoted, so a row whose id was `*` became a glob in git while Python compared it literally — the change list and the rendered diff then disagreed | **Accepted.** `:(exclude,literal)`, and a row whose id is not well formed owns no directory |
| 5 | medium | `security-review evidence` derived the exclusions twice, so a registry write between the two gave selection and diff different boundaries | **Accepted.** One frozen `Exclusions` per command |
| 6 | low | The non-vacuity test wrote `src/keep.py`, not a file under the bound WorkItem's tree, so a blanket `workitems/` exclusion would have passed it; the security test never asserted over `stat`/`diff` and its foreign records were untracked | **Accepted.** Both closed |

I proposed deferring finding 3 and was argued out of it, correctly: before the fix the rename was a
noisy-but-present `R` entry, and after it the entry vanished, so shipping without it would have been a
regression I introduced.

**One test of my own was vacuous and the review's own reasoning caught it.** My first test for finding 4
asserted on the manifest, where a glob never bites, because the Python filter compares literally. It
passed on the unfixed engine. Rewritten to assert on the security-review diff, where the glob actually
corrupted the pathspec; it now fails on the parent and passes on the fix.

Every regression test was run against the parent commit to confirm it fails there. Three of the six
round-2 tests do; the other three are non-vacuity and regression guards and are labelled as such rather
than presented as defect demonstrations.
