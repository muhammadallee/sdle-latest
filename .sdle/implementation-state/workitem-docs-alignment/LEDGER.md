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

154 tracked candidate files surveyed; 37 mention an affected contract. Dispositions:

| Disposition | Count | Files |
|---|---|---|
| **UPDATE** | 12 | `docs/tutorials/iterative.md`, `defect-fix.md`, `hotfix.md`, `brownfield-discovery.md`, `greenfield.md`; `docs/dry-runs/01-happy-path.md`, `09-bootstrap-failures.md`; `docs/SDLE-Reference-Guide.md`; `docs/workitems/README.md`; `docs/GETTING-STARTED.md`; `docs/architecture/ADR-012-*.md`; `scripts/sdle.py` (CLI help string only) |
| **VERIFIED CURRENT** | 21 | The remaining ADRs, `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/lifecycle/`, `docs/troubleshooting/`, `scripts/README.md`, the prompt files already corrected by the implementation, and the dry runs whose "setup recipe" hit is an unrelated `preflight` mention |
| **RETAINED HISTORICAL** | 4 | `.sdle/implementation-state/repository-cleanup/**`, `.sdle/implementation-state/workitem-isolation/**`, `docs/dry-runs/verification-matrix.md` run rows, ADR bodies recording superseded decisions |

Historical records are **not** rewritten to resemble current behaviour. ADR-004, -005 and -008 keep
their recorded decisions and their existing supersession notes.

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

_Appended as each phase completes._
