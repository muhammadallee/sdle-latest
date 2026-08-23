# T02 checkpoint a01-05 — M5 complete (`migrate-workflow`)

**Milestone:** M5 — `migrate-workflow --workitem <id>`, plan D8 / contract §20.

## Engine

- `verify_audit_chain(entries)` — the `prev_sha` walk **extracted unchanged**
  from `cmd_audit_verify`, so the migration verifies a ledger at a second
  location without restating the rule. `cmd_audit_verify` now calls it; its
  emitted data and exit codes are byte-identical.
- `workitem_metadata_file(paths)` — the identity file, so step 10 does not
  concatenate.
- `cmd_migrate_workflow` — all 12 D8 steps, plus the parser entry.
  `--workitem` on the subparser uses `dest="migrate_workitem"` so it works on
  either side of the subcommand: a same-dest flag on both parsers would let
  argparse clobber the global value with the subparser's default.
- `MIGRATION_VERIFIED_FIELDS` — the nine fields §20.11 requires to survive.

### Ordering, and the one deliberate refinement to D8

D8 lists the audit entry as step 11, *after* the step-8 commit point. Appending
to the ledger updates `audit_sha`, so a literal reading would leave the
committed `state.json` carrying a stale `audit_sha` — `audit verify` would fail
immediately after a successful migration — unless `state.json` were rewritten
post-commit, which would defeat "written last".

Implemented order (the *property* D8 asks for is preserved exactly):

1-6 as written. 7 copies `audit.md`, the manifest, the completion summary,
`evidence/migration-<executionId>.json` and `execution.json`. 8 then (a)
verifies the **copied** ledger at the new location against the legacy
`audit_sha` before anything commits, (b) migrates the state in memory to 1.14
and sets `workitem`, (c) appends the `workflow_migrated` entry to the **target**
ledger, and (d) writes the target `state.json` **last** — the sole commit
marker. 9 re-reads `state.json`, compares the nine fields, re-verifies the
target chain and `audit_sha`, and on mismatch unlinks `state.json` so the
target stops resolving and the legacy stays authoritative. 10 records the
`migration` object on `workitem.json`. 12 emits the legacy path as archival.

Every write before the commit point is a whole-file overwrite, so a re-run
after any interruption is safe — which is what the crash test proves. Step 11
is merged into 8c; the entry still lands in the target ledger, which is what
§20.12 requires.

Step 9's comparison anchor is the in-memory migrated state rather than the raw
legacy dict. When the version chain runs no steps the two are identical, so it
*is* §20.11's comparison; when the chain does run (e.g. a 1.9 legacy state
whose `progress` is recomputed), the chain's own documented effect is not a
migration defect. The migration test asserts the nine fields against the
**legacy** file directly, so the stronger claim is still pinned by a test.

## Tests

12 new cases in `tests/test_units_workitem_runtime.py` (N19-N26 plus a
post-migration resolution case). The `legacy_workflow` helper stands up a
genuine pre-T02 repository: a v1.14 engine can no longer *create* a
repository-global runtime (that is C4/D2), so it builds a real one under a
throwaway WorkItem, moves it to `.workflow/`, erases the WorkItem layer, and
winds `state.json` back to a v1.13 shape with no `workitem` field. The ledger
moves byte-for-byte, so `audit_sha` still matches and the migration runs
against a ledger that genuinely verifies.

Covered: full field preservation + legacy byte-identity (SHA map before/after),
evidence file + `workitem.json` `migration` object + `workflow_migrated` as the
last target entry, `workitem_unknown`, `target_exists`, corrupt legacy JSON
(exit 3), unknown legacy version (exit 3), broken legacy audit chain
(`legacy_audit_broken`, names `audit rebaseline`), crash injection parametrised
over `write_atomic` calls 1-4 (each leaves no target `state.json`, leaves the
legacy byte-identical, and re-runs successfully), and that the WorkItem runtime
is what resolves afterwards.

## Evidence

`pytest tests/test_units_workitem_runtime.py -q -k "migrate or crash or
after_migration"` → **12 passed, raw exit 0**.

(First run: 12 failed, raw exit 1 — the helper tried `init` without a WorkItem,
which C4/D2 now refuses. The **helper** was wrong, not the engine.)

## Next

M6 — write fence, dirty-tree hook cases, Phase 17 diff exclusion, `.gitignore`.
