# T10 Plan — Progressive Claude Skills and Specialist Subagents

**Phase:** T10
**Contract sections:** `transition.md` §16 (T10), §24.2 (PLAN), §1 cl. 18, §24.7, TP-006, TP-011
**Planner context:** fresh/isolated
**Planned at HEAD:** `adbdc5ee9188ec7df8d6179ce327ffb4c4df8147` (OBSERVED, `git rev-parse HEAD`)
**Rollback point:** `adbdc5e` for the whole tree; product files at `adbdc5e` are byte-identical to `6318541` because `adbdc5e` touched only `docs/transition/` (OBSERVED, `git show --stat adbdc5e`)
**Status recommendation:** PLANNED

---

## Objective

§16's goal is one sentence and it contains the whole risk:

> Optimize reasoning quality/context **without moving authority back into prompts**.

Every phase from T00 to T09 moved authority *into* `scripts/sdle.py`. T10 adds skills and subagents — the two constructs most able to quietly move it back. The plan is therefore built around a single organising rule:

> **T10 adds no new authority. It adds a deterministic way to decide *what to load* and *who may look*, and it adds nothing that can decide *what may happen*.**

Concretely, T10:

1. makes **which capability files a phase loads** a parsed constant table owned by the engine, not a judgement the model makes each turn;
2. adds a read-only **`sdle resume`** so a fresh session reconstructs a WorkItem from disk in one call — the §16 exit criterion, driven rather than asserted;
3. introduces **four product subagents** that can read and reason and nothing else, with their inability to mutate or approve expressed as a *tool grant* plus a *deny hook* plus a *lint check*, not as prose;
4. **widens** `lint-skill`'s file set so that splitting the prompt layer strengthens the cross-file rules instead of diluting them.

T10 adds **no state field, no migration row, no version bump, no gate, no policy value and no mutating command**. That is not modesty; it is the acceptance criterion. If the diff contains a new writer, the phase has failed regardless of what the tests say.

---

## Repository evidence

All rows re-derived in this planner context at `adbdc5e` unless the class says otherwise.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `adbdc5e`; working tree clean except `.claude/settings.local.json` | OBSERVED | `git rev-parse HEAD`; `git status --porcelain` → ` M .claude/settings.local.json` |
| E2 | `validate.py` prints `TRANSITION_VALID: complete=10/12 next=T10`, exit 0 | OBSERVED | `rtk proxy "python tools/transition/validate.py"`; `VALIDATE_EXIT=0` |
| E3 | `lint-skill` reports **33 checks**, `failed: []`, `tables_wellformed` = "Parsed 21 phases, 8 gates, 16 migration rows", `version_string_consistent` = "all four locations report v1.16" | OBSERVED | `rtk proxy "python scripts/sdle.py lint-skill"`, payload nested under `data` |
| E4 | Full pytest suite result **not observed in this context** | UNKNOWN | Not run here (~23 min). The most recent independently verified figure is T09's `1402 collected / 1402 passed / RAW_EXIT 0` in `progress.md`'s T09 row and `T09-verification-a01.md`. It is inherited as prior evidence, never as an observation of this phase |
| E5 | Python 3.11 behaviour and CI outcome | UNKNOWN | Never observed at any point in this migration (`RESUME.md`, "CI has never run") |
| E6 | `.claude/agents/` holds exactly four files, all `sdle-transition-*` | OBSERVED | `ls .claude/agents/` → `sdle-transition-{implementer,orchestrator,planner,verifier}.md` |
| E7 | `.claude/skills/` holds exactly two directories: `apply-sdle-transition` and `sdle`; `.claude/skills/sdle/modules/` holds exactly `gate-protocol.md`, `phase-execution.md`, `security-review.md` | OBSERVED | `ls -la .claude/skills/ .claude/skills/sdle/modules/` |
| E8 | §16's `sdle-transition-*` exclusion is also written into the contract body at §1.4 ("their existence does not satisfy T10") | OBSERVED | `transition.md` §1.4 and §16 "Subagents" note |
| E9 | Agent frontmatter supports `tools:`, `model:`, `permissionMode:` and a per-agent `hooks:` block; the transition control plane already uses all four | OBSERVED | Frontmatter of `.claude/agents/sdle-transition-planner.md` (`tools: Read, Grep, Glob, Bash, Write, Edit`; `hooks: PreToolUse: … command: "python tools/transition/agent_guard.py planner"`) |
| E10 | A per-agent frontmatter `PreToolUse` hook **actually fires and actually denies** | OBSERVED | This planner session was refused verbatim: `PreToolUse:Bash hook error: [python tools/transition/agent_guard.py planner]: SDLE transition agent guard: planner Bash/PowerShell must be observational; blocked command shape` |
| E11 | A declared `tools:` list is honoured by the runtime | OBSERVED (this session) / INFERRED (general) | The running planner's available tools are exactly `Read, Grep, Glob, Bash, Write, Edit` — its frontmatter list — and no `Agent`/`Task` tool is available to it, while `sdle-transition-orchestrator.md` declares `tools: Agent, Read, Grep, Glob, Bash`. Two agents, two grants, two different observed tool sets |
| E12 | `lint-skill`'s content checks read a **hardcoded four-file list** | OBSERVED | `scripts/sdle.py` `def _skill_files(paths: Paths)` returns `[skill_md, phase_execution_md, gate_protocol_md, security_review_md]`; its three consumers are the loops at `for path in _skill_files(paths):` inside `discovery_vocabulary_is_not_restated_in_prompt_files`, `_check_no_powershell` and `_check_no_hardcoded_progress` |
| E13 | Therefore a new capability file added under `modules/` is invisible to those three checks until `_skill_files` changes | INFERRED from E12 | The list is by property name, not by glob. This is the exact "splitting the prompt layer weakens `lint-skill`" failure the phase must not commit |
| E14 | A constants table already lives outside `SKILL.md`: `GATE_TO_EXECUTION_PHASE` is parsed from `gate-protocol.md` | OBSERVED | `scripts/sdle.py`: `for row in parse_md_table(paths.gate_protocol_md, "GATE_TO_EXECUTION_PHASE"):` |
| E15 | Module loading today is *prose-conditional*, decided by the model | OBSERVED | `SKILL.md` Step 5/Step 6: "**Read `modules/phase-execution.md`** and follow it" / "**Read `modules/gate-protocol.md`** when `current_phase` is a gate…" |
| E16 | Cross-references between capability files already exist and are load directives | OBSERVED | `gate-protocol.md:196` (gate_design remediation → `modules/phase-execution.md`), `:197` (gate_security remediation → `modules/security-review.md`), `phase-execution.md:211` (Phase 17 → `modules/security-review.md`) |
| E17 | `artifact review` already accepts an agent actor: `--actor-type` validated against `REVIEW_ACTOR_TYPES = ("human", "agent", "tool", "test", "system")`, `--actor-name` free text | OBSERVED | `scripts/sdle.py` `REVIEW_ACTOR_TYPES`, `cmd_artifact_review` refusal `review_actor_invalid` |
| E18 | The actor name is a **caller-supplied string**; the engine cannot attest who produced a finding | OBSERVED | `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md:170` — "string supplied by the caller… It creates, registers and invokes no subagent"; `:175` — "The later phase that introduces specialist subagents therefore inherits a…" |
| E19 | The engine already cannot distinguish a human approval from an orchestrator-issued one, and says so | OBSERVED | `ADR-006`, asserted verbatim by `test_units_gate_policy.py` — `assert "cannot tell whether a human being or the orchestrator issued" in body` |
| E20 | Two existing tests assert the **absence** of T10 | OBSERVED | `tests/test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage` (agents must all start `sdle-transition-`; `skills == ["apply-sdle-transition", "sdle"]`; `modules == ["gate-protocol.md", "phase-execution.md", "security-review.md"]`) and `tests/test_units_artifact_review.py::test_t06_creates_no_subagent` (`for forbidden in ("Task(", "subagent", "launch_agent"): assert forbidden not in source`) |
| E21 | `test_n31_no_t10_or_t11_leakage` also carries T11's assertions in the same function | OBSERVED | Same function asserts `legacy_workflow`, `current_feature_id`, `SDLE_OWNED_PREFIXES` and `".sdle" not in sdle.SDLE_OWNED_PREFIXES` are untouched |
| E22 | The invariant-8 statement exists in three prose places today | OBSERVED | `CLAUDE.md:71`; `SKILL.md:301` ("never delegated to a subagent"); `.claude/commands/sdle-start.md:17` |
| E23 | `_searchable_files()` (the invariant-7 restatement search) covers `.claude/skills`, `.claude/commands`, `.claude/hooks`, `.sdle`, `docs/architecture`, `README.md`, `CLAUDE.md`, the Reference Guide — but **not** `.claude/agents/` | OBSERVED | `tests/test_units_governance.py` `def _searchable_files()`; a second copy is referenced at `tests/test_units_discovery.py:651` ("T06's `_searchable_files()` set, reused verbatim") |
| E24 | The `lint-skill` self-test fixture copies only `.claude/skills/sdle` plus `README.md` and the Reference Guide | OBSERVED | `tests/test_lint_skill.py` `@pytest.fixture def repo(tmp_path)` |
| E25 | Hook tests drive **the exact command string registered in `.claude/settings.json`**, and will `AssertionError(f"{guard} is not registered in settings.json")` for a guard that is not there | OBSERVED | `tests/test_hooks.py` `def registered(guard)` / `def fire(guard, payload, cwd)` |
| E26 | `hooks.py` reads only `tool_input.file_path`; no guard inspects a Bash `command` | OBSERVED | `scripts`-side `def tool_path(payload)` in `.claude/hooks/hooks.py`; `dirty_tree` ignores the command entirely |
| E27 | No `resume` subcommand exists | OBSERVED | No `add_parser("resume")` among the 90 `add_parser(` registrations in `build_parser`; `retry`, `doctor`, `preflight`, `repo-staleness` are the bare ones |
| E28 | `cmd_constants` dumps an explicit dict of parsed tables; a new table must be added there by hand | OBSERVED | `def cmd_constants(args, paths)` — `emit("constants", { "phase_sequence": …, "flows": …, "version_chain": … })` |
| E29 | Adding a parsed table is a three-line pattern: a `Constants` field, a `parse_md_table(skill, "<NAME>")` loop in `load_constants`, a `cmd_constants` key | OBSERVED | `class Constants` field list; `def load_constants(paths)` loops |
| E30 | README and the Reference Guide both enumerate the three modules | OBSERVED | `README.md:399-402` (tree) and `:660` (**v1.3 version-history row — a historical record, not a current statement**); `docs/SDLE-Reference-Guide.md:111,115,118` |
| E31 | The engine is standard-library only and a test enforces it | OBSERVED | `test_t06_creates_no_subagent` asserts `not (imported - set(sys.stdlib_module_names))` |
| E32 | `.claude/commands/` holds 9 files; `sdle-continue.md:8-9` decides which module to load in prose | OBSERVED | `ls .claude/commands/*.md \| wc -l` → 9; `grep` of `modules/` in `.claude/commands/` |
| E33 | `phase-execution.md:205` still names `.workflow/implementation-manifest.md` | OBSERVED | The T04 N-6 documentation residual. **T11's. Not adopted by T10** |

