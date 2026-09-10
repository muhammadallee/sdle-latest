# Dry Run 10 — `BROWNFIELD_DISCOVERY` (Reading a Repository Before Changing It)

| | |
|---|---|
| **Scenario ID** | DR-10 |
| **Flow** | `BROWNFIELD_DISCOVERY` |
| **Purpose** | The first WorkItem in an existing codebase. `discovery` runs before anything is specified, its findings are classified, and completion establishes the repository baseline. **19 phases, 8 gates.** |
| **Defect IDs** | D01, D02 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation and the discovery reading are simulated |
| **Starting conditions** | An existing repository with real code and history, and no `.sdle/baseline.json`. SpecKit initialised. `requirements/reporting-export.md` present. Governance classifies the WorkItem `enhancement` on `BROWNFIELD_DISCOVERY`, LOW risk. No feature directory bound. Clean working tree |
| **Guardrails exercised** | Flow binding at `init`, the gateless `discovery` phase, finding classification (`observed` / `inferred` / `unknown`), the read-only discovery agent, the `discovery_missing` refusal on both movers, and baseline establishment at the final gate |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; finding
> counts and hashes are illustrative. The engine behaviour it depends on is
> asserted by the tests under *Executable coverage*. Their results — **PASS**,
> **FAIL**, **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

> From `constitution_draft` onward this flow is element-for-element
> `GREENFIELD` shifted by one, so that stretch is compressed. The gate numbers
> are the same 1–8, because `discovery` is gateless.

---

## Setup

An existing repository with source and tests, SpecKit initialised with the
README command, and SDLE copied in. The executable form drives the real CLI
over the suite's fixture and records discovery from a generated input in
which every finding is honestly classified `unknown` — a scratch fixture has
nothing to discover (`Project.record_discovery` in `tests/conftest.py`).

---

## Transcript

**User:** `start workflow` → **SDLE:** `WorkItem name?` → **User:** `Reporting Export`

**SDLE:**

```
📋 SDLE Status: Phase 1/19 — Requirements Check [IN PROGRESS]

WorkItem created: reporting-export. Preflight passed.

I found requirements/:
  • requirements/reporting-export.md (3.1 KB)

Content scan passed.

This repository has no recorded baseline, and it is not empty — I can see an
existing source tree. This WorkItem is therefore bound to BROWNFIELD_DISCOVERY:
19 phases, 8 gates. It opens with a discovery pass that reads the repository as
it actually is, before anything is specified about changing it.

Shall I proceed?
```

*(Engine: `sdle.sh workitem create --name "Reporting Export"`, then
`sdle.sh --workitem reporting-export preflight`, then
`sdle.sh --workitem reporting-export governance assess --input governance-input.json`
with `flow: BROWNFIELD_DISCOVERY`, then
`sdle.sh --workitem reporting-export --session 3b8f0c21 init` bound it. The flow
is bound **once**. A later record naming a different flow is refused
`flow_mismatch`.)*

---

**User:** `yes`

**SDLE:**

```
<!-- SDLE_STATE phase=discovery status=in_progress progress=2/19 -->
📋 SDLE Status: Phase 2/19 — Repository Discovery [IN PROGRESS]

Reading the repository across the discovery categories...

Discovery recorded: 47 findings across 14 categories.

  observed   31   — read directly out of a file that exists here
  inferred   12   — a conclusion drawn from findings, each naming its basis
  unknown     4   — the honest answer; no evidence either way

## repository_inventory
  [observed] 214 Python modules under src/, 9 entry points declared in
             pyproject.toml.  (cites: pyproject.toml, src/)
## persistence_data_architecture
  [inferred] There is no read-replica routing.  (rests on: F-012, F-013)
## test_practices
  [unknown]  Nothing in the repository records whether the integration suite
             is run in CI.
[... 44 findings abridged ...]
```

*(Where the orchestrator delegates the reading, it goes to the read-only
`sdle-discovery` agent, whose declared tools grant no writes. Whether it
delegates at all is convention, not something the engine enforces. Either way
the findings enter the record through one door, `sdle.sh discovery assess --input discovery-input.json`, which validated
every classification and citation and wrote
`workitems/reporting-export/.sdle/discovery.json`. The phase has no gate. The
record is what replaces one.)*

---

**User:** `skip discovery, I know this codebase`

**SDLE:** *(had discovery not been recorded)*

