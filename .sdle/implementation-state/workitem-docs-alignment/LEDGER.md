# Documentation alignment — WorkItem binding, isolation and setup

## Baseline

Repository `D:/Learning/AI/sdle-git-repo/sdle-latest`. Working branch
**`docs/alignment-binding-and-isolation`**, cut from `main` at
**`369ff96336e0f068833ec1a77ecdf7b18c3e94c2`** on 2026-09-22.

Working tree at start: clean of tracked modifications. One pre-existing untracked file,
`plan-claude-codex-defectfix.md`, which is the owner's and is **preserved untouched**.

The implementation this pass documents is the merge `cb9a183..369ff96` (30 files, +1546/−130):
F-102 (cross-WorkItem evidence isolation), F-101/ADR-012 (requirements source binding) and F-103
(the concurrency boundary). Accepted decisions: ADR-010, ADR-011, ADR-012 including its §10
amendments, and the owner's F-103 option 1.

**Evidence rule for this pass.** The engine and its tests are the authority. Existing prose — including
prose written during the implementation itself — is an input to check, never proof. Where a document
and the code disagree, the document is the defect; where the *code* and an accepted decision disagree,
that is reported, not reconciled by choosing the convenient reading.

## Contracts read from the engine, not from prose

| Fact | Source | Value |
|---|---|---|
| Binding commands | `build_parser` | `requirements bind` (`--source` repeatable, `--all-current`, `--primary`), `requirements show` |
| Refusals | `scripts/sdle.py` | `requirements_unbound`, `requirements_source_missing`, `requirements_source_invalid`, `requirements_source_duplicate`, `requirements_binding_empty`, `requirements_binding_ambiguous`, `requirements_primary_required`, `requirements_binding_invalid` (integrity) |
| Primary | `cmd_requirements_bind` | Inferred only when exactly one source is bound; **required** for more than one |
| `--all-current` | `cmd_requirements_bind` | Expands `requirements/` to an exact file list at that moment; never re-expanded |
| Freshness | `governance_freshness` | Three distinct facts: bound documents' contents changed; the binding itself changed (`rebound`); the record predates any binding (`assessed_without_a_binding`) |
| Preflight report | `cmd_preflight` | `data.requirements` is the **bound** set as repository-relative paths |
| Evidence isolation | `implementation_exclusions` | Other registered WorkItems' trees and `workitems/index.md`; **not** application code |

## Inventory and disposition

154 tracked candidate files surveyed; 37 mention an affected contract. Every one of the 37 carries
its own row — a grouped count cannot be audited, which is what Codex R1-D08 objected to.

**UPDATE** — changed in this pass:

| File | Contract it described wrongly | Round |
|---|---|---|
| `docs/tutorials/iterative.md` | F-101 taught as intended: digest covers the directory | R0 (D-01) |
| `scripts/sdle.py` (`--primary` help only) | "(default: the first)" vs `requirements_primary_required` | R0 (D-02) |
| `docs/architecture/ADR-012-requirements-source-binding.md` | §8 refusals; §5 staleness; §7 digest provenance and the project-name chain | R0 (D-03), R1 (D-05/D-06/D-07) |
| `docs/workitems/README.md` | "branch or worktree"; the contamination window's real boundary | R0 (D-04), R1 (D-01) |
| `docs/GETTING-STARTED.md` | "branch or worktree"; §6 directory semantics; who chooses the binding; the three starting situations; the project-name chain | R0 (D-04), R1 (D-01/D-02/D-04/D-07) |
| `docs/SDLE-Reference-Guide.md` | Branch/worktree rules; `governance_stale` as a directory fact; preflight "infers a project name"; the `project_name` row | R0 (D-07), R1 (D-01/D-04/D-07) |
| `docs/tutorials/brownfield-discovery.md` | No binding step between create and assess | R0 (D-06) |
| `docs/tutorials/greenfield.md` | No binding step; "a directory with at least one document in it" | R0 (D-06), R1 (D-03/D-04) |
| `docs/tutorials/defect-fix.md` | No binding step | R1 (D-03) |
| `docs/tutorials/hotfix.md` | No binding step | R1 (D-03) |
| `docs/tutorials/greenfield-full-tour.md` | No binding step; implied a knob could relax it | R1 (D-03) |
| `docs/dry-runs/01-happy-path.md` | Engine-call annotation skipped `requirements bind` | R0 (D-05), R1 (D-03) |
| `docs/dry-runs/05-untrusted-content-scan.md` | Same; scan reads bound sources, so order matters | R1 (D-03) |
| `docs/dry-runs/09-bootstrap-failures.md` | "I found requirements/"; Part 4's "a warning, not a halt" | R0, R1 (D-09, found by me) |
| `docs/dry-runs/10-brownfield-discovery.md` | Annotation skipped binding | R1 (D-03) |
| `docs/dry-runs/11-iterative.md` | Annotation skipped create and binding | R1 (D-03) |
| `docs/dry-runs/12-defect-fix.md` | "WorkItem created … Preflight passed" with nothing bound | R1 (D-03) |
| `docs/dry-runs/13-hotfix.md` | Same | R1 (D-03) |
| `README.md` | Phase-1 row "Validates requirements/"; `governance_stale` as a directory fact; `project_name` row | R1 (D-04/D-07) |
| `.claude/skills/sdle/SKILL.md` | Bound source restricted to `requirements/`; binding chosen without the user; project-name chain | R1 (D-02/D-04/D-07) |
| `.claude/commands/sdle-start.md` | No branch for a registered WorkItem with no state; binding without asking | R1 (D-02) |
| `docs/troubleshooting/README.md` | Claims to cover every refusal; had **no** section for the nine binding refusals | R1 (D-10, found by me) |
| `CLAUDE.md` | Runtime-state paragraph listed the WorkItem runtime's files and omitted `requirements.json` | R1 (found by me) |
| `docs/brownfield/README.md` | Silent on whether a brownfield WorkItem binds, and on whether discovery reads the binding | R1 (found by me) |

