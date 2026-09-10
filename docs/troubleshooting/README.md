# Troubleshooting — recovery procedures

**Applies to:** SDLE v1.17

SDLE **refuses; it does not warn.** A refusal is final, it is structured, and it
names a way out. Nothing in this document is a workaround: every procedure below
is the intended path.

## Read the exit code first

| Code | Meaning | What to do |
|---|---|---|
| `0` | Success | — |
| `1` | **Refused.** A rule said no | Read the reason. Do what it names |
| `2` | **Usage error.** The invocation was wrong | Fix the flags |
| `3` | **Integrity failure.** Something on disk is not trustworthy | Stop. Do not "repair" by hand until you have read the section below |

JSON goes to stdout, human text to stderr. Parse the `reason` and `data` fields;
do not pattern-match the prose.

---

## 1. `workitem_required` — nothing is registered

**Exit 1.** No WorkItem is registered in this repository.

### 1a. A new repository

```bash
sdle.sh workitem create --name "<name>"
```

### 1b. A repository still on the pre-v1.14 runtime

If `data` carries a `legacy_state` path, this repository has a repository-global
`.workflow/state.json` from before v1.14. As of v1.17 that is **not a runtime**
— SDLE no longer runs one. Recover in exactly two steps, **in this order**:

```bash
sdle.sh workitem create --name "<name>"
sdle.sh migrate-workflow --workitem <id>
```

Both commands are runtime-free: neither resolves a WorkItem before it runs, so
neither can be locked out by the very condition you are recovering from.

`migrate-workflow` **never modifies, renames or deletes `.workflow/`.** It is
left in place, byte for byte, as an archive — whether the migration succeeds,
refuses, or is interrupted partway through. Re-running an interrupted migration
is safe.

Migration refusals you may see:

| Reason | Meaning |
|---|---|
| `target_exists` | The WorkItem already has a runtime. Migrating would overwrite it |
| `legacy_state_missing` | There is no `.workflow/state.json` to migrate |
| `legacy_state_invalid` | The legacy state will not parse. It is not safe to move |
| `legacy_audit_broken` | The legacy audit chain does not verify. Migrating would import a tampered ledger |

`init` refuses `legacy_workflow_present` while a legacy runtime is on disk.
That is deliberate: initialising beside it would create a second runtime that
`migrate-workflow` would then refuse to move.

You can confirm a legacy runtime is still on disk at any time — `sdle.sh
validate` reports it as `runtime_state_outside_workitem`.

---

## 2. `workitem_ambiguous` — several are plausible

**Exit 1.** More than one WorkItem is registered and none was named.

**SDLE never picks one for you.** Do not add a tie-break, and do not read the
candidate order as a ranking.

```bash
sdle.sh workitem resolve      # always exits 0; reports candidates with evidence
sdle.sh <command> --workitem <id>
sdle.sh workitem use --workitem <id>   # persist it for this working directory
sdle.sh workitem use --clear           # forget it
```

`workitem resolve` is a diagnostic and never refuses, so it is always safe to
run first. The right resolution is a **human** answer: show the candidates, ask,
and let the answer re-enter the engine as an explicit `--workitem`.

Related: `workitem_unregistered` means you are standing inside a
`workitems/<x>/` directory that is not in the registry. SDLE refuses rather than
binding a neighbouring WorkItem.

---

## 3. `feature_ambiguous` — two Spec Kit feature directories in one tier

**Exit 1.** `feature resolve` found more than one candidate feature directory in
the tier it chose, and it will not pick by recency. Recency is not evidence of
ownership, and picking silently is how one WorkItem ends up holding another's
specification.

**Remedy — resolve it by precedence, not by flag.** Tier 1 is this WorkItem's
own `workitems/<id>/specs/`. Move the directory this WorkItem owns into it:

```bash
mv specs/<the-one-this-workitem-owns> workitems/<id>/specs/
sdle.sh --workitem <id> feature resolve
```

Tier 1 now yields exactly one candidate and resolution is deterministic. There
is no override flag by design.

Related: `feature_unresolved` (zero candidates — the specification step did not
produce a feature directory; the refusal lists every tier it searched) and
`speckit_capability_missing` (the installed Spec Kit cannot do what SDLE needs;
`sdle.sh feature capabilities` reports the detail and never refuses).

---

## 4. `index_malformed` — the registry does not parse

**Exit 3.** `workitems/index.md` is a strict Markdown table with the columns
`Created | WorkItem | Type | Title | Synopsis`. A row with a different cell
count, a missing heading or a missing separator row is an integrity failure.

**The engine never rewrites the file to repair it.** That is the point: the
registry is versioned, so a malformed registry is almost always a merge
conflict, and a silent repair would destroy the evidence of what each side
intended.

Typical cause — conflict markers left in the file:

```text
<<<<<<< HEAD
=======
>>>>>>> other-branch
```

