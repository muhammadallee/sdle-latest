# Dry Run 14 — Gate Evidence Refusals (Missing Artifacts, Unsuccessful Verification) and Recovery

| | |
|---|---|
| **Scenario ID** | DR-14 |
| **Flow** | `GREENFIELD` |
| **Purpose** | Every way a gate decision is now refused for lack of evidence: an artifact that cannot be resolved, found or read (D01), and verification that did not run, did not pass, or does not belong to the manifest (D02). Each refusal is followed by the valid recovery. |
| **Defect IDs** | D01, D02 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated. Refusal texts are the engine's real output, with the WorkItem id adapted |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, taken to three positions in turn: `gate_spec` with `feature resolve` not yet run, `gate_implement`, and `gate_security` before `security-review begin`. LOW risk |
| **Guardrails exercised** | `required_gate_artifact` (`artifact_unresolved`, `feature_ambiguous`, `artifact_missing`, `artifact_unreadable`) and Gate 7's evidence precondition (`tests_not_passed`, `test_evidence_missing`, `test_evidence_stale`, `test_evidence_malformed`). Every refusal leaves the phase, the approvals and the ledger unchanged |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**,
> but each `Refused:` block is the engine's real message, captured by driving
> the CLI through the suite's fixtures (WorkItem id changed from
> `fixture-workitem` to `todo-api`; SHAs and execution ids are real but vary
> per run). The engine behaviour is asserted by the tests under *Executable
> coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are
> recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01, stopping at each position named above. To reproduce the
ambiguity, create a second directory under `workitems/todo-api/specs/`. To
reproduce the unreadable case, remove read permission from the artifact
(POSIX `chmod 000`; the suite simulates it portably by making `sha256_file`
raise `PermissionError`).

---

## Transcript

### Part 1 — D01: the specification gate with no feature binding

*(The spec was generated, but `feature resolve` never ran, so
`specKit.featureDirectory` is null.)*

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [AWAITING APPROVAL]

Refused: artifact_unresolved

Cannot approve gate_spec: its artifact ({speckit_feature_directory}/spec.md) cannot be
resolved because speckit_feature_directory is not recorded. A gate decision is about
specific content, and there is none to fingerprint. To recover, run `feature resolve` so
this WorkItem's feature directory is recorded, then try again.
```

*(Before D01, this exact command answered exit 0 with `sha: null`, and the
workflow moved on to `plan_draft`.)*

With a second candidate directory present, the same approval names the
ambiguity instead:

```
Refused: feature_ambiguous

Cannot approve gate_spec: no feature directory is recorded for 'todo-api', and 2
candidates exist under workitems/todo-api/specs/: 001-todo-api, 002-other. SDLE will not
choose between them. Move the one this WorkItem owns into workitems/todo-api/specs/ and
run `feature resolve`.
```

**Recovery:** the user removes the stray directory. `sdle.sh feature resolve`
binds `workitems/todo-api/specs/001-todo-api`, the spec is reviewed, and
`sdle.sh gate approve --gate gate_spec` succeeds with a real fingerprint.

---

### Part 2 — D02: Gate 7 without a passing run

**Skipped tests.** The manifest was built with `--skip-tests`, then given a PASS review.

```
<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [AWAITING APPROVAL]

Refused: tests_not_passed

Cannot approve gate_implement: the recorded verification result is 'skipped by caller'.
Gate 7 needs a test run that actually ran and passed, and there is no exception path: a
PASS review of the manifest does not change the result it reports. Fix the failures, or —
if the runner was not detected or not installed — supply the project's real test command
with `manifest build --test-command "<command>"`, then rebuild.
```

**A failed run with a PASS review.** The same refusal, now reporting
`'FAILED' (exit 1)`. The review judged the manifest's presentation; the
evidence judges the tests.

**The result line edited by hand.** Someone changes `FAILED` to `passed` in the
manifest and re-reviews it:

```
Refused: test_evidence_stale

Cannot approve gate_implement: workitems/todo-api/.sdle/evidence/implementation-sdl-20260910T195446Z-12db09f4.json
does not belong to the manifest being approved (manifestSha256 is '2ae6a3de…838b',
expected 'd1134cd7…a50d'). A result for other content, another implementation base or
another WorkItem proves nothing about this one. Rebuild it with `manifest build`, adding
`--test-command "<command>"` when the project's test runner is not auto-detected.
```

**A hand-written manifest with every heading.** This is the shape the old
check accepted:

```
Refused: test_evidence_missing

