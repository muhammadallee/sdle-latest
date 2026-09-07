# Dry Run 09 — Bootstrap Failures (Missing Prerequisites)

| | |
|---|---|
| **Purpose** | The three ways a workflow can fail to start: no requirements, SpecKit not initialized, and SpecKit skills not discoverable. Each halts with concrete instructions instead of proceeding on assumptions. |
| **Guardrails exercised** | Step 2 requirements validation, Step 1b SpecKit installation check, Step 1c skill-prefix discovery, fail-safe rule (never proceed without prerequisites). |
| **Starting state** | Varies per part — each part is an independent fresh project (no WorkItem runtime). |

---

## Transcript

### Part 1 — No `requirements/` directory

*(Fresh project, SpecKit initialized, but the user never created `requirements/`.)*

**User:**

```
start workflow
```

**SDLE:**

```
I need requirements before starting the workflow.

Create a `requirements/` folder and add at least one document (e.g. `requirements/feature.md`).
Then say "start workflow" or "continue".
```

*(No `state.json` is created, no status header is shown (state does not exist), and nothing is generated. An empty `requirements/` directory produces the same halt.)*

---

### Part 2 — SpecKit not initialized

*(Fresh project with `requirements/todo-api.md`, but no `.specify/` directory.)*

**User:**

```
start workflow
```

**SDLE:**

```
SDLE requires SpecKit to be initialized in this project.

Please run:
  uvx --from git+https://github.com/github/spec-kit.git specify init . --skills --here

Then try again.
```

*(Checked before anything else in bootstrap — SDLE cannot orchestrate an engine that isn't installed. The user runs the command in their terminal, then:)*

**User:** `start workflow`

**SDLE:**

```
📋 SDLE Status: Phase 1/18 — Requirements Check [IN PROGRESS]

I found requirements/:
  • requirements/todo-api.md (2.4 KB)

Content scan passed. Requirements look good — project name inferred: "Todo List REST API".

I'll now generate the project constitution. Shall I proceed?
```

---

### Part 3 — SpecKit skills not discoverable

*(`.specify/` exists — perhaps copied from another machine — but the `speckit-*` skills were never installed into `.claude/skills/` or the user profile. Skill discovery probes all four locations and prefixes and finds nothing.)*

**User:**

```
start workflow
```

**SDLE:**

```
⚠️ SDLE cannot locate SpecKit skills. Re-initialize SpecKit:
  uvx --from git+https://github.com/github/spec-kit.git specify init . --skills --here
```

*(Discovery probes, in order: `.claude\skills\speckit-constitution\SKILL.md`, `.claude\skills\speckit.constitution\SKILL.md`, then the same two under `%USERPROFILE%\.claude\skills\`. The discovered prefix (`speckit-` vs `speckit.`) is cached in `state.json → speckit_skill_prefix`; if an invocation later fails mid-workflow, discovery re-runs automatically before surfacing an error.)*

---

### Part 4 — Requirements deleted mid-workflow (contrast case)

*(Workflow at `plan_draft` (6/18); the user deleted `requirements/` to tidy up.)*

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=pending progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [PENDING]

⚠️ Note: the requirements/ directory is no longer present. The approved constitution and
specification already capture the requirements, so the workflow can continue — but the
original ground-truth input is gone from disk.

Generating plan...
```

*(Deliberately a warning, not a halt: by Phase 6 the requirements have been transcribed into approved, fingerprinted artifacts. The missing folder only matters when *starting* a workflow.)*

---

## State & audit notes

- Parts 1–3 all halt **before** `state.json` exists — nothing is initialized, so there is nothing to clean up after a false start.
- The prerequisite order is: SpecKit installed (1b) → skills discoverable (1c) → requirements present (Step 2). Each failure names the exact command or action needed.
- Part 4 shows the deliberate asymmetry: missing input at bootstrap is fatal; missing input mid-workflow is survivable because approvals have already captured it.
