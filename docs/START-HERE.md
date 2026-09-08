# Start here

**Applies to:** SDLE v1.17

SDLE is an SDLC orchestrator for Claude Code. You describe what you want built;
it runs the work through a governed lifecycle — specify, plan, implement,
review — and stops at every checkpoint that needs a human decision.

It wraps [GitHub SpecKit](https://github.com/github/spec-kit), but you never
type a SpecKit command. You talk to SDLE.

---

## The four ideas

Everything else in this documentation set is detail on one of these.

### 1. A WorkItem is the unit of work

One feature, one defect, one hotfix. Each has its own directory under
`workitems/`, its own state, its own append-only audit ledger, and its own
lock. Two WorkItems in one repository cannot see or corrupt each other's
runtime.

### 2. A flow decides which phases run

There is a 21-phase registry, and a *flow* is an ordered subset of it. Five
exist:

| Flow | Phases | Gates | Use when |
|---|---:|---:|---|
| `GREENFIELD` | 18 | 8 | New project, no established baseline |
| `BROWNFIELD_DISCOVERY` | 19 | 8 | Existing codebase, first WorkItem |
| `ITERATIVE` | 16 | 7 | Existing codebase with a valid baseline |
| `DEFECT_FIX` | 14 | 6 | A bug, with impact analysis first |
| `HOTFIX` | 10 | 3 | Urgent — shorter, but never ungoverned |

A hotfix does not need a constitution review. A first pass over an unfamiliar
codebase does need discovery. The flow is chosen once, when the WorkItem
starts, and is never re-bound.

### 3. Gates are where a human decides

A gate halts the workflow and shows you the artifact **in the conversation** —
you never open a file to approve it. You approve, or you reject with comments
and it remediates.

Which gates are *required* depends on assessed risk. Low-risk work can omit a
design review; high-risk work cannot. Some floors are absolute: anything
touching authentication, credentials, payments or a production security
boundary is forced to HIGH or CRITICAL, **and the model cannot lower a floor** —
that decision belongs to deterministic policy, not to Claude.

### 4. The engine refuses; it does not warn

The mechanical layer is `scripts/sdle.py` — plain Python, no dependencies. It
owns state transitions, gate enforcement, artifact fingerprinting, the audit
hash chain, drift detection and locking.

When something is wrong it **refuses and exits non-zero**. It does not print a
warning and continue. You cannot skip a gate by asking nicely, forward-jump
past a phase, or approve an artifact that changed after it was reviewed. That
refusal is the product; the prompts are presentation.

---

## Where to go next

**I want to try it.**
→ [Quick Start in the README](../README.md#quick-start) — prerequisites,
installing into your project, and your first run.

**I want to see what a real run looks like before installing.**
→ [`dry-runs/01-happy-path.md`](dry-runs/01-happy-path.md) — a complete
conversation transcript, start to finish.

**I want to learn a specific flow.**
→ [`tutorials/`](tutorials/README.md) — a walkthrough per flow, plus a
GREENFIELD tour covering every customization surface.

**Something has gone wrong.**
→ [`troubleshooting/`](troubleshooting/README.md) — recovery procedures for
refusals, corrupt state, broken audit chains and stale baselines.

**I need the authoritative detail.**
→ [`SDLE-Reference-Guide.md`](SDLE-Reference-Guide.md) — the canonical
reference: every phase, the state schema, the glossary, worked examples.

**I want to know why it is built this way.**
→ [`architecture/`](architecture/) — eight ADRs recording the decisions and
what was rejected.

**I am looking for a specific topic.**
→ [The documentation index](README.md) — every document, and who it is for.

---

## What SDLE is not

- **Not a CI system.** It governs how work is produced, not how it is built,
  tested in CI, or deployed.
- **Not a project tracker.** A WorkItem is a lifecycle record, not a ticket.
- **Not autonomous.** It runs the work, then stops and waits for you at every
  gate the risk policy requires. That is the point of it.
