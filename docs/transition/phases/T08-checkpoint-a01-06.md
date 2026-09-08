# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 06

**Phase:** T08
**Attempt:** 01 (unchanged — contexts 1–3 were §24.6 interruptions, not FAILs)
**Milestone:** M6 — ADR-005, the documentation sweep, and the final evidence

**No red window.** M6 changes documents, one ADR and two assertions inside
tests T08 itself authored. The engine (`scripts/sdle.py`) is **byte-identical**
to the state context 2 left it in: context 3 made no engine edit.

## Objective currently being worked

M6, resumed by a third context after context 2 was terminated mid-M6 by an API
session limit. Context 2 had already applied most of the documentation sweep and
the two ADR fixes checkpoint 05 lists, and recorded neither — so the first job
was to verify the tree rather than repeat the work.

## State verified from disk before any edit

| Claim | How verified in this context |
|---|---|
| HEAD `9c10eb5`, T08 entirely uncommitted | `git log --oneline -5`, `git status --porcelain` |
| `lint-skill` exit 0, **32** checks, `failed: []` | ran it, parsed `data.checks` |
| **1025** tests collected, RAW_EXIT 0 | `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"`, redirected, `$?` read with no pipe |
| **Full suite green at the inherited tree** | `1025 passed in 1251.81s (0:20:51)`, RAW_EXIT 0 |
| `baseline_precondition` present, one call site | AST walk: only `cmd_init`, at a line before its first `mkdir` |
| `GREENFIELD_V1_PHASES` frozen | parsed from `c80f341` and from the working tree: identical, 19 entries, no `discovery` |
| Checkpoint 05's two ADR defects | **already fixed on disk** by context 2 — read, not assumed |
| `validate.py` | `TRANSITION_VALID: complete=8/12 next=T08`, exit 0 |

## Completed in this context

### ADR-005 — read line by line against the shipped engine, corrected in place

Four further inaccuracies beyond checkpoint 05's two, each found by a command:

1. **D4** said `discovery_precondition` "lives in `apply_advance`". An AST walk
   reports three call sites (`apply_advance`, `cmd_gate_approve`, `cmd_skip`) —
   the shape `governance_precondition` and `flow_precondition` already have,
   because the latter two append to the ledger before they delegate. Recorded
   with that reason.
2. **The Consequences refusal list was one short.** An AST diff of every
   `Refused` / `IntegrityError` reason code against `c80f341` reports **nine**
   added and none removed; `discovery_workitem_required` was missing.