**VERIFIED CURRENT** — inspected against the engine this pass and correct as written (16):
`CLAUDE.md`; `docs/README.md`; `docs/lifecycle/README.md`; `docs/risk-and-gates/README.md`;
`docs/spec-kit-integration/README.md`; `docs/tutorials/README.md`; `docs/dry-runs/README.md`;
`scripts/README.md`; `docs/architecture/` ADR-001, -002, -004, -005, -007, -011. Each was re-read for
what is *absent* as well as what is wrong, after D-10 showed a keyword scan cannot find a gap.

**RETAINED HISTORICAL** — deliberately not rewritten (4):
`.sdle/implementation-state/repository-cleanup/**`; `.sdle/implementation-state/workitem-isolation/**`;
`docs/dry-runs/verification-matrix.md` recorded run rows; ADR-003/-006/-008/-009/-010 bodies recording
superseded decisions, which keep their existing supersession notes.

Historical records are **not** rewritten to resemble current behaviour.

## Drift found, before any edit

| ID | Severity | Where | What is wrong |
|---|---|---|---|
| D-01 | high | `docs/tutorials/iterative.md` §"requirements lists both documents" | Teaches F-101 **as intended behaviour**: "the requirements directory is repository-level and accumulates… the digest covers the directory as it now stands… an edit to an *old* requirement document makes the *current* WorkItem's governance stale. That is intended." Exactly the defect ADR-012 fixed |
| D-02 | high | `scripts/sdle.py` `--primary` help | Ships "(default: the first)". Binding more than one source without `--primary` now refuses `requirements_primary_required`. Shipped CLI help contradicting shipped behaviour |
| D-03 | medium | `docs/architecture/ADR-012-*.md` §8 | Refusal table omits `requirements_binding_invalid` and `requirements_binding_ambiguous` |
| D-04 | medium | `docs/workitems/README.md`, `docs/GETTING-STARTED.md` §11b | "branch or Git worktree" is ambiguous: two branch names in one working directory are not two workspaces. Only a separate working directory gives simultaneous isolation. Wording I wrote myself during F-103 |
| D-05 | medium | `docs/dry-runs/01-happy-path.md` | Transcript shows glob-era startup: "I found requirements/:" with no binding step; preflight line predates the bound-set report |
| D-06 | medium | tutorials `defect-fix`, `hotfix`, `brownfield-discovery`, `iterative` | None shows the binding step, so four of five flow tutorials describe a startup sequence that now refuses `requirements_unbound` |
| D-07 | low | `docs/SDLE-Reference-Guide.md` §"Branch and worktree rules" | States one active WorkItem per branch *or* worktree without the implement-window boundary, and shares D-04's conflation |

## Phase plan

