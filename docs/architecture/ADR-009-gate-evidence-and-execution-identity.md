# ADR-009 — Gate Evidence, Change Selection and Execution Identity

**Status:** Accepted
**Date:** 2026-09
**Extends:** ADR-001 (the deterministic core), ADR-003 (governance and artifact review), ADR-008 (V1 convergence).
**Diverges from:** the transition contract's execution-identity format (§"Execution identity"), deliberately — see §5.
**Context:** SDLE-DEFECT-STABILIZATION-01, defects D01–D06. The execution record is
[`docs/verification/defect-stabilization-01.md`](../verification/defect-stabilization-01.md).

---

## 1. The decision

Every gate decision is about **evidence the engine can check**, and a decision
whose evidence cannot be checked is refused, never waved through with a null.
Five defects had the same shape: a precondition existed in name, and the code
that should have enforced it accepted its absence.

| Defect | What was accepted | What is refused now |
|---|---|---|
| D01 | An artifact path that could not be resolved, found or read — the gate approved with `sha: null` | `artifact_unresolved`, `feature_ambiguous`, `artifact_missing`, `artifact_unreadable` |
| D02 | A Gate 7 manifest carrying the right headings, whatever its tests did | `tests_not_passed`, `test_evidence_missing`, `test_evidence_stale`, `test_evidence_malformed` |
| D03 | A change set measured from the current `HEAD` instead of the pinned base | `implementation_base_missing`, `implementation_base_invalid` |
| D04 | Two executions in one second sharing one id, one evidence file and one ledger marker | `execution_id_collision` (exit 3), after a bounded retry |
| D05 | Instructions the runtime rejects | Nothing new is refused. The instructions now match the runtime, and a test parses them |

---

## 2. D01 — a gate approves specific content or nothing

`required_gate_artifact` is the one precondition behind `gate approve`, drift
re-approval and `gate omit`. It resolves the ARTIFACT_OWNERSHIP template, finds
the file and hashes it, or refuses. The refusal names the binding that is
missing and the command that records it. It is a pure reader placed before every
write, so a refusal leaves the phase, the approvals and the ledger
byte-identical.

The one artifact-free gate remains a template of `(none)`. A flow that omits
the phase producing an artifact never reaches that artifact's gate, so no flow
is asked for an artifact it cannot have.

**Rejected:** refusing in `resolve_artifact_path` itself. Its callers include
read-only reporters (`gate show`, `artifact path`, drift detection) that must
be able to say "not resolved yet" without refusing.

## 3. D02 — the evidence contract at Gate 7

`manifest build` writes a structured record, `evidence/implementation-<execution-id>.json`,
holding the runner, command, exit code, status and output tail, the manifest's
own SHA-256, the pinned base and the WorkItem. The manifest names the record on
an `Evidence:` line. Gate 7 reads it back, binds it to **this manifest's
bytes**, **this base** and **this WorkItem**, and requires a run that actually
exited 0.

- **There is no exception path**, because none existed in the code to extend,
  and inventing one was out of scope by decision. `--skip-tests` still builds a
  manifest; that manifest can never carry Gate 7.
- **`--test-command` is not a waiver.** It lets a project whose runner is not
  auto-detected (.NET, Go, Make, a runner that needs arguments) supply its real
  command. The engine runs it without a shell and records its exit code, as it
  would for a detected runner.
- **A PASS review does not override the result.** TP-011's review judges the
  manifest as a document; the evidence judges the tests. Editing the result
  line and re-reviewing is caught as `test_evidence_stale`, because the
  record's SHA no longer matches.
- **Compatibility.** A manifest built before this ADR has no `Evidence:` line.
  It is refused `test_evidence_missing` with an explicit statement that the
  format cannot establish success, and it is never guessed at from its prose.

**Rejected:** a state field for the test result. It would have needed a schema
version, a migration row and a writer, for a fact that belongs to one build of
one manifest. A file named by an execution id carries it with no schema
movement.

## 4. D03 — one change set, measured from the pinned base

`implementation_changes` diffs `implementation_base_ref` against the working
tree with `-z`, which covers committed, staged and unstaged work in one
comparison, and adds untracked files. It marks renames, deletions and binary
files, and filters through `implementation_exclusions`, the single list of
engine bookkeeping. The manifest and the security-review evidence both read it.
A missing or invalid base is refused, because a change set measured from
anywhere else is wrong but plausible.

While reproducing D03, one more defect was found. `git()` stripped leading
whitespace from its whole output, so the first `git status --short` line lost
the leading space of ` M path`, and `line[3:]` cut a character off the path.
The dirty-tree guard then reported a false `dirty_tree` for an SDLE-owned file
that sorted first. `git()` now trims trailing whitespace only.

## 5. D04 — collision-resistant execution identity

The id becomes `<prefix>-<UTC second>-<8 hex>`. This **diverges from the
transition contract**, which specified `<prefix>-<UTC datetime>` and called it
lightweight metadata. ADR-008 recorded that shared labels were harmless.
They were not: the id is also a key, naming every evidence file and
de-duplicating the governance ledger entry. The divergence is deliberate and is
recorded here, not in the ADR-008 text, which is immutable.

Each evidence writer claims its file with an exclusive create
(`reserve_evidence`) before writing. It retries with a fresh id up to three
times, then refuses exit 3 having recorded nothing. No evidence file is ever
replaced. Historical ids without the suffix are read unchanged, because nothing
parses an id; every id is compared whole.

**Rejected:** a hard link from a temporary file. It is atomic, but not every
filesystem supports hard links, and the claim-then-fill shape needs only
`open(path, "x")`. A crash between claim and fill leaves an empty file, which
every reader refuses as malformed. That is the fail-safe direction.

## 6. How the change was verified without weakening the pins

The repository freezes its behavioural contract: three integration files and
nine transcripts were byte-pinned to historical commits, and `sdle.py`'s write
primitives are counted. Two frozen tests asserted the defects themselves, so a
fix could not leave the pins untouched. The maintainer chose **declared
deltas**, as T11 did:

- The frozen test files are compared unit by unit. Each permitted edit,
  addition and removal is written out in `tests/conftest.py`, and anything
  undeclared still fails.
- New write-primitive call sites are declared per needle, and the one
  exclusive-create writer is pinned by name.
- The nine GREENFIELD transcripts had to be rewritten to match the engine, so
  their byte pins were **released** and replaced by
  `tests/test_dry_run_contracts.py`. That test recomputes every fraction, gate
  number, label and refusal in all sixteen transcripts from the engine.

## 7. Consequences

- A project with no auto-detected test runner can no longer pass Gate 7 without
  saying how its tests are run. That is the intended cost.
- Every flow is affected, because `gate_implement`, `gate_spec` and
  `gate_security` are in every flow.
- `security-review evidence` no longer falls back to `HEAD~1`, and refuses
  instead when no base is pinned.
- No state field, migration row or version bump: the schema pins are untouched.