3. **D10 overstated its own carve-out** ("would match a dozen pre-existing
   files"). A real search over the test's `searchable_files()` set matches five
   files in total. Replaced with the measured statement; the same claim in
   `discovery_identifiers()`'s docstring was corrected to match.
4. **D12 claimed "a test pins both sets"** when only `SDLE_OWNED_PREFIXES` was
   pinned. Fixed by **making the claim true**: `test_the_two_guard_surfaces_are_unchanged`
   now also pins, on the parsed source of `cmd_manifest_build`, that the Gate 7
   manifest excludes the WorkItem runtime and nothing else.

Plus two precision edits (the evidence document's directory; the discovery
status being derived from the record rather than the flow name) and a forward
pointer to the ADR-002 sentence this phase falsifies. **ADR-002 and ADR-004 were
not edited** — a decision record is superseded, not rewritten.

**D3 was left as written.** It is the phase's deliverable, it was correct, and
the sweep was checked for the opposite failure: no document rounds the
engine-enforced half up into a claim the engine cannot make.

### Documentation sweep — completed, `lint-skill` re-run after every edit

- **`README.md`** — the five new commands as a table in the Commands section
  (the gap the earlier sweep left), with the paragraph stating D3's split in the
  README's voice; the v1.16 changelog row, which still said "20-entry phase
  registry" (no version row added — D11); and "Add a new phase", which told a
  reader to add a `PROGRESS_MAP` row for every phase when that table is the
  GREENFIELD view and two phases deliberately have none.
- **`CLAUDE.md`** — it said "`PHASE_SEQUENCE` is a 20-entry phase *registry*",
  which T08 falsifies. Corrected, plus one paragraph on `discovery`, the
  baseline and ADR-005. Not in the plan's expected-changes list; leaving a false
  sentence in the repository's own instruction file is the drift the sweep
  exists to prevent, and T07 updated this same paragraph for the flow model.
- **`docs/SDLE-Reference-Guide.md`** — §12.4 described the WorkItem's records
  and named two of the three; `discovery.json` added and the heading renamed.

`lint-skill` was run after **every** document edit — seven times — and reported
exit 0, 32 checks, `failed: []` each time.

### Evidence produced in this context

- **Live refusal reproduction** through the real CLI in a throwaway git
  repository: at `discovery` under `BROWNFIELD_DISCOVERY`, `advance` and
  `skip --confirm` both refuse `discovery_missing` and `gate approve` refuses
  `not_at_gate`; `audit.md` **and** `state.json` are SHA-256-identical before
  and after all three; `audit verify` exits 0 with `chain_ok: true`. A second
  WorkItem assessed `ITERATIVE` against an `ABSENT` baseline refuses
  `baseline_required`, and its runtime afterwards holds only the
  `governance.json` and `evidence/` that `governance assess` wrote **before**
  `init` — `init` created no `state.json`, `audit.md` or `execution.json`.
  Recorded honestly: **no T08 refusal is reachable at `gate approve`**, because
  R1/R2 are init-only and `discovery` is by construction not a gate. That call
  site is defensive.
- Byte-identity of 26 paths against `c80f341` with line endings normalised:
  none differ.
- Python walk for `gate_discovery`: one product/test hit, the negative lint
  fixture (an rtk-proxied `grep` gave a false negative earlier in this
  migration, so this was a Python walk).
- The acceptance matrix A1–A20, written into the handoff with the evidence and
  the observing context for each row.

## Existing tests changed at M6 — TP-003

**None.** The two test edits are inside files T08 itself authored, and both are
strengthening: an added assertion (no assertion removed or relaxed) and a
docstring correction. They are recorded in the handoff's TP-003 table with that
classification rather than as category 1, 2 or 3, because no pre-existing
behaviour was superseded. `tests/conftest.py` is still `+66 / −0` — exactly the
two additions the anti-contradiction clause permits.

One real failure occurred and was fixed as a defect: the first version of the
manifest pin matched the explanatory *comment* inside `cmd_manifest_build`
rather than its code. Rewritten onto the AST. The F1 `ENVIRONMENT_FLAKE`
procedure was treated as **VOID**; nothing was pattern-matched to it.

## Tests actually run in this context

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` | **1025 collected**, RAW_EXIT 0 (before and after the edits — context 3 added no test) |
| **Full suite, inherited tree** | `1025 passed in 1251.81s (0:20:51)`, RAW_EXIT 0 |
| Targeted: the manifest pin and the two N14 tests | first run 1 failed / 2 passed (RAW_EXIT 1), then **1 passed**, RAW_EXIT 0 after the fix |
| `python scripts/sdle.py lint-skill` ×7 | exit 0, 32 checks, `failed: []` |
| `python tools/transition/validate.py` | exit 0 |
| **Final full suite** | `1025 passed in 1221.55s (0:20:21)`, RAW_EXIT 0, no short-summary lines |
| `test_units_discovery.py` + `test_lint_skill.py` re-run **after** the final suite | **89 passed in 63.07s**, RAW_EXIT 0 — two ADR wording edits landed after the full run began and `test_n14_*` reads `docs/architecture/` at runtime, so the doc-reading tests were re-run against the exact final tree |
| Python 3.11 · CI | **NOT_RUN** — this host runs 3.13; the branch is local-only |

## Current failures

None.

## Unresolved decisions

None requiring a human. No `T08-blocker.md` was written.

## Remaining

Nothing. M1–M6 are complete, the handoff records the evidence and the acceptance
matrix, and `progress.md`'s T08 row is `IMPLEMENTED`. The phase is ready for
independent verification; it has **not** been committed by the implementer.
