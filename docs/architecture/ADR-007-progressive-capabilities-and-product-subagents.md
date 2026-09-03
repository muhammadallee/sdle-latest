# ADR-007 — Progressive Capabilities and Product Subagents

**Status:** Accepted
**Date:** 2026-09
**Supersedes:** nothing. **Extends:** ADR-001 (deterministic core), ADR-003
(governance inputs and artifact review), ADR-004 (declarative flow model).
**Context:** contract §16, executed under the constraint §16 opens with.

---

## 1. The problem, stated as the contract states it

§16 asks for two things at once and they pull against each other:

> Optimize reasoning quality/context **without moving authority back into
> prompts**.

Every architectural decision before this one moved authority *into*
`scripts/sdle.py`. Skills and subagents are the two constructs most able to
move it quietly back out. A capability file is a prompt, and a prompt that
acquires a rule is a second source of truth. A subagent is a Claude session,
and a Claude session with a shell can approve a gate.

So this decision is organised around a single rule, which is also its
acceptance criterion:

> **This work adds no new authority. It adds a deterministic way to decide
> *what to load* and *who may look*, and it adds nothing that can decide *what
> may happen*.**

No state field, no migration row, no version bump, no gate, no policy value and
no mutating command. `resume` is the only new command and it writes nothing.

---

## 2. Decision

### 2.1 What a phase loads is a parsed constant, not a judgement

Before this, the orchestrator decided which module to read from prose:
*"Read `modules/phase-execution.md` and follow it"*, *"Read
`modules/gate-protocol.md` when `current_phase` is a gate"*. That is a rule the
model re-derives every turn, and a rule the model re-derives is a rule the
model can get wrong.

`CAPABILITY_MAP` in `SKILL.md` maps every phase in the registry to the
capability files that phase requires. The engine parses it, `sdle.sh resume`
reports the row for the current phase, and the orchestrator loads what it is
told. This is the same move `flow show` made for traversal and
`governance gates` made for gate requirement.

It lives in `SKILL.md` and not in a module because it is needed *before*
anything is loaded, and `SKILL.md` is the always-loaded file. `SKILL.md` is
never a value in the map: it is the orchestrator, not a capability, and
`lint-skill` fails if it appears there.

### 2.2 The map is a floor, not a ceiling

A row is what a phase **requires**. Cross-references inside a loaded file
remain exactly as they are and are still followed — remediation at
`gate_design` still sends the reader back to phase execution, and that still
works. Pretending the prompt layer stops reading at the row would be a claim
the design cannot keep.

What makes it *progressive* is still objective and machine-checked: every row
is a **strict** subset of the union of all rows, and the union is exactly the
`modules/*.md` files on disk. A phase that needs everything is a phase for
which nothing was decided, and `every_row_is_a_strict_subset_of_the_capability_set`
fires on it.

### 2.3 Splitting the prompt layer had to make `lint-skill` stronger, not weaker

`lint-skill`'s three content checks — no PowerShell-only cmdlet, no hardcoded
progress fraction, no restated discovery vocabulary — read a file set. That set
used to be four hardcoded properties. A new capability file would have been
invisible to all three until somebody remembered to extend the list.

The set is now **derived**: `SKILL.md`, plus every `modules/*.md`, plus every
`.claude/agents/sdle-*.md` that is not part of the migration control plane. A
future capability file cannot be added to an unlinted corner, because there is
no longer a corner. The same reasoning applies to the invariant-7 restatement
search in the test suite, which now scans the product agent prompts too.

### 2.4 `sdle resume`: the cold-start question, answered from disk

§16's exit criterion is *"a fresh Claude session can resume a WorkItem safely
and load only relevant phase context."* `resume` is that criterion made
executable: one read-only call that returns identity, position, status,
progress, the state header verbatim, the gate disposition when at a gate, what
is pending, the branch mismatch, and `capabilities`.

It is **pure composition**. It calls the same derivations `header`,
`state get`, `flow show` and `gate show` call, and renders nothing of its own.
A second renderer of the header, in the decision whose job is defending
invariant 7, would be the worst available irony. `gate_disposition` was
extracted out of `cmd_gate_show` for the same reason, rather than copied.

It does **not** migrate. A read-only command that silently migrates is not
read-only. If a caller needs `migrate`, it calls `migrate`.

