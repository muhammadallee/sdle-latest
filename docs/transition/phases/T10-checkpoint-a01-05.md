# T10 checkpoint — attempt 01, milestone M5

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M5 — the four product subagents, the fence, the agent lint checks
**Milestone status:** COMPLETE. **The declared red window is closed.**
**HEAD:** `875b361` (OBSERVED, `git log --oneline -3`). Nothing committed; all work is live in the working tree.

This checkpoint is written by a **resuming** implementer. Attempt 1 was not
incremented: the previous run was terminated by an API session limit, which
§24.6 classes as an interruption, not a verification FAIL.

---

## What this context found on disk, and what it changed

M5 was **substantially already applied** when this context started, and
checkpoint 04's resume instruction ("`ls .claude/agents/` must still show only
the four `sdle-transition-*` files") was **stale**. Re-derived here:

| Observation | Command | Result |
|---|---|---|
| Four product agents exist, each granting exactly `Read, Grep, Glob` | `ls .claude/agents/`; `cat .claude/agents/sdle-design-review.md` | `sdle-{code-review,design-review,discovery,security-review}.md` beside the four `sdle-transition-*`. No `Bash`, no `Write`, no `Agent` |
| `product_agent_fence` is the fifth guard, unconditional | `git diff .claude/hooks/hooks.py` | `GUARDS` gains `"product-agent-fence"`; the guard body is a bare `emit("PreToolUse", "deny", …)` |
| The fence is registered in the four agents' own frontmatter, not `settings.json` | agent frontmatter; `git status` shows `.claude/settings.json` untouched | `command: "python .claude/hooks/hooks.py product-agent-fence"` |
| X1, X2, X3, X4, X5, X7 applied | `git diff` on the six test files | see the X table below |
| N13–N19, N25 written | `grep '^def test_' tests/test_units_capabilities.py` | present, plus `test_a20_…` and `test_a21_…` |
| `lint-skill` | `rtk proxy "python scripts/sdle.py lint-skill"` | **42 checks, `failed: []`, exit 0** — E3's 33 plus the nine new ones, all present by name |
| The authority constraint | `git diff scripts/sdle.py` scanned for writer calls | **0 added and 0 removed** lines matching `write_atomic\|save_state\|append_audit\|record_audit\|.write_text\|.write_bytes\|os.replace\|mkdir`; exactly one `add_parser` added (`resume`, read-only) |

**The one thing this context changed in M5: the single remaining failure.**

---

## The failure, its category, and the call that was made

Observed here before touching anything, `rtk proxy "python -m pytest
tests/test_units_gate_policy.py -q -p no:cacheprovider"`, redirected, `$?` read
with no pipe: **`RAW_EXIT=1`, `1 failed, 363 passed in 149.94s`.** Exactly one
failure, and the diff named exactly one file:

```
FAILED tests/test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical
E  AssertionError: .claude/hooks/hooks.py
E  - Four guardrails that execute regardless of what the model decides.
E  + Five guardrails that execute regardless of what the model decides. …
```

It is **T09's** test. It asserted the whole `.claude/hooks/` directory
byte-identical to T09's rollback point `e1cf341`, with the docstring *"hooks
are tripwires and T09 added no fence."* T10's plan **B4** requires a fifth
guard in `hooks.py`, so the assertion is false **by design**.

**Category: TP-003 category 2 — deliberately superseded.** Not a regression:
the failure is the plan's own declared change arriving.

**X-classification: X-GEN, deliberately, and not a blocker.** Recorded as the
call the task asked to be made explicitly rather than drifted into:

- X-GEN's shape is *"any test that enumerates a closed set this phase
  legitimately grows"*, with three conditions. This test pins a closed set —
  the inventory and content of `.claude/hooks/` — that plan B4 legitimately
  grows by exactly one guard. The named examples after X-GEN's dash are
  illustrative of that shape, not an exhaustive allow-list.
- The three conditions are met and are the reason the re-valuation is written
  the way it is: **(a)** every assertion remains exact equality against a
  written-out set — nothing became a subset, a prefix or an `any`; **(b)** the
  old and new literals are recorded verbatim below and will be repeated in the
  handoff; **(c)** no assertion is deleted, only re-valued and subdivided.
