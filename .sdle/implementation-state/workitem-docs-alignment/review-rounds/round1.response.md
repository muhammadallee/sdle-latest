Defects

R1-D01 — high — Concurrency boundary is narrower than the actual contamination boundary.  
Files: [GETTING-STARTED.md §11b](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/GETTING-STARTED.md:378), [workitems/README.md §1](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/workitems/README.md:22), [Reference Guide, “Branch and worktree rules”](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/SDLE-Reference-Guide.md:297).

Evidence: the pages prohibit only two WorkItems “implementing” simultaneously and claim that outside that window WorkItems do not interact. But `implementation_exclusions` deliberately keeps `requirements/` and `design/` changes in implementation evidence, and does not exclude repository-global `reviews/` or `clarifications/` ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:9906)). Meanwhile, gate artifacts include shared `.specify/memory/constitution.md` and `design/app/app-design.md` ([SKILL.md](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/SKILL.md:172)). Thus WorkItem B can contaminate A’s implementation evidence while B is in design, impact analysis, clarification, or requirements work—not only while B is implementing. Two pre-implementation WorkItems can also overwrite the same shared gate artifact.

Consequence: a reader can follow the documented rule and still present another WorkItem’s changes or artifact to a reviewer.

Correction: define the rule around the evidence window, not two `implement` phases: while a WorkItem is between `implement preflight` and completion of its security review, no other WorkItem may write non-excluded repository paths in that directory. Also replace “outside that window … without interacting” with the narrower truth: runtime records are isolated, but repository-global artifacts remain shared and require coordination or separate directories. This is also a code/accepted-decision disagreement that the ledger’s evidence rule says must be reported.

R1-D02 — high — `start workflow` cannot resume a registered WorkItem that has no lifecycle state.  
Files: [.claude/commands/sdle-start.md, steps 1–3](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/commands/sdle-start.md:6), [GETTING-STARTED.md §11](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/GETTING-STARTED.md:359), [dry-run 09](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/09-bootstrap-failures.md:31).

Evidence: for an existing unbound WorkItem, the initial `preflight` returns `requirements_unbound`, and step 1 instructs the orchestrator to stop. If the user binds manually and retries, preflight succeeds, but because there is no `state.json`, step 3 calls the situation “a new workflow,” asks for another name, and runs `workitem create`. Dry-run 09 nevertheless says the identity is reused on the next `start workflow`. The guide does not describe this state, despite being the canonical procedure.

The same prompt binds documents and only reports the result; it never asks the user which sources to bind, while the guide asserts that this decision belongs to the user.

Consequence: a legitimate, explicitly requested setup case dead-ends or attempts duplicate identity creation, and the claimed human ownership of the binding is not implemented by the shipped prompt.

Correction: add an explicit branch for “resolved WorkItem, no `state.json`”: retain that id, ask the user to select sources, bind/show them, run preflight and governance, then initialize that WorkItem. Document that path in the guide.

R1-D03 — high — Multiple tutorials and dry runs still show an impossible startup sequence.  
Files include [greenfield.md §§2–3](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/tutorials/greenfield.md:84), [defect-fix.md §2](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/tutorials/defect-fix.md:72), [hotfix.md §1](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/tutorials/hotfix.md:37), [dry-run 01](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/01-happy-path.md:56), [dry-run 05](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/05-untrusted-content-scan.md:35), and dry runs [10](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/10-brownfield-discovery.md:36), [11](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/11-iterative.md:30), [12](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/12-defect-fix.md:30), and [13](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/13-hotfix.md:30).

Evidence: greenfield shows `workitem create` followed by `governance assess`; dry runs 01 and 10 explicitly show create → preflight → assess. No bind occurs. `governance assess` calls `requirements_sources(..., strict=True)` and refuses `requirements_unbound` ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:5351)). The fixture now binds automatically ([conftest.py](D:/Learning/AI/sdle-git-repo/sdle-latest/tests/conftest.py:407)), which lets executable flow tests pass without validating the published transcript. The dry-run contract test checks numbers, known refusal names, and cited test existence—not command completeness.

Consequence: readers copying the claimed real or complete sequences stop before governance. The acceptance transcripts assert behavior their cited tests do not exercise.

Correction: add create → bind → show → preflight → scan → assess everywhere a startup is shown, or explicitly declare the WorkItem already bound and link to the canonical sequence. The candidate fixed only iterative and brownfield tutorials; its own ledger identified the remaining tutorials and dry-run 01.

R1-D04 — high — Superseded directory-wide requirements semantics remain in primary documentation.  
Files: [README.md](D:/Learning/AI/sdle-git-repo/sdle-latest/README.md:18), [README governance section](D:/Learning/AI/sdle-git-repo/sdle-latest/README.md:241), [GETTING-STARTED.md §6](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/GETTING-STARTED.md:163), [Reference Guide §12.4](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/SDLE-Reference-Guide.md:885), [SKILL.md bootstrap instructions](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/SKILL.md:275), and [dry-run 09 part 4](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/dry-runs/09-bootstrap-failures.md:115).

Evidence:

- README still says Phase 1 validates `requirements/` and that any `requirements/` change causes `governance_stale`.
- The guide says `init` and preflight require a file in that directory, although `--source` may bind any contained repository file.
- SKILL says preflight refuses when `requirements/` is absent or empty.
- The Reference Guide again says staleness follows when `requirements/` changes.
- Dry-run 09 says deleting the directory permits continuation and only a change, rather than disappearance, stales governance. Deleting a recorded source produces a missing SHA and `governance_stale`.

This also directly contradicts ADR-012 §9’s new statement that the pre-launch inventory no longer requires `requirements/`.

