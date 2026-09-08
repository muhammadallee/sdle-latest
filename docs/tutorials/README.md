# Tutorials — pick a flow, then walk it

**Applies to:** SDLE v1.17

Six walkthroughs, one per flow plus a tour of everything you can configure.
Every command and every JSON response in them was produced by running the real
CLI against a throwaway project; nothing is reconstructed.

Before you pick one, read the decision guide below. Choosing the flow is the
only irreversible choice you make about a WorkItem — it is bound once, at
`init`, and there is deliberately no command that re-binds it.

---

## Which flow do I pick?

Two questions decide it, in this order.

**1. Is this a defect or an emergency?**

If you are fixing broken behaviour, the work begins with a blast-radius
question, not a specification question — so both defect flows open with a
gateless `impact_analysis` phase and neither consults the repository baseline
at all. Blocking an urgent production fix on a repository-level artifact is not
a governance rule anyone asks for.

- A bug with time to do it properly → **`DEFECT_FIX`**.
- A production incident where the shortest governed path is the right one →
  **`HOTFIX`**.

The difference is not urgency in the abstract; it is whether you are willing to
give up the plan, tasks, analysis and design gates. `HOTFIX` gives all four up.
It keeps three: specification, implementation, and security.

**2. Otherwise: does this repository already have a baseline?**

Ask the engine rather than guessing:

```
$ sdle.sh baseline show
{
  "ok": true,
  "command": "baseline show",
  "reason": null,
  "data": {
    "status": "ABSENT",
    "path": ".sdle/baseline.json",
    "present": false,
    "findings": [],
    "baseline": null,
    "establishing_flows": [
      "GREENFIELD",
      "BROWNFIELD_DISCOVERY"
    ]
  }
}
```

- `ABSENT`, and there is no code yet → **`GREENFIELD`**.
- `ABSENT`, and there is an existing codebase → **`BROWNFIELD_DISCOVERY`**.
  This is the flow that reads the repository and writes the baseline the next
  WorkItem will inherit.
- `VALID` → **`ITERATIVE`**. Discovery already happened; it does not run again.

You do not have to get this right by reasoning alone, because two of the
answers are enforced. `init` refuses `baseline_present` if you ask for
`BROWNFIELD_DISCOVERY` in a repository that already has a sound baseline, and
refuses `baseline_required` if you ask for `ITERATIVE` in one that does not.
Both refusals fire *before* anything is created, so a wrong answer costs you a
re-assessment and nothing else.

`STALE` and `INVALID` are the two answers that need judgement. A **stale**
baseline is one whose referenced files have changed; it is reported, not
refused, because `ITERATIVE` regenerates the design document anyway and
treating every change as invalidation would push the third WorkItem in any
repository back into full rediscovery. An **invalid** baseline — malformed, or
naming a file that no longer exists — blocks `ITERATIVE` outright. See
[`../brownfield/`](../brownfield/README.md) for that distinction in full.

### The five flows, as the engine reports them

| Flow | Phases | Gates | Distinctive phase | Use when |
|---|---:|---:|---|---|
| `GREENFIELD` | 18 | 8 | — | New product, nothing to discover |
| `BROWNFIELD_DISCOVERY` | 19 | 8 | `discovery` | Existing codebase, first WorkItem |
| `ITERATIVE` | 16 | 7 | — | Existing codebase with a valid baseline |
| `DEFECT_FIX` | 14 | 6 | `impact_analysis` | A bug, with time to do it properly |
| `HOTFIX` | 10 | 3 | `impact_analysis` | An incident. Shorter, never ungoverned |

These counts are the **progress denominators** — the `M` in the `Phase N/M`
header — and they exclude the terminal `complete` phase. The `phases` array the
engine returns is one longer, because it includes it. Read both from the engine
rather than from any table, including this one:

```
$ sdle.sh flow show
```

and, before a flow is bound, `sdle.sh constants` for the whole registry.

