# Round 1 reply — dispositions, changes, and a request for closure

All eight defects **accepted**, none disputed. Both questions conceded. Three further defects were
found while verifying yours; they are listed at the end because you should judge whether the fixes for
them are right, not only the fixes for yours.

I did not take D-05, D-06 or D-07 on your word. Each was driven through the running CLI before I wrote
anything down, and **all six of your factual claims held**. The probe and its output are at
`.sdle/implementation-state/workitem-docs-alignment/runs/adr012-refusal-verification.txt`.

---

## Dispositions

### R1-D01 (high) — concurrency boundary — ACCEPTED, and your correction was itself too narrow

You were right that "outside that window … without interacting" is wrong and that the window is about
what other WorkItems *write*, not what phase they are in. Fixed in `docs/workitems/README.md`,
`docs/GETTING-STARTED.md` §11b and `docs/SDLE-Reference-Guide.md`.

But my first fix enumerated the exclusion as "runtimes, the registry, `.sdle/`, `.specify/`, this
WorkItem's feature directory", and that understates it. Reading `implementation_exclusions` in
`scripts/sdle.py`, the list also removes **every other WorkItem's entire tree** (`workitems/<other>/`),
not merely their runtimes — that is what F-102 did. So a second WorkItem working inside its own
directory is genuinely invisible to the first one's evidence.

What is actually shared, and therefore contaminating, is the **repository-level** set:
`requirements/`, `design/`, `reviews/` and `clarifications/` sit at the repository root and are
deliberately kept in the change set because they are real implementation inputs and outputs. The three
documents now carry a table of excluded vs not-excluded, read from the function rather than from
memory, and say the shared-path overwrite outside the window is a known limitation that the binding
does not address.

Please check that table against the engine. If the "every other WorkItem's whole tree" reading is
wrong, the correction is worse than the original.

### R1-D02 (high) — resuming a registered WorkItem with no state — ACCEPTED

`.claude/commands/sdle-start.md` gains **step 2b**. Step 1 now routes `requirements_unbound` to it
explicitly, because that refusal means a WorkItem *did* resolve. Step 3's `workitem create` would have
refused `workitem_exists`, exactly as you said.

I verified the premise rather than assuming it: `cmd_reset` unlinks `state_file`, `audit_file` and
`lock_file` and nothing else, so a reset WorkItem lands in precisely this state.

On the binding being chosen without asking — accepted, and it was the more serious half. Both
`sdle-start.md` and `SKILL.md` now require listing what is under `requirements/`, asking the user which
documents this WorkItem is about, offering "all of them" as an answer, and asking which is primary when
several are bound. `GETTING-STARTED.md` §11 step 3 is rewritten to say **you** are asked, and gains a
three-situation table (fresh project / existing project / registered WorkItem with no lifecycle state).

### R1-D03 (high) — tutorials and dry runs — ACCEPTED

Bind step added to `greenfield.md`, `defect-fix.md`, `hotfix.md` and `greenfield-full-tour.md`.
`requirements bind` added to the engine-call annotations in dry runs 01, 05, 10, 11, 12 and 13.

Dry runs 12 and 13 said "WorkItem created: `<id>`. Preflight passed." with nothing bound, which cannot
happen; both now name the bound document and carry an annotation.

I used each tutorial's *actual* WorkItem id (`movement-order`, `cross-warehouse-disclosure`) rather
than inventing one from the title, since the ids appear in later JSON in the same file.

Your point that the conftest fixture auto-binds, so the suite cannot catch this, is correct and I have
not tried to fix it — it is a test-design change, outside a documentation pass. Flagging it rather than
silently leaving it: if you think it should be in scope, say so in round 2.

### R1-D04 (high) — directory-wide semantics — ACCEPTED

`README.md` (phase-1 row, the `governance_stale` sentence, the tree comment), `GETTING-STARTED.md` §6,
`SKILL.md` and dry-run 09's "I found requirements/" all corrected. `SKILL.md` and `GETTING-STARTED.md`
now state that a bound source may be **any file in the repository** and that `requirements/` is the
conventional home and the place `--all-current` looks.

The Reference Guide's `governance_stale` sentence was the same defect and you did not cite it; it now
distinguishes the three facts the record actually carries (content moved, `rebound`,
`assessed_without_a_binding`).

### R1-D05 (medium) — refusal table — ACCEPTED, VERIFIED

Every one of your four claims reproduced:

| Claim | Observed |
|---|---|
| `requirements_binding_empty` has two codes | exit **2** with no selector; exit **1** for `--all-current` over an empty directory |
| `requirements_primary_required` comes after source validation | two sources, one missing, no `--primary` → `requirements_source_missing` **exit 1**, not the primary refusal |
| preflight exposes all problems | `reason: speckit_missing` with `data.problems: ["speckit_missing", "requirements_unbound"]` |
| a malformed binding pre-empts the ordering | `preflight` with an unparseable `requirements.json` and no Spec Kit → **exit 3** `requirements_binding_invalid` |

ADR-012 §8 rewritten accordingly. The "three are usage errors … before anything about the repository is
consulted" framing is gone — it was the sentence that made the ordering claim wrong.

### R1-D06 (medium) — `rebound` and the proposal digest — ACCEPTED, VERIFIED

`binding_digest` hashes `sorted(sources)` alone, so: identical set + same primary → `rebound: false`;
identical set + **different** primary → `rebound: false`; different set → `rebound: true`. §5's
"re-binding … immediately makes the assessment stale" is replaced by a table of what does and does not
stale a record, and the different-primary case is called out as the trap it is.

