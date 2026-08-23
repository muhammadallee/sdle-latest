# SDLE V1 Transition — Kickoff

This kit is designed to be extracted at the **root of `muhammadallee/sdle-latest`** while the repository still contains the Wave A deterministic core.

## Start

1. Ensure Claude Code is v2.1.218+ (latest stable recommended).
2. Extract the ZIP at the repository root, preserving `.claude/` and `docs/` paths.
3. Start a **new Claude Code session after extraction** so the new `.claude/agents/` directory is discovered.
4. Invoke:

```text
/apply-sdle-transition
```

That is the normal workflow. Do not manually issue `plan-phase`, `implement-phase`, `verify-phase`, or `/clear` between stages.

## Copy/paste fallback prompt

If you prefer natural language instead of the slash skill, use:

```text
Use the apply-sdle-transition skill and execute the complete SDLE transition autonomously from the durable repository state. Use fresh isolated planner, implementer and independent verifier contexts for every phase and remediation attempt. Do not ask me to manually clear context or advance phases. Preserve all deterministic Wave A guardrails unless the transition contract explicitly supersedes them. Stop only for a material architectural decision, a real baseline mismatch, exhausted bounded remediation, or an external permission/environment blocker. Never invent test results or approvals.
```

## Resume after interruption

Start a new Claude Code session if desired and run the same command again:

```text
/apply-sdle-transition
```

The orchestrator resumes from `docs/transition/progress.md`, phase evidence, Git state, and tests—not conversation history.

For status only:

```text
/apply-sdle-transition status
```

## If Claude reports BLOCKED

Provide the requested decision, then rerun the skill with the decision text, for example:

```text
/apply-sdle-transition resume — decision: <your explicit decision>
```

The decision applies only to the blocker Claude reported and must be persisted in phase evidence.
