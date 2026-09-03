> **SDLE capability — loaded on demand.** `sdle.sh resume` reports which capability files the current phase requires; this is one of them. The Internal Constants are already in context from SKILL.md — do not duplicate them here. Nothing in this file is a threshold, an ordinal, a policy value or a decision rule: those live in `sdle.py` and you ask for them. This file carries judgement and presentation only.

## Design Review

One question: **does the design satisfy the specification and the plan, and can what it describes actually be built and operated?**

### 1. Assemble the evidence

- `sdle.sh artifact path --gate <gate_key>` resolves the artifact under review. Never construct that path yourself.
- Read the specification, the plan and the design documents themselves, plus any project ground rules the constitution records.
- `sdle.sh drift check` tells you whether something already approved has moved underneath you. A design reviewed against a moved plan is a review of a document nobody has.

### 2. Delegate the analysis, or do it here

Design review is high-context independent analysis: it reads a great deal and decides nothing. That is what a product subagent is for. Hand it to **`sdle-design-review`** and give it, in the delegation message:

- the exact file paths to read — it has no shell and cannot resolve a path;
- what the design is supposed to satisfy, in your words;
- the finding shape below.

It returns its findings as its final message. Doing the analysis yourself in this session is equally valid; the finding shape and the recording step are identical either way.

### 3. The finding shape

One line per finding, and every field filled:

```
- [blocking|advisory] <file>:<anchor> — <what is wrong> — <why it matters here> — <what would resolve it>
```

`blocking` means the design cannot be implemented as written without the problem surfacing. `advisory` means it should be improved and does not stop work. Those two words are the whole vocabulary — do not invent a scale, and do not restate the engine's.

What a design review looks for:

- a requirement in the specification that no part of the design satisfies, and a part of the design no requirement asks for;
- an interface, a data shape or an ownership boundary that two documents describe differently;
- state that has no clear owner, or a change of shape with no stated path from the old shape to the new one;
- an operational property the plan claims and the design does not provide — how it fails, what it does under load, what happens when a dependency is unavailable;
- a decision recorded nowhere, which the next person will have to guess at.

Say **what you observed and where**. If something is a judgement rather than an observation, say so in the same line. A finding that cannot be located in a file is not a finding.

### 4. Present, then record

Show the findings in the conversation. The user reads them here, not in a file — that is the same rule that puts artifact content in front of a human at a gate.

Then record the review against the artifact's exact current content:

```
sdle.sh artifact review --path <artifact> --type design-review \
  --result PASS --actor-type agent --actor-name sdle-design-review \
  --evidence <pointer> --comments "<one-line summary>"
```

- `--result FAIL` when any finding is `blocking`. Recording `PASS` over a blocking finding is recording something you did not conclude.
- `--actor-type agent --actor-name sdle-design-review` when the subagent produced the findings; name whoever actually did if it was not.
- `--actor-name` is a string you supply. The engine records it faithfully and **cannot verify it** — it is an attribution, not an attestation.
- The record binds to the artifact's current fingerprint. Change the artifact afterwards and the review is stale by construction, and the gate says so.

## The rule that does not bend

A review is an **input to** a decision. It is never the decision.

- A subagent inspects, reasons and returns findings. It records nothing, because it can record nothing: its tool grant is read-only and a `PreToolUse` hook denies every write and every command it might attempt.
- **You** record the outcome, in this session, with `artifact review`.
- **A human** approves the gate, in this session, after seeing the artifact content in the conversation.

Those three are separate acts performed by three different parties, and collapsing any two of them is the failure this whole design exists to prevent. Nothing a subagent returns approves, omits or skips anything.
