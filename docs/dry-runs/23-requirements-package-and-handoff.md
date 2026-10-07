# Dry Run 23 — A Requirements Package, a Solution Architect's Approval, and the Handoff

| | |
|---|---|
| **Scenario ID** | DR-23 |
| **Flow** | `GREENFIELD` |
| **Purpose** | A source requirements document becomes a validated package. A Solution Architect approves it at an exact digest. One package work item becomes one WorkItem, and a developer starts from it without copying anything. The engine refuses a stale or unapproved package, a work item that is not ready, and a package that moved after the WorkItem started. |
| **Defect IDs** | — |
| **Runtime** | SDLE on `enh/requirements-package-loop`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A repository with a source document at `docs/source/srs.md`. No WorkItem exists and no package has been imported. |
| **Guardrails exercised** | The package is drafted only in staging and moved into `requirements/` only by the engine; every structural problem is named in one refusal; the approval is a hash-chained record bound to the package digest, outside the package; `init` refuses an unapproved, stale or not-ready package work item; a started WorkItem is pinned to its revision; the source document is never written |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**,
> **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

<!-- dry-run-pre-init -->

## Setup

A disposable repository holding `docs/source/srs.md`, a two-section order
management specification. No workflow has started, so there is no status
header: a package is made and approved before any WorkItem exists.

---

## Transcript

### Part 1 — The package is drafted and validated

**User:** `Turn docs/source/srs.md into a requirements package for the orders system.`

**Claude:** I scanned the source first and nothing in it is flagged. I drafted the
package in `package-staging/orders/`, the one place I may write, and I left out
`access-control.md` because the source defines no roles beyond clerk and
manager; the overview says so. Two things I could not decide from the source
are open issues, and one of them blocks work item WI-002.

**SDLE:**

```
package validate --staging

  package     orders
  valid       yes
  work items  WI-001 READY · WI-002 NOT_READY
```

> **Nothing was invented.** A month boundary the source does not define became
> open issue OI-001, and WI-002 is NOT READY because of it. The package was not
> made READY by guessing.

### Part 2 — Fidelity review, then import

**Claude:** I asked the reviewer one thing: does each requirement say what its
source says, and is every "shall" in the source mapped or excluded?

> **Finding (advisory):** FR-003 (nightly export) is excluded with a
> disposition, but section 3.2's last sentence reads as a requirement, not a
> future option.

**User:** `Keep it excluded; the owner confirmed it on the 14th.`

**SDLE:**

```
package import --package orders

  imported    yes
  digest      9c41…e07a
  status      unapproved
```

*(The engine scanned every file, validated the package and copied it into
`requirements/packages/orders/`. A draft containing an instruction aimed at a
model would have been refused `package_invalid` with rule
`package_content_flagged`.)*

### Part 3 — The Solution Architect approves

**Claude:** Here is what the Solution Architect is approving: the overview,
both work items' requirements, the open issues and the readiness verdicts.
*(Shown in full in the conversation; supporting files are listed with their
digests.)*

**User (the Solution Architect):** `Approved: orders package, digest 9c41, WI-001 for build.`

**SDLE:**

```
package approve --package orders --approver "A. Architect" --role "Solution Architect" --wording "Approved: orders package, digest 9c41, WI-001 for build."

  approved    yes   record 1   digest 9c41…e07a
  The approver's name is recorded, not verified.
```

> **An approval records a name it is given.** It does not prove who typed it.
> The repository's CODEOWNERS and branch protection are what give it identity.
> The ledger sits outside the package, so recording it did not change the
> digest it approves.

### Part 4 — Intake and the handoff

**User:** `Start work on WI-001.`

**SDLE:**

```
package intake --package orders --work-item WI-001

  WI-001  →  WorkItem orders-wi-001-orders   created
  bound   requirements/packages/orders/work-items/WI-001-orders/requirements.md
          requirements/packages/orders/system-context.md
```

*(The governance assessment passes, as in DR-01.)* Then:

**User:** `start workflow`

**SDLE:** *(`init` runs; the package is approved, current, and WI-001 is READY.)*

```
package_pinned   orders · WI-001 · revision 9c41…e07a · approval record 1
```

**Claude:** I am starting from the approved package. Nothing was copied:
`sdle.sh package show` and `sdle.sh requirements show` name revision 9c41 and
the Solution Architect's approval.

