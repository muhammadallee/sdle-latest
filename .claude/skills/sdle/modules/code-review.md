> **SDLE capability — loaded on demand.** `sdle.sh resume` reports which capability files the current phase requires; this is one of them. The Internal Constants are already in context from SKILL.md — do not duplicate them here. Nothing in this file is a threshold, an ordinal, a policy value or a decision rule: those live in `sdle.py` and you ask for them. This file carries judgement and presentation only.

## Code Review

One question: **does the implementation do what the tasks and the plan say, and does it leave the repository in a state the next person can work in?**

### 1. Assemble the evidence

- `sdle.sh implement preflight` pins the base reference before implementation starts; the review reads the diff from that pinned point, not from an assumed one-commit history.
- `sdle.sh manifest build` produces the file list, the secrets scan and the test evidence. Read it rather than re-deriving it.
- Read the tasks and the plan, so "does it do what was asked" has something to be measured against.

### 2. Delegate the analysis, or do it here

Code review is high-context independent analysis over a diff. Hand it to **`sdle-code-review`** and give it, in the delegation message:

- the changed files, and the base reference the diff is taken from;
- the tasks and plan paths;
- the finding shape below.

It returns its findings as its final message. It cannot run the tests, and it must not claim to have: test evidence comes from the manifest, which the engine built.

### 3. The finding shape

One line per finding, and every field filled:

```
- [blocking|advisory] <file>:<line> — <what is wrong> — <why it matters here> — <what would resolve it>
```

What a code review looks for:

- a task that the diff does not implement, and a change in the diff that no task asked for;
- behaviour that contradicts the specification, rather than merely differing in style;
- an error path that is unhandled, swallowed, or handled by continuing as though nothing happened;
- input from outside the process trusted without validation, and output that leaks more than it should;
- a change with no test, where the surrounding code is tested;
- something the next reader will misread — a name that means something else, a comment that is now false, a workaround with no note saying why.

Style opinions are not findings. If a linter or a formatter would say it, let the linter say it.

### 4. Present, then record

Show the findings in the conversation, then record the review against the artifact's exact current content:

```
sdle.sh artifact review --path <artifact> --type code-review \
  --result PASS --actor-type agent --actor-name sdle-code-review \
  --evidence <pointer> --comments "<one-line summary>"
```

The same three rules apply as for any governed review: `FAIL` when a finding is `blocking`; `--actor-name` is an attribution and not an attestation; the record binds to the current fingerprint and goes stale the moment the content changes.

## The rule that does not bend

A review is an **input to** a decision. It is never the decision.

- A subagent inspects, reasons and returns findings. It records nothing, because it can record nothing: its tool grant is read-only and a `PreToolUse` hook denies every write and every command it might attempt, when the runtime honours a declared `tools:` list and a registered hook (ADR-007 §3 — that guarantee is Claude Code's, not SDLE's). SDLE's own guarantee is that a finding enters the record only through `artifact review`, which you run.
- **You** record the outcome, in this session, with `artifact review`.
- **A human** approves the gate, in this session, after seeing the artifact content in the conversation.

Those three are separate acts performed by three different parties, and collapsing any two of them is the failure this whole design exists to prevent. Nothing a subagent returns approves, omits or skips anything.
