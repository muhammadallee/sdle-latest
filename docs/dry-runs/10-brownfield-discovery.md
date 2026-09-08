# Dry Run 10 — `BROWNFIELD_DISCOVERY` (Reading a Repository Before Changing It)

| | |
|---|---|
| **Purpose** | The first WorkItem in an existing codebase: `discovery` runs before anything is specified, its findings are classified, and completion establishes the repository baseline. **19 phases, 8 gates.** |
| **Guardrails exercised** | Flow binding at `init`, the gateless `discovery` phase, finding classification (`observed` / `inferred` / `unknown`), the `discovery_missing` refusal on both movers, baseline establishment at the final gate. |
| **Starting state** | An existing repository with real code and no `.sdle/baseline.json`. SpecKit initialized. `requirements/reporting-export.md` present. Clean git working tree. |

> This transcript covers only what is **different** from `01-happy-path.md`. From `constitution_draft` onward the two flows are element-for-element identical, so the middle is compressed; the gate numbering is the same 1–8 because `discovery` is gateless.

---

## Transcript

**User:**

```
start workflow
```

**SDLE:**

```
📋 SDLE Status: Phase 1/19 — Requirements Check [IN PROGRESS]

I found requirements/:
  • requirements/reporting-export.md (3.1 KB)

Content scan passed.

This repository has no recorded baseline, and it is not empty — I can see an
existing source tree. This WorkItem is therefore bound to BROWNFIELD_DISCOVERY:
19 phases, 8 gates. It opens with a discovery pass that reads the repository as
it actually is, before anything is specified about changing it.

Shall I proceed?
```

*(Internally: `governance assess` recorded a classification of `flow: BROWNFIELD_DISCOVERY`; `init` bound it. The flow is bound **once** and never re-bound — a later governance record naming a different flow is refused `flow_mismatch`.)*

---

**User:**

```
yes
```

**SDLE:**

```
<!-- SDLE_STATE phase=discovery status=in_progress progress=2/19 -->
📋 SDLE Status: Phase 2/19 — Repository Discovery [IN PROGRESS]

Reading the repository across the fourteen discovery categories...

Discovery recorded: 47 findings across 14 categories.

  observed   31   — read directly out of a file that exists here
  inferred   12   — a conclusion drawn from findings, each naming its basis
  unknown     4   — the honest answer; no evidence either way

## repository_inventory
  [observed] 214 Python modules under src/, 9 entry points declared in
             pyproject.toml.  (cites: pyproject.toml, src/)
## persistence_data_architecture
  [observed] PostgreSQL via SQLAlchemy; 31 migration scripts under
             migrations/.  (cites: migrations/, src/db/session.py)
  [inferred] There is no read-replica routing.  (rests on: F-012, F-013)
## test_practices
  [unknown]  Nothing in the repository records whether the integration suite
             is run in CI.

[... 44 findings abridged ...]

Every finding above carries one of exactly three classifications. That is
enforced: a finding with no classification, or a fourth value, is refused.
An observation must cite a path that exists in this repository; an inference
must name the findings it rests on, and none of those may itself be unknown.

What is NOT enforced, and is the author's claim: whether an observation is
*true of* the file it cites, and whether an inference actually follows.
```

*(Internally: `discovery assess --input discovery-input.json` validated and wrote `workitems/reporting-export/.sdle/discovery.json`. The phase has no gate — the record is what replaces one.)*

---

**User:**

```
skip discovery, I know this codebase
```

**SDLE:**

```
Refused: discovery_missing
```

> This is the refusal shown **as if** discovery had not been recorded, which is
> the case worth documenting. `advance` and `skip` both refuse:
>
> ```
> WorkItem 'reporting-export' is at discovery and no accepted record exists,
> so the workflow cannot leave the phase.
> ```
>
> A gateless phase is not an ungoverned one. The refusal is what makes the
> record mandatory, and it leaves `audit.md` byte-identical — a refused mover
> writes nothing at all.

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=constitution_draft status=in_progress progress=3/19 -->
📋 SDLE Status: Phase 3/19 — Generate Constitution [IN PROGRESS]

Before drafting: this repository already has conventions, and the constitution
has to be written from what was actually found in it rather than from a blank
page. Re-displaying the discovery record, grouped by category, with each
finding's classification...

[... discovery record re-displayed in full ...]

Generating constitution...
```

*(Internally: the `constitution_draft` block re-runs `discovery show` whenever the bound flow ran `discovery`. The human approving Gate 1 must see, in this conversation, which statements were read out of a file and which were inferred.)*

---

> **Phases 4–18 (`gate_constitution` → `security_review`) are identical to
> `01-happy-path.md`**, with progress fractions shifted by one and the same
> eight gates in the same order:
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

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=19/19 -->
📋 SDLE Status: Phase 19/19 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 8 gates passed. Completion summary: workitems/reporting-export/.sdle/completion-summary.json

Repository baseline established: .sdle/baseline.json

  This is what makes discovery happen once. The baseline references the
  discovery record by path and SHA-256 — it does not copy it. The next
  WorkItem in this repository converges onto ITERATIVE against this baseline;
  a second BROWNFIELD_DISCOVERY is refused `baseline_present`.
```

---

## State & audit notes

- `state.flow` was set to `BROWNFIELD_DISCOVERY` at `init` and never changed.
- `state.json` traversed all 19 phases: `requirements_check → discovery → constitution_draft → gate_constitution → spec_draft → gate_spec → plan_draft → gate_plan → checklist_draft → tasks_draft → gate_tasks → analyze → gate_analyze → design_generation → gate_design → implement → gate_implement → security_review → gate_security → complete`.
- `workitems/reporting-export/.sdle/discovery.json` written exactly once, by `discovery assess`, before the phase could be left.
- The two refused movers appended **nothing**: `audit.md` was byte-identical before and after each, and `audit verify` reported an intact chain throughout.
- `.sdle/baseline.json` written exactly once, at Gate 8 approval, referencing `discovery.json` by path and SHA-256.
- All 8 `approvals.*` entries populated; `artifact_shas` holds 8 baseline fingerprints.

## What this pins that `test_units_flow_model.py` does not

The traversal itself is already driven through the real CLI by the flow-model
tests. What is specific to *this* transcript is the **conversational
obligation**: that the discovery record is displayed in full when it is
recorded, and displayed *again* before the constitution is drafted. Design
invariant 4 says a human approves what they can see, and for a gateless phase
whose output feeds the next document, "what they can see" has to include the
classifications. `tests/test_integration_10_brownfield_discovery.py` asserts
the mechanical half; the display obligation lives in
`modules/phase-execution.md` and is convention, stated here so it is not
mistaken for something the engine enforces.
