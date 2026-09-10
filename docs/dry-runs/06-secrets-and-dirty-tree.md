# Dry Run 06 — Dirty-Tree Guard & Secrets Scan at Gate 7

| | |
|---|---|
| **Scenario ID** | DR-06 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The implementation-phase guards. Uncommitted user changes halt Phase 15 until confirmed. The manifest measures every change from the pinned base, a hardcoded credential is flagged in front of the reviewer at Gate 7, and Gate 7 needs a test run that passed. |
| **Defect IDs** | D02, D03 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `implement` (`15/18`). Gates 1–6 approved. `specKit.featureDirectory` is bound. The user has an uncommitted edit to tracked `notes/ideas.md`. The project's tests run under pytest |
| **Guardrails exercised** | The dirty-tree guard and `confirm implement`, the implementation base pin, the change set from the base, the secrets scan, Gate 7 test evidence, and remediation at Gate 7 |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> and execution ids are illustrative. The engine behaviour it depends on is
> asserted by the tests under *Executable coverage*. Their results — **PASS**,
> **FAIL**, **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01 to Gate 6's approval. Commit, then edit `notes/ideas.md` without
committing.

---

## Transcript

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ Uncommitted changes detected in the working tree:

   M notes/ideas.md

These may be mixed into or overwritten by the implementation, and will appear in the
implementation manifest as if the implementation produced them.

Commit or stash them first, or say "confirm implement" to proceed anyway (logged).
```

*(Engine: `sdle.sh implement preflight` pinned `implementation_base_ref` to
HEAD, filtered SDLE's own paths (`.workflow/`, `.sdle/`, `workitems/`,
`.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`,
`requirements/`), then refused `dirty_tree`. The first status line is read
whole: its leading space is data, not whitespace.)*

---

**User:** `confirm implement`

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=in_progress progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [IN PROGRESS]

Proceeding despite uncommitted changes (logged).

Implementing against tasks.md, informed by the approved design documents...
Implementation complete, committed as two commits. Building the implementation manifest...

⚠️ Secrets scan flagged 1 potential secret in the changed files (see manifest below).
Test evidence: pytest — 28 passed (exit 0).

---
✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval

# Implementation Manifest
Generated: 2026-09-10T14:20:44Z
Evidence: workitems/todo-api/.sdle/evidence/implementation-muh-20260910T142044Z-12db09f4.json
Phase: implement (15/18)

## Changed/Added Files
A design/app/app-design.md
A design/db/db-design.md
M notes/ideas.md
A src/app.py
A src/config.py
A src/models/todo.py
A src/routes/todos.py
A tests/test_todos.py

## Potential Secrets Detected
src/config.py:12 — secret API key — sk-p ****(masked)

## Test Evidence
Runner: pytest
Command: python -m pytest -q
Result: passed (exit 0)

## Summary
Implemented the Todo REST API per tasks.md.

Artifact path: workitems/todo-api/.sdle/implementation-manifest.md
Fingerprint: 7a2e90cf…b14d
---
```

*(Engine: `sdle.sh implement preflight --bypass`, then generation, then
`sdle.sh manifest build --summary "…"`. The implementation was **committed**
during the phase, and it is still listed and scanned, because the change set is
the diff from `implementation_base_ref`, not from the current HEAD. Before D03,
both commits would have been absent from this list and from the scan. The
pre-existing `notes/ideas.md` edit shows as `M`, which is why the guard asked
first.)*

---

**User:** `reject with comments: Move the API key out of src/config.py into an environment variable before I approve this.`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_implement status=rejected progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [REJECTED — REMEDIATION NEEDED]

Understood — I've recorded your feedback. Say "continue" to re-run the Implement step
with this feedback applied.
```

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_implement status=in_progress progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [IN PROGRESS]

Remediation attempt 1/3 for implement. Implementation updated. Rebuilding the manifest...
Secrets scan: no high-risk patterns found in the changed files.
Test evidence: pytest — 28 passed (exit 0).

---
✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval
[... regenerated manifest: `None detected.`, a new Evidence: line naming a new record ...]
---
```

*(The rebuilt manifest names a **new** evidence record under a fresh execution
id. The old record stays on disk, unchanged. Gate 7 accepts only the record
bound to the current manifest's SHA-256.)*

**User:** `approve`

---

## Artifacts, state and audit

- `dirty_tree_guard` and then `dirty_tree_bypassed` audit entries.
- `implementation_base_ref` was pinned by the first preflight and not moved.
- Each `manifest build` wrote `evidence/implementation-<execution-id>.json`
  holding the runner, command, exit code, status, the manifest's SHA-256, the
  base and the WorkItem.
- Secret findings are masked to four characters in the manifest and in the
  `secrets_flagged` audit entry. The secret is never reproduced.
- The scan is a regex tripwire before human review, not a replacement for
  `trufflehog` or `semgrep`, which the Phase 17 review recommends.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Gate 7 on a manifest built with `--skip-tests` | Refused `tests_not_passed` | Approvals unchanged |
| Gate 7 on a hand-written manifest with the right headings | Refused `test_evidence_missing` | Unchanged |
| Gate 7 on a manifest with no `## Test Evidence` section | Refused `manifest_incomplete` | Unchanged |
| Security-review evidence with no pinned base | Refused `implementation_base_missing` | Unchanged, and no fallback range |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| A dirty tree halts implement | `tests/test_integration_06_to_09.py::test_06_dirty_tree_halts_implement` |
| SDLE-owned paths are not dirt | `tests/test_integration_06_to_09.py::test_06_sdle_owned_paths_are_not_dirt` |
| The first status entry is read whole | `tests/test_units_manifest_changes.py::test_d03_the_dirty_tree_guard_reads_the_first_status_entry_whole` |
| Bypass proceeds and is logged | `tests/test_integration_06_to_09.py::test_06_bypass_proceeds_and_is_logged` |
| Preflight pins the base | `tests/test_integration_06_to_09.py::test_06_preflight_pins_the_implementation_base_ref` |
| A committed change after the base is listed and scanned | `tests/test_units_manifest_changes.py::test_d03_a_change_committed_after_the_base_is_listed_and_scanned` |
| A hardcoded key is flagged and masked | `tests/test_integration_06_to_09.py::test_06_manifest_flags_a_hardcoded_key_masked` |
| A built manifest with a passing run is accepted | `tests/test_integration_06_to_09.py::test_06_gate_seven_accepts_a_built_manifest` |
| A skipped run is refused | `tests/test_integration_06_to_09.py::test_06_gate_seven_refuses_a_manifest_whose_tests_were_skipped` |
| A section-less manifest is refused | `tests/test_integration_06_to_09.py::test_06_gate_seven_refuses_a_manifest_without_scan_or_tests` |
| Review evidence refuses with no base | `tests/test_integration_06_to_09.py::test_06_security_review_refuses_when_no_ref_pinned` |
