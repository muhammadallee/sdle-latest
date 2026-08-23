# SDLE Autonomous Transition Kit

Purpose: apply `docs/transition/transition.md` to the Wave A deterministic-core branch with one user invocation while keeping planning, implementation and verification context-isolated and evidence-driven.

## Files installed

```text
.claude/agents/
  sdle-transition-orchestrator.md
  sdle-transition-planner.md
  sdle-transition-implementer.md
  sdle-transition-verifier.md
.claude/skills/apply-sdle-transition/SKILL.md
docs/transition/
  transition.md
  progress.md
  control-plane.sha256
  phases/README.md
  templates/*.md
tools/transition/
  agent_guard.py
  validate.py
SDLE-TRANSITION-KICKOFF.md
```

The kit intentionally does **not** overwrite the existing SDLE product skill, `CLAUDE.md`, hooks, or `.claude/settings.json`.

## Safety model

- Every PLAN / IMPLEMENT / VERIFY stage gets a fresh agent context.
- Repository files are the durable handoff.
- Planner/verifier write scopes are guarded.
- The implementer cannot alter the migration contract/control plane through normal Write/Edit tools.
- `validate.py` refuses inconsistent progress.
- Verification is independent and cannot silently fix code.
- Automatic remediation is bounded to 3 attempts per phase.
- Human SDLE lifecycle approvals remain human/parent-session owned.
- No automatic push is performed.

## Compatibility note

Use Claude Code **v2.1.218 or newer**; latest stable is recommended. The kit uses `context: fork` with `background: false` plus nested custom agents.

The agents request `permissionMode: auto` to minimize manual prompts while preserving Claude Code permission classification and all repository hooks. The kit never enables `bypassPermissions`. Organization policy may still surface or deny a permission when required.

The kit uses project agents and a project skill. Extract it before starting Claude Code. If Claude Code was already running before `.claude/agents/` existed, restart the session so the agent directory is discovered.

## Deterministic preflight

You can optionally run this yourself, but the orchestrator also runs it:

```text
python tools/transition/validate.py
```

Expected initial output:

```text
TRANSITION_VALID: complete=0/12 next=T00
```

## Post-transition

Do not remove the transition control-plane files until T11 has independently passed. After completion they may be retained as migration evidence/recovery tooling or removed in a separate reviewed cleanup change.