Cannot approve gate_implement: workitems/todo-api/.sdle/implementation-manifest.md names
no verification evidence. A manifest in this form — written by hand, or built before SDLE
recorded evidence — cannot establish that the tests ran, let alone passed. Rebuild it with
`manifest build`, adding `--test-command "<command>"` when the project's test runner is
not auto-detected.
```

**Recovery:** the failing test is fixed, and the manifest is rebuilt.

```
# Implementation Manifest
Generated: 2026-09-10T19:54:49Z
Evidence: workitems/todo-api/.sdle/evidence/implementation-sdl-20260910T195449Z-706077af.json
Phase: implement (16/18)
[...]
## Test Evidence
Runner: custom command
Command: python -c "raise SystemExit(0)"
Result: passed (exit 0)
```

*(This project's runner is not auto-detected, so the real test command was
supplied with `sdle.sh manifest build --test-command "<command>"`. The evidence
record carries `kind: implementation`, the manifest's SHA-256, the pinned
`baseRef`, the WorkItem and `tests: {status: passed, exit_code: 0}`. After a
fresh review, `sdle.sh gate approve --gate gate_implement` moves to
`security_review` at `17/18`.)*

---

### Part 3 — D01: the security gate before the review was named

*(Standing at `gate_security` without `security-review begin`, so
`security_review_artifact` is null.)*

```
<!-- SDLE_STATE phase=gate_security status=awaiting_approval progress=18/18 -->
📋 SDLE Status: Phase 18/18 — Gate 8: Security Review Approval [AWAITING APPROVAL]

Refused: artifact_unresolved

Cannot approve gate_security: its artifact ({security_review_artifact}) cannot be resolved
because security_review_artifact is not recorded. A gate decision is about specific
content, and there is none to fingerprint. To recover, run `security-review begin`, which
names the review file, and write the review there, then try again.
```

*(Before D01 this approval completed the workflow, including the completion
summary and the repository baseline, with `sha: null`, in every flow.)*

**Recovery:** `sdle.sh security-review begin` names
`reviews/security-review-<stamp>.md`. The review is written, recorded and
reviewed, and Gate 8 approves.

---

## Artifacts, state and audit

- Every refusal above is raised by a pure reader before the first write:
  `state.json`, `approvals`, `artifact_shas` and `audit.md` are byte-identical
  before and after.
- Each `manifest build` writes a new `evidence/implementation-<execution-id>.json`.
  Old records stay, and only the record bound to the current manifest's bytes
  can carry Gate 7.

## Negative cases

| Refusal | Cause | Recovery |
|---|---|---|
| `artifact_unresolved` | A binding the artifact path needs is unset | `feature resolve` / `security-review begin` |
| `feature_ambiguous` | Several candidate feature directories | Move the owned one into the WorkItem, `feature resolve` |
| `artifact_missing` | The path resolves, no file | Regenerate or restore |
| `artifact_unreadable` | Exists, cannot be read | Fix permissions or the lock holder |
| `tests_not_passed` | FAILED, skipped, no runner, not installed, timed out | Fix, or `--test-command`, then rebuild |
| `test_evidence_missing` | No `Evidence:` line, or the file is gone | Rebuild |
| `test_evidence_stale` | Evidence for other content, base or WorkItem | Rebuild; never hand-edit |
| `test_evidence_malformed` | Empty, not JSON, or self-contradictory | Rebuild |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| Null feature reference refused, in every flow | `tests/test_units_gate_artifacts.py::test_d01_a_null_feature_reference_refuses_approval` |
| Two candidates refuse as ambiguous | `tests/test_units_gate_artifacts.py::test_d01_two_candidate_features_refuse_as_ambiguous` |
| Unresolved security review refused, in every flow | `tests/test_units_gate_artifacts.py::test_d01_an_unresolved_security_review_refuses_approval` |
| A deleted artifact refuses | `tests/test_units_gate_artifacts.py::test_d01_a_deleted_artifact_refuses_approval` |
| An unhashable artifact refuses without mutation | `tests/test_units_gate_artifacts.py::test_d01_an_unhashable_artifact_refuses_without_mutation` |
| The omit path shares the precondition | `tests/test_units_gate_artifacts.py::test_d01_an_omission_of_an_unhashable_artifact_refuses` |
| A valid artifact still approves | `tests/test_units_gate_artifacts.py::test_d01_a_valid_uniquely_resolved_artifact_still_approves` |
| A failed command with a PASS review is refused | `tests/test_units_implementation_evidence.py::test_d02_1_a_failed_command_with_a_pass_review_is_refused` |
| A headings-only manifest is refused | `tests/test_units_implementation_evidence.py::test_d02_3_a_headings_only_manifest_is_refused` |
| Malformed or contradictory evidence is refused | `tests/test_units_implementation_evidence.py::test_d02_4_malformed_or_contradictory_evidence_is_refused` |
| A suite that never ran is refused | `tests/test_units_implementation_evidence.py::test_d02_5_a_suite_that_never_ran_is_refused` |
| An edited manifest no longer matches its evidence | `tests/test_units_implementation_evidence.py::test_d02_6_an_edited_manifest_no_longer_matches_its_evidence` |
| Evidence from before a new preflight is stale | `tests/test_units_implementation_evidence.py::test_d02_6_evidence_from_before_a_new_preflight_is_stale` |
| There is no exception path to apply | `tests/test_units_implementation_evidence.py::test_d02_7_there_is_no_exception_path_to_apply` |
| A passing command approves | `tests/test_units_implementation_evidence.py::test_d02_8_a_passing_test_command_approves` |
