# Dry Run 24 — Obligations Traced to the End, and Evidence Bound to the Tree

| | |
|---|---|
| **Scenario ID** | DR-24 |
| **Flow** | `GREENFIELD` |
| **Purpose** | A WorkItem started from an approved requirements package carries every in-scope obligation into the specification and the tasks, ends with a verification disposition for each acceptance criterion, and cannot pass the implementation gate on test evidence that belongs to a different tree. The wrong kind of review does not carry a gate. |
| **Defect IDs** | — |
| **Runtime** | SDLE on `enh/requirements-package-loop`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The WorkItem `orders-wi-001-orders` from DR-23 has started under package `orders`, revision approved. Its work item has requirements FR-001, AC-001 and NFR-001, with AC-001 the one acceptance criterion. |
| **Guardrails exercised** | The engine checks that ids are present and well-formed, never that they are meant; `gate_spec` and `gate_tasks` refuse an omitted or invented id and an untested criterion; an omitted `gate_tasks` cannot let an uncovered criterion through; `gate_implement` refuses evidence for another tree and a run during which the tree changed; an unmapped pass is shown apart and never as verified; a design review does not carry the implementation gate |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**,
> **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

## Setup

The repository and WorkItem of DR-23. The constitution and the architecture
placement are approved; the specification has just been generated. Spec Kit was
told to cite the source requirement ids it covers, and the in-scope ids come
from `sdle.sh trace check`.

---

## Transcript

### Part 1 — The specification must carry every in-scope id

<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=7/20 -->
📋 SDLE Status: Phase 7/20 — Gate 3: Specification Approval [AWAITING APPROVAL]

**User:** `approve`

**SDLE:** `Refused: trace_spec_incomplete`

```
spec.md does not carry FR-001 of work item WI-001. Every in-scope requirement
must appear in the specification, or be excluded with an approved disposition.
```

> **The engine checked presence, not meaning.** FR-001 was not in the text, so
> the gate stopped before anything was written. Whether the text that *is*
> there says what FR-001 says is the review's judgement, and the engine does
> not pretend to make it.

**Claude:** I added FR-001 where the specification covers it.

**User:** `approve`

*(Approved. A specification that cited `FR-999`, which the package does not
define, would have been refused `trace_unknown_id`.)*

### Part 2 — Every acceptance criterion needs a test task

<!-- SDLE_STATE phase=gate_tasks status=awaiting_approval progress=12/20 -->
📋 SDLE Status: Phase 12/20 — Gate 5: Tasks Approval [AWAITING APPROVAL]

**User:** `approve`

**SDLE:** `Refused: trace_tasks_uncovered`

```
These acceptance criteria have no task that tests them: AC-001. Add a test task
citing each, or record an approved exclusion.
```

**Claude:** Task T002 now says "Test AC-001: creating an order returns its
number". T003 is purely engineering and cites the constitution principle PRN-01
instead of a business id; T004, "tidy the readme", cites nothing and is only
listed.

> **An untraced task is listed, never blocking.** An acceptance criterion with
> no test task is.

### Part 3 — Evidence belongs to one tree

*(`manifest build` runs the tests. The engine took a digest of the working tree
before and after the run, and recorded it in the evidence.)*

**Claude:** The tests passed. Before the gate I tidied one line in `app.py`.

<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=18/20 -->
📋 SDLE Status: Phase 18/20 — Gate 8: Implementation Approval [AWAITING APPROVAL]

**User:** `approve`

**SDLE:** `Refused: test_evidence_stale`

```
the implementation changed after the tests ran against it (the working tree is
not the one the evidence was taken from). A passing result for other content
proves nothing about this one. Rebuild it with `manifest build`.
```

*(The same refusal, with `changed_during_run`, is what a test command that
writes a file into the tree produces: the evidence says so instead of claiming a
pass.)*

### Part 4 — What counts as verified

**Claude:** I rebuilt the evidence, and the project's runner writes a JUnit
report under the WorkItem's evidence directory.

**SDLE:**

```
verification show

  unmapped   AC-001        ← a passing suite that no test names
  verified   (none)
```

