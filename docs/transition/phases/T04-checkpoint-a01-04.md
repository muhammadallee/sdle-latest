# T04 checkpoint a01-04 — M4 (write-fence carve-out)

**Phase:** T04 · **Attempt:** 1 · **Milestone:** M4 of 7 · **Status:** CLOSED GREEN.

Predecessors: checkpoints 01–03 (M1, M2, M3), all closed green. Rollback point is still `beb28f2`; nothing committed yet.

## What M4 landed (D11)

`.claude/hooks/hooks.py`:

- New `SPECS_CARVE_OUT = re.compile(r"(?:^|/)workitems/[^/]+/specs/")`, evaluated in `write_fence` **before** the `FENCED` loop; a match returns without emitting a decision, which is this hook's "allow".
- The `workitems` entry of `FENCE_REASONS` had its forward-looking *"NOTE for the phase that moves clarifications/, reviews/ and Spec Kit artifacts under workitems/…"* sentence replaced with a statement of the carve-out that now exists. That note called this a "one-line change"; it was.

### Declared deviation from the plan's wording

The plan specifies `^workitems/[^/]+/specs/` on the repo-relative path. The hook's `relative()` is best-effort — it only strips a genuine `PROJECT_DIR` prefix, and Claude Code passes absolute native paths — so a strictly `^`-anchored pattern would not have matched `/proj/workitems/wi-a/specs/…`. The pattern is therefore anchored to a **path-segment boundary** (`(?:^|/)`), which is exactly the semantics the neighbouring `in_dir()` already uses, and is still applied to `relative(path)`. Nothing else under `workitems/` can match: the third segment must be literally `specs` followed by `/`.

## Tests (N10)

Added to `tests/test_hooks.py`'s two existing parametrize lists — the file that drives the **exact command string in `.claude/settings.json`**, which is the point of testing hooks there rather than anywhere else. No existing case was changed or removed.

- **Allowed** (added): `/proj/workitems/wi-a/specs/001-todo-api/spec.md`, `workitems/wi-a/specs/001-todo-api/plan.md`, `C:\proj\workitems\wi-a\specs\001-todo-api\tasks.md`. The existing `/proj/.specify/specs/001/spec.md` allow case is unchanged.
- **Denied** (added): `/proj/workitems/wi-a/.sdle/lock`, `/proj/workitems/wi-a/reviews/security-review-2026-01-01-0900.md`, `/proj/workitems/wi-a/specs.md` (near-miss: no trailing `/`), `/proj/workitems/specs/not-a-workitem.md` (near-miss: `specs` in the id position). The existing `workitems/index.md`, `workitem.json` and `.sdle/state.json`, `.sdle/audit.md` cases are unchanged.

## Verification at M4

- Targeted `tests/test_hooks.py` → **44 passed, RAW_EXIT=0** (37 at baseline; +7 new parametrize cases).
- **Full suite after M4: `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → 445 passed in 516.96s, RAW_EXIT=0**, no short-summary section. 445 = 438 baseline + the 7 added hook cases.

## How to resume from here

Next is **M5**: `tests/test_units_speckit_binding.py` (N1–N13) plus — declared in checkpoint 03 — the `phase-execution.md` half of D12, because N2(d) is that file's test.
