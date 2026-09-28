# Requirements Refinement Loop — implementation plan

Baseline: `fca6c00` (branch `feat/requirements-refinement`), CI green on all four cells
(`36374476221`). Stage 0's closure changed the engine materially since the brief was written at
`48a853a`: `governance assess` now re-scans bound sources itself and can refuse
`governance_content_unacknowledged`, and a new pre-init record (`scan-acknowledgements.json`) and
command surface (`accept-content --path`) exist. Every fact below is re-verified against `fca6c00`, not
assumed from the brief.

## 1. §1 re-verification, corrected

All facts F1–F14 hold as originally stated **except**:

- **F5 (partial, per O1).** Governance is enforced at `advance`/`gate approve`/`gate omit`/`skip`
  (`governance_precondition`, `sdle.py:7427`), not at `init`. `state.json` still does not exist at
  assessment time. Unaffected: loop state still cannot live in `state.json`.
- **F10, revised.** `scan --path` is no longer the *only* untrusted-content check: `governance assess`
  (`sdle.py:5420`) independently re-scans every bound source (`unacknowledged_flagged_sources`,
  `sdle.py:9933`) before persisting a record, refusing `governance_content_unacknowledged` if anything is
  flagged with no matching acknowledgement. **This refinement loop's own re-scan requirement (F10 in the
  brief) is now partially satisfied by the engine already** — every `governance assess` call re-examines
  bound sources on its own, including ones the refinement loop revises. The loop's job narrows to:
  producing the *proposal* (the twelve answers) and the *edits*, not re-implementing the re-scan.
- **New fact, F15.** A WorkItem-owned pre-init record already exists for exactly this class of problem:
  `workitems/<id>/.sdle/scan-acknowledgements.json`, read by `read_scan_acknowledgements` (`sdle.py:9810`),
  written by `write_content_acknowledgement` (`sdle.py:9897`), append-only, WorkItem-scoped
  (`doc["workitem"] == paths.workitem`, checked on every read). Replayed into `audit.md` at the first
  `advance` by `record_scan_acknowledgement_audit` (`sdle.py:6935`), validated *unconditionally* (even
  with `state=None`) so a malformed record is caught before any caller's own first irreversible append.
  This is the **direct, working precedent** for this brief's own §3.5 "shared-document transaction" idea
  and for `refinement.json`'s own write discipline — cited throughout §4 below, not re-derived.
- **New fact, F16.** Path safety for any orchestrator-named file (not just bound sources) exists:
  `safe_repo_path` (`sdle.py:4478`) and the shared lexical core `_lexically_safe_path` (`sdle.py:4435`),
  returning `(target, canonical_key)`. `refinement`'s own path handling (§4.5) must go through this, not
  reinvent it.

## 2. Impact surface map

Sourced from three Explore-agent reports run at Stage 1's start (engine governance surface, hooks/agents/
tests surface, ledger enumeration) plus Stage 0's own grep inventories, refreshed against `fca6c00`.