- **It is not a material decision, so no `T10-blocker.md` is warranted.** There
  is exactly one defensible resolution: the plan mandates the fifth guard and
  simultaneously mandates (F2, N27) that no hook change go unnoticed. A
  blocker would stall the migration for a judgement with one answer.
- **T09 NB-1 is the reason X-GEN exists.** NB-1's own recommendation to the
  orchestrator was *"future plans should carry a generic X row for closed-set
  assertions that must name a newly added command, so this class of change is
  authorised rather than requiring a judgement call mid-flight."* T10's plan
  carries exactly that row. Using it is following NB-1's remedy, not repeating
  NB-1's error — the error there was that no such row existed and the
  implementer proceeded anyway.

### The re-valuation, literal for literal

**Old (verbatim, `test_units_gate_policy.py`):**

```python
def test_n28_the_hooks_are_byte_identical():
    """A10: hooks are tripwires and T09 added no fence. Whole directory, so a
    new hook file would fail here rather than pass unnoticed."""
    hooks = sorted((REPO_ROOT / ".claude" / "hooks").rglob("*"))
    present = sorted(p.relative_to(REPO_ROOT).as_posix()
                     for p in hooks if p.is_file())
    assert present, "the hooks directory has gone missing"
    for relative in present:
        original = at_rollback(relative)
        assert original is not None, relative
        assert here(relative) == original, relative
```

**New (verbatim, same function name, same file, same `ROLLBACK = "e1cf341"`):**
the docstring records the supersession, and the one assertion becomes four,
each still exact equality against an enumerated set:

```python
HOOKS_FILE = ".claude/hooks/hooks.py"
HOOK_FILES = (HOOKS_FILE,)
T09_GUARDS = ("write-fence", "untrusted-read", "dirty-tree", "secrets-scan")
T10_GUARD_ADDITIONS = ("product-agent-fence",)
T10_HOOK_ADDITIONS = ("PRODUCT_AGENT_FENCE_REASON", "product_agent_fence")
```

