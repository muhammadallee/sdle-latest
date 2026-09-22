## Q1 — Use the base/current union

Stray visibility is worth preserving. The two judgements reconcile through ownership:

- `workitems/index.md` is a known engine-owned file.
- A directory registered at either endpoint has an established WorkItem owner.
- An unregistered directory has no established owner, so the evidence selector should not presume it is bookkeeping.

`validate` is not a substitute. It is a diagnostic invoked when resolution behaves strangely, not a prerequisite for implementation or Gate 7 ([SKILL.md:313](/D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/SKILL.md:313)); the implementation sequence goes directly from manifest construction to Gate 7 without validation ([phase-execution.md:190](/D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/modules/phase-execution.md:190)). Moreover, a base-existing stray that is deleted during implementation leaves nothing for current-state validation to diagnose. Blanket exclusion would silently hide that deletion.

That matches the repository’s existing stated contract: exclusions are deliberately narrow, bound-tree implementation remains visible, and unregistered anomalies remain evidence ([sdle.py:9374](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9374), [test_units_manifest_changes.py:283](/D:/Learning/AI/sdle-git-repo/sdle-latest/tests/test_units_manifest_changes.py:283)).

For the base registry:

- **Absent at the base:** treat it as empty. That mirrors `read_index`’s existing absent-file contract ([sdle.py:2139](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:2139)). It can legitimately be absent because preflight pins `HEAD` while ignoring all `workitems/` dirty changes ([sdle.py:9212](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9212), [sdle.py:9230](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9230)).
- **Structurally malformed or unreadable at the base:** fail closed with a dedicated integrity error naming the base SHA and registry path. Do not silently use only the current registry or fall back to blanket exclusion. Both alternatives produce plausible but untrustworthy evidence, contrary to the selector’s existing refusal policy ([sdle.py:9445](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9445)).
- **Structurally valid row with an invalid ID:** do not grant that row ownership of a directory—omit it from the exclusion IDs, leaving its paths visible. `workitem_id_wellformed` is already the canonical predicate ([sdle.py:2093](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:2093)).

So: parse the base blob with the same pure table parser, union its valid IDs with current valid IDs, remove the bound ID, and freeze that result for the command.

## Q2 — Fix rename classification in this shipment

Yes, there is a concrete regression: before F-102, `src/shared.py → workitems/B/shared.py` remained an `R` entry because B was not excluded. F-102 adds B’s prefix, while the selector stores the rename under its destination and filters only that key ([sdle.py:9423](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9423), [sdle.py:9480](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9480), [sdle.py:9517](/D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9517)). The patch therefore converts noisy-but-present evidence into a silent omission of application-code deletion.

The underlying destination-only mechanism predates F-102, but widening the excluded set activates it for the ordinary cross-WorkItem case. That makes it part of completing F-102, not merely adjacent cleanup.

Use the four-way projection:

| Old path | New path | Evidence |
|---|---|---|
| visible | visible | `R old → new` |
| visible | excluded | `D old` |
| excluded | visible | `A new` |
| excluded | excluded | omit |

Apply the same projection to `changes`, `stat`, and `diff`; the security-review contract explicitly promises that the diff covers exactly the Gate 7 selection ([security-review.md:17](/D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/modules/security-review.md:17)). It may be a preparatory commit for reviewability, but it should be in the same shipment.