| Surface | Location | Role for this work |
|---|---|---|
| `cmd_governance_assess` | `sdle.py:5420` | Where `evaluateQuality`'s twelve answers are validated; §3.2's flip/lint-floor refusals attach here |
| `evaluate_quality` | `sdle.py:4791` | Shape/severity validation of the twelve answers — unchanged by this work |
| `governance_precondition` | `sdle.py:7427` | Advance-time re-check; unaffected — refinement runs pre-`init` only (C4) |
| `requirements_sources` / `unacknowledged_flagged_sources` | `sdle.py:4694` / `:9933` | Single-read-per-source pattern (closed in Stage 0) — the model for how refinement's own re-scan-after-edit must read |
| `read_scan_acknowledgements` / `write_content_acknowledgement` | `sdle.py:9810` / `:9897` | The precedent pre-init record; F15 above |
| `record_scan_acknowledgement_audit` | `sdle.py:6935` | The precedent deferred-audit-replay pattern; F15 above |
| `safe_repo_path` / `_lexically_safe_path` | `sdle.py:4478` / `:4435` | The precedent path-safety API; F16 above |
| `reserve_evidence` | `sdle.py:3005` | Evidence-file naming (`{kind}-{execution_id}.json`) — `refinement-*.json` follows the same pattern |
| `append_audit` | `sdle.py:1407` | Single audit-chain writer — `refinement` commands never call this directly except through the same deferred-replay shape F15 establishes |
| `bind_workitem` / `resolve_paths` | `sdle.py:2851` / `:413` | WorkItem resolution ladder — `refinement` commands resolve exactly like `governance`/`requirements` do |
| Write-fence hook | `.claude/hooks/hooks.py`, `FENCED = (".workflow", "workitems", "requirements", "guidance")` | `refinement.json` under `workitems/<id>/.sdle/` is **already covered** by the `workitems` prefix — no hook change needed. **Gap, not fixed here:** there is no `lint-skill` rule enforcing this the way `_check_product_agents` enforces the agent fence; the write-fence hook is the only guarantee, and it is a tripwire per CLAUDE.md's own architecture section, not a proof. Recorded, not treated as blocking — matches every other engine-owned file's coverage. |
| Product agents / `PRODUCT_AGENT_TOOLS` | `sdle.py:10896`(approx, re-verify at Stage 3) | New `sdle-requirements-review` agent joins the existing four; `lint-skill`'s `product_agent_files` glob (`sdle-*.md`) picks it up automatically — proven by a test, per CLAUDE.md's own drift-list warning about assumed coverage |
| `CAPABILITY_MAP` | `SKILL.md:232` | New row needed. `requirements_check` is the natural phase — refinement runs pre-`init`, and `requirements_check` is the one phase every flow starts at before any generation. **Verify in a throwaway worktree before Stage 3**, not assumed: `lint-skill`'s `capability_map_covers_every_registry_phase` check requires every *registry* phase to have a row, and adding a *capabilities* pointer to an existing phase's row (rather than declaring a new phase) is the minimal, correct move — this is not a new phase, and must never look like one. |
| `test_units_governance.py`, `test_units_capabilities.py`, `test_units_invariants.py`, `test_units_startup_contract.py` | `tests/` | Direct consumers of every function this work touches; also where `PRODUCT_AGENTS` (capabilities test) and `WRITE_PRIMITIVE_COUNTS` (invariants test) are pinned and must be updated in the same commit as any new write call site |

## 3. Blast-radius measurement (§3.2/§3.3, decides the design)

### 3.a `quality_verdict_flip`

Grepped every test file and `docs/dry-runs/`, `docs/tutorials/` for a BLOCKED-then-PASS sequence on
unchanged document bytes. **One hit**: `tests/test_units_governance.py::test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`
(line 919) calls `assess(project, blocked_input())` then `assess(project)` — the governance *proposal*
changes, but `requirements/todo-api.md`'s bytes never do. **No dry-run or tutorial shows this sequence at
all** (a second `grep -rln` for `requirements_quality_blocked`/`governance_blocked` in `docs/dry-runs/`
and `docs/tutorials/` returns nothing) — zero documentation drift from this refusal. Design consequence:
this one test's premise must change in the same commit as `quality_verdict_flip` ships (edit the document
substantively before the second `assess`, matching the pattern already used for
`test_scanning_again_after_init_makes_acknowledgement_available` in Stage 0's own DEF-RR-001 work).

### 3.b The lint floor's blast radius on the existing suite

Built a scratchpad prototype (`lint-prototype.py`, this directory) implementing §3.3's rules. Findings:

- **Against `requirements/todo-api.md`: clean**, as the brief requires — but only after fixing a bug the
  prototype itself first exposed: a naive `TODO` marker check matched the ordinary product noun "todo"
  (the document is *about* a todo-list API). Fixed by making that one check case-sensitive; every other
  §3.3 rule (missing sections, vague terms, unresolved markers, quantitative NFRs) stayed as designed.
  This is exactly the failure mode C6 warns about, caught by testing against real content rather than
  trusting the rule's description.
