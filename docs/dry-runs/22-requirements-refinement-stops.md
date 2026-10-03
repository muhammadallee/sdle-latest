# Dry Run 22 — When Refinement Stops

| | |
|---|---|
| **Scenario ID** | DR-22 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The four ways a refinement loop is stopped on purpose: an assessor changing its mind about unchanged requirements, a document another WorkItem still holds, a loop that stops making progress, and a loop that has used all its rounds. Each is the engine's refusal or record, and none can be argued past. |
| **Defect IDs** | — |
| **Runtime** | SDLE on `feat/requirements-refinement`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | One WorkItem with a bound document that fails `acceptance_criteria`, a loop already open, and — for Part 2 — a second WorkItem that has not finished and binds the same document. |
| **Guardrails exercised** | `quality_verdict_flip`; the dispute path and what it exempts; `refinement_shared_source`; stall and cap escalation; the open boundary around shared documents |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable
> coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** —
> are recorded in [verification-matrix.md](verification-matrix.md).

---

<!-- dry-run-pre-init -->

## Setup

The loop from DR-21, stopped after the proposal. Nothing has been applied yet.

---

## Transcript

### Part 1 — The assessor changes its mind about unchanged text

**Claude:** *(re-runs the assessment without any edit having been applied, and
this time the assessor answers `PASS` for the failing check.)*

**SDLE:**

```
Refused: quality_verdict_flip

These checks failed in an earlier assessment of requirements with exactly this
content, and now read as passing: acceptance_criteria. Unchanged requirements
cannot have become adequate, so the earlier result stands and nothing was
recorded as the verdict. Change the requirements substantively and assess
again; an earlier result is overturned only by a recorded dispute.
```

> **The recorded verdict did not move.** `governance.json` is byte-identical,
> so `advance` still sees the failure. The refused attempt is kept as evidence
> of its own kind and is not part of the assessment history. A re-wrapped or
> re-spaced document does not count as a change either: "the same content" is
> decided on the document's normal form, not its bytes.

**Claude:** The first assessment may simply have been wrong. There is a way to
say so, but it needs your decision. If I take it, the earlier failure stays in
the record, marked overturned; it does not count as the requirements having
improved. Do you want to dispute it?

**User:** `yes — the document does state AC-1 in the Data section; the first
assessor missed it`

**SDLE:**

```
refinement dispute

  check       acceptance_criteria
  outcome     overturned_by_dispute
  next        run `governance assess` again; only this check at this content
              is exempt from the verdict-flip rule
```

> **Three things were needed, and none could be supplied by the proposer:** the
> refused re-assessment as independent evidence, a written rationale, and the
> human's decision. The exemption covers exactly one result at exactly one
> content. A second dispute reusing the same evidence or the same decision is
> refused `refinement_dispute_replayed`.

### Part 2 — Another WorkItem holds the document

*(A second WorkItem has **started** and is bound to the same file.)*

**SDLE:**

```
Refused: refinement_shared_source

Another WorkItem still holds a document this refinement would change
(requirements/todo-api.md: payments-api). Editing it would stale their
assessment, so it is refused and nothing was written. Complete or re-bind those
WorkItems first, or change the document by hand and re-assess each WorkItem.
```

> **No override exists** for a WorkItem that has started. A WorkItem that has
> *finished* does not count, so a later WorkItem can build on documents
> earlier ones used.
>
> **A WorkItem that has not started does not block.** If `payments-api` had no
> state yet, the edit would be applied and SDLE would print that `payments-api`
> holds the changed document, that its assessment is now stale, and that it
> must assess again before it starts. Nothing of `payments-api` is written. Only
> WorkItems in this checkout can be seen: a teammate's branch is theirs to be
> told about.
>
> **Not shipped:** an acknowledged edit to a document a *started* WorkItem holds,
> recorded in both WorkItems' audit, with crash recovery, is deferred pending a
> decision on how one WorkItem may write another's record.

### Part 3 — A loop that is not getting anywhere

*(Two rounds follow in which the edits applied do not reduce the failing
checks.)*

**SDLE:**

