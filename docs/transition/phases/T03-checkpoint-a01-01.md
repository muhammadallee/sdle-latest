# T03 checkpoint a01-01 — M1 (D1: repository-root discovery)

**Phase:** T03 · **Attempt:** 1 · **Milestone:** M1 of 8
**Base HEAD:** `767b657009d9631c3a10a7fee3b87f4e0c549558` (product baseline for T03 = `ab889a1`)

## What landed

`scripts/sdle.py` only. Symbols, not line numbers:

- `class Paths` — new field `launch_cwd: Path | None = None`.
- New module constant `PROJECT_ROOT_MARKERS` = `(("workitems","index.md"), (".workflow","state.json"), (".git",))`.
- New `discover_project_root(start)` — nearest-ancestor-inclusive walk, markers tested in order at each level, returns `None` when nothing matches.
- New `_within(child, parent)`.
- `resolve_paths` — `--project-root` / `SDLE_PROJECT_ROOT` still win; otherwise the marker walk; otherwise the launch directory itself (byte-identical to pre-T03 behaviour). `launch_cwd` = the real CWD when it is inside the resolved root, else the resolved root.
- All three `Paths(...)` constructions in `resolve_paths` now pass `launch_cwd`.

## Structural proof (the plan's M1 gate)

- `git diff --numstat` → `57  4  scripts/sdle.py` and nothing else under `scripts/`, `tests/`, `.claude/`. **Zero test edits.**
- `python -m pytest -q -rsxX` → `341 passed`, **RAW EXIT 0**.
- `python scripts/sdle.py lint-skill` → raw exit 0, 22 PASS / 0 FAIL, `Parsed 19 phases, 8 gates, 14 migration rows`, `all four locations report v1.14`.

Working tree also carries the pre-existing, out-of-scope ` M .claude/settings.local.json`.

## Decisions taken at M1

- `launch_cwd` follows plan D1 literally: an explicit root plus a real CWD *inside* it yields the real CWD (so the hook can reach rung 2 when Claude is genuinely launched inside a WorkItem); an explicit root plus a CWD outside it yields the root. This makes the existing suite deterministic, because `conftest.Project.run` always passes `--project-root` while pytest's CWD is the SDLE repository.

## Next

M2 — D3 active-context helpers, `workitem use`, persistence at `init` / `migrate-workflow`, `.gitignore` + the single permitted `conftest.init_git` mirror line.
