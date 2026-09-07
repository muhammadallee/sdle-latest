# WorkItems — the unit of work

**Applies to:** SDLE v1.17
**Authority:** `scripts/sdle.py`. Every constant named below is read out of the
engine — `RUNTIME_FREE_COMMANDS`, `INDEX_COLUMNS`, `ACTIVE_CONTEXT_SETTERS`,
`Paths`, `resolve_decision`. This document is a derived view. If it and the
engine disagree, the engine is right and this file is the defect.

---

## 1. What a WorkItem is

A **WorkItem** is one tracked piece of work with its own lifecycle state. It is
the unit SDLE runs: a phase, a flow, a gate ledger and an audit chain all belong
to a WorkItem, never to the repository.

Before v1.14 the runtime was repository-global — one `.workflow/` directory, so
one lifecycle at a time. As of v1.14 the runtime is **WorkItem-scoped**, and as
of v1.17 that is the only runtime there is. A repository can carry as many
WorkItems as you like, concurrently, on the same branch or on different ones,
and they do not interact.

---

## 2. On-disk layout

```
workitems/
  index.md                     the registry — the list of WorkItems that exist
  .active-context.json         which WorkItem is "current" (a hint, never a truth)
  <workitem-id>/
    workitem.json              identity: id, name, type, created
    specs/                     Spec Kit's own artifacts — SDLE never writes these
    .sdle/                     the runtime
      state.json               phase, flow, approvals, fingerprints
      audit.md                 append-only, hash-chained
      lock                     the session lock (gitignored)
      execution.json           the execution record
      governance.json          the risk assessment and derived gate policy
      reviews.json             artifact review records
      discovery.json           brownfield discovery evidence
      implementation-manifest.md
      completion-summary.json
      evidence/                gate evidence
```

**Everything under `workitems/` is versioned by design** except
`workitems/*/.sdle/lock`, which is the only ignored path. The record of what was
decided, when, and on what evidence is meant to be reviewable in the same commit
history as the code it governed.

**Everything under `workitems/` is written only by the engine** (invariant 6),
with one carve-out: `workitems/<id>/specs/` holds Spec Kit's artifacts, which
SDLE neither writes nor governs. The write-fence hook enforces exactly that
boundary — see §7.

---

## 3. Isolation

Two WorkItems share nothing. Concretely:

- separate `state.json`, so a phase advance in one does not move the other;
- separate `audit.md`, each verifying independently — neither chain contains the
  other's execution id;
- separate `lock`, so a session holding one WorkItem never blocks another;
- separate `execution.json`, `governance.json`, `reviews.json`, `discovery.json`
  and `evidence/`.

A full run of one WorkItem leaves the other's whole `.sdle/` byte-identical.
That is asserted, not assumed.

---

## 4. The registry — `workitems/index.md`

`index.md` is a Markdown table with **exactly** these columns, in this order:

| Created | WorkItem | Type | Title | Synopsis |
|---|---|---|---|---|

The first line must be `# Work Items`. A header row and a separator row must
follow. Every data row must have exactly five cells.

**Anything else is `index_malformed` — an integrity failure, exit 3.**

### Why a malformed index is never auto-repaired

The registry is what makes resolution unambiguous. A file SDLE cannot parse is a
file whose meaning SDLE does not know, and "repairing" it means *guessing* what
the author meant — which is precisely what contract §9 forbids the resolver to
do. So:

- `index_malformed` refuses at exit 3;
- the file is left **byte-identical**;
- `workitem create` refuses too, rather than appending a row to a file it could
  not read.

The commonest cause is an unresolved merge: two branches each registered a
WorkItem, and `<<<<<<<` / `=======` / `>>>>>>>` markers are now in the table.
Resolve the merge by hand, keeping both rows. If a badly-resolved merge produced
two rows with the same id, `sdle.sh validate` reports it as a duplicate ERROR.

---

## 5. Resolution — how a command finds its WorkItem

`resolve_decision` runs contract §9's ladder. It is **pure**: it reads, it never
writes, and it never guesses.

| Rung | Condition | Result |
|---|---|---|
| 1 | `--workitem <id>` given | Binds if registered; `unknown` if not |
| 2 | The launch directory is inside `workitems/<x>/` | Binds `<x>` if registered; **refuses** if the directory exists but is unregistered |
| 3 | Exactly one WorkItem is registered | Binds it |
| 4 | A persisted, still-valid active context | Binds it |
| 5 | A **unique** Git-branch match | Binds it |
| 6 | Zero WorkItems registered | `workitem_required` |
| 7 | Anything else | `workitem_ambiguous` — candidates listed, **no pick** |

Two details are load-bearing.

**Rung 2 refuses rather than falling through.** Binding some other WorkItem
while the developer is standing inside `<x>` would be the silent wrong pick §9
exists to prevent.