```
refinement propose

  status      ESCALATED
  reason      stall
```

**Claude:** The loop has stopped. It tried twice and the same check still fails,
so another round would not help. What is left is yours to decide: edit the
document yourself and re-assess, take the open question to whoever owns the
requirement, or stop here. I will not start a second loop to get around this
one.

> **A repeated proposal, or a change that leaves the content as it was, ends the
> loop at once; a change that helps nothing ends it after the second round.**
> Escalation is the record of a loop that ended, not a failure of the person.

### Part 4 — A loop that used all its rounds

*(Each round made progress, but the requirements still fail after the last
round the loop is allowed.)*

**SDLE:**

```
Refused: refinement_cap_exhausted

The refinement used its 3 iterations and the requirements still fail. The loop
is recorded as ESCALATED: edit the requirements by hand, or take the findings
back to the people who own them.
```

> **The number of rounds is the engine's.** A repository policy may lower it and
> can never raise it.

### Part 5 — After the workflow has started

**SDLE:**

```
Refused: refinement_post_init

`refinement propose` works on requirements before the workflow starts, and
workitems/<id>/.sdle/state.json already exists. Nothing was written. A change
to the requirements after `init` is an ordinary edit followed by
`governance assess`.
```

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `workitems/<id>/.sdle/evidence/governance-flip-attempt-*.json` | the refused re-assessment: the checks that would have flipped, the content digest, and the quality it proposed |
| `workitems/<id>/.sdle/evidence/refinement-dispute-*.json` | the rationale and the reference to the human decision |
| `workitems/<id>/.sdle/refinement.json` | the dispute outcome `overturned_by_dispute`; later, status `ESCALATED` |

Nothing in this scenario writes `governance.json` except a `governance assess`
the engine accepted.

---

## Negative cases

| What is tried | What happens |
|---|---|
| A dispute with no decision reference, no rationale, or ordinary assessment evidence | `Refused: refinement_dispute_incomplete` |
| A dispute that reuses an earlier dispute's evidence, decision or result | `Refused: refinement_dispute_replayed` |
| A document a started WorkItem holds, with or without an acknowledgement key | `Refused: refinement_shared_source` / `Refused: refinement_input_invalid` |
| Another WorkItem's record unreadable | `refinement_registry_invalid` (exit 3), nothing changed |
| Two commands at once | `Refused: refinement_transaction_locked` |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| A FAIL cannot become a PASS at unchanged content | `tests/test_units_assessment_integrity.py::test_a_fail_then_a_pass_at_the_same_content_is_refused` |
| The refused flip cannot unlock progression | `tests/test_units_assessment_integrity.py::test_the_refused_flip_cannot_unlock_progression` |
| A whitespace-only change does not unlock a flip | `tests/test_units_assessment_integrity.py::test_a_presentation_only_change_does_not_unlock_the_flip` |
| A complete dispute exempts exactly its pair | `tests/test_units_refinement_commands.py::test_a_complete_dispute_overturns_the_pair_and_unlocks_exactly_that_pass` |
| One decision cannot authorise two disputes | `tests/test_units_refinement_commands.py::test_one_human_decision_cannot_authorise_two_disputes` |
| A document a started WorkItem holds is refused before any write | `tests/test_units_refinement_commands.py::test_a_sharer_that_started_blocks_even_with_an_assessment` |
| A document only not-started WorkItems hold can be refined, and they are told | `tests/test_units_refinement_commands.py::test_a_document_only_not_started_workitems_hold_can_be_refined` |
| A finished WorkItem does not count as a sharer | `tests/test_units_refinement_commands.py::test_a_completed_sharer_does_not_block` |
| A repeated proposal escalates | `tests/test_units_refinement_commands.py::test_a_repeated_proposal_is_a_stall_and_escalates` |
| The round limit escalates and refuses | `tests/test_units_refinement_commands.py::test_the_cap_ends_the_loop_escalated_and_refuses` |
| Refinement after `init` is refused before any write | `tests/test_units_refinement_commands.py::test_propose_after_init_is_refused_before_any_write` |

Result: **PASS**.
