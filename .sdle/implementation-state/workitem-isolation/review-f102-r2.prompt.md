# F-102 review, round 2

Your review was right on all six. I verified the two I could check directly:

- **Finding 4 confirmed.** `scripts/sdle.py:9712` builds `f":(exclude){prefix.rstrip('/')}"` with no
  pathspec magic, so a registry cell containing `*` becomes a glob in git while Python's `startswith`
  treats it literally. `changes` and `diff` then disagree.
- **Finding 5 confirmed.** `cmd_security_review_evidence` calls `implementation_changes()` (which reads
  the registry) and then `implementation_exclusions()` again at 9712 — two independent snapshots in one
  command.

**Accepted without argument, and being fixed:** 2 (exact file matched as a prefix — `index.md.backup`
disappears), 4 (literal pathspec magic plus ID validation), 5 (one snapshot per command), 6 (both test
gaps — the bound-tree file, and asserting over `stat`/`diff` with a *tracked* foreign record).

I am taking your overall shape: **one immutable, typed exclusion snapshot** — exact files matched by
equality, directory prefixes by prefix, computed once per command, used for both Python filtering and
git pathspecs.

Two questions left, and only two.

## Q1 — Finding 1: is the base-registry union worth its machinery?

Your scenario is real: B's row and directory are deleted before A builds, `read_index()` no longer names
B, and every deletion under `workitems/B/` is reported as A's implementation.

Your fix is the union of the registry at `implementation_base_ref` and the registry now. That means
`git show <base>:workitems/index.md`, parsing a registry that may be structurally different at that
commit, and deciding what to do when it is absent or malformed *at the base* — a new failure mode in a
command whose whole job is evidence.

The alternative I am weighing: **exclude `workitems/` wholesale, then re-include the bound WorkItem's
own tree minus its `.sdle/` runtime and its feature directory.** No registry read at all, so:

- deleted-WorkItem drift cannot reproduce the leak, because nothing depends on a row still existing;
- finding 4 disappears entirely — no registry cell ever reaches a pathspec;
- finding 5 gets easier, because the snapshot has no external input.

The cost is judgement 2: an unregistered stray directory becomes invisible instead of visible.

So: **how much is stray visibility actually worth?** My case for keeping it was that an unregistered
runtime appearing during an implementation should reach a reviewer. But `validate` reports it as
`runtime_state_outside_workitem`, and Gate 7 is not where that question belongs — which is precisely the
argument I used to exclude `index.md`. If I am honest, judgement 2 and judgement 3 point in opposite
directions and I have not reconciled them.

Which do you defend: union-with-base (keeps stray visibility, adds a base read and its failure modes),
or blanket-plus-carve-out (simpler and drift-proof, loses stray visibility to `validate`)? If you still
want the union, tell me what `implementation_exclusions` should do when the registry at the base is
absent or unparseable.

## Q2 — Finding 3: rename reclassification, in this fix or its own?

You are right that a rename into an excluded tree vanishes entirely, and that the two boundary
directions have different semantics. But this predates my change — it is a property of keying `changes`
by destination and filtering once. My change widens the excluded set, so it makes an existing defect
easier to hit; it does not create it.

Your fix ("visible→excluded becomes a deletion of the old path, excluded→visible becomes an addition,
exclude only when both sides are excluded") changes what `status` means for a class of entries, which
touches manifest rendering and the D03 rename tests.

I would rather **record it as its own finding with your scenario and fix it separately**, so the F-102
change stays reviewable as one thing. Argue if you think that is wrong — specifically, is there a
scenario where shipping F-102 *without* the rename fix is worse than not shipping F-102 at all?

## Output

Answer Q1 and Q2 directly. If either answer depends on something in the repository, check it and cite it.
Do not re-list the accepted findings.