**Rung 5 applies the 0/1/>1 rule to a set.** Two WorkItems on one branch stay
ambiguous. There is no tie-break, no ordering preference, and no "most recent".

Rungs 4 and 5 are only reachable with two or more registered WorkItems, so the
Git subprocess of rung 5 never runs in a single-WorkItem repository.

### The rung that was removed

Up to v1.16 there was a sixth rung between 5 and "none": if nothing was
registered but `.workflow/state.json` existed, the engine bound the legacy
repository-global runtime. **v1.17 deleted it.** It was deleted, not replaced by
an inference — with zero WorkItems the answer is `none` whether or not legacy
state exists.

Nothing is stranded by the removal. The refusal names the two-step recovery, and
both steps are runtime-free (§6), so neither reaches this ladder and neither can
be locked out by it:

```bash
sdle.sh workitem create --name "<name>"
sdle.sh migrate-workflow --workitem <id>
```

`migrate-workflow` **reads** `.workflow/` and never writes, renames or deletes
it. After a migration — successful, refused, or interrupted at any write point —
every file under `.workflow/` has the SHA-256 it had before.

---

## 6. Which commands need a WorkItem

Most commands bind one. `RUNTIME_FREE_COMMANDS` is the exhaustive set that does
not, and each is runtime-free for a stated reason:

| Command | Why it needs no WorkItem |
|---|---|
| `lint-skill`, `sha`, `constants` | Repository- or input-scoped; no lifecycle state involved |
| `workitem` | It is how a WorkItem comes to exist |
| `migrate-workflow` | It is the other half of the recovery above |
| `validate` | It exists to diagnose repositories too broken to resolve, so it must never be gated on resolution succeeding. It runs the ladder speculatively and turns a refusal into a finding |
| `config` | Repository-global by definition (§11) |
| `governance policy` | Reads a repository-scoped policy. `assess`, `show` and `gates` are WorkItem-scoped and bind explicitly |
| `discovery schema` | Reports the closed §14 category vocabulary, which must be answerable before any workflow exists. `assess` and `show` bind explicitly |
| `baseline` | The convergence invariant is a property of the repository, not of any WorkItem |

For **every other** command, a successful bind returns a WorkItem. There is no
longer any code path that runs a lifecycle command with no WorkItem bound.

---

## 7. `.workflow/` — its two surviving roles

`.workflow/` is **archival**, not transitional. It is no longer a runtime, and
v1.17 is not going to make it one again. It survives as exactly two things:

1. a **migration source**, read by `migrate-workflow` and never written; and
2. a **project-root marker** — `PROJECT_ROOT_MARKERS` still carries
   `('.workflow', 'state.json')`, without which a legacy-only repository could
   not be discovered and therefore could not be migrated at all.

It is also still fenced (`hooks.py::FENCED`), still an entry in
`SDLE_OWNED_PREFIXES`, and still gitignored. A migration source that could be
edited by hand between the read and the write is not a migration source.

---

## 8. The active context

`workitems/.active-context.json` records which WorkItem was last selected. It is
a **convenience, not an authority**: rung 4 consults it, and only after rungs 1–3
have declined. It is validated against the registry before it is honoured, so a
stale entry naming a deleted WorkItem is ignored rather than obeyed.

It has exactly three writers — `ACTIVE_CONTEXT_SETTERS`:

```
init · use · migrate-workflow
```

That constant is enforced, not documentary: `write_active_context` raises if
handed any other `set_by`. Adding a fourth writer means changing the constant
deliberately.

Resolution itself never writes it. That purity is what lets the `dirty-tree`
hook run the ladder speculatively from a `PreToolUse` callback without becoming
a second writer.

---

## 9. The write fence

`workitems/` is one of four fenced roots (`.workflow`, `workitems`,
`requirements`, `guidance`). The hook denies hand-edits to the registry,
`workitem.json` and the whole `<id>/.sdle/` runtime, and carves out exactly one
path: `workitems/<id>/specs/`.

The fence matches on the **repository-relative** path, mirroring
`SDLE_OWNED_PREFIXES`, so it denies what the engine owns and nothing more —
`docs/workitems/`, for instance, is not fenced. Candidate paths are normalised
before matching, so `workitems/<id>/specs/../.sdle/state.json` does not escape
through the carve-out.

The hook is a **tripwire**. Where it overlaps the engine, the engine's refusal at
the choke point is the guarantee: skipping the hook does not get an unaudited
write past `sdle.py`.

---

## 10. Recovery

Refusal-by-refusal procedures — `workitem_required`, `workitem_ambiguous`,
`index_malformed`, corrupt state, a broken chain, a fence denial — are in
[`docs/troubleshooting/`](../troubleshooting/README.md).
