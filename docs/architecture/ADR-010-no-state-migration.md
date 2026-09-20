# ADR-010 — No state migration: refuse another schema, detect the retired runtime

**Status:** Accepted
**Date:** 2026-09
**Supersedes:** ADR-008 §3 and §3.1 (the preserved migration path). The rest of ADR-008 stands.

---

## 1. The decision

SDLE reads exactly one state schema, `CURRENT_VERSION`. A `state.json` written under any other
schema is **refused, never upgraded, reinterpreted or reset**, and the remedy is a new WorkItem.
There is no `migrate`, no `migrate-workflow`, and no version chain in the engine.

The repository-global `.workflow/` from the retired runtime is **detected, never run**. Nothing
binds it, nothing writes it, and nothing moves it. What remains of it is exactly what a refusal
needs: a project-root marker, a write fence, and one pointer at the way out.

## 2. Why

ADR-008 kept a migration path so a pre-WorkItem repository could be recovered in place. Keeping it
cost more than it protected:

- **A retained path needs its own refusals, prose and tests, and they drift.** Migration text
  outlived the code paths it described, in the troubleshooting runbook, the Reference Guide and
  the ADRs, and each copy said something slightly different about what a user should do.
- **A migration is a rewrite of a governed record.** The audit chain and drift detection assume
  one writer and one schema. Reinterpreting an old state under today's flow, gate and label rules
  can produce a plausible-looking record that no gate ever approved.
- **The chain grew with every state change.** Each schema change needed a migration row, a
  migration step and a lint rule to keep them in step (ADR-005 D11 counts sixteen rows).

Refusing is the conservative choice: the old record stays exactly as it was, versioned in Git
where WorkItem records already live, and a new WorkItem starts from a state the engine can prove.

## 3. What the engine does now

| Situation | Behaviour |
|---|---|
| `state.json` of another schema version | Every command that interprets state refuses `unsupported_state_version` (exit 1); the file and the audit ledger are left byte-for-byte as found |
| Inspecting such a file | `state get` returns a stored field as written and `audit verify` checks the ledger's hash chain; neither interprets the state, so both read any version. `state dump` and `doctor` derive a flow, a label and a verdict, so they refuse |
| `.workflow/state.json` with no WorkItem registered | Runtime commands refuse `workitem_required`; the message says SDLE does not run or migrate it and points at `workitem create` |
| `init` while `.workflow/state.json` exists | Refused `legacy_workflow_present`, whatever WorkItems are registered: a second runtime beside it would leave two competing records. The user removes it or moves it aside |
| Editing `.workflow/` | Denied by the write fence, so a hand edit cannot corrupt a record nothing can repair |
| Finding the project root of a repository that has only `.workflow/` | Still works: the marker stays, so the refusal can reach the user instead of the engine reporting no project |

## 4. Consequences

- A repository still on the retired runtime, or holding a state of an older schema, cannot be
  continued in place. It starts a new WorkItem; the old record is not touched.
- Changing the state schema means changing the state template and `CURRENT_VERSION` together and
  updating the field list in `tests/test_units_invariants.py`. There is no migration step to write.
- The refusal is proven, not asserted: `tests/test_units_state.py` covers the refusal, the
  byte-identical non-mutation, and the two commands that still read.

## 5. Not decided here

Whether a supported in-place upgrade should ever return is a product question for a future
schema change that has a user to protect. It would be a new ADR with its own tests, not a
restoration of the removed chain.
