# WorkItems — the unit of work

**Authority:** `scripts/sdle.py`. Every constant named below is read out of the
engine — `RUNTIME_FREE_COMMANDS`, `INDEX_COLUMNS`, `ACTIVE_CONTEXT_SETTERS`,
`Paths`, `resolve_decision`. This document is a derived view. If it and the
engine disagree, the engine is right and this file is the defect.

---

## 1. What a WorkItem is

A **WorkItem** is one tracked piece of work with its own lifecycle state. It is
the unit SDLE runs: a phase, a flow, a gate ledger and an audit chain all belong
to a WorkItem, never to the repository.

The runtime is **WorkItem-scoped**, and that is the only runtime there is. A
repository can carry as many WorkItems as you like, and their **records** never
interact: state, audit, evidence, locks and identity are per WorkItem, and one
WorkItem's records are excluded from another's Gate 7 manifest and security
evidence.

**Two WorkItems may not implement in the same working directory at the same
time.** That is a real constraint, not advice. From `implement preflight` —
which pins the commit the work is measured from — until the security review is
complete, SDLE measures the implementation as a diff of the *working tree*
against that commit. Git cannot say which WorkItem wrote a given line of
application code, so two implementations sharing one directory put each other's
code into each other's manifest, secrets scan and security-review diff. A
reviewer would then be approving changes belonging to a gate they are not
standing at.

**A branch is not a workspace.** Two branch names do not give you two
workspaces: a working directory has exactly one branch checked out, so switching
between them is taking turns, not working concurrently. Taking turns is fine —
the constraint is about *simultaneous* implementation. What gives you two
workspaces at once is a second working directory: a `git worktree`, or a
separate clone.

**The window is about what other WorkItems write, not only about what they are
doing.** Its boundary is the evidence, not the phase name: while a WorkItem is
between `implement preflight` and the end of its security review, anything
another WorkItem writes in that directory to a path the exclusion does not cover
lands in the first WorkItem's manifest and diff.

What the exclusion covers, read from `implementation_exclusions` in
`scripts/sdle.py`:

| Excluded | Not excluded |
|---|---|
| This WorkItem's own runtime, `workitems/<id>/.sdle/` | Anything else under its own directory |
| The repository-global configuration root, `.sdle/` | `requirements/` |
| Spec Kit's tree, `.specify/` | `design/` |
| This WorkItem's Spec Kit feature directory | `reviews/` |
| **Every other WorkItem's whole tree**, `workitems/<other>/` (F-102) | `clarifications/` |
| The registry file, `workitems/index.md` | Application code, which is the point |

So a second WorkItem working *inside its own directory* is invisible to the
first one's evidence — that is what F-102 fixed. What is still shared is the
repository-level set on the right: `requirements/`, `design/`, `reviews/` and
`clarifications/` are deliberately kept in, because they are genuine
implementation inputs and outputs and dropping them would hide real work. A
second WorkItem generating a design into `design/`, saving a clarification or
recording a review therefore lands in the first one's manifest and diff just as
an implementation would.

Outside that window, runtime **records** never interact: state, audit, evidence,
locks and identity are per WorkItem. The repository-level directories above are
still shared — `design/app/app-design.md` has one path, whichever WorkItem
writes it — so two WorkItems that both reach a design phase overwrite each
other's artifact wherever they share a working directory. That is a known
limitation of those shared paths, not something the binding changes: the
binding says which *requirement documents* a WorkItem is about, and has no
bearing on where generated artifacts land.

```bash
git worktree add ../feature-b -b feature-b   # a second working directory
cd ../feature-b                              # drive WorkItem B here
```

The resolution ladder is built for this — each worktree resolves its own
WorkItem with no `--workitem` flag — and two worktrees driving two WorkItems to
completion with independent ledgers is covered by the suite.

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

**Everything under `workitems/` is versioned by design** except two
developer-local paths that `.gitignore` excludes: `workitems/*/.sdle/lock`, the
session lock, and `workitems/.active-context.json`, which records which WorkItem
this working directory last selected. The record of what was
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

### A retired runtime never binds

No rung binds a repository-global `.workflow/state.json` from a retired runtime, and
none infers one. With zero WorkItems registered the answer is `none` whether or not
such state exists.

Nothing is stranded by that. The refusal points at `workitem create`, which is
runtime-free (§6), so it never reaches this ladder and cannot be locked out by it:

```bash
sdle.sh workitem create --name "<name>"
```

SDLE does not run, migrate or write the retired directory: every file under
`.workflow/` keeps the SHA-256 it had.

---

## 6. Which commands need a WorkItem

Most commands bind one. `RUNTIME_FREE_COMMANDS` is the exhaustive set that does
not, and each is runtime-free for a stated reason:

| Command | Why it needs no WorkItem |
|---|---|
| `lint-skill`, `sha`, `constants` | Repository- or input-scoped; no lifecycle state involved |
| `workitem` | It is how a WorkItem comes to exist |
| `validate` | It exists to diagnose repositories too broken to resolve, so it must never be gated on resolution succeeding. It runs the ladder speculatively and turns a refusal into a finding |
| `config` | Repository-global by definition (§11) |
| `governance policy` | Reads a repository-scoped policy. `assess`, `show` and `gates` are WorkItem-scoped and bind explicitly |
| `discovery schema` | Reports the closed §14 category vocabulary, which must be answerable before any workflow exists. `assess` and `show` bind explicitly |
| `baseline` | The convergence invariant is a property of the repository, not of any WorkItem |

For **every other** command, a successful bind returns a WorkItem. No code path
runs a lifecycle command with no WorkItem bound.

---

## 7. `.workflow/` — detection only

`.workflow/` is the retired repository-global layout. Nothing runs against it, and
it survives as detection only:

- a **project-root marker**: `PROJECT_ROOT_MARKERS` still carries
  `('.workflow', 'state.json')`, so a repository whose only runtime is that
  directory is found and refused with an explanation rather than treated as empty; and
- the thing the `workitem_required` and `legacy_workflow_present` refusals point at.

It is also still fenced (`hooks.py::FENCED`), still an entry in
`SDLE_OWNED_PREFIXES`, and still gitignored, so its contents stay exactly as found.

---

## 8. The active context

`workitems/.active-context.json` records which WorkItem was last selected. It is
a **convenience, not an authority**: rung 4 consults it, and only after rungs 1–3
have declined. It is validated against the registry before it is honoured, so a
stale entry naming a deleted WorkItem is ignored rather than obeyed.

It has exactly two writers — `ACTIVE_CONTEXT_SETTERS`:

```
init · use
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