### Derived facts (INFERRED, evidence named)

| # | Claim | Evidence |
|---|---|---|
| I1 | §16's precondition "do this only after deterministic lifecycle ownership is stable" is **met** | E2 (10/12 complete, each independently PASS), E3 (33 cross-file checks green, 21-phase registry, 5 flows, policy-driven gates), and the fact that T07 and T09 changed lifecycle semantics and both landed with independent PASS verification. Lifecycle ownership now sits in `sdle.py`: flow binding (`init`, no `flow set`), gate requirement (`governance gates`), traversal (`advance`). Nothing about lifecycle ownership is pending in T10's own scope |
| I2 | The strongest available guarantee that a subagent cannot mutate state or approve a gate is **the tool grant plus the deny hook**, not an engine check | E11 + E10 give two independently observed runtime enforcement points. E18 + E19 show the engine cannot attest the caller: `sdle.sh gate approve` looks identical whoever runs it. A subagent with no `Bash` tool cannot run it at all; a subagent whose `Write`/`Edit`/`Bash` calls are denied by its own frontmatter hook cannot reach the filesystem or the CLI |
| I3 | An engine-side actor attestation (`--actor` flag or `SDLE_ACTOR` env) would be **security theatre** | It is set by the caller. A misbehaving caller omits it. It would create a *new* refusal that a compliant caller trips and a non-compliant one does not — the exact fail-open shape §24.4 cl. 10 tells the verifier to hunt. D9 rejects it explicitly |
| I4 | Making `_skill_files` a glob is a strict strengthening with a bounded blast radius | E12: three checks consume it. The files it would newly cover are files this phase authors, plus nothing else — `modules/` currently holds exactly the three already covered (E7) |
| I5 | `test_t06_creates_no_subagent`'s bare `"subagent" not in source` string ban and T10's lint work are in genuine tension | The engine must *read* `.claude/agents/*.md` to lint them; the natural vocabulary for that code is "subagent". D11 resolves it by preserving the guarantee (the engine invokes nothing) and retiring the vocabulary ban, TP-003 category 2 |

---

## Design decisions

### D1 — The capability set for a phase becomes a parsed constant, not a model judgement

Today the model decides which module to read from prose (E15). T10 replaces that with **`CAPABILITY_MAP`**, a new table in `SKILL.md`'s Internal Constants:

```markdown
### CAPABILITY_MAP
| phase | capabilities |
|---|---|
| `gate_design` | modules/gate-protocol.md modules/design-review.md |
```

Cell convention is `FLOW_PHASES`' convention, for the same reason and with the same pitfall documented in place: **space separated, not backticked** — one pair of backticks around the whole cell is stripped and the list mangles into a single unrecognisable path.

It lives in `SKILL.md` and not in a module, because it is needed *before* anything is loaded and `SKILL.md` is the always-loaded file. `GATE_TO_EXECUTION_PHASE` living in `gate-protocol.md` (E14) is precedent that tables *may* live in modules — it is not precedent that this one may.

`SKILL.md` is never itself a value in the map, and `lint-skill` asserts it is not: it is the orchestrator, not a capability.

### D2 — The map is *required load*, not *permitted load*

A phase's row is what the phase requires. Cross-references inside a loaded file (E16 — remediation at `gate_design` sends you to `phase-execution.md`) remain exactly as they are and are still followed. The map is a floor, not a ceiling, and the plan says so rather than pretending the prompt layer stops reading at the row.

The property that makes it *progressive* is still objective and non-vacuous: **every row is a strict subset of the union of all rows**, and the union is exactly the set of files present under `modules/`. Both are lint checks (D6) and tests (N3, N4).

### D3 — Two new capability files, and no restructuring of `phase-execution.md`

New:

- `.claude/skills/sdle/modules/design-review.md`
- `.claude/skills/sdle/modules/code-review.md`

