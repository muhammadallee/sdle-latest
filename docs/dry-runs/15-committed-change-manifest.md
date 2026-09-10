# Dry Run 15 — The Implementation Change Set, Measured From Its Base

| | |
|---|---|
| **Scenario ID** | DR-15 |
| **Flow** | `GREENFIELD` |
| **Purpose** | Work committed during implementation, plus staged, unstaged and untracked changes, a rename, a deletion and a binary file, all reach the Gate 7 manifest, the secrets scan and the security-review evidence as **one** change set measured from the pinned base. A missing or invalid base is refused, not replaced. |
| **Defect IDs** | D03 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated. The manifest and refusal texts are the engine's real output, with the WorkItem id adapted |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `implement` (`15/18`), with Gates 1–6 approved. The tracked tree holds `src/rename_me.py` and `src/delete_me.py`. `implement preflight` has not run yet |
| **Guardrails exercised** | The implementation base pin, `implementation_changes` (diff from the base to the working tree, plus untracked files), `implementation_exclusions`, deletions and binaries listed but never read, a secret committed after the base still scanned, and one selection shared by both consumers |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**,
> but the manifest and each `Refused:` block are the engine's real output,
> captured through the suite's fixtures (WorkItem id changed from
> `fixture-workitem`; execution ids and SHAs vary per run). The engine
> behaviour is asserted by the tests under *Executable coverage*. Their results
> — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01 to Gate 6's approval, then commit `src/rename_me.py` and
`src/delete_me.py`. The fake credential below is a syntactically valid AWS
key id that belongs to nobody. Use one like it, never a real one.

---

## Transcript

### Part 1 — Building before the base is pinned

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=in_progress progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [IN PROGRESS]

Refused: implementation_base_missing

No implementation base is pinned for this WorkItem, so the implementation change set has
nothing to be measured from. Run `implement preflight` before implementing — it pins the
commit the change set is measured against — then build again.
```

*(Before D03, this built a manifest measured from the current HEAD. The same
refusal comes from `security-review evidence`, which used to fall back
silently to `HEAD~1`.)*

---

### Part 2 — Implementing, with commits along the way

*(Engine: `sdle.sh implement preflight --bypass` pinned the base. During
implementation the orchestrator:*
- *committed `src/feature.py`, which contains a fake AWS key;*
- *`git mv`'d `src/rename_me.py` to `src/renamed.py`;*
- *`git rm`'d `src/delete_me.py` and committed both;*
- *added the binary `assets/logo.png`;*
- *left `src/untracked_helper.py` untracked.*

*Then `sdle.sh manifest build --summary "…" --test-command "<command>"`.)*

**SDLE:**

```
# Implementation Manifest
Generated: 2026-09-10T19:54:59Z
Evidence: workitems/todo-api/.sdle/evidence/implementation-sdl-20260910T195459Z-d0fa8a37.json
Phase: implement (15/18)

## Changed/Added Files
A assets/logo.png (binary)
D src/delete_me.py
A src/feature.py
R src/rename_me.py -> src/renamed.py
A src/untracked_helper.py

## Potential Secrets Detected
src/feature.py:1 — AWS access key — AKIA ****(masked)

## Test Evidence
Runner: custom command
Command: python -c "raise SystemExit(0)"
Result: passed (exit 0)
```

What each line proves:

| Row | Why it is there |
|---|---|
| `A src/feature.py` and its secret | Committed **after** the base. Before D03 the manifest compared against current HEAD, so this file and its secret were invisible to both the list and the scan |
| `R src/rename_me.py -> src/renamed.py` | One entry for a rename, not the literal string `"old -> new"` the old parse produced |
| `D src/delete_me.py` | Listed, and never read — there is no current file to scan |
| `A assets/logo.png (binary)` | Listed and marked; no text decoding is attempted |
| `A src/untracked_helper.py` | Untracked files are part of the change set |
| *(no `.sdle/`, `.specify/`, runtime or feature-directory rows)* | Engine bookkeeping stays excluded by the one shared list |

---

### Part 3 — The security review reads the same set

*(Engine: `sdle.sh security-review evidence`.)*

```
changes:   assets/logo.png, src/delete_me.py, src/feature.py, src/renamed.py,
           src/untracked_helper.py
untracked: assets/logo.png, src/untracked_helper.py   ← read these directly; no diff shows them
diff:      git diff -M <base> -- . (with the same exclusions)
```

*(Before D03 this command carried its own, narrower exclusion list, which
missed the repository-global `.sdle/`, and it had no `untracked` list at all.)*

---

### Part 4 — An invalid base

*(History was rewritten, so the pinned base no longer exists.)*

```
Refused: implementation_base_invalid

The pinned implementation base ffffffffffffffffffffffffffffffffffffffff is not a commit
in this repository (was history rewritten, or the repository replaced?). SDLE will not
measure from a different commit instead. If the rewrite was deliberate, re-run
`implement preflight` to pin a new base, knowing that changes before it will no longer be
listed.
```

---

## Artifacts, state and audit

- `state.implementation_base_ref` is set by `implement preflight` and read, never
  moved, by both consumers.
- The evidence record carries the same `changes` list as the manifest,
  `{path, status, old_path, binary, untracked}` per entry, sorted and
  de-duplicated. Rebuilding against unchanged inputs gives the same list.
- `secrets_flagged` is audited, with the finding masked to four characters.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `manifest build` with no pinned base | Refused `implementation_base_missing` | No manifest, no evidence written |
| `security-review evidence` with no pinned base | Refused `implementation_base_missing` | Unchanged, no `HEAD~1` fallback |
| Either consumer with a base that is not a commit | Refused `implementation_base_invalid` | Unchanged |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| A post-base commit is listed and scanned, and reaches the review consumer | `tests/test_units_manifest_changes.py::test_d03_a_change_committed_after_the_base_is_listed_and_scanned` |
| Staged, unstaged and untracked changes are listed | `tests/test_units_manifest_changes.py::test_d03_staged_unstaged_and_untracked_changes_are_all_listed` |
| A rename and a delete are represented | `tests/test_units_manifest_changes.py::test_d03_a_rename_and_a_delete_are_represented` |
| A binary change is represented without decoding | `tests/test_units_manifest_changes.py::test_d03_a_binary_change_is_represented_without_decoding` |
| Engine bookkeeping stays excluded | `tests/test_units_manifest_changes.py::test_d03_engine_bookkeeping_stays_excluded` |
| A missing base is refused, not replaced | `tests/test_units_manifest_changes.py::test_d03_a_missing_base_is_refused_not_replaced` |
| An invalid base is refused | `tests/test_units_manifest_changes.py::test_d03_an_invalid_base_is_refused` |
| Rebuilding gives the same change set | `tests/test_units_manifest_changes.py::test_d03_rebuilding_unchanged_inputs_gives_the_same_change_set` |
| The dirty-tree guard reads the first entry whole | `tests/test_units_manifest_changes.py::test_d03_the_dirty_tree_guard_reads_the_first_status_entry_whole` |
| Review evidence refuses with no base | `tests/test_integration_06_to_09.py::test_06_security_review_refuses_when_no_ref_pinned` |