**P1 — the contracts that are simply wrong** (D-01, D-02, D-03).
Files: `docs/tutorials/iterative.md`, `scripts/sdle.py` (help text), `docs/architecture/ADR-012-*.md`.
Acceptance: `requirements bind --help` matches behaviour; ADR-012 §8 lists every refusal the engine
raises; the iterative tutorial describes bound-set freshness. Risk: ADR-012 is an accepted decision —
§8 is corrected as an omission, and §10 already records the primary change, so no decision is rewritten.

**P2 — the concurrency wording** (D-04, D-07).
Files: `docs/workitems/README.md`, `docs/GETTING-STARTED.md`, `docs/SDLE-Reference-Guide.md`.
Acceptance: every statement says *separate working directory*, names worktree or clone, and scopes the
rule to the implement→security-review window. Risk: must not overstate — outside that window there is
no constraint.

**P3 — the startup sequence everywhere** (D-05, D-06).
Files: four tutorials, `docs/dry-runs/01-happy-path.md`, and any dry run whose transcript shows startup.
Acceptance: every startup sequence shows binding between `workitem create` and `preflight`; tutorials
link to the canonical guide rather than restating it.

**P4 — verification.** Documentation checks, a guide-alone replay in a disposable target, focused
binding scenarios driven through the real CLI, and the full suite.

**P5/P6 — Codex rounds 1 and 2**, each with a frozen candidate, findings, dispositions and a reply.

## Phase log

| Phase | Commit | What landed | Verification |
|---|---|---|---|
| P0 baseline + inventory | `0cf995c` | Baseline recorded at `369ff96`; 154 files surveyed; D-01..D-07 opened; plan written | `git status` clean of unrelated work; `plan-claude-codex-defectfix.md` recorded as the owner's, untouched |
| P1 wrong contracts | `9dc1f7f` | D-01 (iterative tutorial), D-02 (`--primary` help), D-03 (ADR-012 §8 first pass) | `requirements bind --help` read back from the CLI; `lint-skill` PASS |
| P2 branch ≠ workspace | `9dc1f7f` | D-04, D-07 across `docs/workitems/README.md`, GETTING-STARTED §11b, Reference Guide | `p2_concurrency.py`; `implementation_exclusions` read from the engine |
| P3 exit codes + binding step | `cdf8316` | ADR-012 §8 exit codes and precedence; bind step in the iterative and brownfield tutorials | `probe_exits.py` against the running CLI; `binding-scenarios.txt` (7 scenarios); `guide-replay.txt` |
| P4 verification | (in `cdf8316`) | Doc checks, guide replay, binding scenarios | `lint-skill` PASS; `test_dry_run_contracts.py` PASS |
| P5 review round 1 | candidate `cdf8316` + 3 uncommitted paths | Codex returned 8 defects and 2 questions; all 8 accepted; D-09 found by me while verifying D-04 | `adr012-refusal-verification.txt` (6/6 Codex claims confirmed); `deleted-bound-source.txt` (D-09 confirmed) |
| P5 round-1 fixes | working tree at `cdf8316` | R1-D01..D08 + D-09 implemented across 21 files | `lint-skill` PASS; `test_dry_run_contracts.py` 118 PASS; documented-commands + invariants 935 PASS; guide replay exit 0; full suite recorded below |
| P5 round-1 fixes | `b83cf4a`, `44c5d24` | R1-D01..D08 plus D-09/D-10/D-11 found while verifying | lint PASS; contracts 118; units 935; guide replay exit 0 |
| P6 sweep | `ecb749c`, `7da1f6c` | D-12 found sweeping documents neither round had opened; round-2 packet | lint PASS |
| P6 review round 2 | candidate `bd56045` | Codex returned 9 defects, 3 preferences, 0 questions. All 9 accepted, all 3 adopted, none disputed | `runs/probe` reproduced 9 of 9 reviewer claims |
| P6 round-2 fixes | `a669b03` + this record | R2-D01..D09, R2-P01..P03, tutorials made runnable, records frozen | lint PASS; contracts 118; **1124** across four modules; full suite NOT_RUN (OPEN-03) |

## Round 1 dispositions

Every finding **accepted**. Nothing was disputed, and R1-D05/D06/D07 were re-verified against the
running CLI before being written down rather than taken on the reviewer's word — the probe and its
output are at `runs/adr012-refusal-verification.txt`, and all six claims held.