```
Refused: discovery_missing

WorkItem 'reporting-export' is at discovery and no accepted record exists, so the
workflow cannot leave the phase.
```

> A gateless phase is not an ungoverned one. `advance` and `skip` both refuse,
> and the refusal leaves `audit.md` byte-identical.

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=constitution_draft status=in_progress progress=3/19 -->
📋 SDLE Status: Phase 3/19 — Generate Constitution [IN PROGRESS]

Before drafting: re-displaying the discovery record, grouped by category, with each
finding's classification — the constitution is written from what was found here, not
from a blank page.
[... discovery record re-displayed in full ...]
```

---

> **Phases 4–18 proceed as in `01-happy-path.md`**, shifted by one:
>
> | Gate | Phase | Progress |
> |---:|---|---|
> | 1/8 | `gate_constitution` | 4/19 |
> | 2/8 | `gate_spec` | 6/19 |
> | 3/8 | `gate_plan` | 8/19 |
> | 4/8 | `gate_tasks` | 11/19 |
> | 5/8 | `gate_analyze` | 13/19 |
> | 6/8 | `gate_design` | 15/19 |
> | 7/8 | `gate_implement` | 17/19 |
> | 8/8 | `gate_security` | 19/19 |
>
> Each gate still refuses an unresolved artifact (D01). Gate 7 still refuses
> anything but a passing test run for its exact manifest (D02). In an existing
> codebase that usually means the project's real suite, via the detected runner
> or `--test-command`.

---

**User:** `approve` *(at Gate 8/8)*

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=19/19 -->
📋 SDLE Status: Phase 19/19 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 8 gates passed. Completion summary: workitems/reporting-export/.sdle/completion-summary.json

Repository baseline established: .sdle/baseline.json
  It references the discovery record by path and SHA-256 — it does not copy it. The
  next WorkItem converges onto ITERATIVE against it (see DR-11); a second
  BROWNFIELD_DISCOVERY is refused `baseline_present`.
```

---

## Artifacts, state and audit

- `state.flow` = `BROWNFIELD_DISCOVERY`, set at `init` and never changed.
- The traversal was all 19 phases:
  `requirements_check → discovery → constitution_draft → gate_constitution → spec_draft → gate_spec → plan_draft → gate_plan → checklist_draft → tasks_draft → gate_tasks → analyze → gate_analyze → design_generation → gate_design → implement → gate_implement → security_review → gate_security → complete`.
- `discovery.json` was written once, by `discovery assess`, with evidence in
  `evidence/discovery-<execution-id>.json`.
- `.sdle/baseline.json` was written once, at the Gate 8 approval. It records
  `establishedBy.flow: BROWNFIELD_DISCOVERY` and `discovery.status: PERFORMED`,
  and references the constitution and the design document by SHA-256.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Leave `discovery` with no accepted record | Refused `discovery_missing` | `audit.md` byte-identical |
| A second `BROWNFIELD_DISCOVERY` WorkItem after completion | Refused `baseline_present` at `init` | No runtime created — see DR-11 |
| Approve `gate_spec` before `feature resolve` | Refused `artifact_unresolved` | Unchanged — see DR-14 |

## Cleanup

`rm -rf` the disposable repository. `.sdle/baseline.json` lives inside it.

## Executable coverage

| Claim | Test |
|---|---|
| The flow opens on discovery | `tests/test_integration_10_to_13.py::test_10_the_flow_opens_on_discovery_before_anything_is_specified` |
| The progress fractions are the engine's | `tests/test_integration_10_to_13.py::test_10_the_transcript_progress_fractions_are_what_the_engine_emits` |
| Discovery is gateless but not ungoverned | `tests/test_integration_10_to_13.py::test_10_discovery_is_gateless_but_not_ungoverned` |
| Findings are classified and readable back | `tests/test_integration_10_to_13.py::test_10_the_recorded_findings_are_classified_and_readable_back` |
| Completion establishes the baseline | `tests/test_integration_10_to_13.py::test_10_completion_establishes_the_repository_baseline` |
| The whole flow traverses exactly its phases | `tests/test_units_flow_model.py::test_a_flow_traverses_exactly_its_declared_phases[BROWNFIELD_DISCOVERY]` |
| Null feature reference refused in this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_a_null_feature_reference_refuses_approval[BROWNFIELD_DISCOVERY]` |
| Unresolved security artifact refused in this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_an_unresolved_security_review_refuses_approval[BROWNFIELD_DISCOVERY]` |