### What "gates" counts, and what it does not

The gate column above is how many gates the flow *contains*. How many a
particular WorkItem must clear is a different number, derived per WorkItem from
assessed risk, the change type, and flow membership. A gate the flow does not
contain is reported `not_in_flow` and is never quietly satisfied; a gate the
policy does not require is `omittable`, and omitting it is an audited decision
with recorded evidence, not a shortcut.

One gate is required by a rule that lives in no policy dictionary at all: the
flow's last gate before `complete` is always required, as `terminal_gate`. That
is why `HOTFIX` — the shortest flow, at three gates — still cannot reach
`complete` without a human approving its security review.

---

## The tutorials

| Tutorial | Flow | What it is for |
|---|---|---|
| [greenfield.md](greenfield.md) | `GREENFIELD` | A new project, 18 phases and 8 gates, ending in the baseline it establishes |
| [brownfield-discovery.md](brownfield-discovery.md) | `BROWNFIELD_DISCOVERY` | Reading an existing codebase: the `discovery` phase, its evidence rules, and the baseline |
| [iterative.md](iterative.md) | `ITERATIVE` | The second WorkItem in the same repository, and why discovery does not run again |
| [defect-fix.md](defect-fix.md) | `DEFECT_FIX` | A bug, entered through `impact_analysis`; what a defect classification adds |
| [hotfix.md](hotfix.md) | `HOTFIX` | The shortest flow, and specifically what it still enforces |
| [greenfield-full-tour.md](greenfield-full-tour.md) | `GREENFIELD` | Every customization surface: policy overrides, risk floors, gate omission, verbose, skip/restart/reset, drift, agent reviews, subagents |

Read one tutorial, not all six. They share a spine — create a WorkItem, assess
the requirements, `init`, then walk the phases — and each one spends its length
on what is *different* about its flow rather than repeating that spine.

---

## What these tutorials are not

**They are not the acceptance specification.** That is
[`../dry-runs/`](../dry-runs/README.md): nine conversation transcripts that
`tests/test_integration_01..09` assert against, two of which byte-pin all nine
files. All nine are `GREENFIELD`. Where the mechanics are shared, these
tutorials link into them rather than restating them, because a second
description of a behaviour a byte-pinned document already fixes is a
description that will eventually drift out of agreement with it.

The dry-runs show what the *conversation* looks like — what SDLE says at a
gate, what you type to approve. These tutorials show what the engine underneath
does, which is what you need when you are deciding, debugging, or writing a
policy.

**They are not the runbook.** When something refuses and you need to know what
to type, go to [`../troubleshooting/`](../troubleshooting/README.md). Refusals
appear here only where they teach the flow — `baseline_present` teaches which
flow you are in — never as recovery procedure.

**They are not the reference.** Every field of every response is in
[`../SDLE-Reference-Guide.md`](../SDLE-Reference-Guide.md).

---

## Reading the transcripts

Every block that begins `$ sdle.sh` is a real invocation. SDLE prints a JSON
envelope on stdout and human-readable text on stderr; the transcripts show
stdout, and stderr where it adds something — the rendered status header, or a
refusal message. The exit code follows: `0` success, `1` refused, `2` usage,
`3` integrity failure.

Two liberties are taken with the captured output, and nothing else: absolute
filesystem paths are shortened to `...`, and a few very long arrays are
summarised in a table with a note saying so. Reasons, SHAs, counts and
dispositions are verbatim.

The tutorials drive the CLI directly because that is the layer where behaviour
is decided. In ordinary use you talk to the orchestrator instead — `start
workflow`, `approve`, `reject with comments: ...` — and it issues these
commands for you. The [command table in the README](../../README.md#commands)
maps one to the other.

On Windows outside Git Bash, substitute `scripts\sdle.ps1` for `sdle.sh`; the
arguments are identical. See [`../../scripts/README.md`](../../scripts/README.md).