> **Shown apart, never as verified.** After `verification map --junit`, a
> passing test whose name cites AC-001 moves it to `verified-mapped`; a failing
> one makes it `blocked`. Rebuilding the evidence ends a mapping, because a
> mapping is only as good as the run it came from.

### Part 5 — The right kind of review

**Claude:** I reviewed the design.

**SDLE:** *(Gate 7, Design Approval)* `Refused: review_type_mismatch`

```
design/app/app-design.md has been reviewed, but not by a review gate_design
accepts (it needs design-review by any; recorded: content-review by agent).
```

*(A `design-review` of the current content carries the gate. A later review of
another kind would not have displaced it.)*

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `workitems/<id>/specs/<feature>/spec.md`, `tasks.md` | the text the trace is read from |
| `workitems/<id>/.sdle/evidence/implementation-*.json` | the test result, the tree digest before and after, whether the tree changed during the run, and the package, requirements and tasks digests it was made against |
| `workitems/<id>/.sdle/verification.json` | the append-only dispositions, written only by `verification record` and `verification map` |
| `workitems/<id>/.sdle/reviews.json` | each review with its type, actor and, when given, its findings summary |
| `workitems/<id>/.sdle/audit.md` | a `verification_recorded` entry per disposition |

---

## Negative cases

| What is tried | What happens |
|---|---|
| A requirement left out of the specification | `Refused: trace_spec_incomplete` |
| An id the package does not define, in the specification or the tasks | `Refused: trace_unknown_id` |
| An acceptance criterion with no test task | `Refused: trace_tasks_uncovered` |
| An omitted `gate_tasks` with the test task dropped afterwards | `Refused: trace_tasks_uncovered` at `gate_implement` |
| A file edited after a passing test run | `Refused: test_evidence_stale` |
| A test run that changes the tree | `Refused: test_evidence_stale` (`changed_during_run`) |
| A policy that refuses an unmapped pass | `Refused: trace_verification_unmapped` |
| A design review standing in for a code review | `Refused: review_type_mismatch` |
| A `PASS` over an open blocking finding | `Refused: review_findings_open` |
| `drift rebaseline` on a package WorkItem | `Refused: rebaseline_not_permitted` |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| A requirement left out of the spec refuses the spec gate | `tests/test_units_trace.py::test_as10_a_requirement_left_out_of_the_spec_refuses_the_spec_gate` |
| An unknown id in the spec is refused | `tests/test_units_trace.py::test_as11_a_spec_that_cites_an_unknown_id_is_refused` |
| An obligation tag is accepted and an untraced task is only listed | `tests/test_units_trace.py::test_as12_an_engineering_task_may_cite_an_obligation_tag_and_an_untraced_one_is_only_listed` |
| A criterion with no test task refuses the tasks gate | `tests/test_units_trace.py::test_as18_a_criterion_with_no_test_task_refuses_the_tasks_gate` |
| An omitted tasks gate cannot let an uncovered criterion through | `tests/test_units_trace.py::test_an_omitted_tasks_gate_cannot_let_an_uncovered_criterion_through` |
| An unmapped pass is shown apart and never as verified | `tests/test_units_trace.py::test_as19_a_passing_suite_that_names_no_criterion_is_unmapped_not_verified` |
| A JUnit test that names a criterion verifies it | `tests/test_units_trace.py::test_a_junit_test_that_names_the_criterion_verifies_it` |
| A file edited after a passing run makes the evidence stale | `tests/test_units_tree_digest.py::test_as14_a_file_edited_after_a_passing_run_makes_the_evidence_stale` |
| A tree that changes during the run invalidates the evidence | `tests/test_units_tree_digest.py::test_as16_a_tree_that_changes_during_the_run_makes_the_evidence_invalid` |
| Uncommitted and untracked changes count; ignored ones do not | `tests/test_units_tree_digest.py::test_as15_uncommitted_and_untracked_changes_move_the_digest_and_ignored_ones_do_not` |
| A design gate will not take a content review | `tests/test_units_review_types.py::test_as13_a_design_gate_will_not_take_a_content_review` |
| A `PASS` is refused over an open blocking finding | `tests/test_units_review_types.py::test_a_pass_is_refused_while_a_blocking_finding_is_open` |

Result: **PASS**.