`security-review.md` already exists and already *is* the security-review capability; a third new file would duplicate it (invariant 7). `phase-execution.md` is **not split**: `lint-skill`'s `every_phase_has_execution_block` and `execution_block_numbers_are_the_greenfield_positions` parse it as one document, and splitting it would mean rewriting two of the checks that make the prompt layer trustworthy in the same phase that introduces subagents. That is two architectural axes at once (TP-002). §16 is a direction, not a file list.

Each new file carries judgement and presentation only: how to conduct that review, what a structured finding looks like, how to delegate it to the matching product subagent, and how the **parent** records the outcome with `sdle.sh artifact review --actor-type agent --actor-name <agent>` (E17). No threshold, no gate number, no phase number, no policy value, no risk level. After M1 that is machine-checked, because the three content checks will cover these files (D6).

### D4 — Four product subagents, read-only by grant and by hook

`.claude/agents/sdle-discovery.md`, `sdle-design-review.md`, `sdle-code-review.md`, `sdle-security-review.md` — §16's four named uses (brownfield discovery, architecture/design review, code review, security review).

Each declares:

```yaml
tools: Read, Grep, Glob
model: inherit
hooks:
  PreToolUse:
    - matcher: "Write|Edit|MultiEdit|NotebookEdit|Bash"
      hooks:
        - type: command
          command: "python .claude/hooks/hooks.py product-agent-fence"
```

Two independent enforcement points, both with observed precedent in this repository (E9, E10, E11):

