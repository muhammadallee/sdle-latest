# Dry Run 09 — Bootstrap Failures (Missing Prerequisites)

| | |
|---|---|
| **Scenario ID** | DR-09 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The ways a workflow fails to start: no WorkItem yet, no requirements, SpecKit not initialised, and SpecKit skills not discoverable. Each halts with a concrete remedy instead of proceeding on assumptions. |
| **Defect IDs** | D05 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6, the version the install command pins |
| **Starting conditions** | Each part starts from an independent fresh project (no WorkItem runtime), and varies by what is missing |
| **Guardrails exercised** | The supported bootstrap order (identity → preflight → scan → governance → `init`), `preflight`'s prerequisite checks, the fail-safe rule, and the tested SpecKit command |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> SpecKit command is quoted from the engine's `SPECKIT_INIT_COMMAND`. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

For each part, make a fresh disposable repository as in DR-01, leaving out what
that part says is missing.

---

## Transcript

### Part 0 — The first command in a new repository

**User:** `start workflow`

**SDLE:** `No workflow exists in this repository yet. WorkItem name?`

*(`/sdle-start` runs `sdle.sh preflight` first. With no WorkItem registered it
refuses `workitem_required` before it checks anything, because preflight
resolves a WorkItem like every runtime command. That refusal means "create the
identity first", not "stop", so SDLE asks for the name, runs
`sdle.sh workitem create --name "<name>"`, and then
`sdle.sh --workitem <id> preflight`.)*

---

### Part 1 — No `requirements/` directory

**User:** `Todo API` *(the WorkItem name)*

**SDLE:**

```
WorkItem created: todo-api.

I need requirements before starting the workflow. Create a `requirements/` folder and
add at least one document. Then say "start workflow" or "continue".
```

*(Engine: `sdle.sh --workitem todo-api preflight` exited 1 with
`requirements_missing`. No `state.json` was created, so there is no status
header. An empty `requirements/` directory produces the same halt.)*

---

### Part 2 — SpecKit not initialised

*(`requirements/todo-api.md` present, no `.specify/`.)*

**SDLE:**

```
SDLE requires SpecKit to be initialized in this project. Run:
  uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script sh
(use `--script ps` for PowerShell scripts).
```

*(Preflight reported `speckit_missing` first, because SDLE cannot orchestrate an
engine that is not installed. The command is the one actually run against
SpecKit v1.0.6. The form earlier versions of this document gave,
`specify init . --skills --here`, fails on v1.0.6 with `No such option: --skills`.
After the user runs it, `start workflow` proceeds:)*

```
📋 SDLE Status: Phase 1/18 — Requirements Check [IN PROGRESS]

Preflight passed. I found requirements/:
  • requirements/todo-api.md (2.4 KB)
```

---

### Part 3 — SpecKit skills not discoverable

*(`.specify/` exists, perhaps copied from another machine, but no `speckit-*`
skills are installed in `.claude/skills/` or under the home directory.)*

**SDLE:**

```
⚠️ SDLE cannot locate SpecKit skills (looked for .claude/skills/speckit-constitution/ here
and in your home directory). SpecKit's Claude integration installs them; re-run its init:
  uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script sh
```

*(`speckit_skills_missing`. Discovery probes `.claude/skills/speckit-constitution/SKILL.md`
and `.claude/skills/speckit.constitution/SKILL.md`, here and under the home
directory. The discovered prefix is cached in `state.speckit_skill_prefix`.)*

---

### Part 4 — Requirements deleted mid-workflow (contrast case)

*(At `plan_draft`, the user deleted `requirements/` to tidy up.)*

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=pending progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [PENDING]

⚠️ Note: the requirements/ directory is no longer present. The approved constitution and
specification already capture the requirements, so the workflow can continue.
```

*(A warning, not a halt: by Phase 6 the requirements live in approved,
fingerprinted artifacts. The governance record is a separate matter. If
`requirements/` changes rather than disappears, the next `advance` refuses
`governance_stale`.)*

---

## Artifacts, state and audit

- Parts 1–3 halt **before** `state.json` exists. Nothing is initialised, so
  there is nothing to clean up after a false start. The WorkItem identity
  created in Part 1 stays registered and is reused on the next `start workflow`.
- Preflight's check order is SpecKit installed, then skills discoverable, then
  requirements present. Each failure names the exact command or action.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `sdle.sh preflight` with no WorkItem registered | Refused `workitem_required` | Nothing written |
| `specify init . --skills --here` (SpecKit v1.0.6) | Rejected by SpecKit: exit 2, `No such option: --skills` | Nothing installed |
| `preflight` with `.specify/` and `requirements/` removed | `speckit_missing` reported first | Nothing written |

## Cleanup

`rm -rf` each disposable project.

## Executable coverage

| Claim | Test |
|---|---|
| No WorkItem → `workitem_required`, then preflight passes | `tests/test_units_documented_commands.py::test_preflight_in_a_repository_with_no_workitem_asks_for_one_first` |
| No requirements directory halts | `tests/test_integration_06_to_09.py::test_09_no_requirements_directory_halts` |
| An empty requirements directory halts | `tests/test_integration_06_to_09.py::test_09_empty_requirements_directory_halts` |
| Missing SpecKit halts first, naming `specify init` | `tests/test_integration_06_to_09.py::test_09_missing_speckit_halts_first` |
| Undiscoverable skills halt | `tests/test_integration_06_to_09.py::test_09_undiscoverable_skills_halt` |
| A healthy project passes | `tests/test_integration_06_to_09.py::test_09_healthy_project_passes_preflight` |
| The messages carry the tested v1.0.6 command | `tests/test_units_documented_commands.py::test_the_engine_messages_carry_the_tested_command` |
