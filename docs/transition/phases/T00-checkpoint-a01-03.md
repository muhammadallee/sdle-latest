# T00 Checkpoint a01-03 — baseline.md complete

**Phase:** T00 | **Attempt:** 01 | **Milestone:** all seven baseline sections written and self-checked

## Durable on disk

- `docs/transition/baseline.md` — §1 through §7, complete.
- `docs/transition/phases/T00-checkpoint-a01-01.md`, `-02.md`.

## Self-checks run in this context

| Check | Result |
|---|---|
| `grep -n "^## " baseline.md` | exactly 7 top-level sections, in plan order |
| `grep -c "^### 4\."` | 14 subsections |
| §4 table parse (5 columns, no blank cell) | 183 rows, 0 malformed, 0 blank |
| §18 coverage in §5 | 31/31 present, 0 missing, 0 duplicated, 0 invented |
| §5 total rows | 47 (31 §18 + 16 NOT_IN_S18) |
| `git status --porcelain` | 7 lines, all `??`; no `M`, no `D` |
| `ls -d */` | `docs/ requirements/ scripts/ tests/ tools/` — no new top-level dir |
| `workitems/`, `.sdle/` | absent |
| `python tools/transition/validate.py` | exit 0, `TRANSITION_VALID: complete=0/12 next=T00` |

## Remaining work

1. `docs/transition/phases/T00-handoff-a01.md`.
2. `docs/transition/progress.md` T00 row → `IMPLEMENTED | 1 | ... | UNCOMMITTED | ...`.
3. Final `python tools/transition/validate.py`, require exit 0.