- **Against `bare_project`'s minimal fixture** (`tests/conftest.py:388`, used directly or via `project`
  across the majority of this suite's ~3,150 tests): the missing-sections rule fires (no `## Acceptance`,
  no "out of scope" text). **This does not translate into suite breakage**, because of where the floor
  actually attaches: per §3.6, `governance assess` changes *only* to enforce §3.2 (the flip and the new
  `governance_content_unacknowledged`-style check) — the lint floor itself is enforced inside the new
  `refinement` command group, consulted only once a WorkItem's initial assessment is genuinely `BLOCKED`
  and refinement starts (§3.4's "Pass" case: *F₀ = ∅ → the loop is never entered*). Every existing test's
  `record_governance()` helper reports all twelve checks `PASS` unconditionally, so `F₀` is always empty
  for them and refinement never runs. **The floor's blast radius on the existing 3,150+ tests is zero.**
  The risk moves entirely to Stage 3's *new* tests for the refinement command group itself, which must
  use realistic corpus documents (§3.c below) when exercising the floor, never the suite's minimal stub
  fixtures.
- **Against a deliberately vague fixture**: the vague-terms rule correctly flagged `fast`, `user-friendly`,
  `as appropriate`/`appropriate`, `robust` and `several` — no false negatives observed in this sample.

**Design consequence:** the lint floor is wired into `refinement propose`/`refinement dispute` only, never
into `governance assess` directly, exactly as §3.6 already specifies — Stage 1's own measurement confirms
this reading is safe, not merely textually correct. No owner decision needed on scope; the safe default
the brief already chose is the one the data supports.

### 3.c Corpus (built at Stage 3, not before — see §7)

`tests/fixtures/requirements-quality/` will hold one seeded-defect document per check id plus a clean
copy of `todo-api.md`, `labels.json` kept **outside** the working tree until baseline-assessor runs
finish (so a general-purpose subagent measuring the baseline cannot `Glob`/`Read` the answer key), and
each baseline-assessor run in a **fresh** context with no prior verdicts. Per the advisor's design
addition: each document is assessed **three times independently** (fresh context each time) to measure
per-check agreement on identical bytes — this is the actual rate at which `quality_verdict_flip` will
fire on an honest rerun (an assessor disagreeing with its own earlier verdict at unchanged content, not a
refinement edit), and how often `dispute` becomes load-bearing rather than an edge case. This is
Stage-3-phase-A work (contracts and corpus), not duplicated here.

## 4. Design decisions (Stage 2 attacks each of these)

### D1 — pre-init audit for the shared-document transaction (C1)

Precedent now exists and is followed exactly, not re-derived: `record_scan_acknowledgement_audit`
(F15) validates unconditionally (even `state=None`) and replays only once state exists, de-duplicated
structurally (`_already_recorded`, matching on the entry's own `event`/`Artifact` fields, never a
substring search). `refinement`'s own transaction record follows the identical shape:

- A pending, unaffected-by-`init` WorkItem's transaction intent is written into its own
  `refinement.json` — never into `state.json` — with the same "validate unconditionally, replay once
  state exists" split.
- Every **affected** WorkItem (the other side of a shared-document acknowledgement/edit under C1) that
  has already run `init` gets `append_audit` immediately, under its own session lock, exactly like any
  other governed fact.
- An affected WorkItem that has **not** run `init` gets the deferred-replay treatment, at its own first
  `advance` — mirroring F15's `governance_precondition` call site precisely, not inventing a second one.

**Flagged for Stage 2's specific attack**, per the brief's own instruction: is this precedent actually
load-bearing for a *multi-WorkItem* transaction (F15 is single-WorkItem), or does the shared-document
case need its own recovery state machine regardless? Codex is asked to decide this from the code, not
from this plan's framing.

### D2 — the refusing lock (shared-document transaction serialization)

A new primitive: exclusive `open(paths.refinement_lock_file, "x")` per affected WorkItem, acquired in
sorted WorkItem-id order, released on completion or abort. Unlike `lock acquire` (which only warns), this
one **refuses** if already held — the shared-document transaction (C1) genuinely cannot proceed
concurrently, unlike ordinary session locking. Also closes the class of race
`write_content_acknowledgement`'s own docstring documents as an accepted limitation (R2-D04, deferred
explicitly to this primitive) — cited, not re-litigated.

