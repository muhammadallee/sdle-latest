# T00 Checkpoint a01-02 — capability inventory complete

**Phase:** T00 | **Attempt:** 01 | **Milestone:** baseline.md §4 written

## What is durable on disk

- `docs/transition/baseline.md` §1–§4.
- `docs/transition/phases/T00-checkpoint-a01-01.md`.

## §4 shape actually written

14 subsections in contract §6 item 3 order, each with the mandated
`| Item | Observed behavior | Evidence | Disposition | Changing phase |` table
and no blank cell. Row counts:

| Subsection | Rows | Completeness rule satisfied |
|---|---|---|
| 4.1 CLI subcommands | 65 | 33 top-level + 32 nested `add_parser` names |
| 4.2 Exit codes | 4 | all four constants |
| 4.3 State fields | 33 | 25 top-level keys + 8 `approvals` gate keys |
| 4.4 Audit behavior | 8 | one per distinct behavior |
| 4.5 Lock behavior | 7 | one per distinct behavior |
| 4.6 Rate limits | 6 | one per distinct behavior |
| 4.7 Drift behavior | 10 | one per distinct behavior |
| 4.8 Hooks | 8 | all four wired entries + 4 cross-cutting |
| 4.9 Dirty-tree behavior | 4 | one per distinct behavior |
| 4.10 Untrusted-content scan | 8 | one per distinct behavior |
| 4.11 Secrets scan | 5 | one per distinct behavior |
| 4.12 Test evidence | 5 | one per distinct behavior |
| 4.13 Implementation-base-ref | 5 | one per distinct behavior |
| 4.14 Migrations | 15 | all 13 chain rows + 2 chain-level behaviors |

## Plan divergence found (report, do not absorb)

The plan's evidence ledger says "The CLI exposes 21 top-level subcommands".
Observed this session: **33** `subparsers.add_parser(` registrations and **32**
nested. The plan's *operative* rule (every `add_parser` name is its own row) was
followed; the ledger count was not. Recorded in the handoff per §24.3 item 2.

## Remaining work

1. baseline.md §5 — regression matrix, all 31 contract §18 rows exactly once.
2. baseline.md §6 — four known baseline conditions.
3. baseline.md §7 — five contract §6 explicit-preserve items.
4. `T00-handoff-a01.md`, then `progress.md`, then `validate.py` exit 0.