### 2.5 Four product subagents that can read and reason and nothing else

`sdle-discovery`, `sdle-design-review`, `sdle-code-review` and
`sdle-security-review` — §16's four named uses. Each may inspect, reason and
return structured findings as its final message. Each **MUST NOT** mutate
lifecycle state, approve a human gate, bypass deterministic policy, or become
an independent workflow controller.

Those four inabilities are not asserted in prose. They are expressed twice, and
each layer holds if the other is removed:

1. **The grant.** `tools: Read, Grep, Glob`. No `Bash`, so the agent cannot run
   `sdle.sh` at all — not `gate approve`, not `advance`, not anything. No
   `Write` or `Edit`, so it cannot reach the filesystem. No `Agent`/`Task`, so
   it cannot spawn a further agent and become a controller for want of the only
   tool that would let it.
2. **The fence.** Each agent's own frontmatter registers a `PreToolUse` hook,
   `python .claude/hooks/hooks.py product-agent-fence`, matching
   `Write|Edit|MultiEdit|NotebookEdit|Bash`. If a grant is ever widened by a
   later edit, the call is denied anyway.

And `lint-skill` fails the moment either layer stops being true:
`product_agents_are_read_only`, `product_agents_declare_the_fence`,
`product_agents_declare_the_non_approval_clause`.

### 2.6 The fence denies unconditionally, unlike the other four guards

The other four hooks inspect the payload and stay silent when it does not
concern them. `product-agent-fence` does not inspect anything: every call it is
registered for is denied.

That is deliberate. A guard that read a Bash command string and denied "the
mutating sdle subcommands" would need a list of mutating subcommands — a second
source of truth for something `sdle.py` already knows, and one that fails open
on the subcommand nobody remembered to add. A product subagent has no
legitimate reason to write anything or to run anything, so denial is total.
There is no list to drift and no payload shape that gets through.

It is registered in the four agent frontmatters and **not** in
`.claude/settings.json`, because it must bind those agents and not the parent
session: the parent legitimately writes, through `sdle.py`.
`.claude/settings.json` is byte-identical to what it was before this decision.

### 2.7 One door into the governed record, and it already existed

```
subagent returns findings (text, in the parent's conversation)
        |
        v
parent displays them to a human
        |
        v
parent runs: sdle.sh artifact review --path <artifact> --type <review-type>
             --result PASS|FAIL --actor-type agent --actor-name sdle-<x>
             --evidence <pointer>
        |
        v
engine: a review record bound to the artifact's exact current SHA, plus an
        audit event
```

No new command, no new field, no new refusal. The stale-review rule applies
unchanged: if the artifact changes after the agent reviewed it, the review is
stale and the gate refuses. They return findings; they do not record them. The
parent records.

### 2.8 The engine spawns nothing

`sdle.py` reads `.claude/agents/*.md` in order to lint them. It starts no
process that could be an agent. The suite proves this structurally rather than
by vocabulary: every `subprocess.*` / `os.*` spawning call in the engine is
located by AST, the set of functions containing one is pinned, and no string
argument to any of them may name `claude`, `agent` or `Task`.

The earlier test banned the bare substring `"subagent"` in the engine source.
That ban is retired, because linting agent files honestly requires the word.
Passing by wording discipline — writing "agent" everywhere and never
"subagent" — was considered and rejected: it leaves a booby trap for the next
editor and makes a green test mean nothing.

---

## 3. What SDLE enforces, what Claude Code enforces, and what is only convention

This table is the point of the ADR. Named specialist agents *look* like
enforcement, and the arrival of four of them must not make a reader believe
that anything moved up this table. Nothing did.