### Part 5 — What the engine refuses

**User:** `Start WI-002 as well.`

**SDLE:** `Refused: package_workitem_not_ready`
*(WI-002 is NOT READY because of its blocking open issue. Resolve it in the
package, re-import, re-approve.)*

**User:** *(a teammate fixes a typo in `open-issues.md` after the approval)*
`Start WI-001 in another clone.`

**SDLE:** `Refused: package_approval_stale`
*(`package show --diff` shows the one changed line. The package needs a new
approval; the first approval remains in the ledger.)*

**User:** *(back in the running WorkItem)* `continue`

**SDLE:** `Refused: package_revision_changed`
*(The package moved under a WorkItem that had already started, and the manifest
is not a file governance freshness watches. The refusal fires before anything is
written. The Solution Architect approves the new revision, `package adopt`
re-pins and audits it, and the requirements are re-assessed.)*

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `docs/source/srs.md` | unchanged throughout; its bytes are never written |
| `package-staging/orders/` | the draft, written by the orchestrator |
| `requirements/packages/orders/` | the validated package, written only by the engine |
| `.sdle/package-approvals/orders/ledger.json` | the append-only, hash-chained approval records |
| `.sdle/package-approvals/orders/revisions/<digest>/` | the approved revision, so a later diff needs no Git |
| `workitems/orders-wi-001-orders/.sdle/package-binding.json` | the revision this WorkItem started under, with its own digest |
| `workitems/orders-wi-001-orders/.sdle/audit.md` | a `package_pinned` entry at `init`, a `package_adopted` entry at adoption |

---

## Negative cases

| What is tried | What happens |
|---|---|
| A duplicate id, an id outside the grammar, a dangling reference, a requirement with no source or clarification | `Refused: package_invalid`, every offender named by rule |
| A requirement neither assigned to a work item nor excluded | `Refused: package_invalid` (`package_scope_unassigned`) |
| `init` before any approval | `Refused: package_approval_missing` |
| A package file edited after approval | `Refused: package_approval_stale` |
| A package work item marked NOT READY | `Refused: package_workitem_not_ready` |
| A package change after the WorkItem started | `Refused: package_revision_changed`, nothing written |
| A hand-edited approval ledger | exit 3 `package_approvals_invalid`, never an empty ledger |
| Replacing an approved package so that an approved id vanishes | `Refused: package_invalid` (`package_id_retired_without_successor`) |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| A well-formed package validates and imports | `tests/test_units_package_validate.py::test_a_well_formed_package_validates_and_imports` |
| A requirement with no source or clarification is refused | `tests/test_units_package_validate.py::test_as01_a_requirement_with_no_source_or_clarification_is_refused` |
| Unassigned scope is refused and named | `tests/test_units_package_validate.py::test_as02_a_requirement_neither_assigned_nor_excluded_is_refused_and_named` |
| An unwarranted supporting file is absent and explained | `tests/test_units_package_validate.py::test_as03_an_unwarranted_supporting_file_is_absent_and_explained` |
| The source document is never written | `tests/test_units_package_validate.py::test_the_source_document_is_never_written` |
| The approval is a chained record outside the package | `tests/test_units_package_approval.py::test_approval_records_who_what_and_when_in_a_chained_ledger` |
| A hand-edited ledger is an integrity failure | `tests/test_units_package_approval.py::test_a_ledger_edited_by_hand_is_an_integrity_failure_not_an_empty_one` |
| A file edited after approval makes `init` refuse | `tests/test_units_package_approval.py::test_as05_a_file_edited_after_approval_makes_init_refuse_stale` |
| A NOT READY work item is refused | `tests/test_units_package_approval.py::test_as06_a_not_ready_work_item_is_refused` |
| The developer resumes with nothing copied | `tests/test_units_package_approval.py::test_as08_the_developer_resumes_with_nothing_copied` |
| A package change after `init` stops progression before any write | `tests/test_units_package_approval.py::test_a_package_change_after_init_stops_progression_before_any_write` |
| Adopting an approved revision unblocks progression | `tests/test_units_package_approval.py::test_adopting_a_newly_approved_revision_unblocks_progression` |
| An approved id cannot silently disappear | `tests/test_units_package_approval.py::test_an_approved_id_cannot_silently_disappear` |

Result: **PASS**.