| ID | Sev | Disposition | What was done |
|---|---|---|---|
| R1-D01 | high | Accepted | Boundary restated as "what other WorkItems **write**", naming `requirements/`, `design/`, `reviews/`, `clarifications/` as deliberately un-excluded, in `docs/workitems/README.md`, GETTING-STARTED and the Reference Guide. The "outside that window … without interacting" over-claim is gone; shared repository-level paths are now named as a known limitation |
| R1-D02 | high | Accepted | `sdle-start.md` gains step 2b (a registered WorkItem with no `state.json` — verified: `reset` deletes `state.json`, `audit.md` and `lock`, leaving exactly that), and the binding paragraph now requires asking the user. GETTING-STARTED gains a three-situation table |
| R1-D03 | high | Accepted | Bind step added to greenfield, defect-fix, hotfix and the full tour; `requirements bind` added to the engine-call annotations in dry runs 01, 05, 10, 11, 12, 13 |
| R1-D04 | high | Accepted | Directory-wide semantics removed from `README.md` (phase row, `governance_stale`, tree comment), GETTING-STARTED §6, SKILL.md, the Reference Guide and dry-run 09 |
| R1-D05 | med | Accepted, **verified** | ADR-012 §8 rewritten: `requirements_binding_empty` carries exit 2 *and* exit 1; `requirements_primary_required` is exit 2 but raised **after** source validation; `data.problems` lists every problem while `reason` names one; `requirements_binding_invalid` (exit 3) pre-empts the ordering |
| R1-D06 | med | Accepted, **verified** | ADR-012 §5 gains a table of what does and does not stale a record — re-binding the *same set* with a different primary returns `rebound: false`, confirmed. §7 no longer claims the proposal carries the digest: a 5th top-level key is refused `governance_input_malformed`, so the engine writes it |
| R1-D07 | low | Accepted, **verified** | Full chain (`--project` → primary's first `#` → WorkItem title → project-root dir name) stated in ADR-012 §7, README, SKILL.md, GETTING-STARTED and the Reference Guide. Also fixed: the Reference Guide claimed `preflight` infers a name — `infer_project_name` has exactly one caller, `cmd_init` |
| R1-D08 | med | Accepted | This ledger: file-by-file inventory, phase log, dispositions. `STATE.json` now describes the candidate |
| R1-Q01 | — | Conceded | The round-1 packet said "clean of tracked modifications". It was not: `STATE.json` was modified and `runs/` and `plan-claude-codex-defectfix.md` were untracked. The round-2 packet states the candidate as commit **plus** working-tree delta |
| R1-Q02 | — | Addressed | `runs/` now holds `adr012-refusal-verification.txt`, `deleted-bound-source.txt` and the full-suite result alongside the earlier two |

### Found while verifying, not reported by Codex

**D-09 (high)** — `docs/dry-runs/09-bootstrap-failures.md` Part 4 taught that deleting `requirements/`
mid-workflow is "a warning, not a halt … the workflow can continue". Driven through the real CLI, an
`advance` after a bound document is deleted refuses **`governance_stale` (exit 1)** and the phase does
not move: a bound document that is gone hashes to nothing, so the sources digest moves. Evidence:
`runs/deleted-bound-source.txt`. Part 4 rewritten, and a negative-case row added.

**D-10 (medium)** — `docs/troubleshooting/README.md` is the document CLAUDE.md's documentation-set table
charters as "every refusal a user can hit, and the intended way out". It had no section for the binding
family at all: `requirements_unbound`, `requirements_binding_empty` (both exit codes),
`requirements_binding_ambiguous`, `requirements_primary_required`, `requirements_source_missing`,
`requirements_source_invalid`, `requirements_source_duplicate` and `requirements_binding_invalid` were
undocumented there. I had marked the file VERIFIED CURRENT on a keyword scan, which found nothing
*wrong* in it and so missed what was *absent* — a scan for drift does not find a gap. Section 16 added,
with the exit codes from `runs/adr012-refusal-verification.txt`, and the file moved to UPDATE.

**D-11 (medium)** — `docs/SDLE-Reference-Guide.md` attributed the Untrusted Content Scan to `preflight`
("runs the Untrusted Content Scan on each bound file"). `cmd_preflight` contains no call to `scan_text`;
`scan` is a separate command taking `--path` that scans exactly the file it is given, and it is the
orchestrator — a prompt-file instruction in SKILL.md, not an engine guarantee — that invokes it once per
bound document. A caller driving the engine directly gets no scan unless it asks. Corrected, and the
guarantee/convention split stated, because that split is the kind of thing this repository documents
explicitly elsewhere (ADR-007 §3) and should not blur here.

**Two further gaps found by asking the D-10 question of the rest of the VERIFIED CURRENT list:**
`CLAUDE.md`'s runtime-state paragraph enumerated the WorkItem runtime's files and omitted
`requirements.json`, the binding itself — the one file ADR-012 added. `docs/brownfield/README.md` said
nothing about binding at all, leaving open whether a brownfield WorkItem is exempt (it is not) and
whether `discovery assess` reads the bound set (it does not — discovery reads the repository, and the
binding's consumers are `preflight`, `governance assess` and `init`, verified by tracing every caller of
`bound_sources`). Both corrected.

**Two exit codes in the new troubleshooting §16 were carried from ADR-012 prose rather than measured** —
`requirements_binding_ambiguous` and `requirements_source_duplicate` — which is the exact failure mode
R1-D05 caught. Both have since been driven through the CLI (claim 7 in
`runs/adr012-refusal-verification.txt`): exit 2 and exit 1 respectively, as written.

**The exclusion enumeration was wrong in my first R1-D01 fix** and is corrected in the same pass. I
wrote "runtimes, the registry, `.sdle/`, `.specify/`, this WorkItem's feature directory", which
understates it: `implementation_exclusions` also removes **every other WorkItem's entire tree**, not
merely their runtimes (F-102). That materially narrows the contamination claim — a second WorkItem
working inside `workitems/<its-id>/` is genuinely invisible. What remains shared is the
repository-level set (`requirements/`, `design/`, `reviews/`, `clarifications/`), and that is what the
three documents now say.

**D-12 (medium)** — found sweeping the documents neither round had opened. SDLE carries **two** path
lists that disagree on purpose, and nothing said so. `SDLE_OWNED_PREFIXES` (`scripts/sdle.py`) filters
`implement preflight`'s dirty-tree check and *includes* `requirements/`, `design/`, `reviews/`,
`clarifications/` and `guidance/`; `implementation_exclusions` drives Gate 7's manifest and the
security-review evidence and deliberately *excludes* them — the engine's own comment says choosing
`SDLE_OWNED_PREFIXES` there "would silently drop requirements/ and design/ edits from the manifest".

So an uncommitted design does not block entry to the implement phase but does appear in the evidence at
the end of it. Until you know both lists exist, the two behaviours read as a contradiction, and it is
exactly the asymmetry the R1-D01 concurrency story rests on: a clean tree at `implement preflight` is
not a promise that nobody else's artifacts will land in your evidence. Documented in
`docs/workitems/README.md` beside the exclusion table.

Also checked in the same sweep and found **accurate**: `docs/dry-runs/06-secrets-and-dirty-tree.md`
enumerates `SDLE_OWNED_PREFIXES` exactly as the tuple declares it, and `docs/lifecycle/`,
`docs/risk-and-gates/`, `docs/spec-kit-integration/` and dry runs 02, 03, 04, 07, 08, 14, 15 and 16
carry no claim about the requirements directory, the binding or the isolation boundary at all.

## Round 2 — summary

Nine defects, three preferences, no questions, against `bd56045`. **All nine accepted, none disputed**;
all three preferences adopted. Every factual claim re-verified against the running CLI before being
written down: **9 of 9 held**, as 6 of 6 did in round 1. Full dispositions at
`review-rounds/round2.dispositions.md`; Codex's response verbatim at `review-rounds/round2.response.md`.

The finding that matters most is **R2-D06**, because it was mine: troubleshooting §16, which I added in
round 1, told users to delete `workitems/<id>/.sdle/requirements.json` by hand. That is an invariant-6
violation, it is what the write fence exists to prevent, and it was unnecessary — `requirements bind`
replaces a corrupt binding deliberately. A round-1 fix introduced a worse defect than the gap it closed,
which is the argument for the second round existing at all.

**Three items go to the owner** rather than being resolved here: OPEN-01 (should `accept content` work
before `init`? — an engine change), OPEN-02 (the conftest fixture auto-binds, so the suite cannot catch
a missing bind step — a test-design change), OPEN-03 (the full suite is NOT_RUN after three attempts,
two stopped by the harness memory reaper). None is a disagreement; Codex and I agree on all three.

**On my own method.** Two findings across the two rounds came from asking what a document *omits*
rather than what it states wrongly — D-10 and D-12 — and a keyword scan finds neither. Two more came
from checking a claim I had already written down: my exclusion enumeration in round 1 and my diff sizes
in round 2 were both wrong in the same way, stated from memory of a measurement rather than from the
measurement. Codex caught the second; I caught the first.
