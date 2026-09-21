# Design debate, round 3 of 3

Your proposal changes my recommendation, but not exactly as written.

## What I concede

C’s two-scope model is too weak for genuine many-to-many sharing.

A root requirement applies to every WorkItem; a local requirement applies to one. C cannot naturally represent “this API invariant governs WorkItems A and B, but not C.” Explicit selection can. That is a stronger objection to C than classification difficulty.

You are also right that declaration makes sharing more explicit. Two governance records naming the same source demonstrate an intentional dependency more clearly than merely observing that the file lives at the repository root.

## Where I disagree

### 1. C’s classification is structural, but not permanent or silent

Moving a document from root to a WorkItem directory changes the effective source set:

- The target WorkItem sees a path replacement and becomes stale.
- Every other WorkItem sees the shared source disappear and becomes stale.
- After reassessment, only the target WorkItem retains the dependency.

Moving it back to root stales every WorkItem because they acquire a new shared source.

That is broad, but it is not silent. Assuming freshness compares the effective set correctly, the move itself exposes the semantic change. Git also makes the relocation reviewable.

C’s real defect is its all-or-one cardinality, not permanence.

### 2. An assess-time flag is not a complete selection mechanism

`governance assess` runs after the orchestrator has already read, scanned, and evaluated the requirements. The engine only records sources near the end of assessment ([scripts/sdle.py:5047](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:5047>)). Therefore:

```text
governance assess --requirements ...
```

can bind the resulting evidence to paths, but cannot prove that the proposal was produced from those paths.

The selected set must exist before:

1. Preflight.
2. The untrusted-content scan.
3. The model writes the governance proposal.
4. Governance assessment.
5. Project-name inference.
6. Later discovery and impact-analysis phases.

Otherwise the system has one source set for orchestration and another for freshness.

### 3. “Declare nothing means current root contents” is unsafe

The fallback has unstable semantics. Suppose A’s first assessment omits the flag and snapshots `a.md`. Later `b.md` is added and A is reassessed for an unrelated reason. The identical command now silently changes A’s selection from `{a.md}` to `{a.md, b.md}`.

Alternatives are also problematic:

- Reuse the previous set by default: new intended requirements are silently excluded.
- Re-expand the directory: unrelated additions are silently included.
- Infer from the governance proposal: the proposal is not an authoritative source manifest.

With no compatibility obligation, omission should refuse. Provide an explicit convenience such as `requirements bind --all-current`, but record that as an exact snapshot.

### 4. Declaration has a real fail-open mode

Structure supplies one guarantee selection does not: a repository-wide requirement cannot accidentally be omitted from a WorkItem’s assessment.

With pure selection, a model or user can forget the regulatory document and obtain a lower classification or risk result. The engine cannot distinguish deliberate exclusion from oversight.

That does not defeat selection, but it means source selection is itself a governed scope decision. The selected paths must be shown prominently, recorded, and ideally confirmed by the user. Hiding them among command-line arguments is not enough.

## Is selection cheaper than C?

No. It is probably more expensive, although it expresses the domain better.

A correct implementation needs a durable WorkItem source binding, not merely another `argparse` option. For example:

```text
requirements bind --source requirements/feature-a.md \
                  --source requirements/regulatory.md
requirements show
governance assess --input governance-input.json
```

The binding should record canonical repository-relative paths, a designated primary document if heading inference remains, and a digest. `requirements show` should be the one source consumed by preflight, scanning, assessment, initialization, discovery, and impact analysis.

Required behavior:

- A nonexistent source is refused when binding.
- An empty binding is refused.
- A directory is refused; an explicit `--all-current` operation may expand it into exact files.
- Absolute paths, traversal, repository escapes, and symlink/junction escapes are refused.
- Case aliases are normalized on Windows before duplicate detection.
- A later missing or renamed file makes governance stale, naming the missing path.
- A malformed binding or malformed recorded path is an integrity failure.
- Rebinding is explicit and immediately makes the existing assessment stale.
- A governance proposal carries the binding digest it analyzed, closing the read-to-record race.
- `infer_project_name` reads the binding’s primary source, not an alphabetically accidental file.

The governance record already has exact source entries, but current freshness ignores those paths and re-enumerates the entire root ([scripts/sdle.py:4890](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:4890>)). That must change.

## Does selection break preflight?

Yes, as proposed.

Preflight currently checks only whether root `requirements/` contains something ([scripts/sdle.py:9741](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9741>)), and startup runs preflight before governance assessment ([docs/GETTING-STARTED.md:363](</D:/Learning/AI/sdle-git-repo/sdle-latest/docs/GETTING-STARTED.md:363>)).

An assess-time selection could therefore produce both false results:

- Preflight passes because an unrelated root document exists, even though the selected source is missing.
- Preflight fails because root `requirements/` is empty, even though valid selected sources exist elsewhere.

The correct lifecycle is:

```text
create WorkItem
→ bind requirement sources
→ preflight the binding
→ scan exactly those sources
→ produce proposal against that binding digest
→ assess
→ initialize
```

`cmd_init` must use the same binding; today it independently checks the root directory and independently infers a heading from it ([scripts/sdle.py:1572](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:1572>), [scripts/sdle.py:1595](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:1595>)).

## The Gate 7 defect and work order

I agree with your order, with one qualification.

First fix the live isolation defect. Other WorkItems’ engine runtime is not implementation and must never enter this WorkItem’s manifest or security evidence. The current exclusion includes only the bound runtime ([scripts/sdle.py:9374](</D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9374>)) even though the repository promises concurrent WorkItems on the same branch that do not interact ([docs/workitems/README.md:17](</D:/Learning/AI/sdle-git-repo/sdle-latest/docs/workitems/README.md:17>)).

But excluding every `.sdle/` runtime is containment, not complete implementation attribution. If A and B modify ordinary source code after A’s pinned base, Git’s repository-wide working-tree diff cannot determine which WorkItem produced each change. The architecture must choose one of these truths:

- WorkItems may implement concurrently only on isolated branches/worktrees.
- Implementation changes are explicitly attributed to a WorkItem.
- Same-checkout concurrency is unsupported during implementation.

A path-prefix patch must not be described as full WorkItem isolation.

The order I would use is:

1. Add the failing cross-WorkItem manifest and security-evidence tests.
2. Exclude all engine-owned runtime/configuration changes from both consumers using one segment-aware classifier.
3. Settle general implementation attribution or narrow the concurrency promise.
4. Implement durable requirements binding.
5. Replay setup and run the full verification matrix.

This order also prevents the requirements change from being designed around an implementation filter already known to be false.

## Recommendation

Choose explicit source selection, but reject both the assess-only flag and the implicit whole-root fallback.

Make the selected source set a durable, engine-written WorkItem binding established before preflight. Require an explicit first binding; offer `--all-current` only as an explicit snapshot operation. Every consumer must read that same binding, and the governance proposal must name its digest.

I will defend that over C because it represents one-to-one, one-to-many, and many-to-many dependencies without copying content or pretending that every shared constraint governs every WorkItem. C remains simpler and safer against omission, but its all-or-one scope model is not expressive enough for the cases this repository already claims to support.