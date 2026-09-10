# Dry Run 07 — Audit Integrity, Session Lock & Staleness Warning

| | |
|---|---|
| **Scenario ID** | DR-07 |
| **Flow** | `GREENFIELD` |
| **Purpose** | Resuming a workflow in a new conversation while three integrity signals fire: a fresh lock from another session, a hand-edited audit ledger, and commits newer than the last approval. |
| **Defect IDs** | D05 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `gate_design` (`14/18`, `awaiting_approval`), Gates 1–5 approved. Since then, another session touched `workitems/todo-api/.sdle/lock` 4 minutes ago with a different token, someone deleted a rejection entry from `workitems/todo-api/.sdle/audit.md`, and two commits landed on the branch |
| **Guardrails exercised** | The per-WorkItem session lock (warn-only), the audit hash chain and `accept audit`, the repository staleness notice, and `--session` as a global option |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or
> **NOT RUN** — are recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01 to Gate 6's prompt. Then, in the fixture:
- write the lock file with a foreign token;
- delete one `## AUDIT` block from `audit.md`;
- make two commits touching a recorded artifact path.

---

## Transcript

**User:** *(in a new conversation)* `status`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_design status=awaiting_approval progress=14/18 -->
📋 SDLE Status: Phase 14/18 — Gate 6: Design Approval [AWAITING APPROVAL]

⚠️ Another session may be operating on this WorkItem (lock touched 4 minutes ago).
Proceed only if you are sure no other session is active.

⚠️ Audit log integrity check failed.
workitems/todo-api/.sdle/audit.md has been edited, truncated, or written by another session.

Say `accept audit` to re-baseline the audit hash and continue (logged), or inspect
workitems/todo-api/.sdle/audit.md before proceeding.
```

*(Engine, in the order SKILL.md Step 1 prescribes:
`sdle.sh --session 5d2e81f0 lock acquire` returned `warn: true` and does not
halt, and `sdle.sh audit verify` exited 3 with `audit_chain_broken`, which
halts. `--session` is a global option, so it goes before the subcommand; the
form `lock acquire --session …` is a usage error. `audit.md` is left untouched
so the evidence can be inspected. The staleness check runs after the halt
clears.)*

---

**User:** *(inspects the ledger, confirms with the colleague who trimmed it)* `accept audit`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_design status=awaiting_approval progress=14/18 -->
📋 SDLE Status: Phase 14/18 — Gate 6: Design Approval [AWAITING APPROVAL]

Audit hash re-baselined (logged).

ℹ️ The repository has commits newer than your latest gate approval that touch recorded
artifact paths — approved artifacts may reflect a stale view of the codebase.

---
✋ APPROVAL REQUIRED — Gate 6/8: Design Approval
[... design/app/app-design.md displayed in full — abridged ...]

Artifact path: design/app/app-design.md
Fingerprint: 2f84c1d9…6e0b
---
```

*(Engine: `sdle.sh audit rebaseline` wrote its own audit entry, so a re-baseline
can never happen silently. Then `sdle.sh repo-staleness` reported `stale`,
which is informational and shown once per conversation.)*

---

### Variant — the mismatch was NOT expected

**User:** `show state`

*(The pending acknowledgement is cancelled by the new command. On the next turn
`audit verify` fails again with the same halt, and the mismatch does not go
away until someone re-baselines it on purpose.)*

---

## Artifacts, state and audit

- **Lock:** warn-only, per WorkItem, rewritten on every state save with the
  session token. A lock on one WorkItem never blocks another.
- **Audit chain:** every entry carries the digest of the one before it, and
  `state.audit_sha` fingerprints the whole ledger. A mismatch is
  tamper-*evidence*, not proof of malice: another session's legitimate write
  also trips it, which is what you want surfaced.
- **`accept audit`** is the only way past, and it is itself logged.
- **Staleness:** compares the newest approval timestamp with commits touching
  recorded artifact paths. It never halts.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Any phase movement while the chain is broken | Halted at Step 1 | Unchanged |
| `lock acquire --session <token>` (option after the subcommand) | Usage error, exit 2 | Unchanged |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| An edited ledger halts until re-baselined | `tests/test_integration_06_to_09.py::test_07_edited_audit_halts_until_rebaselined` |
| The mismatch persists until acknowledged | `tests/test_integration_06_to_09.py::test_07_the_mismatch_persists_until_acknowledged` |
| A foreign fresh lock warns but never halts | `tests/test_integration_06_to_09.py::test_07_foreign_fresh_lock_warns_but_never_halts` |
| Staleness is scoped to recorded paths | `tests/test_integration_06_to_09.py::test_07_staleness_is_scoped_to_recorded_artifact_paths` |
| Global options precede the subcommand | `tests/test_units_documented_commands.py::test_the_position_check_catches_the_forms_that_were_wrong` |