### D3 — assessor provenance, no new governance-input key

`GOVERNANCE_INPUT_SECTIONS` stays strict (unchanged); assessor output is copied into evidence
(`evidence/refinement-*.json`), never into a new governance-input field. Faithful copying is convention
(F8), stated plainly in the final report, not claimed as verified.

### D4 — deliberate test/constant changes, each in the commit that causes it

- `test_re_assessing_a_fixed_requirement_unblocks_the_same_advance` — edit the document before the
  second `assess` (§3.a).
- `PRODUCT_AGENTS` (`test_units_capabilities.py`) — four agents becomes five.
- `WRITE_PRIMITIVE_COUNTS` (`test_units_invariants.py`) — updated for every new `write_atomic`/
  `save_state`/`append_audit` call site the refinement commands add, each with the same inline
  comment style the file already uses (Stage 0 set this precedent four times over).
- CLAUDE.md's "four read-only product subagents" line.
- A new test proves `lint-skill`'s `sdle-*.md` glob picks up the fifth agent — do not assume it.

### D5 — command surface

`refinement propose | decide | apply | dispute | show`. **Stage 2 is asked, per the brief, whether
`propose` and `decide` can collapse into one command** — Stage 1 takes no position; this is exactly the
kind of minimalism question Codex should answer from the frozen contracts (§5), not from prose.

### D6 (new, from Stage 0's own experience) — path handling

Every path `refinement` commands take (an edit's target, a dispute's cited file) goes through
`safe_repo_path`/`_lexically_safe_path` (F16). No second path-validation implementation, on pain of
repeating Stage 0's own V2-01 mistake (a hand-rolled validator that drifted from the shared one on day
one).

### D7 (new) — acknowledgement/refinement-edit interaction

`is_content_acknowledged` matches on exact `(path, sha256)`. This means **any** edit — including an
auto-applied, presentation-neutral whitespace edit under C2 — changes the digest and silently
un-matches any prior acknowledgement for that path, by construction, with no special-casing needed. This
is the safe default (an edit is never assumed still-acknowledged) and requires no new mechanism. What it
does mean, stated plainly for Stage 2 to attack: **every refinement iteration that touches a
previously-scanned, previously-flagged-then-acknowledged document invalidates that acknowledgement**,
even if the edit is unrelated to the flagged line — `governance_content_unacknowledged` will fire again
on the next assessment, and the loop must re-surface it (not treat it as new "progress" per §3.4, and not
loop-stall on it either, since it is a direct, expected consequence of the edit rather than drift). No
carry-forward mechanism is built; re-acknowledging is one `accept-content --path` call, matching the
existing UX.

## 5. JSON contracts

### 5.a `refinement.json` (WorkItem-owned, `workitems/<id>/.sdle/refinement.json`)

```json
{
  "refinementVersion": "1",
  "workitem": "<id>",
  "status": "IN_PROGRESS | PASSED | ESCALATED | CANCELLED | FAILED",
  "iterationCap": 3,
  "iterations": [
    {
      "iteration": 1,
      "contentDigest": "<sha256, presentation-neutral normal form>",
      "proposalDigest": "<sha256>",
      "failingChecks": ["acceptance_criteria", "..."],
      "findings": [{"checkId": "...", "text": "..."}],
      "questions": [{"id": "...", "text": "...", "options": ["..."], "answer": null}],
      "edits": [{"op": "replace|insert_after|append_section", "path": "...", "anchor": "...",
                "baseSha256": "...", "autoApplied": true, "decision": "accepted|rejected|null"}],
      "outcome": "progress|regression|stall|null"
    }
  ],
  "startedAt": "...", "endedAt": null
}
```

