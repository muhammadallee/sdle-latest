---
name: apply-sdle-transition
description: Execute or resume the SDLE Wave A deterministic-core to WorkItem V1 transition autonomously with isolated planner, implementer, and verifier contexts.
disable-model-invocation: true
context: fork
agent: sdle-transition-orchestrator
background: false
---

Execute or resume the SDLE transition defined by `docs/transition/transition.md`.

Invocation arguments: `$ARGUMENTS`

Default behavior with no arguments is to continue autonomously from durable repository state until either T11 is independently verified PASS or a true BLOCKED condition requires human/external action.

Do not ask the user to issue per-phase commands or `/clear`.

Before any phase action:

1. validate the transition control plane with `python tools/transition/validate.py`;
2. verify repository/baseline/Git safety;
3. read `docs/transition/progress.md` to determine the next stage.

Use fresh `sdle-transition-planner`, `sdle-transition-implementer`, and `sdle-transition-verifier` agents exactly as defined by the contract. Do not implement product changes in the orchestrator.

If arguments contain `status`, do not execute product changes; validate and report current durable status.

If execution is BLOCKED and the user reruns this skill with an explicit decision in the arguments, treat that text as a user decision only for the currently blocked issue. Ensure the next specialist persists that decision in the phase evidence before relying on it. Never generalize it to unrelated choices.

Stop only for the BLOCKED conditions defined by the transition contract or an external environment/permission failure that cannot be resolved safely. Ordinary implementation and verification failures use bounded fresh-context remediation.