Consequence: readers believe unrelated files affect freshness, or that valid sources outside `requirements/` cannot be used—the behavior ADR-012 was meant to remove.

Correction: consistently say that preflight, assessment, and freshness operate on the bound file list. Present `requirements/` as the conventional location used by `--all-current`, not a universal precondition.

R1-D05 — medium — The revised refusal table and precedence claim are not accurate.  
File: [ADR-012 §8](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:108).

Evidence:

- `requirements bind` with no selector raises `requirements_binding_empty` as usage exit 2, but `--all-current` over an absent or empty directory raises the same reason as refusal exit 1 ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:8598)).
- Therefore the statement that three reasons are invariably usage errors is false.
- `requirements_primary_required` occurs only after every named source has been validated, so it is not determined “before anything about the repository is consulted.”
- Preflight exposes every accumulated item in `data.problems` but uses only the first as `reason`; it does not simply report one problem rather than every problem ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:10367)).
- A malformed binding raises integrity immediately and can pre-empt the stated Spec Kit → unbound → missing ordering.

Consequence: callers can implement the wrong exit handling and diagnostic precedence.

Correction: split `requirements_binding_empty` into its two invocation cases, remove the claim that all three usage reasons precede repository inspection, and scope the precedence statement to the accumulated preflight problems when binding validation itself succeeds.

R1-D06 — medium — “The binding changed” is broader than the implemented freshness identity, and the governance proposal cannot carry the digest.  
Files: [ADR-012 §§5, 7–8](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/architecture/ADR-012-requirements-source-binding.md:66), [iterative tutorial](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/tutorials/iterative.md:216), and the [ledger contract table](D:/Learning/AI/sdle-git-repo/sdle-latest/.sdle/implementation-state/workitem-docs-alignment/LEDGER.md:24).

Evidence: `binding_digest` hashes only the sorted source list ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:4478)). Reissuing the same binding, changing `boundAt`, or changing only the primary does not set `rebound` and does not stale governance ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:8665)). Thus “re-binding … immediately makes the assessment stale” and “the binding itself changed” are over-broad.

ADR-012’s lifecycle says the governance proposal “carries the binding digest,” but its input schema permits exactly four top-level fields and rejects unknown ones ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:4652)). The engine adds `bindingDigest` to the governance record during assessment.

Consequence: readers misunderstand what `rebound` means and where the traceability digest is introduced.

Correction: use “the bound source set changed” throughout. Say the proposal is prepared from the bound sources and `governance assess` writes their binding digest into the resulting record.

R1-D07 — low — Project-name inference is still described incompletely and incorrectly.  
Files: [GETTING-STARTED.md §11](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/GETTING-STARTED.md:363), [SKILL.md](D:/Learning/AI/sdle-git-repo/sdle-latest/.claude/skills/sdle/SKILL.md:307), and [Reference Guide Appendix B](D:/Learning/AI/sdle-git-repo/sdle-latest/docs/SDLE-Reference-Guide.md:1168).

Evidence: the implemented order is explicit `init --project`, then the first `#` heading in the binding’s primary source only, then WorkItem title, then project-root directory name ([sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:1585), [sdle.py](D:/Learning/AI/sdle-git-repo/sdle-latest/scripts/sdle.py:1651)). The Reference Guide instead ends with “asked of the user,” and SKILL does not identify the primary source.

Consequence: users cannot predict the name when the primary is headingless or `--project` is supplied.

Correction: document the exact four-step fallback chain once and refer to it elsewhere.

R1-D08 — medium — The committed implementation-state record does not describe the candidate.  
Files: candidate object `.sdle/implementation-state/workitem-docs-alignment/STATE.json` and [LEDGER.md](D:/Learning/AI/sdle-git-repo/sdle-latest/.sdle/implementation-state/workitem-docs-alignment/LEDGER.md:1).

Evidence: at `cdf8316`, `STATE.json` still says `current_sha: 369ff96`, phase P1 planned, no completed phases, all original drift open, review not started, and verification not started. The ledger’s phase log is empty. It classifies 12 files as UPDATE, including defect-fix, hotfix, greenfield, dry-runs 01 and 09, but none of those files changed in `369ff96..cdf8316`. It also does not provide the claimed file-by-file inventory of 154 files; it gives grouped summaries.

Consequence: the audit record cannot be used to establish what was fixed, verified, or intentionally retained at the frozen candidate.

Correction: commit the final state for the frozen SHA, append the phase log, enumerate each affected file with its final disposition, and reconcile the UPDATE list with the actual diff.

Preferences

P1 — no finding. Keeping GETTING-STARTED as the only installation recipe is reasonable. README and the tutorial index point to it, and the documented-command test enforces that the Spec Kit installation command is taught only there. The defects above concern the guide’s lifecycle coverage, not its canonical status.

Questions

R1-Q01 — The current checkout is not in the packet’s stated state. `HEAD` is `cdf8316`, but `STATE.json` is tracked-modified and `runs/` is untracked in addition to the declared plan file. Is that post-candidate material intended for round 2, or was it meant to be part of this candidate?

R1-Q02 — The available `runs/` directory contains only `binding-scenarios.txt` and `guide-replay.txt`. It does not contain the asserted documentation-check logs or a full-suite result. I did not run pytest because it writes disposable test directories; the round-2 packet should identify the frozen SHA and include the completed result.

No: this documentation is not yet an accurate description of the implementation. The single most valuable thing missing is an executable startup contract covering both a fresh repository and a pre-created WorkItem without `state.json`, asserting the complete create-or-reuse → user-selected bind → show/scan → preflight → assess → init sequence; that one check would expose most of the remaining tutorial, dry-run, prompt, and setup defects.