### 5.b Lint evidence (`evidence/refinement-lint-<execution_id>.json`)

```json
{"kind": "refinement-lint", "executionId": "...", "documentSha256": "...",
 "findings": [{"ruleId": "...", "mappedCheck": "...", "floors": true, "line": N, "text": "..."}]}
```

### 5.c Refusal reason codes (new)

| Reason | Raised by | Exit |
|---|---|---|
| `quality_verdict_flip` | `governance assess` | 1 |
| `quality_verdict_below_floor` | `governance assess` | 1 |
| `refinement_shared_source` | `refinement propose`/`apply` | 1 |
| `refinement_dispute_incomplete` | `refinement dispute` | 1 |
| `refinement_cap_exhausted` | `refinement propose` | 1 |
| `refinement_edit_stale_base` | `refinement apply` | 1 |
| `refinement_record_invalid` | any `refinement` command | 3 |

## 6. State-transition table (summary; full table at Stage 3 phase A)

Initial pass (F₀=∅) → no loop, existing flow. Remediation (F₀≠∅) → `propose` → findings/questions →
human `decide` (batched, ≤5 questions, ranked by resolvable-check count) → `apply` (per-item
accept/reject, auto-apply only if presentation-neutral per §3.5) → re-`scan` → re-`assess` → Progress /
Regression / Stall / Exhaustion per §3.4's exact definitions. Interruption at every write point recovers
via the same read-before-write pattern F15 establishes (read the record, check for an incomplete
transaction, resume or refuse `refinement_record_invalid`).

## 7. File-level estimates by phase

| Phase | Files | Rough size |
|---|---|---|
| A — contracts, lint, corpus | `sdle.py` (+~400 lines: record I/O, digest fns), `tests/fixtures/requirements-quality/*` (12+ docs), `tests/test_units_refinement_lint.py` | Medium |
| B — assessment integrity | `.claude/agents/sdle-requirements-review.md`, `sdle.py` (+~150: flip/floor checks in `evaluate_quality`'s caller), `tests/test_units_governance.py` (+tests) | Small-medium |
| C — edit/loop control | `sdle.py` (+~600: `cmd_refinement_*`, edit ops, D2's lock), `tests/test_units_refinement.py` (new) | Large |
| D — orchestration | `modules/requirements-refinement.md`, `CAPABILITY_MAP` row, `SKILL.md` governance section, `/sdle-start` if needed, `CLAUDE.md` | Small |
| E — tests/docs/ADR | `docs/GETTING-STARTED.md` §11/§13, `docs/architecture/ADR-013-*.md`, scenario tests | Medium |

## 8. Traceability, risks, rollback

- **Traceability:** each acceptance scenario (brief §7, 30 items) maps to a named test in Stage 3E's
  plan; not enumerated twice here.
- **Risks:** the lint floor's real exposure is entirely in Stage 3's new tests (§3.b) — mitigated by
  using corpus documents, never minimal stubs, for any test that exercises the floor. The shared-document
  transaction (D1/D2) is the largest unproven design element — flagged explicitly for Stage 2.
- **Rollback:** revert commits; no data migration (no `state.json` schema change, per brief's own
  constraint — unaffected by anything in this plan).

## 9. Parallel capability check

Confirmed already, repeatedly, within this session rather than re-demonstrated: ten-plus `git worktree
add`/`git worktree remove` cycles (Stage 0's review rounds) and multiple Agent-tool dispatches (the three
Stage 1 Explore agents) both worked cleanly throughout. No fresh drill needed; citing existing evidence
per the brief's own "don't redo what's already done" principle.
