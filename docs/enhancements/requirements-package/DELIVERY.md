# Requirements package, traceability and the implementation loop — delivery record

Three releases on branch `enh/requirements-package-loop`, cut from `1c557d1`. The decisions are ADR-016 and ADR-017; the plan, the ledger, the review rounds and every run record are in `.sdle/implementation-state/requirements-package-loop/`. This page is the short version and the list of what is **not** done.

## What shipped

| Release | What | Where it is described |
|---|---|---|
| R1 | Requirements package contract; `package import / validate / approve / show / reseal / adopt / intake`; an engine-written, hash-chained approval ledger outside the package digest; per-WorkItem package pin; the handoff refusals at `init`; `modules/requirements-package.md`; a source-fidelity mode for `sdle-requirements-review` | ADR-016, DR-23, GETTING-STARTED §11e |
| R2 | `trace check` and the `gate_spec` / `gate_tasks` / `gate_implement` preconditions (package WorkItems only); per-criterion verification dispositions with JUnit-only mapping from the report the build captured; `GATE_REVIEW_TYPES` and `review_type_mismatch`; `artifact review --findings`; tree-bound implementation evidence; the post-analyze rebaseline removed | ADR-017 §2–5, DR-24, GETTING-STARTED §11f |
| R3 | The bounded implementation loop inside `implement`: `loop begin / step / record / stop / show`, `tasks reconcile`, one completion predicate shared with the gate; the policy keys `implementation_loop_max_iterations` and `unmapped_verification_blocks` | ADR-017 §6, DR-25, GETTING-STARTED §11g |

No phase, no gate and no `state.json` field was added; `CURRENT_VERSION` is unchanged.

## Decisions that deviate from the brief (owner-approved)

- **D02**: no normalized reference package existed, so the contract was designed from the brief; `reference/SRS.docx` is a worked source example and is **not committed** (it names client staff).
- **D09**: the loop's iteration limit lives in the pinned governance policy, not `.sdle/config.json` (ADR-002 forbids lifecycle reads of config).

## Not done, and why

- **AS-30** (a real model-driven run with Spec Kit v1.0.6 through `gate_implement`) was **not** performed. See `.sdle/implementation-state/requirements-package-loop/AS-30-EVIDENCE.md` for what was verified against the real v1.0.6 templates and a real install, and what remains for a human run.
- Spec Kit honouring the "cite the source ids" instruction, and real `converge`/`implement` interacting with the task list, are **unverified** until that run.
- The brief's premise that v1.0.6 `implement` ticks tasks in tasks.md is not in the template; the loop accepts ticks regardless.
- The wider tutorials and reference pages were not rewritten. Only statements the shipped behaviour made false were corrected (the analyze rebaseline in the greenfield and defect-fix tutorials and dry run 01). Open items: the tutorials do not yet walk a package or the loop end to end; `docs/tutorials/` could take a package tutorial.
- Per-test mapping exists for JUnit XML only. No other runner format is read.
- Code locations in tasks.md remain informative; they are not validated links.
- Approver identity is recorded, not verified: protect `requirements/packages/` and `.sdle/package-approvals/` with CODEOWNERS and branch protection.
- The tree digest hashes the whole working tree on each of manifest build (twice), the gate, and loop steps: fine for ordinary repositories, noticeable for very large ones. Nothing caches it.
- Two file-symlink tests skip on a Windows account that cannot create symlinks; Linux CI runs them.
- Nothing has been pushed. The branch is local.