**Procedure:**

1. Do not run `workitem create` hoping it will fix it. It refuses too.
2. Open `workitems/index.md` and resolve the conflict by hand, keeping **both**
   sides' rows unless one is genuinely a duplicate of the other.
3. Keep the heading, the header row and the separator row intact, and keep every
   row at exactly five cells.
4. Re-run `sdle.sh validate`.

If the merge was resolved badly and two rows now share one WorkItem id,
`validate` reports a **duplicate id ERROR**. Ids are immutable, so the fix is to
delete the row that was never real — not to rename a WorkItem that already has a
runtime on disk.

Note the ordering: in a repository with both a corrupt index and legacy state,
`init` reports `index_malformed` rather than `legacy_workflow_present`. That is
correct — a registry that will not parse is the more fundamental problem, and
you cannot migrate into a registry you cannot read.

---

## 5. Corrupt state — exit 3

`workitems/<id>/.sdle/state.json` will not parse (`state_unreadable`).

- The audit ledger is left **byte-identical**. Nothing is written on the way
  out.
- No `.tmp` sibling is left behind.
- `sdle.sh doctor` and `sdle.sh resume` still answer usefully: they name the
  file and the way out.

Recover from version control — WorkItem records are versioned by design. If the
state file was never committed, the audit ledger is the record of what happened;
read it before deciding anything.

---

## 6. A broken audit chain

`sdle.sh audit verify` reports the **first** broken entry by index, not merely
that something is wrong.

- Detection **writes nothing at all**.
- A tamper cannot be laundered by continuing to use the tool — the break stays
  visible on every subsequent verification.
- `sdle.sh audit rebaseline` is the only way past it, and the rebaseline is
  **itself an audited event**. It does not erase the break; it records that a
  human accepted it.

If you did not expect a break, treat it as a real integrity event: find out who
wrote to `audit.md` other than `sdle.py`. The write fence exists to make that
answer "nobody".

---

## 7. A stray `.tmp` file next to `state.json`

Harmless. Every write creates a **uniquely named** temp and renames that one, so
a leftover from a hard process kill is inert: it is never read as authoritative
by `state get`, `resume` or `audit verify`.

SDLE deliberately does **not** sweep temp files it did not create — a sweep
could delete a concurrent writer's in-flight temp, which is a real failure mode
in exchange for a cosmetic benefit. Delete it yourself if it bothers you.

---

## 8. `branch_mismatch`

A two-step command (`skip`, `reset`, `restart`, `implement preflight`) was
acknowledged on one branch and completed on another.

An acknowledgement names **one** checkout. Switching branch between the two
steps invalidates it, and the action does not run. Re-run the first step on the
branch you actually mean to act on.

---

## 9. `dirty_tree`, `drift_pending`, `rate_limit_exceeded`

| Reason | Meaning | Remedy |
|---|---|---|
| `dirty_tree` | Uncommitted changes where a clean tree is required | Commit or stash. SDLE's own bookkeeping under `.sdle/` is excluded and never counts against you |
| `drift_pending` | An approved artifact changed and re-approval is queued | Re-approve at the gate. `retry` deliberately refuses until then |
| `rate_limit_exceeded` | A remediation or retry loop hit its limit | Stop and reconsider. The limit exists because a loop that has failed *N* times is not going to succeed on *N+1* |

---

## 10. `session_required` and the lock

Each WorkItem has its own session lock at `workitems/<id>/.sdle/lock`. A lock on
one WorkItem never blocks another.

A fresh Claude session needs no recovery ritual: pass a new `--session` and run
`sdle.sh resume`. Resolution succeeds from durable on-disk state alone, and
deleting the developer-local `workitems/.active-context.json` loses nothing.

---

## 11. When a hook denies a write

The write fence hook denies hand-edits to SDLE-owned paths — `workitems/`,
`.workflow/`, `requirements/`, `guidance/` at the repository root. It is a
tripwire; the engine's refusal at the choke point is the actual guarantee.

**Do not route around it.** Use the matching subcommand (`state set`, `audit
append`, `gate`, `limit set`, `workitem create`). If you believe the fence is
denying a path SDLE does not own, that is a defect in the fence — report it
rather than writing the file another way.

---

## 12. `execution_id_collision` — exit 3

Every evidence file is named after an execution id,
`<prefix>-<UTC second>-<8 random hex>`, and is claimed with an exclusive create
before it is written, so existing evidence is never replaced. If three freshly
drawn ids in a row all name files that already exist, the command refuses with
exit 3. **Nothing is recorded** — no governance record, no review, no discovery
record — and no existing evidence is touched.

This does not happen by chance. It means the random source is not random, or
someone is creating files under `workitems/<id>/.sdle/evidence/` by hand. Check
for the second, then re-run the command. Do not delete evidence files to make
room. They are the record of what happened.