1. `assert present == sorted(HOOK_FILES)` — the file list. **T10 adds no hook
   file, so the original sentence ("a new hook file would fail here rather than
   pass unnoticed") is preserved intact and is now stronger: it was
   `assert present, "…"`, a non-emptiness test that would have accepted a new
   file, and it is now an enumeration.**
2. Every hook file **other than** `hooks.py` is still byte-identical to
   `at_rollback(relative)` — unchanged assertion, unchanged baseline.
3. Inside `hooks.py`, `ast`-parsed top-level definitions: the **name set** is
   exactly T09's plus `T10_HOOK_ADDITIONS`, and every definition T09 pinned is
   compared **byte-for-byte one at a time** via `ast.get_source_segment`.
   `GUARDS` is the single exemption from the byte comparison and is pinned
   separately by rule 4.
4. `_registered_guards(...) == list(T09_GUARDS + T10_GUARD_ADDITIONS)` — the
   registry by name **and order**, read out of the source rather than by
   importing, so a guard that is defined but never wired still fails.

The baseline is **not** moved: `ROLLBACK` stays `e1cf341` and every other test
that uses it (`FROZEN_FILES`, the dry-run transcripts,
`test_the_rollback_point_is_reachable`) is untouched. Only the hooks test knows
about T10's one declared delta.

### Proof it still fires, driven not asserted

`<scratchpad>/fire_n28.py` mutates the real tree, runs the single test, restores
in a `finally`, and verifies the restore by SHA-256. Observed verbatim:

```
baseline sha256: 78528b8d6ad82740b0643ef7821ef26e614bf82ca4b1ef1458de01ca49c62494
UNMUTATED: (0, '1 passed in 0.45s')
A stray hook file       -> (1, '1 failed in 0.30s')
An edited write_fence   -> (1, '1 failed in 0.48s')
Fence defined not wired -> (1, '1 failed in 0.54s')
A stray module constant -> (1, '1 failed in 0.45s')
restored sha256: 78528b8d6ad82740b0643ef7821ef26e614bf82ca4b1ef1458de01ca49c62494 MATCH
RESTORED: (0, '1 passed in 0.31s')
```

A check that cannot fail is not evidence; all four unexpected-change shapes
fail, and the tree is restored byte-exactly.

---

## Evidence — every figure re-derived in this context

| Measurement | Result |
|---|---|
| `tests/test_units_gate_policy.py`, **before** the fix | `1 failed, 363 passed in 149.94s`, `RAW_EXIT=1` |
| `-k n28`, after the fix | `6 passed, 358 deselected in 1.73s`, `RAW_EXIT=0` |
| **M5 targeted set** — `test_units_gate_policy.py test_units_artifact_review.py test_hooks.py test_lint_skill.py test_units_capabilities.py test_units_governance.py test_units_discovery.py` | **907 passed in 571.41s (0:09:31)**, `RAW_EXIT=0` |
| `lint-skill` | **42 checks, `failed: []`**, `LINT_EXIT=0` |
| The nine new check names, observed | `capability_map_covers_every_registry_phase`, `every_capability_file_exists`, `capability_map_never_names_the_orchestrator`, `every_capability_file_is_linted`, `every_row_is_a_strict_subset_of_the_capability_set`, `capability_cross_references_are_mapped_files`, `product_agents_are_read_only`, `product_agents_declare_the_fence`, `product_agents_declare_the_non_approval_clause` |
| Full suite | **NOT_RUN in this milestone.** M6 owns it |
| `git diff --numstat`, in scope | `sdle-continue.md 8 3`; `sdle-start.md 4 2`; `hooks.py 37 2`; `SKILL.md 45 3`; `gate-protocol.md 3 2`; `phase-execution.md 2 1`; `sdle.py 421 20`; `test_hooks.py 120 0`; `test_lint_skill.py 129 0`; `test_units_artifact_review.py 64 5`; `test_units_discovery.py 14 0`; `test_units_gate_policy.py 122 20`; `test_units_governance.py 14 0` |
| Untracked, in scope | 4 product agents, `modules/code-review.md`, `modules/design-review.md`, `tests/test_units_capabilities.py` |
| Out of scope, untouched | `.claude/settings.local.json` |
| Python | 3.13.0. **Python 3.11: `NOT_RUN`.** **CI: `NOT_RUN`** |

## A18 at M5 — the acceptance criterion of the whole phase

`git diff scripts/sdle.py`, scanned mechanically: **zero added and zero removed
lines** containing `write_atomic`, `save_state`, `append_audit`, `record_audit`,
`.write_text`, `.write_bytes`, `os.replace` or `mkdir`. Exactly one
`add_parser` added, for `resume`, which is read-only. `lint-skill` still reports
v1.16 at all four locations. No state field, no migration row, no gate change,
no policy value. **The diff contains no new writer.**

---

## Remaining — M6 only

- `README.md` tree/extension notes (**not** the v1.3 version-history row),
  `docs/SDLE-Reference-Guide.md` skill layout, `CLAUDE.md` architecture section,
  and new `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md`
  carrying **D12's honesty table verbatim, all three "convention only" rows
  unsoftened** (A25, F15).
- The guardrail test slice: N20, N21, N22, N24, N26, N27, plus
  `test_a25_the_enforcement_split_is_stated_without_being_softened` — which
  `tests/test_units_capabilities.py`'s module docstring already names, so it
  must exist by the end of M6.
- Full suite, `lint-skill`, `validate.py`, the acceptance matrix,
  `docs/transition/phases/T10-handoff-a01.md`, `progress.md` → `IMPLEMENTED`.

## Exact resume instruction for a fresh context

1. `git rev-parse HEAD` = `875b361`; `git status --porcelain` matches the file
   list above; **nothing is committed**.
2. `rtk proxy "python scripts/sdle.py lint-skill"` → **42 checks, `failed: []`**.
3. `rtk proxy "python -m pytest tests/test_units_gate_policy.py -q -p no:cacheprovider -k n28"`
   → **6 passed**. If it fails, M5 has regressed; re-read this checkpoint's
   re-valuation section before touching it.
4. M5 is complete and its red window is closed. Start at M6's first item; do
   **not** re-apply any M5 script — the agents, the fence and the lint checks
   are all on disk.

Never run another command while a full suite is in flight: two runs in the
previous context differed by 4× in wall clock purely from CPU contention. The
suite currently takes roughly 28 minutes.
