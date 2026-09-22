## Q1 — Treat it as stale; do not bump the version

A missing `bindingDigest` must make freshness false. If there is no current binding, refuse `requirements_unbound`; after binding, require reassessment.

A version bump does not solve the compatibility path cleanly:

- If version 3 becomes unsupported, reassessment itself is blocked because `governance assess` reads the superseded record before replacing it at [scripts/sdle.py:5335](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:5335).
- If version 3 remains readable, freshness still needs explicit missing-`bindingDigest` handling, so version 4 adds no enforcement.

ADR-012 explicitly chooses fail-closed with no compatibility obligation at [ADR-012:79](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:79). Implement `recorded_binding is None` as stale, ideally exposing that fact separately in freshness diagnostics rather than calling it a digest mismatch.

## Q2 — Refuse `requirements_source_invalid`, and let it propagate

A retargeted symlink should refuse immediately as `requirements_source_invalid`, including during `advance`. Do not translate it into `fresh: false` or `governance_stale`.

ADR-012 assigns an escaping symlink to `requirements_source_invalid` at [ADR-012:115](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:115), while `governance_stale` is reserved for changed, renamed, or deleted documents at [ADR-012:117](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:117).

Therefore the authoritative reader should:

- Validate syntax and containment on every read, raising on escape.
- Permit a contained-but-missing path to reach consumers that need to report deletion as stale.
- Use strict existence checking for assessment and preflight.
- Let the containment exception propagate through `governance_freshness`; only a legitimate freshness mismatch should reach the generic `governance_stale` mapping at [scripts/sdle.py:7266](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:7266).

That gives the advance path the integrity-flavoured refusal you proposed.

## Q3 — Require `--primary` when more than one source is bound

The inference-only fix does not remove the arbitrary-primary defect.

Concrete remaining case:

```text
requirements/00-regulatory.md  → # PCI DSS
requirements/product.md        → # Todo API
requirements bind --all-current
```

The current default makes the alphabetically first source primary at [scripts/sdle.py:8600](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:8600). Primary-only inference therefore still produces “PCI DSS.” It no longer falls through to a secondary, but the wrong document has already been designated primary.

`requirements show` makes that choice visible; it does not make the engine-invented choice correct. ADR-012 gives primary semantic weight—project naming comes from it at [ADR-012:101](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:101).

So:

- One source: infer it as primary.
- Multiple sources, including `--all-current`: require `--primary`.
- `infer_project_name`: inspect only that primary, then fall back to WorkItem title/root.

## Q4 — Discovery reads bound requirements, then the whole repository

There is no exception for discovery.

ADR-012 explicitly names discovery and impact analysis as consumers of the one binding at [ADR-012:13](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:13), and requires the untrusted scan over exactly the bound sources at [ADR-012:94](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:94).

ADR-005’s repository-wide scope means discovery examines the entire repository as its subject. It does not turn every file under `requirements/` into an input. The correct composition is:

```text
bound requirement documents
        +
the repository as it stands
```

Accordingly, replace the directory-wide instructions at [phase-execution.md:50](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/modules/phase-execution.md:50) and [phase-execution.md:63](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/modules/phase-execution.md:63). Each phase should obtain the current list from `requirements show`, scan/read only those requirement paths, and then perform its repository or code-impact examination normally.