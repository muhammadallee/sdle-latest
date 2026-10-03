# Dry Run 21 — Fixing Blocked Requirements Before the Workflow Starts

| | |
|---|---|
| **Scenario ID** | DR-21 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The ordinary refinement loop. A requirements document is assessed and blocked. The user accepts help, a human decides each change, the engine applies what was accepted, and a re-assessment passes. Nothing in the loop assesses except `governance assess`, and no change is applied that a human did not accept. |
| **Defect IDs** | — |
| **Runtime** | SDLE on `feat/requirements-refinement`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A WorkItem with one bound requirements document that states what to build but has no acceptance criteria. No `init` has run. |
| **Guardrails exercised** | The assessor reads from the engine's own definitions; the failing set comes from the engine's record, not from the proposal; a change that alters meaning needs a human decision; the engine, not the proposer, decides what is only presentation; `init` waits for an open loop |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**,
> **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

<!-- dry-run-pre-init -->

## Setup

A disposable repository with one WorkItem and one bound document, `requirements/todo-api.md`.
The workflow has not started, so there is no status header: refinement happens
before there is a workflow to have a position in.

---

## Transcript

### Part 1 — The assessment blocks

**User:** `start workflow`

*(The WorkItem is created and the document bound and scanned, as in DR-01. The
assessment is the next step.)*

**SDLE:**

```
Requirements quality is BLOCKED and the workflow cannot progress:
acceptance_criteria: the document states no criteria by which "done" can be checked.
The assessment has been recorded; fix the requirements and re-run `governance assess`.
```

**Claude:** The requirements say what to build but not how anyone would know it
works. I can help fix that: I would draft the missing criteria, show them to
you, and apply only the ones you accept. Do you want to try?

**User:** `yes`

> **Offered, never started.** The module that carries this loop is loaded only
> because the user said yes. Declining means editing the document and
> re-assessing, exactly as before.

### Part 2 — A proposal, shown in the conversation

**Claude:** One check is failing. This is what I propose, and why.

> **Finding:** no acceptance criteria.
>
> **Question 1:** Who is allowed to create a todo? *(staff / anyone)*
>
> **Edit e1** adds a new section at the end of the document:
>
> ```
> ## Acceptance
>
> - AC-1: Creating a todo returns status 201.
> ```
>
> **Edit e2** changes only spacing: `The  service  stores items.` becomes
> `The service stores items.`

*(The proposal is written to a file and recorded.)*

**SDLE:**

```
refinement propose

  status      IN_PROGRESS
  iteration   1
  failing     acceptance_criteria        ← read from the engine's own record
  lint        1 advisory evidence file   ← hints; never a verdict
```

> **The failing set is the engine's.** The proposal named a finding, but which
> checks are failing was read from the recorded assessment, so a proposal
> cannot invent a failure or hide one.

### Part 3 — The human decides; the engine decides what is only layout

**User:** `staff`  *(answers question 1)*

**User:** `accept e1`

**SDLE:**

```
refinement decide

  question    q1 → staff
  edit        e1 → accepted
```

*(Edit e2 is not put to the user. Whether a change is only presentation is
decided by comparing the document's normal form before and after, never by what
the proposer called it. Replacing `must` with `should` would have been put to a
human; changing two spaces into one is not.)*

### Part 4 — Apply, re-assess, finish

**SDLE:**

```
refinement apply   (e1)   path requirements/todo-api.md   neutral: no
refinement apply   (e2)   path requirements/todo-api.md   neutral: yes
  next: run `governance assess`, then `refinement propose`
```

**SDLE:** *(`governance assess` — passes.)* Then:

```
refinement propose

  status      PASSED
  iteration   1  → progress
```

**Claude:** The requirements now pass. The workflow can start.

**User:** `continue`

*(`init` runs. While a loop is open it would have been refused; a passed loop
does not stand in the way.)*

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `workitems/<id>/.sdle/refinement.json` | the loop: one iteration, its findings, the question and its answer, both edits and what became of them, outcome `progress`, status `PASSED` |
| `workitems/<id>/.sdle/evidence/refinement-baseline-*.json` | the document as it was before the loop, preserved once |
| `workitems/<id>/.sdle/evidence/refinement-apply-*.json` | one file per applied edit: before and after fingerprints and the diff |
| `workitems/<id>/.sdle/evidence/refinement-lint-*.json` | the advisory lint findings, each marked as not enforced |
| `workitems/<id>/.sdle/governance.json` | the passing assessment, written only by `governance assess` |

No audit entry is written before `init`, so none is written here; the loop's
history is the record and its evidence, and `state.json` does not exist yet.

---

## Negative cases

| What is tried | What happens |
|---|---|
| A proposal that carries quality results | `Refused: refinement_input_invalid` — assessing is `governance assess`'s job alone |
| A finding for a check that is not failing | `Refused: refinement_input_invalid` |
| An edit written against text that has since changed | `Refused: refinement_edit_stale_base` |
| Applying an edit no human accepted | `Refused: refinement_wrong_status` |
| A question that was already answered in an earlier round | `Refused: refinement_input_invalid` |
| `init` while a loop is open | `Refused: refinement_in_progress` |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| The loop is entered and the failing set comes from the engine | `tests/test_units_refinement_commands.py::test_propose_enters_the_loop_and_derives_the_failures_from_the_assessment` |
| The lint is advisory evidence and never refuses | `tests/test_units_refinement_commands.py::test_the_lint_is_recorded_as_advisory_evidence_and_never_refuses` |
| A substantive edit needs a human decision | `tests/test_units_refinement_commands.py::test_a_substantive_edit_needs_a_human_decision` |
| A presentation-only edit is decided by the engine | `tests/test_units_refinement_commands.py::test_a_presentation_only_edit_is_decided_by_the_engine_and_needs_no_human` |
| A one-word change is never called neutral | `tests/test_units_refinement_commands.py::test_a_one_word_change_is_never_called_neutral` |
| An accepted edit is applied and the loop awaits re-assessment | `tests/test_units_refinement_commands.py::test_an_accepted_edit_is_applied_and_the_loop_awaits_reassessment` |
| A passing re-assessment ends the loop | `tests/test_units_refinement_commands.py::test_a_passing_reassessment_ends_the_loop_passed` |
| A question already answered is not asked again | `tests/test_units_refinement_commands.py::test_a_question_already_answered_is_not_asked_again` |
| `init` waits for an open loop | `tests/test_units_refinement_commands.py::test_init_is_refused_while_a_loop_is_active_and_allowed_after` |

Result: **PASS**.