On §7: a 5th top-level key in the proposal is refused `governance_input_malformed`, confirmed, so the
proposal cannot carry the digest even in principle. §7 now says the engine reads the binding itself and
writes `requirements.{sources,digest,bindingDigest}` into the record — which is what makes it evidence
rather than a claim.

### R1-D07 (low) — project-name chain — ACCEPTED, VERIFIED

`args.project or infer_project_name(paths) or metadata.title or project_root.name`. Stated identically
in ADR-012 §7, `README.md`, `SKILL.md`, `GETTING-STARTED.md` and the Reference Guide. The Reference
Guide's `project_name` row said "else asked of the user", which never happens.

### R1-D08 (medium) — records — ACCEPTED

`STATE.json` now describes the candidate, including the fact that it is a commit **plus** a working-tree
delta. `LEDGER.md` gains a per-file inventory (all 37 rows, not four grouped counts), a phase log with
commits and verification per phase, and a dispositions table.

### R1-Q01 — CONCEDED

You are right and it was my error. The round-1 packet said "clean of tracked modifications". It was
not: `STATE.json` was modified and `runs/` was untracked. The round-2 packet will state the candidate as
a commit plus an explicit working-tree delta, and the fixes are committed before it is sent so
`git diff` shows you the reviewed state.

### R1-Q02 — ADDRESSED

`runs/` now also holds `adr012-refusal-verification.txt`, `deleted-bound-source.txt` and the full-suite
result.

---

## Three defects I found while verifying yours

Judge these as you would your own findings.

**D-09 (high)** — `docs/dry-runs/09-bootstrap-failures.md` Part 4 taught that deleting `requirements/`
mid-workflow is "a warning, not a halt … the approved constitution and specification already capture
the requirements, so the workflow can continue". Driven through the CLI: at `constitution_draft`, after
unlinking the bound document, `advance` refuses **`governance_stale` exit 1** and the phase does not
move. A bound document that is gone is recorded with a `null` SHA, so the sources digest moves.
`governance_precondition` runs on every `advance`, at every phase. Evidence:
`runs/deleted-bound-source.txt`. Part 4 rewritten; a negative-case row added.

**D-10 (medium)** — `docs/troubleshooting/README.md` is chartered by CLAUDE.md's documentation-set table
as "every refusal a user can hit, and the intended way out", and had **no** section for the binding
family. Eight reasons were undocumented there. New §16 added with the exit codes from the probe.

I had marked that file VERIFIED CURRENT on a keyword scan, which found nothing wrong in it and so
missed what was absent. A scan for drift does not find a gap. I then asked the same absence question of
the rest of the VERIFIED CURRENT list and found two more: `CLAUDE.md`'s runtime-state paragraph
enumerated the WorkItem runtime's files and omitted `requirements.json`, the one file ADR-012 added; and
`docs/brownfield/README.md` said nothing about binding, leaving open whether brownfield is exempt (it is
not) and whether `discovery assess` reads the bound set (it does not — tracing every caller of
`bound_sources` gives `preflight`, `governance assess` and `init`). Both corrected.

**D-11 (medium)** — `docs/SDLE-Reference-Guide.md` attributed the Untrusted Content Scan to `preflight`.
`cmd_preflight` contains no call to `scan_text`. `scan` is a separate command taking `--path` that scans
exactly the file it is given, and it is the **orchestrator** — a SKILL.md instruction, not an engine
guarantee — that invokes it once per bound document. Corrected, with the guarantee/convention split
stated explicitly, since this repository draws that line carefully elsewhere (ADR-007 §3).

---

## Verification after the changes

| Check | Result |
|---|---|
| `python scripts/sdle.py lint-skill` | PASS |
| `pytest tests/test_dry_run_contracts.py` | PASS — 118 |
| `pytest tests/test_units_documented_commands.py tests/test_units_invariants.py` | PASS — 935 |
| Guide replay into an empty target (13 blocks) | PASS — exit 0, inventory matched, `workitems/` absent |
| Binding scenarios through the real CLI (7) | PASS |
| ADR-012 refusal probe (7 claim groups) | PASS — every claim reproduced |
| Deleted-bound-source probe | PASS — `governance_stale` exit 1 confirmed |
| Full suite | **NOT_RUN** — see below |

**The full suite is NOT_RUN, and I am not claiming otherwise.** Two attempts
produced no result that describes this candidate. The first began before the
last six edits of this pass, so it was measuring a tree that changed underneath
it, and I killed it rather than quote it. The second, against the committed
tree, was stopped by the harness at roughly 4% because the system ran critically
low on memory while the session was idle — not a test failure, and the harness
asks that it not be restarted unattended. No failure appeared in the part that
ran, which is not evidence of a pass. Recorded at
`runs/full-suite-NOT_RUN.txt`. Treat every claim in this reply as resting on the
seven checks above, not on the suite.

---

## What I am asking for

For each of R1-D01 … R1-D08: **confirm closure, or explain the remaining objection.** For R1-D01
specifically, please check my exclusion table against `implementation_exclusions` rather than against
my prose — I got that enumeration wrong once already.

For D-09, D-10 and D-11: these are my findings and my fixes, so they have had no independent review at
all. Treat them as the least-trustworthy part of this diff.

And the standing question: name anything still describing superseded behaviour, and anything I have
asserted that the evidence does not support.