1. **The grant.** No `Write`, no `Edit`, no `Bash`, no `Agent`/`Task`. A subagent with no `Bash` tool cannot invoke `sdle.sh gate approve`, cannot invoke anything, and cannot spawn a further agent — so it cannot become an independent workflow controller (§16's fourth MUST NOT) for want of the only tool that would let it.
2. **The fence.** If a grant is ever widened by a future edit, the frontmatter hook denies the call anyway, and `lint-skill` fails the widened grant on the next CI run.

They may inspect, reason and return structured findings as their final message. They return findings; they do not record them. The **parent** records, through the existing command (E17). That is the whole integration: T10 adds no write path.

### D5 — `hooks.py product-agent-fence`: deny everything it matches

A fifth guard in the existing hooks file. Unlike the other four it is **unconditional**: every matched tool call is denied, with a reason naming invariant 6 (single writer) and invariant 8 (gates stay in the parent).

Unconditional is deliberate. A guard that inspects a Bash command string and denies "the mutating sdle subcommands" needs a list of mutating subcommands — a second source of truth for something `sdle.py` already knows, and one that fails open on the subcommand nobody remembered to add. A product subagent has no legitimate reason to write anything or run anything. Deny is total, has no list to drift, and cannot fail open.

It is registered **in the four agent frontmatters, not in `.claude/settings.json`**, because it must apply to those agents and not to the parent session — the parent legitimately writes through `sdle.py`. `.claude/settings.json` stays byte-identical to `adbdc5e`, and a test asserts that (N24).

Consequence for tests: `tests/test_hooks.py::registered()` looks the guard up in `settings.json` and would raise (E25). M5 adds a sibling resolver that extracts the command from an agent file's frontmatter and drives *that exact string* the same way — preserving the file's stated philosophy ("a test that exercises a path production never takes proves nothing") rather than working around it. Frontmatter is read with a narrow regex over the `command:` line; **no YAML dependency is introduced** anywhere, in engine or tests (E31).

### D6 — `lint-skill` gets wider, not weaker: `_skill_files` becomes derived

`_skill_files` changes from a four-property list to:

```
SKILL.md  +  sorted(modules/*.md)  +  sorted(.claude/agents/sdle-*.md excluding sdle-transition-*)
```

Every capability file and every product subagent prompt therefore falls under `no_powershell_only_cmdlets`, `no_hardcoded_progress_outside_progress_map` and `discovery_vocabulary_is_not_restated_in_prompt_files` **automatically and forever** — a future capability file cannot be added to an unlinted corner. This is the answer to "splitting the prompt layer must not weaken those checks": the file set stops being a list somebody must remember to extend.

The `sdle-transition-*` files are excluded by prefix, matching how `test_n31_no_t10_or_t11_leakage` already excludes them by name (E20) and how §1.4 describes them.

New checks (names are the contract with the verifier):

| Check | Asserts |
|---|---|
| `capability_map_covers_every_registry_phase` | every phase in `PHASE_SEQUENCE` has a row, and no row names an unknown phase |
| `every_capability_file_exists` | every path named resolves under the skill root |
| `capability_map_never_names_the_orchestrator` | `SKILL.md` is not a capability value (D1) |
| `every_capability_file_is_linted` | the set of files named by the map ⊆ `_skill_files`, and every `modules/*.md` on disk is named by at least one row — no orphan module, no unlinted capability |
| `every_row_is_a_strict_subset_of_the_capability_set` | the progressive property (D2); fires if any row equals the union |
| `capability_cross_references_are_mapped_files` | every `modules/<x>.md` referenced *inside* a capability file exists and is itself in the map (E16 keeps working) |
| `product_agents_are_read_only` | every product agent's `tools:` ⊆ `{Read, Grep, Glob}`; `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Agent`, `Task` are each named in the failure message |
| `product_agents_declare_the_fence` | every product agent declares the `product-agent-fence` `PreToolUse` hook with a matcher covering all five mutating tools |
| `product_agents_declare_the_non_approval_clause` | every product agent file contains the literal invariant-8 marker sentence |

Absence handling, and the vacuity trap it opens: the agent checks are emitted only when `.claude/agents/` exists, mirroring how the documentation checks tolerate a project with no `README.md` (`test_a_project_with_no_repository_documentation_still_lints`). That tolerance is exactly how a check passes vacuously, so it is paid for twice: the `lint-skill` fixture is extended to copy `.claude/agents/` (E24), and a separate repository-level test asserts the four product agents exist in the real tree (N19). A check that stops firing must break something.

### D7 — `sdle resume`: one read-only command, and the exit criterion's home

§16's exit criterion is *"a fresh Claude session can resume a WorkItem safely and load only relevant phase context."* §22 already names `sdle resume` as a target capability and it does not exist (E27).

`sdle resume` takes no arguments beyond the standard `--workitem`, **writes nothing**, and returns everything a cold session needs:

```
workitem, flow, current_phase, status, progress, header (verbatim),
gate (key, number, total, required, requirement_reasons) when at a gate,
pending (drift_queue, pending_confirm_action, phase_checkpoint, clarification_phase),
branch_mismatch, capabilities: ["modules/…", …]
```

It is **pure composition**: it calls the same derivations `header`, `state get`, `flow show` and `gate show` call. It must not re-derive or re-render anything. N11 pins that by byte-comparing `resume`'s `header` field against `header`'s `rendered`, and its phase/flow/progress/gate fields against the existing commands' output for the same WorkItem. A second renderer would be an invariant-7 violation introduced by the very phase that is supposed to be defending invariant 7.

It follows the ordinary resolution refusals (`workitem_required`, `workitem_ambiguous`, `workitem_unregistered`) and it does **not** run `migrate` — a read-only command that silently migrates is not read-only.

Name collision, stated so nobody trips on it: the user word `resume` routes to `/sdle-continue` (`SKILL.md` Step 4). `sdle resume` is the CLI call `/sdle-continue` makes first. The routing table does not change.

### D8 — TP-006 is what this phase is actually testing

TP-006 and §16's prompt/memory invariant say correctness may not depend on conversation history. `resume` is the mechanical expression of that: a brand-new OS process, given only the repository, reconstructs the run. Every `Project.run` in the suite is already a fresh process, so the test is not a simulation of a fresh session — it *is* one, for the only part of the system that holds durable truth.

This migration's own history is the design input the task points at: it has been interrupted repeatedly and has recovered from `progress.md` plus phase artifacts every time, never from context. The generalisation is what `resume` returns: identity, position, what is pending, and what to read next. Those four are precisely the four things a resuming transition agent has had to reconstruct by hand each time.

### D9 — Rejected: engine-side actor attestation

Considered and rejected: a global `--actor` / `SDLE_ACTOR` that mutating commands refuse when it says "agent".

It is set by the caller. A compliant caller sets it and gets refused; a non-compliant one omits it and proceeds. It converts a real guarantee (the callee has no Bash tool) into a self-declaration, and it invites a reader to believe the engine knows who called — which E18 and E19 say plainly it does not. The honest architecture is: the runtime constrains the agent, the engine constrains the operation, and neither pretends to know the other's business. This is recorded in ADR-007 so a later phase does not reinvent it.

### D10 — Rejected: making the gate-omission or approval path agent-aware

`gate approve`, `gate omit`, `gate reject` and `advance` are untouched by T10. Not one line. §5's Lifecycle Semantics column for T10 reads "equivalent governance", and that is taken literally.

### D11 — `test_t06_creates_no_subagent` is deliberately superseded, narrowly (TP-003 category 2)

The test currently bans three literals in `scripts/sdle.py`: `Task(`, `subagent`, `launch_agent` (E20). T10's lint checks must read and reason about `.claude/agents/*.md`, and the honest name for what is in those files is a subagent (I5).

Resolution: **keep the guarantee, retire the vocabulary ban.**

- `Task(` and `launch_agent` stay banned — those are invocation.
- The AST/stdlib-only assertion stays.
- `subagent` as a bare substring is dropped, and replaced by a stronger *behavioural* assertion: no `subprocess`/`os.system`/`os.exec*` call anywhere in `sdle.py` takes an argument containing `claude`, `agent` or `Task`, and the engine registers no command that spawns anything. The engine may *describe* agents; it may not *start* one.

Passing by wording discipline (writing "agent" everywhere and never "subagent") was considered and rejected: it leaves a booby trap for the next editor and makes a green test mean nothing.

### D12 — The two enforcement layers are labelled, and so is the third thing that is only convention

ADR-007 and the plan's acceptance criteria both carry this table verbatim. It is the T08/T09 honesty split applied to T10.

| Property | Enforced by | Detectable how |
|---|---|---|
| A product subagent's declaration grants no mutating tool | **SDLE** (`lint-skill`, CI) | `product_agents_are_read_only` fires; N16 proves it fires |
| A product subagent's declaration carries the deny fence | **SDLE** (`lint-skill`, CI) | `product_agents_declare_the_fence`; N17 |
| A denied call is actually denied when the fence runs | **SDLE** (hook unit tests) | N13/N14 drive the exact frontmatter command string with Write/Edit/Bash payloads and assert `permissionDecision == "deny"` |
| The engine spawns no agent | **SDLE** (source/AST test) | N18 (D11) |
| A capability set is chosen by the engine, not the model | **SDLE** (constants + `resume` tests) | N1–N5, N9–N11 |
| A declared `tools:` list is actually applied | **Claude Code runtime** — *not* SDLE | Observed for this session (E11); not assertable from the suite |
| A frontmatter `PreToolUse` hook actually fires | **Claude Code runtime** — *not* SDLE | Observed for this session (E10); not assertable from the suite |
| The parent delegates to the *right* agent, or at all | **Convention only** | Nothing enforces it. The prompt says it |
| An `--actor-name` truthfully names who produced a finding | **Convention only** | E18 — a caller-supplied string. Unchanged by T10, and T10 must not imply otherwise |
| A human, not the orchestrator, typed `approve` | **Convention only** | E19 — already recorded in ADR-006 and asserted there. T10 changes nothing about it |

The three "convention only" rows are not defects introduced by T10; two of them predate it and are already documented. What T10 must not do is let the arrival of named specialist agents make a reader believe those rows moved up the table.

### D13 — What T10 deliberately does not do

- No `phase-execution.md` split (D3).
- No new gate, no gate semantics change (D10).
- No state field, no `VERSION_MIGRATION` row, no version bump. v1.16 stands. The engine's `resume` reads state; it does not extend it.
- No new mutating command. `resume` is the only new command and it is read-only.
- No change to `governance`, `discovery`, `flow`, `baseline`, `gate` or `advance`.
- No adoption of any T11 finding (see Scope exclusions).
- No removal or relaxation of any existing `lint-skill` check. The 33 observed at E3 must all still be present and passing, plus the new ones.

### D14 — Where a subagent's output enters the governed record

Only one door, and it already exists (E17):

```
subagent returns findings (text, in the parent's conversation)
        |
        v
parent displays / uses them
        |
        v
parent runs: sdle.sh artifact review --path <artifact> --type <review-type>
             --result PASS|FAIL --actor-type agent --actor-name sdle-<x>
             --evidence <pointer>
        |
        v
engine: TP-011 record bound to the artifact's exact current SHA + audit event
```

No new command, no new field, no new refusal. The stale-review rule (TP-011) applies unchanged: if the artifact changes after the agent reviewed it, the review is stale and the gate refuses. That is the same guarantee T06 built and T09 leaned on, and T10 inherits it rather than parallelling it.

---

## Behavioral delta

### Deliberate changes

| # | Change |
|---|---|
| B1 | `SKILL.md` gains a `CAPABILITY_MAP` constants table; Steps 5 and 6 stop naming a module in prose and instead name what `sdle.sh resume` reports (`capabilities`) |
| B2 | `.claude/skills/sdle/modules/` gains `design-review.md` and `code-review.md` |
| B3 | `.claude/agents/` gains four product subagents, read-only by grant and fenced by hook |
| B4 | `.claude/hooks/hooks.py` gains a fifth guard, `product-agent-fence`, which denies every call it matches |
| B5 | `scripts/sdle.py` gains: a `capability_map` field on `Constants`, its `parse_md_table` loop, its `cmd_constants` key, `cmd_resume` + the `resume` parser entry, nine `lint-skill` checks, and a derived `_skill_files` |
| B6 | `lint-skill`'s three content checks widen their file set from four hardcoded paths to every capability file and every product agent prompt |
| B7 | `/sdle-continue` (and `/sdle-start`'s resume branch) call `sdle.sh resume` and load exactly the capability files it names |
| B8 | Documentation: `README.md` tree and extension notes, `docs/SDLE-Reference-Guide.md` skill-layout section, `CLAUDE.md` architecture section, and a new `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md` |
| B9 | `tests/test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage` and `tests/test_units_artifact_review.py::test_t06_creates_no_subagent` are amended under TP-003 category 2 (X1, X2) |
| B10 | `tests/test_units_governance.py::_searchable_files()` gains `.claude/agents/`, closing the invariant-7 gap at E23 |

### Preserved invariants

Each is a test in the acceptance set, not a promise in prose.

| Invariant | How T10 keeps it |
|---|---|
| 1 — state first | `resume` reads state and returns the header verbatim; nothing changes about the header |
| 2 — gate discipline | Untouched (D10). No new path to `advance` past a gate |
| 3 — SpecKit opacity | The new capability files and all four agent prompts must contain no `speckit`/`/speckit.` token, and no product agent may be told to invoke SpecKit. A24 pins it. (`SKILL.md`, `phase-execution.md`, `gate-protocol.md`, `security-review.md` already contain 15/60/15/3 case-insensitive occurrences respectively — the existing files are unchanged and out of scope for this rule; the rule binds T10's new files) |
| 4 — gate content in conversation | Gate presentation stays in `gate-protocol.md`, loaded in the parent. No agent is mapped to, invoked at, or mentioned in a gate decision path |
| 5 — fail safe | No new failure path; `resume` is read-only and cannot leave a partial state |
| 6 — single writer | The fence denies every write a product agent could attempt; the engine gains no second writer; a refusal still leaves `audit.md` byte-identical (N23) |
| 7 — one source of truth | The capability map exists once, in `SKILL.md`, parsed by the engine; `resume` composes rather than re-derives (N11); `_skill_files` widening puts the new files under the restatement checks; `_searchable_files()` gains `.claude/agents/` |
| 8 — gates stay in the parent | The phase's central risk. Grant + fence + lint + the marker-clause check, and no capability row and no agent prompt that puts an agent on a gate path |
| Core refuses, does not warn | `lint-skill` fails; the fence denies; neither warns |
| Claude cannot lower a deterministic floor | No policy value is read, written or restated by anything T10 adds |
| GREENFIELD frozen | `GREENFIELD_V1_PHASES` untouched, 19 entries (N21) |
| Transcripts / happy path byte-identical | `tests/test_integration_01_happy_path.py` and `docs/dry-runs/*.md` unchanged (N20) |
| Legacy `.workflow/` dual-read; `migrate-workflow` never mutates it | Untouched; T11's (N22) |

---

## Files expected to change

| Path | Nature |
|---|---|
| `scripts/sdle.py` | `Constants.capability_map`, `load_constants` loop, `cmd_constants` key, `cmd_resume`, `resume` parser entry, `_skill_files` derived, nine new checks in `run_sync_checks` |
| `.claude/skills/sdle/SKILL.md` | `CAPABILITY_MAP` table; Steps 5/6 reworded to load what `resume` names; one sentence on product subagents and the non-delegation rule |
| `.claude/skills/sdle/modules/design-review.md` | **new** |
| `.claude/skills/sdle/modules/code-review.md` | **new** |
| `.claude/skills/sdle/modules/phase-execution.md` | pointer edits only where a review capability is now a separate file. **No block added, removed or renumbered** |
| `.claude/skills/sdle/modules/gate-protocol.md` | pointer edits only. `GATE_TO_EXECUTION_PHASE` untouched |
| `.claude/agents/sdle-discovery.md` | **new** |
| `.claude/agents/sdle-design-review.md` | **new** |
| `.claude/agents/sdle-code-review.md` | **new** |
| `.claude/agents/sdle-security-review.md` | **new** |
| `.claude/hooks/hooks.py` | fifth guard + `GUARDS` entry |
| `.claude/commands/sdle-continue.md`, `.claude/commands/sdle-start.md` | call `sdle.sh resume`; load what it names |
| `README.md` | tree at `:399-402`, extension notes. **The v1.3 row at `:660` is version history and must not be rewritten** |
| `docs/SDLE-Reference-Guide.md` | skill-layout section at `:111-118` |
| `CLAUDE.md` | Architecture section: capability files, product agents, the D12 enforcement split |
| `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md` | **new** |
| `tests/test_units_capabilities.py` | **new** — the map, `resume`, the agents, the fence |
| `tests/test_lint_skill.py` | fixture copies `.claude/agents/`; one fire-test per new check |
| `tests/test_hooks.py` | frontmatter-hook resolver + fence tests |
| `tests/test_units_gate_policy.py` | X1 |
| `tests/test_units_artifact_review.py` | X2 |
| `tests/test_units_governance.py` | X3 |
| `tests/conftest.py` | fixture support only, if the new tests need it (see anti-contradiction clause) |
| `docs/transition/phases/T10-checkpoint-a01-*.md`, `T10-handoff-a01.md`, `docs/transition/progress.md` | transition evidence |

**Must not change:** `.claude/settings.json`, `.claude/skills/sdle/templates/state.json`, `.gitignore`, `tests/test_integration_01_happy_path.py`, `tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py`, `docs/dry-runs/*`, `.claude/agents/sdle-transition-*.md`, `tools/transition/*`, `docs/transition/phases/T00..T09-*`.

---

## Existing tests affected

Every row is TP-003 category 2 — deliberately superseded behaviour — and each names what replaces the assertion.

| # | Test | Change | Why it is not a weakening |
|---|---|---|---|
| X1 | `tests/test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage` | Split. The **T10 half** (agents all `sdle-transition-`; `skills == [...]`; `modules == [...]`) becomes an assertion of T10's *expected new shape*: agents == the four control-plane files **plus exactly the four named product agents**; `skills` still exactly `["apply-sdle-transition", "sdle"]` (T10 adds no skill directory); `modules` == the five named files. The **T11 half** (`legacy_workflow`, `current_feature_id`, `SDLE_OWNED_PREFIXES`, `".sdle" not in SDLE_OWNED_PREFIXES`) is moved verbatim into a separate `test_n31_no_t11_leakage` and **not touched otherwise** | The assertion keeps its shape: exact equality against an enumerated set. It is not relaxed to `startswith`, a subset test or an `any`. A fifth product agent appearing without a plan still fails |
| X2 | `tests/test_units_artifact_review.py::test_t06_creates_no_subagent` | Rename to `test_the_engine_invokes_no_agent`; drop the bare `"subagent"` literal; keep `Task(`, `launch_agent`, the stdlib-only AST assertion and the `--actor-name sdle-architect` recording assertion; **add** the D11 behavioural assertion (no spawn call whose argument names `claude`, `agent` or `Task`) | D11/I5. The guarantee (the engine invokes nothing) is strengthened from a string ban to a structural one |
| X3 | `tests/test_units_governance.py::_searchable_files()` | Add `.claude/agents/` to the scanned roots | A strengthening. If any control-plane agent file trips it, **do not narrow the root** — report it, and restrict to product agents (`sdle-*` minus `sdle-transition-*`) with the reason recorded in the handoff |
| X4 | `tests/test_units_discovery.py` (~`:651`, "T06's `_searchable_files()` set, reused verbatim") | Follow X3 so the two copies do not diverge, **or** leave it and record why | Invariant 7 applies to test helpers too |
| X5 | `tests/test_lint_skill.py::repo` fixture | Also copy `.claude/agents/` | Without it the new agent checks pass vacuously (D6) |
| X6 | `tests/test_lint_skill.py::test_the_repo_passes_every_check` | No change expected (`len(checks) > 15`) | Recorded so the verifier knows it was considered |
| X7 | `tests/test_hooks.py::registered` / `test_the_registered_interpreter_resolves_on_this_machine` | Add a sibling frontmatter resolver; the settings.json-based ones are **unchanged** | The fence is not in `settings.json` by design (D5) |
| **X-GEN** | **Any test that enumerates a closed set this phase legitimately grows** — `.claude/agents/` contents, `.claude/skills/` contents, `modules/*.md`, `_skill_files` membership, a `lint-skill` check-name list, `_searchable_files()` roots, a subcommand inventory | May be updated to the new expected literal **only if** (a) the assertion keeps its shape — exact equality against an enumerated set, never relaxed to a subset, prefix or `any`; (b) the handoff records the old and new literal verbatim; (c) no assertion is deleted, only re-valued | T09 NB-1. Mechanically-forced closed-set growth is foreseeable and should not force a blocker |

**Anything outside X1–X7 and the X-GEN shape is a plan defect. Stop and write `docs/transition/phases/T10-blocker.md`.** A test that fails for a reason not listed here is evidence the plan was wrong, not a test to adjust.

### Anti-contradiction clause

"Do not edit tests" elsewhere in this plan means *do not weaken or delete a regression assertion*. It explicitly permits:

- creating `tests/test_units_capabilities.py`;
- additive fixtures/helpers in `tests/conftest.py` needed by the new tests, provided no existing fixture changes behaviour for an existing test;
- the fixture and helper changes named in X5 and X7;
- the re-valuations described by X-GEN.

It does not permit touching `tests/test_integration_01_happy_path.py`, either integration file, or any `docs/dry-runs/` transcript.

---

## New tests required

New file `tests/test_units_capabilities.py` unless a row says otherwise.

### The capability map

| # | Assertion |
|---|---|
| N1 | Every phase in `PHASE_SEQUENCE` (21) has a `CAPABILITY_MAP` row, and every row names a known phase — driven through `sdle.sh constants`, parametrised over the registry so a new phase without a row fails |
| N2 | Every path named by every row exists under the skill root, and none is `SKILL.md` |
| N3 | **Progressive.** For every row, the set is a *strict* subset of the union of all rows; the union equals exactly the `modules/*.md` files on disk. Non-vacuity guard: the union has ≥ 4 members and at least one row has exactly 1 |
| N4 | Every gate phase's row contains `modules/gate-protocol.md`; no non-gate phase's row does |
| N5 | Every `modules/*.md` on disk is named by at least one row — no orphan capability file |
| N6 | The new capability files contain no progress fraction, no gate ordinal, no phase number, no risk level and no policy identifier — driven by re-running the three widened `lint-skill` checks plus `test_no_policy_default_value_is_restated_outside_sdle_py` |
| N7 | Every `modules/<x>.md` cross-reference inside a capability file resolves and is itself mapped (E16 keeps working) |
| N8 | `sdle.sh constants` exposes `capability_map`; a renamed `### CAPABILITY_MAP` heading makes `lint-skill` fail loudly rather than defaulting to an empty map (the `test_an_empty_table_never_yields_an_empty_default` pattern) |

### `sdle resume` — the §16 exit criterion, driven

| # | Assertion |
|---|---|
| N9 | **The headline.** For a WorkItem built to phase P on disk, a **fresh process** with no arguments returns exit 0 and a payload naming the workitem, flow, phase, status, progress, header, pending items and `capabilities`; every capability file it names exists. Parametrised over **every phase in the registry** and over at least two flows |
| N10 | `resume` at a gate additionally reports `required` and `requirement_reasons` identical to `gate show --gate <key>` for the same WorkItem |
| N11 | **No second source of truth.** `resume`'s `header` is byte-identical to `header`'s `rendered`; its phase/flow/progress equal `state get` / `flow show`; its gate block equals `gate show` (D7) |
| N12 | `resume` writes nothing: SHA map of the whole project tree identical before and after, `audit.md` byte-identical, and it does **not** migrate an old-version state (the state file's `workflow_version` is unchanged afterwards) |
| N12b | `resume` refuses `workitem_required` / `workitem_ambiguous` / `workitem_unregistered` in the same situations and with the same exit codes as its sibling read-only commands |

### The subagent boundary — a violation must be *detectable*

| # | Assertion |
|---|---|
| N13 | **The headline.** The `product-agent-fence` command string is extracted verbatim from each of the four agent frontmatters and run as a real subprocess against a payload battery: `Write` to `workitems/<id>/.sdle/state.json`; `Edit` to `workitems/<id>/.sdle/audit.md`; `Write` to `workitems/index.md`; `Write` to an ordinary source file; `Bash` running `scripts/sdle.sh gate approve --gate gate_spec`; `Bash` running `scripts/sdle.sh advance`; `Bash` running anything at all. **Every one returns `permissionDecision == "deny"`**, exit 0, with a reason naming invariant 6 or 8 |
| N14 | The fence denies with **no payload path at all** and with a malformed payload — it never fails open (contrast: `write_fence` returns silently when `tool_path` is `None`, which is correct for *that* guard and wrong for this one) |
| N15 | The four product agents declare `tools:` ⊆ `{Read, Grep, Glob}`; none names `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Agent` or `Task` — asserted from the files, and independently asserted by `lint-skill` |
| N16 | `lint-skill` **fires**: a fixture agent granted `Bash` makes `product_agents_are_read_only` fail and nothing else (`assert_only_failure`), in `tests/test_lint_skill.py` |
| N17 | `lint-skill` **fires**: an agent with the fence hook stripped fails `product_agents_declare_the_fence`; an agent with the invariant-8 marker sentence removed fails `product_agents_declare_the_non_approval_clause` |
| N18 | The engine invokes nothing (D11/X2): no `Task(`, no `launch_agent`, stdlib-only, and no spawn call whose argument names `claude`, `agent` or `Task` |
| N19 | **Anti-vacuity.** The real repository contains exactly the four named product agents plus exactly the four `sdle-transition-*` control-plane agents; and with `.claude/agents/` removed from the lint fixture the agent checks are *absent* rather than *passing*, so a missing directory can never read as a pass |
| N25 | No `CAPABILITY_MAP` row and no product agent prompt places an agent on a gate-decision path: no agent file names `gate approve`, `gate omit` or `advance` except inside the sentence forbidding it; the sentence is matched exactly |

### Guardrails that must not move

| # | Assertion |
|---|---|
| N20 | `tests/test_integration_01_happy_path.py`, both other integration files and the nine `docs/dry-runs/*.md` are byte-identical to `adbdc5e` (line endings normalised — the tree is CRLF, `git show` is LF) |
| N21 | `GREENFIELD_V1_PHASES` is the same 19-entry tuple; every flow's phase list element-wise identical to `adbdc5e` |
| N22 | Legacy `.workflow/` dual-read still binds with no WorkItem registered; `migrate-workflow` still leaves `.workflow/` byte-for-byte untouched |
| N23 | **Ledger byte-identity.** Every refusal T10 can reach (`resume`'s three resolution refusals) leaves `audit.md` byte-identical; `audit verify` still passes |
| N24 | `.claude/settings.json`, `.claude/skills/sdle/templates/state.json` and `.gitignore` byte-identical to `adbdc5e`; `version_string_consistent` still v1.16; still 16 migration rows; still 8 `approvals` keys; `PHASE_SEQUENCE` still 21 |
| N26 | All **33** checks observed at E3 are still present by name and still pass, and `failed` is `[]` with the new checks added |
| N27 | The four existing hook guards behave exactly as before: the existing `tests/test_hooks.py` cases pass unmodified |
| N28 | Invariant 3: no new capability file and no agent prompt contains `speckit` (case-insensitive) or `/speckit.` |

---

## Implementation sequence

Six milestones. Every milestone ends green — full suite plus `lint-skill` — except the single declared red window inside M5, which is confined to M5 and must be closed before M5's checkpoint is written. **Write each checkpoint before starting the next milestone** (§24.3; ~14 agent runs in this migration have been killed mid-flight).

| M | Work | End state |
|---|---|---|
| **M1** | `_skill_files` becomes derived (D6). **No new files.** | Riskiest structural change first, and its proof is that nothing moves: `lint-skill` still 33/33, suite green, `git diff` touches one function |
| **M2** | `CAPABILITY_MAP` in `SKILL.md` mapping the **three existing** modules; `Constants` field, loader, `cmd_constants` key; the six map-related lint checks; N1–N5, N7, N8 | Green. The map is live and correct before any new file exists |
| **M3** | `design-review.md` + `code-review.md`; map rows updated; `SKILL.md` Steps 5/6; `phase-execution.md` / `gate-protocol.md` pointer edits; N6, N28 | Green. Now the M1 widening is doing real work |
| **M4** | `cmd_resume` + parser entry; `/sdle-continue`, `/sdle-start` resume branch; N9–N12b | Green. **Safe resume boundary — see below** |
| **M5** | Four product agents; `product-agent-fence`; `test_hooks.py` frontmatter resolver; the three agent lint checks; X1, X2, X3, X4, X5, X7; N13–N19, N25 | Green. Contains the declared red window |
| **M6** | `README.md`, `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`, ADR-007; N20–N24, N26, N27; full suite + `lint-skill` + `validate.py`; handoff | Green; phase `IMPLEMENTED` |

**Safe resume boundary: the end of M4.** M1–M4 are additive and behaviour-neutral — no existing test is amended, no agent exists, every guardrail is where `adbdc5e` left it. An agent resuming from a killed run should restart at a milestone boundary, never mid-milestone, and should verify claimed state against disk (`--collect-only` is the cheap check) rather than trusting a checkpoint's prose.

**The declared red window (inside M5).** The instant `.claude/agents/sdle-discovery.md` appears, `test_n31_no_t10_or_t11_leakage` fails; amending it first fails it the other way. Either order is red. Therefore: create the four agents and apply X1 **in one working step**, run the two affected files targeted (`pytest tests/test_units_gate_policy.py tests/test_units_artifact_review.py`) to close the window immediately, and only then continue with the fence and the lint checks. The window must not survive into M5's checkpoint, and it must never be open while the full suite is running.

**ADR-007 is written in M6 but drafted in M5**, because D12's honesty table is the thing most likely to be quietly softened once everything is green.

---

## Failure modes

| # | Failure | Detected by | Response |
|---|---|---|---|
| F1 | **Authority moves back into the prompt layer** — the phase's defining risk. A capability file acquires a rule the engine could enforce (a risk→review table, a "when to require a design review" heuristic, a restated gate list) | N6, the three widened content checks, `test_no_policy_default_value_is_restated_outside_sdle_py` | Stop-the-phase. The capability files carry judgement and presentation only. If a rule is worth having, it belongs in `sdle.py` — and that is a different phase |
| F2 | **A subagent gains a path to mutation** — a grant widens, the fence is stripped, or an agent is told to run a command | N13–N17 fire; `lint-skill` fails in CI | Stop-the-phase. Both layers must hold independently: removing either must fail a named check |
| F3 | An agent is put on a gate-decision path (invariant 8) | N25, and reading every agent prompt and capability row | Stop-the-phase. §16's parent-session invariant and CLAUDE.md invariant 8 have held through ten phases |
| F4 | **`lint-skill` coverage silently narrows** — a new capability file lands outside `_skill_files`, or an agent check passes vacuously because `.claude/agents/` is absent | N5, N19, N26 | M1 exists to make this structurally impossible; N19 exists because "tolerate absence" is exactly how a check stops meaning anything |
| F5 | `resume` becomes a second renderer of the header or a second derivation of gate requirement | N11 | Compose; call the same functions. A second source of truth in the invariant-7 phase would be the worst possible irony |
| F6 | `resume` acquires a write — a migration, a checkpoint, an audit line "for convenience" | N12, N23 | Read-only means read-only. If a caller needs `migrate`, it calls `migrate` |
| F7 | The capability map is treated as a ceiling and an existing cross-reference stops being followed, breaking remediation at `gate_design`/`gate_security` | N7, and the existing integration tests | D2. The map is a floor. `gate-protocol.md:196-197` must keep working verbatim |
| F8 | `phase-execution.md` gets split "while we are in here" | `every_phase_has_execution_block`, `execution_block_numbers_are_the_greenfield_positions` | D3/TP-002. Out of scope. Revert |
| F9 | A state field, migration row or version bump appears | N24 | D13. T10 adds no state. T11 owns the version bump |
| F10 | Breakage lands outside the X table | Full suite | X-GEN covers mechanically-forced closed-set growth. Anything else: stop and write `T10-blocker.md` (T09 NB-1 — the plan said stop, and extra rows were recorded instead) |
| F11 | The full suite is red | Full run | The F1 `ENVIRONMENT_FLAKE` procedure from T00/T01 is **VOID**. Any failure is a presumed real regression — investigate it; never pattern-match it to the old `WinError 5` signature |
| F12 | A false green or false negative from tooling | — | Plain `python -m pytest` under the `rtk` proxy prints `Pytest: No tests collected` and exits 0. Use `rtk proxy python -m pytest`, redirect to a file, read `$?` **with no pipe**. Reproduce any negative grep with `rtk proxy "grep -rnE …"` or a Python walk — a plain `grep -rn` has produced a false negative in this repository. `sdle.py constants` and `lint-skill` nest payloads under `data`. The tree is CRLF and `git show` is LF: normalise before concluding a file differs. The Bash tool caps a foreground command at 600 s; the suite takes ~23 min and must be backgrounded or chunked |
| F13 | `progress.md` becomes unparseable | `validate.py` exit 3 | A literal `\|` inside a table cell breaks it. Escape or reword |
| F14 | A YAML parser sneaks in to read agent frontmatter | N18's stdlib-only assertion; code review of the tests | D5. Regex over the `command:` / `tools:` lines. The engine has been stdlib-only for ten phases and §11's policy-format decision explicitly refuses a hand-rolled YAML parser |
| F15 | ADR-007's honesty table is softened — a "convention only" row is written as if enforced | Reading; D12's table is reproduced verbatim in ADR-007 and in the acceptance criteria | T08 and T09 both landed with an explicit not-guaranteed section. T10's is the most load-bearing yet, because named specialist agents *look* like enforcement |

---

## Rollback/recovery strategy

- **Whole-phase rollback:** `git reset --hard adbdc5e`. Nothing outside `docs/transition/` is shared with a later phase, and no state schema, migration or audit format changes, so rollback needs no data migration and cannot strand a WorkItem. A runtime created under T10 remains readable at `adbdc5e`: `state.json` is unchanged.
- **Per-milestone rollback:** each milestone is a coherent revert. M1 alone is revertible by restoring `_skill_files`. M5 is the only milestone whose partial state is red; if it is interrupted mid-window, the recovery is to finish X1 or delete the four agent files — either closes the window.
- **Recovery from an interrupted run:** read `docs/transition/phases/T10-checkpoint-a01-*.md`, `git status`, `git diff adbdc5e`, then restart at the last completed milestone boundary. Verify claimed state against disk; `pytest --collect-only -q` is the cheap check that a claimed test file exists.
- **If verification FAILs:** a fresh implementer reads `T10-verification-a01.md` as a finding set, increments the attempt, remediates only T10, and does not rewrite the verifier's evidence (§24.3).
- **Nothing to un-migrate.** T10 writes no runtime data at all.

---

## Acceptance criteria

Objective, and each one checkable by a command or a named test.

**Deterministic capability selection**

- [ ] A1 — `sdle.sh constants` reports a `capability_map` with a row for all 21 registry phases; `lint-skill` fails loudly on a missing or unknown row (N1, N8).
- [ ] A2 — Every capability path exists; `SKILL.md` is never a value (N2).
- [ ] A3 — Every row is a strict subset of the union; the union is exactly the `modules/*.md` on disk; no orphan module (N3, N5).
- [ ] A4 — Every gate phase maps to `gate-protocol.md` and no non-gate phase does (N4).
- [ ] A5 — Every capability cross-reference resolves and is itself mapped (N7).

**Fresh-session resume (the §16 exit criterion)**

- [ ] A6 — For **every phase in the registry** and at least two flows, a fresh process running `sdle.sh resume` with no arguments returns identity, position, pending items and an existing capability set, exit 0 (N9).
- [ ] A7 — At a gate, `resume` reports the same requirement and reasons as `gate show` (N10).
- [ ] A8 — `resume` composes rather than re-derives: header byte-identical to `header`, fields identical to `state get`/`flow show`/`gate show` (N11).
- [ ] A9 — `resume` writes nothing, migrates nothing, and audits nothing (N12, N23).
- [ ] A10 — `/sdle-continue` and `/sdle-start`'s resume branch load exactly what `resume` names, and name no module in prose.

**The subagent boundary is detectable, not asserted**

- [ ] A11 — Driving the exact fence command string from each agent's frontmatter, **every** mutating payload in the N13 battery is denied — including `Bash` running `sdle.sh gate approve` and `Bash` running `sdle.sh advance` (N13).
- [ ] A12 — The fence never fails open: no path, malformed payload, unknown tool all deny (N14).
- [ ] A13 — All four product agents grant only `Read, Grep, Glob` (N15).
- [ ] A14 — Each of the three agent lint checks has a test proving it **fires**, using `assert_only_failure` (N16, N17).
- [ ] A15 — The agent checks are absent rather than passing when `.claude/agents/` is absent, and the real repository has exactly four product agents and exactly four control-plane agents (N19).
- [ ] A16 — The engine invokes nothing: no `Task(`, no `launch_agent`, stdlib-only, no spawn naming `claude`/`agent`/`Task` (N18).
- [ ] A17 — No agent prompt and no capability row places an agent on a gate-decision path (N25).
- [ ] A18 — A subagent's findings reach the record only through `artifact review --actor-type agent`; **`git diff adbdc5e -- scripts/sdle.py` shows no new mutating command and no new state field** (D14, N24).

**`lint-skill` got stronger, not weaker**

- [ ] A19 — All 33 checks observed at E3 present by name and passing; new checks added; `failed: []` (N26).
- [ ] A20 — `_skill_files` is derived, and the three content checks now cover every capability file and every product agent prompt (N5, N6).
- [ ] A21 — `_searchable_files()` covers `.claude/agents/` (X3), or the narrowing is documented with its reason.

**Nothing else moved**

- [ ] A22 — `test_integration_01_happy_path.py`, both other integration files and the nine dry-run transcripts byte-identical to `adbdc5e` (N20).
- [ ] A23 — `settings.json`, `templates/state.json`, `.gitignore` byte-identical; v1.16; 16 migration rows; 8 approvals keys; 21 phases; `GREENFIELD_V1_PHASES` 19 entries; every flow element-wise identical (N21, N24).
- [ ] A24 — Invariant 3 holds for every new file (N28); the four existing hook guards behave exactly as before (N27); legacy dual-read and `migrate-workflow` untouched (N22).
- [ ] A25 — **The honesty table (D12) appears in ADR-007 verbatim**, with its three "convention only" rows intact and unsoftened, and `CLAUDE.md` states which of the two runtime enforcement points belongs to Claude Code rather than to SDLE.

**Process**

- [ ] A26 — Full suite green and `lint-skill` `failed: []`, both run in this repository with output redirected to a file and `$?` read with no pipe; `validate.py` exit 0.
- [ ] A27 — Every changed test is in X1–X7 or matches the X-GEN shape, and every X-GEN re-valuation records the old and new literal verbatim in the handoff.

---

## Unknowns / decision requirements

**None is material. No blocker is warranted.**

| # | Unknown | Class | Why it does not block |
|---|---|---|---|
| U1 | Full-suite result at `adbdc5e` in this context | UNKNOWN (E4) | The implementer establishes its own baseline before M1. T09's 1402/1402 is cited as prior evidence, never inherited as an observation — the T08 planner's precedent |
| U2 | Python 3.11 and CI behaviour | UNKNOWN (E5) | Unchanged by this phase and never observed at any point in the migration. T10 introduces no new dependency and no new syntax level |
| U3 | Whether Claude Code enforces a declared `tools:` list and a frontmatter `hooks:` block **in general** | INFERRED (E10, E11) | Both were observed live in this session — one as a verbatim refusal, one as this agent's own tool set. The plan does not assume more than that, and D12 records the limit rather than hiding it |
| U4 | Whether a hook payload can identify the calling agent | UNKNOWN | Nothing in the design depends on it. The fence is per-agent by registration, not by payload inspection — which is why it can be unconditional (D5) |
| U5 | Whether `.claude/agents/` files trip `_searchable_files()` when added to it (X3) | UNKNOWN | Discovered in M5 by running the test. Both outcomes have a defined response in X3, neither is architectural |
| U6 | Exact final wording of the two new capability files | UNKNOWN | Content is judgement, constrained mechanically by N6/N28 and the widened checks. Not an architectural decision |
| U7 | Whether §16's precondition ("only after deterministic lifecycle ownership is stable") is met | **Judged met** — INFERRED (I1) | Stated explicitly rather than assumed, per the task. Ten phases complete, each independently PASS; lifecycle ownership sits in `sdle.py` (flow bound at `init` with no re-binder, gate requirement from policy, traversal in `advance`); 33 cross-file checks green. If the verifier disagrees, that is a FAIL finding, not a silent difference of opinion |

**Note on T09 NB-3** (§15's HIGH list names a documentation review that no gate implements): T10 **does not adopt it** and must not. It is recorded here only as an observation the task asked for — T10's capability split makes it *easier* to close later, because a `documentation-review` capability would be one new `modules/*.md` file, one `CAPABILITY_MAP` row and one product agent, with the lint coverage already automatic after M1. It would still need a gate, which is policy work and not T10's.

---

## Scope exclusions

Explicitly **not** in T10. Each would be future-phase leakage (§24.4 cl. 8).

**T11 owns all of these, and T10 adopts none of them:**

- removal of the legacy repository-global `.workflow/` rung and its dual-read;
- the repo-global lock remnants, `current_feature_id`, WorkItem-less initialisation, transitional dual-path code;
- **T03-1** — the declared `branch_guard` fail-open window (needs a schema change, hence T11);
- **T04 N-2** — Spec Kit discovery tier 2 newest-mtime cross-adoption;
- **T04 N-7 / T05 NB-7(b)** — `.sdle` absent from `SDLE_OWNED_PREFIXES` and the missing `cmd_manifest_build` exclusion;
- **T04 N-3** — the non-normalised write-fence carve-out path;
- **T04 N-6 / T02 residual** — stale `.workflow/` paths in `phase-execution.md` (including `:205`, E33) and `gate-protocol.md`, and ~17 lines in `docs/dry-runs/`;
- **T04 N-4** — `SKILL.md:358`'s inaccuracy;
- **T03-4/5/6/7/8/10**, **T02 NB-2/4/5** — the assorted hardening residuals;
- **T09 NB-2** — the LOW→HIGH / HIGH→LOW revalidation asymmetry;
- **T09 NB-3** — §15's unimplemented documentation review;
- the version bump past v1.16 and the fixed-8-gate prose.

**Also excluded:**

- splitting `phase-execution.md` (D3);
- any change to gate, approval, omission, risk, flow, baseline or discovery semantics (D10);
- any new state field, migration row or mutating command (D13);
- removal of the `sdle-transition-*` control plane or `apply-sdle-transition` — §1.4 forbids the transition deleting itself while still executing; a separate post-transition cleanup after T11 owns that;
- every §27 deferred item (MCP, DB, web UI, release/build, distributed locks, RAG, OPA/Rego, other agent adapters);
- `.claude/settings.local.json`, which is untracked local state and out of scope.

---

## One-paragraph summary for the implementer

Do M1 first and prove it changed nothing. Put the capability map in `SKILL.md`, let the engine answer "what do I load", and add `sdle resume` so a cold process can answer "where am I" from disk alone. Then add two capability files and four subagents that can read and nothing else — and make each of those four inabilities fail a named check when it stops being true. Add no writer, no state field, no gate, no policy value. If a test outside the X table breaks, stop and write the blocker.