| Property | Enforced by | Detectable how |
|---|---|---|
| A product subagent's declaration grants no mutating tool | **SDLE** (`lint-skill`, CI) | `product_agents_are_read_only` fires; N16 proves it fires |
| A product subagent's declaration carries the deny fence | **SDLE** (`lint-skill`, CI) | `product_agents_declare_the_fence`; N17 |
| A denied call is actually denied when the fence runs | **SDLE** (hook unit tests) | N13/N14 drive the exact frontmatter command string with Write/Edit/Bash payloads and assert `permissionDecision == "deny"` |
| The engine spawns no agent | **SDLE** (source/AST test) | N18 |
| A capability set is chosen by the engine, not the model | **SDLE** (constants + `resume` tests) | N1–N5, N9–N11 |
| A declared `tools:` list is actually applied | **Claude Code runtime** — *not* SDLE | Observed live during this work; not assertable from the suite |
| A frontmatter `PreToolUse` hook actually fires | **Claude Code runtime** — *not* SDLE | Observed live during this work; not assertable from the suite |
| The parent delegates to the *right* agent, or at all | **Convention only** | Nothing enforces it. The prompt says it |
| An `--actor-name` truthfully names who produced a finding | **Convention only** | A caller-supplied string. Unchanged by this decision, which must not imply otherwise |
| A human, not the orchestrator, typed `approve` | **Convention only** | Already recorded in ADR-006 §3 and asserted there. Nothing about it changed |

The three "convention only" rows are not defects introduced here. Two of them
predate this decision and are already documented: ADR-003 records that
`--actor-name` is a string supplied by the caller and that the engine creates,
registers and invokes nothing; ADR-006 records that the engine cannot tell
whether a human being or the orchestrator issued an approval.

### 3.1 Rejected: engine-side actor attestation

A global `--actor` flag or an `SDLE_ACTOR` environment variable that mutating
commands refuse when it says "agent" was considered and rejected.

It is set by the caller. A compliant caller sets it and gets refused; a
non-compliant one omits it and proceeds. That is a fail-open shape wearing the
costume of a control. Worse, it converts a real guarantee — the callee has no
`Bash` tool — into a self-declaration, and invites a reader to believe the
engine knows who called it, which it does not.

The honest architecture is: **the runtime constrains the agent, the engine
constrains the operation, and neither pretends to know the other's business.**
This is recorded so a later decision does not reinvent it.

### 3.2 Rejected: making the approval or omission path agent-aware

`gate approve`, `gate omit`, `gate reject` and `advance` are untouched. Not one
line. Invariant 8 — human approval gates stay in the parent Claude session —
has held since the beginning, and the way to keep it holding was to give the
agents no way to reach those verbs, not to teach those verbs about agents.

---

## 4. Consequences

**Good.**

- The orchestrator asks the engine what to load instead of deciding from prose,
  so context is scoped by a table that CI checks rather than by a habit.
- A cold session reconstructs a WorkItem in one call. Correctness stopped
  depending on conversation history for the part of the system that holds
  durable truth.
- Splitting the prompt layer strengthened the cross-file rules: the linted file
  set is derived, so it can no longer fall behind the files that exist.
- Four inabilities that used to be sentences in a prompt are now three named
  lint checks and a hook that denies.

**Costs, stated plainly.**

- Two of the enforcement points belong to the Claude Code runtime, not to SDLE.
  If a future runtime ignored a declared `tools:` list or a frontmatter hook,
  the suite would stay green. Section 3 is the whole mitigation: say so, in a
  table, rather than letting a green suite imply otherwise.
- `CAPABILITY_MAP` is one more constant table to keep in sync. That cost is
  paid by `lint-skill`, which fails on a missing row, an unknown phase, a
  non-existent file, an orphan module, a row that names the orchestrator, a row
  that requires everything, and an unmapped cross-reference.
- A capability file is a prompt, and a prompt can acquire a rule. The three
  widened content checks plus the policy-restatement test are the defence, and
  the rule for authors is the flat one: **capability files carry judgement and
  presentation only.** If a rule is worth having, it belongs in `sdle.py`.

---

## 5. Invariants this decision is bound by

- **6 — single writer.** The engine gained no second writer. `resume` writes
  nothing; the fence denies every write a product agent could attempt.
- **7 — one source of truth.** The capability map exists once, in `SKILL.md`.
  `resume` composes rather than re-derives. The linted file set and the
  restatement search both widened to cover the new files.
- **8 — gates stay in the parent.** No capability row and no agent prompt puts
  an agent on a gate-decision path. The three gate verbs may appear in an agent
  prompt only inside the sentence that forbids them, and the test removes that
  sentence first and requires the rest to be silent.
- **3 — SpecKit opacity.** No new capability file and no agent prompt contains a
  SpecKit token.
- **The core refuses; it does not warn.** `lint-skill` fails; the fence denies.
  Neither warns.
