# The lifecycle — phase registry, flows and gates

**Applies to:** SDLE v1.17
**Authority:** the constant tables in `.claude/skills/sdle/SKILL.md`, parsed by
`scripts/sdle.py`. Read them with `sdle.sh constants`. This document is a
derived view; the engine is the source of truth.

---

## 1. A registry, not a fixed sequence

Up to v1.15 SDLE assumed one universal 18-phase lifecycle. It no longer does.

- **`PHASE_SEQUENCE` is a 21-entry phase *registry*.** It says which phases
  exist, what each is called, which artifact each owns and which gate (if any)
  follows it.
- **A *flow* is an ordered subset of that registry**, and a flow is what a
  WorkItem actually traverses.

Five flows ship:

| Flow | Phases | For |
|---|---|---|
| `GREENFIELD` | 19 | A new product or component in a repository with no baseline |
| `BROWNFIELD_DISCOVERY` | 20 | The first WorkItem in an existing repository — adds the `discovery` phase |
| `ITERATIVE` | 17 | Ordinary change in a repository that already has a sound baseline |
| `DEFECT_FIX` | 15 | A defect, entering through `impact_analysis` |
| `HOTFIX` | 11 | An urgent production fix — the shortest flow that still gates |

Counts include the terminal `complete` phase. `GREENFIELD` is **frozen in the
engine** rather than declared in `FLOW_PHASES`, so a new registry row can never
silently join it.

The flow is bound **once**, at `init`, and never re-bound. A governance record
that later proposes a different flow is refused `flow_mismatch`. Read the bound
flow with `sdle.sh flow show` (read-only).

Because phase counts differ per flow, **progress fractions, gate numbers and
gate labels are all derived per flow**. Never read a phase number, a gate number
or an `N/18` from a table — take it from the engine's response.

---

## 2. Gates

Eight approval gates exist in the registry:

```text
gate_constitution  gate_spec   gate_plan     gate_tasks
gate_analyze       gate_design gate_implement gate_security
```

Which of them a given WorkItem must clear is **not** fixed. It is derived from
three independent facts:

1. **Flow membership** — a gate the bound flow does not contain is reported
   `not_in_flow`. It is never "quietly satisfied".
2. **Risk policy** — see `docs/risk-and-gates/`.
3. **Change type** — a defect always adds `gate_tasks`, for example.

Every gate is reported with one of exactly three dispositions: `required`,
`omittable`, `not_in_flow`.

### Gate discipline

- No phase advances past a gate without an explicit human `approve`.
- **No forward jumps.** `advance` moves exactly one step along the bound flow.
- **Gate content is displayed in conversation.** The user approves what they can
  see; they are never asked to open a file.
- **Gates stay in the parent context.** A gate needs artifact content in front
  of a human, so nothing holding a gate is ever delegated to a subagent.
- An `omittable` gate may be omitted only with recorded evidence, and the
  orchestrator must offer the human both options.

---

## 3. Moving through a flow

| Command | What it does |
|---|---|
| `header` | The state assertion header. Emitted **first**, every turn |
| `resume` | Everything a fresh session needs to pick a WorkItem up. Read-only |
| `advance` | Move to the next phase of the bound flow |
| `gate show` / `approve` / `reject` / `omit` | Gate disposition and decisions |
| `artifact` | Artifact bookkeeping and SHA fingerprints |
| `drift` | Detect a changed approved artifact and queue re-approval |
| `remediate` | Post-rejection re-run, rate-limited |
| `skip` / `restart` / `reset` | Two-step confirmed deviations |
| `checkpoint` | In-phase crash recovery |

**State first.** Read state before any action and emit the state assertion
header before anything else. **Fail safe:** on any failure, freeze — never
advance the phase.

---

## 4. Two-step commands and the branch guard

`skip`, `reset`, `restart` and `implement preflight` are two-step: the first
call reports what will happen and records a pending confirmation, the second
performs it.

Since v1.17, an acknowledgement of a mismatched branch is **attributed to the
branch it was given for**. The `pending_branch_ack` state field records that
branch, and the second step refuses `branch_mismatch` if the checkout moved in
between. Before v1.17 an acknowledgement was standing permission for whatever
branch happened to be checked out at step two — a declared fail-open, now
closed.

---

## 5. Artifacts, drift and the audit ledger

Every generated artifact is fingerprinted (SHA-256) and recorded. If an approved
artifact changes afterwards, `drift` detects it and queues re-approval;
`retry` refuses while a drift re-approval is pending.

Every state transition, approval, rejection, omission and deviation is appended
to the WorkItem's `audit.md` as a **hash-chained** entry. The chain is
tamper-**evident**: `audit verify` locates the first broken entry, writes
nothing when it finds one, and `audit rebaseline` — itself audited — is the only
way past. A **refused** command leaves `audit.md` byte-identical.

`sdle.py` is the single writer of `state.json` and `audit.md`. The write fence
hook is a tripwire in front of that rule; the engine's refusal at the choke
point is the guarantee.
