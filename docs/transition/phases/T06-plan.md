# T06 Plan

**Phase:** T06 — Requirements Quality, Structured Classification and Hybrid Risk (contract §12)
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED

> Planner wrote no product code, edited no test, and altered no prior phase artifact or the transition contract. Every figure below was produced by a command run in **this** context and is classed `OBSERVED`. Nothing is cited by bare line number; citations are by symbol or greppable anchor string.

---

## Objective

Contract §12 asks for four subsystems plus one standing regime:

1. a **Requirements Quality Gate** of twelve structured checks whose blocking findings *stop progression*;
2. **classifications** — WorkItem type and engineering flow proposal — advisory and recorded only;
3. **hybrid risk** — Claude proposes signals, deterministic policy decides, and *Claude cannot lower deterministic policy floors*;
4. **evidence persistence** of quality result, classification, signals, deterministic score, hard floors, final risk and uncertainty;
5. **governed artifact review/validation** — from this phase onward every governed artifact must be registered and reviewed before a downstream phase consumes it, with `ARTIFACT_REVIEWED` audit linkage and **staleness enforcement when the artifact SHA no longer matches the reviewed SHA**.

Exit criterion: *every WorkItem has deterministic, testable governance metadata before current planning/implementation begins.*

### The scoping tension, resolved explicitly

§12 also says: *"Preserve current gates temporarily. Do not make gates conditional yet. Record what the future required gate set **would be** for test comparison."*

That clause constrains **routing**, not **enforcement**. T06 therefore:

- **does not change** the phase sequence, the gate set, gate conditionality, or flow-based routing — those are T07/T09;
- **does** add two new deterministic refusals on the existing lifecycle path, because §12's "blocking findings stop progression" and TP-011's "SDLE MUST NOT allow a stale review to authorize downstream consumption" are unambiguous MUSTs, and *the core refuses; it does not warn*.

The orchestrator's framing of T06 as "records what it would imply, no behaviour change" is correct for items 2, 3 and the would-be gate set, and **not** correct for items 1 and 5. Where the framing and the contract disagree, **the contract is authority** (`transition.md` §1.3 and `progress.md`'s authority line). The absence-of-behaviour-change property T06 *does* prove is narrower and is pinned by A17/A18 below: risk level, classification and the would-be gate set change **nothing** about the traversal, and the eight gates stay unconditional.

### The judgement the orchestrator asked for: build on existing machinery, do not fork it

**Decision: extend, do not duplicate.** Evidence:

| Existing mechanism | What fact it owns | Verdict |
|---|---|---|
| `state["artifact_shas"][<gate_key>]` | the **approved baseline** SHA, written only by `cmd_gate_approve` / `_approve_drift` / `cmd_drift_rebaseline`, consumed only by `compute_drift` | **Keep as-is.** It records *human approval*, a different fact from *review*. T06 adds no key to it and changes none of its writers. |
| `cmd_artifact_record` → `current_artifact` / `current_artifact_sha` | "artifact exists, clears the floor, here is its fingerprint" | **This already is §12's "Register artifact + SHA" box.** T06 does not re-implement registration. |
| `compute_drift` | approved-baseline SHA vs current SHA | **Reused conceptually, not forked.** T06 adds the *review*-SHA comparison in a new function and reuses `sha256_file` and `resolve_artifact_path` rather than re-deriving either. |
| `evidence_dir` (`workitems/<id>/.sdle/evidence/`) | migration evidence today (`migration-<execution-id>.json`) | **Reused verbatim** as the evidence store, with the same `<kind>-<execution-id>.json` naming. |
| `append_audit` chain | the auditable event | **Reused.** T06 adds two *optional* keyword arguments, never a second ledger. |

Invariant 7 is satisfied because *review result* and *approval baseline* are **two different facts**, each with exactly one home. A second SHA-tracking mechanism for the *same* fact would be the hazard; that is not what this is, and A9 pins it by proving `artifact_shas`' writer set is unchanged.

---

## Repository evidence

Every row re-derived in this context.

| Claim | Class | Evidence |
|---|---|---|
| HEAD is `abee131` "T05 verified PASS; phase COMPLETE" on `transition/workitem-v1` | OBSERVED | `git log --oneline -8` |
| Working tree carries only ` M .claude/settings.local.json` | OBSERVED | `git status --short` |
| `abee131` is **control-plane only** — `A docs/transition/phases/T05-verification-a01.md`, `M docs/transition/progress.md` | OBSERVED | `git diff --name-status 475795a abee131` |
| **Rollback point for T06 is `475795a`** (the last commit containing product change) | OBSERVED | previous row: `abee131` touches no product file |
| Product baseline is `f8fdaa0` | OBSERVED | `progress.md` header |
| `python tools/transition/validate.py` → `TRANSITION_VALID: complete=6/12 next=T06`, **raw exit 0** | OBSERVED | run in this context |
| **Full suite: `569 passed in 616.00s (0:10:16)`; `-rsxX` produced no short-summary section** | OBSERVED | `rtk proxy "python -m pytest -q -rsxX"`, background task reported completion |
| `--collect-only -q` → **569 tests collected**, so collected == passed, zero skips/xfails/errors | OBSERVED | run in this context |
| Per-file collected counts sum to 569: resolution 96, repo_config 69, workitem 57, speckit_binding 55, workitem_runtime 45, hooks 44, integration_02_to_05 42, integration_06_to_09 38, state 37, infra 28, transitions 24, lint_skill 17, cli 9, integration_01 8 | OBSERVED | `--collect-only -q` piped through `sed`/`sort`/`uniq -c` |
| `lint-skill` raw exit 0, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15` | OBSERVED | `rtk proxy "python scripts/sdle.py lint-skill"` |
| `scripts/sdle.py` is **6311 lines**; **77** `add_parser(` registrations | OBSERVED | `wc -l`, `grep -c 'add_parser('` |
| The repository `.sdle/` contains exactly `config.json`, `implementation-state/.gitkeep`, `policies/.gitkeep`, `templates/.gitkeep` | OBSERVED | `find .sdle -type f` |
| `REPO_CONFIG_DEFAULTS = {"configVersion": "1", "policyFormat": "json"}`; `SUPPORTED_POLICY_FORMATS = ("json",)` | OBSERVED | `scripts/sdle.py`, symbols `REPO_CONFIG_DEFAULTS`, `SUPPORTED_POLICY_FORMATS` |
| **NB-4 confirmed by reading the source:** `read_repo_config` catches `(OSError, json.JSONDecodeError, ValueError)` and `return config` — the defaults | OBSERVED | `scripts/sdle.py`, symbol `read_repo_config` |
| **NB-3 confirmed:** `README.md` restates the defaults as a literal JSON block near the anchor `` `policyFormat` is `json` because `` | OBSERVED | `grep -n configVersion README.md` |
| `apply_advance` is the single shared phase-movement choke point; its docstring says *"enforcing the two refusals that matter … the guardrails the model must not be able to reason its way around"* | OBSERVED | `scripts/sdle.py`, symbol `apply_advance` |
| `apply_advance` has exactly **three** call sites — `cmd_advance`, `cmd_gate_approve`, `cmd_skip` | OBSERVED | `grep -n 'apply_advance('` returns the def plus three calls |
| `cmd_init` completes `requirements_check` and moves to `constitution_draft` by **direct assignment**, not via `apply_advance` | OBSERVED | `scripts/sdle.py`, symbol `cmd_init`, anchor `Requirements check completes immediately` |
| `gate_precondition_hook` is the existing named per-gate refusal site, already carrying the Gate 7 manifest clause and the four Spec Kit containment clauses, and already **skips under the transitional legacy binding** (`paths.workitem is None`) | OBSERVED | `scripts/sdle.py`, symbol `gate_precondition_hook` |
| `_approve_drift` does **not** call `gate_precondition_hook` | OBSERVED | `grep -n 'gate_precondition_hook'` returns exactly one call, inside `cmd_gate_approve` |
| `append_audit` renders a fixed 8-line block ending `**Prev:** …`; `_entry_digest` hashes the stripped block text | OBSERVED | `scripts/sdle.py`, symbols `append_audit`, `_entry_digest` |
| `tests/test_units_workitem_runtime.py` asserts the ledger ends with `**Prev:** ` + digest, so any new audit line must be inserted **before** `**Prev:**` | OBSERVED | `grep -rn '\*\*Prev:\*\*' tests/` |
| `tests/test_integration_01_happy_path.py` asserts `text.count("**Gate Decision:** APPROVED") == len(GATES)`, so a review must **not** reuse the `decision` field | OBSERVED | `grep -rn 'Gate Decision' tests/` |
| `run_happy_path` is a **single shared driver** used at 14 call sites across three files (`test_integration_01_happy_path.py`, `test_units_repo_config.py`, `test_units_workitem_runtime.py`) | OBSERVED | `grep -n 'run_happy_path' tests/*.py` |
| `"approve"` literal counts per test file: integration_01 8, integration_02_to_05 9, integration_06_to_09 9, speckit_binding 14, transitions 6, infra 1, resolution 1, runtime 1 — **49 total across 8 files** | OBSERVED | per-file `grep -c '"approve"'` loop |
| `"init"` literal counts total **116 across 11 files** (conftest 3, repo_config 25, speckit_binding 29, runtime 19, resolution 17, state 6, integration_02_to_05 8, integration_06_to_09 4, workitem 3, cli 1, integration_01 1) | OBSERVED | per-file `grep -c '"init"'` loop |
| `tests/test_units_repo_config.py::test_no_lifecycle_command_reads_the_repository_configuration` asserts **no** function whose name starts with `cmd_gate`/`cmd_advance`/`cmd_approve`/`cmd_init` references any `CONFIG_MEMBERS` name | OBSERVED | read the test body |
| `CONFIG_REFERENCE_SITES` is a closed 5-member set: `cmd_config_init`, `cmd_config_show`, `read_repo_config`, `repo_config_findings`, `collect_validation_findings` | OBSERVED | `tests/test_units_repo_config.py` |
| `test_the_runtime_member_names_are_derived_from_paths` asserts an **exact** 7-name runtime set and an exact 5-name config set, and that they are disjoint | OBSERVED | read the test body |
| `test_the_scrubbed_state_comparison_still_has_teeth` asserts `scrubbed["workflow_version"] == "1.15"` | OBSERVED | `tests/test_units_repo_config.py` |
| `tests/conftest.py` fixture chain: `bare_project` → `project` (registers one WorkItem) → `started` (runs `init`) and → `git_project` (git, **no** `init`) | OBSERVED | read `tests/conftest.py` |
| `.gitignore` ignores under `workitems/` only `workitems/*/.sdle/lock` and `workitems/.active-context.json`; `git check-ignore -v workitems/x/.sdle/governance.json` and `… .sdle/policies/governance-policy.json` both **exit 1** (not ignored) | OBSERVED | `cat .gitignore`, two `git check-ignore` runs |
| `SDLE_OWNED_PREFIXES` contains `workitems/` and does **not** contain `.sdle/` | OBSERVED | `scripts/sdle.py`, symbol `SDLE_OWNED_PREFIXES`; pinned by `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` |
| `.claude/hooks/hooks.py` `FENCED = (".workflow", "workitems", "requirements", "guidance")` — `.sdle` absent | OBSERVED | read `hooks.py` |
| ADR-002 records: *"The first phase that puts executable policy under `policies/` is the phase that must fence it"*, and that a bare `".sdle"` fence entry would shadow the `workitems` reason text because `in_dir` matches `/{name}/` anywhere | OBSERVED | `docs/architecture/ADR-002-repository-configuration-boundary.md` |
| Existing refusal-reason vocabulary: **40** `Refused` reasons, 5 `UsageError`, 13 `IntegrityError`. None of T06's proposed reasons collides | OBSERVED | AST-free regex enumeration over `scripts/sdle.py` |
| `T05-plan.md` acceptance **A19** forbade `classification`, `quality_gate`, `risk evaluate`, `risk_tier`, `flow_id` from appearing in the T05 diff — i.e. T05 explicitly reserved this vocabulary for T06 | OBSERVED | `docs/transition/phases/T05-plan.md` |
| `docs/transition/RESUME.md` is **stale**: it still says `complete=5/12 next=T05`. Non-authoritative by its own first paragraph | OBSERVED | read `RESUME.md`; contradicted by `validate.py` |
| The F1 `ENVIRONMENT_FLAKE` procedure is **VOID** — `6e8af8c` fixed the `write_atomic` `WinError 5` flake and the suite is green | OBSERVED | green 569-pass run; `RESUME.md` §1 |
| Host Python is **3.13**; CI pins 3.11 on `ubuntu-latest` + `windows-latest`; the branch is local-only | INFERRED from prior verification artifacts + this host | CI outcome is `UNKNOWN`; **predict nothing** |
| Whether any *additional* existing test (beyond the declared set) will require an inserted governance/review call | UNKNOWN | Bounded above by the 49 `"approve"` literals; the exact set must be derived at implementation and declared |

---

## Behavioral delta

### Deliberate changes

**D1 — Two new `Paths` runtime members and one new configuration member.**

- `Paths.governance_file` → `runtime / "governance.json"`
- `Paths.reviews_file` → `runtime / "reviews.json"`
- `Paths.governance_policy_file` → `policies_dir / "governance-policy.json"`

`workitem_runtime_member_names` gains the two runtime names, so both leak detectors in `collect_validation_findings` inherit them with no new code (the invariant-7 discipline T05 established).

**Naming is load-bearing:** the repository policy file is `governance-policy.json`, **not** `governance.json`. The runtime record and the policy must not share a basename, or the two leak detectors and the disjointness assertion in `test_the_runtime_member_names_are_derived_from_paths` would be contradictory.

**D2 — The built-in governance policy is a module constant; the repository file may only *strengthen* it.**

`GOVERNANCE_POLICY_BUILTIN` in `scripts/sdle.py` is the single source of truth for: the twelve check ids, which checks are blocking, which checks may be reported `NOT_APPLICABLE`, the closed set of risk signal ids and their weights, the score→level thresholds, the hard floor rules, and the would-be required-gate map.

A repository may place `.sdle/policies/governance-policy.json` to override. **The override is monotone: it may only make governance stricter.** Concretely, the reader refuses `policy_weakens_baseline` (exit 1) if the override

- removes any id from `blocking_checks`,
- adds any id to `optional_checks` that the built-in does not already list,
- lowers any signal weight below the built-in weight,
- raises any score threshold for a level above the built-in threshold,
- removes or lowers any hard floor,
- removes any gate from the would-be required-gate map.

Adding signals, adding floors, raising weights, adding blocking checks and adding gates are all permitted.

This is what makes "absent policy file → built-in defaults" **safe rather than fail-open**: the built-in is by construction the *weakest admissible* policy, so a missing, empty or unreadable override can never yield a weaker outcome than a present one.

**D3 — `read_governance_policy` is fail-closed. It does not inherit `read_repo_config`'s swallow (T05 NB-4 answered).**

`read_governance_policy(paths) -> dict` behaves as:

- file absent → return `GOVERNANCE_POLICY_BUILTIN` (deep-copied), `source = "builtin"`;
- file present but unreadable / not JSON / not a JSON object / unknown top-level key / wrong value type → **`raise Refused("policy_malformed", …)`**, exit 1. No `except: return defaults` anywhere in this function;
- file present and weakening → **`raise Refused("policy_weakens_baseline", …)`**;
- otherwise → the merged policy, `source = ".sdle/policies/governance-policy.json"`, plus its `sha256`.

`read_repo_config` is **not modified** — T05's NB-4 stays open and owned by T09; T06's obligation is only that its own security-relevant reader does not repeat the pattern. A test asserts, by AST, that `read_governance_policy` contains no `except` handler that returns.

**D4 — `governance` command group.** Four subcommands, JSON on stdout as always:

| Command | Writes? | Runtime-free? | Effect |
|---|---|---|---|
| `governance policy` | no | **yes** (repository-scoped, like `config`) | The effective policy, its source and SHA. Refuses `policy_malformed` / `policy_weakens_baseline`. |
| `governance assess --input <path>` | yes | no (needs a bound WorkItem) | Reads Claude's structured proposal, evaluates it against the policy, persists `governance.json` + an evidence file, and refuses `requirements_quality_blocked` when a blocking check failed. |
| `governance show` | no | no | The recorded record plus a freshness verdict against the current `requirements/` digest. |
| `governance gates` | no | no | The **would-be** required gate set for the recorded governance. Advisory. Nothing consumes it. |

`governance assess` **does not require `state.json`** — it may run before `init`, and must, because §12 places governance *before* planning. It therefore appends **no** audit entry (there is no `audit_sha` to rebaseline into and no state file to save); `init` and the first `advance` are where the governance facts enter the ledger. This preserves the audit chain's single-writer discipline exactly as it stands.

**D5 — The twelve checks are evaluated deterministically over a Claude-supplied structured proposal. Claude reports observations; the policy decides consequences.**

Input document (`--input`), stdlib JSON:

```json
{
  "governanceInputVersion": "1",
  "quality": {
    "problem_statement":          {"result": "PASS", "finding": null},
    "scope":                      {"result": "PASS", "finding": null},
    "out_of_scope":               {"result": "PASS", "finding": null},
    "acceptance_criteria":        {"result": "FAIL", "finding": "no measurable criteria for the filter endpoint"},
    "ambiguity":                  {"result": "PASS", "finding": null},
    "contradictions":             {"result": "PASS", "finding": null},
    "constraints":                {"result": "PASS", "finding": null},
    "nfrs":                       {"result": "NOT_APPLICABLE", "finding": "no non-functional requirement is in scope"},
    "security_data_implications": {"result": "PASS", "finding": null},
    "compatibility":              {"result": "PASS", "finding": null},
    "dependencies":               {"result": "PASS", "finding": null},
    "blocking_unknowns":          {"result": "PASS", "finding": null}
  },
  "classification": {"type": "enhancement", "flow": "ITERATIVE"},
  "risk": {
    "signals": ["external_api_surface", "persistent_data_store"],
    "proposedLevel": "LOW",
    "uncertainty": "MEDIUM"
  }
}
```

Deterministic rules, all refusals not warnings:

- all twelve ids present, no extras → else `quality_incomplete` / `quality_unknown_check`;
- each `result` ∈ `{PASS, FAIL, NOT_APPLICABLE}` → else `quality_malformed`;
- `NOT_APPLICABLE` only for ids in `optional_checks` → else `quality_not_applicable_refused`. §12 says *"NFRs when relevant"*, so `nfrs` is optional in the built-in; the other eleven are not;
- a `FAIL` **must** carry a non-empty `finding` → else `quality_malformed`. A blocking finding that says nothing is not remediable;
- **severity is read from the policy, never from the input.** Claude cannot mark its own failure advisory;
- any `FAIL` on an id in `blocking_checks` → `quality.result = "BLOCKED"`;
- `classification.type` ∈ `{enhancement, defect, hotfix, chore}`, `classification.flow` ∈ `{GREENFIELD, BROWNFIELD_DISCOVERY, ITERATIVE, DEFECT_FIX, HOTFIX}` → else `classification_invalid`. **Advisory and recorded only** — nothing reads it to route anything.

**D6 — Hybrid risk: `final = max(deterministic, proposed)` over a totally ordered lattice, and the maximum is computed by the core.**

`LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")`, index-ordered.

1. Every signal id must be in the policy's closed signal set → else `unknown_risk_signal` (refuse; a silently ignored signal is a silently lowered risk).
2. `score = sum(policy.weights[s] for s in signals)`; `deterministic_level` = the highest level whose threshold the score meets.
3. **Hard floors**: each floor rule is `{"signal": <id>, "level": <LEVEL>}` or `{"uncertainty": <LEVEL>, "level": <LEVEL>}`; a matching rule raises `deterministic_level` to at least its level. Floors are recorded individually in the evidence, with which rule fired.
4. `final = max(deterministic_level, proposedLevel)`.
5. If `proposedLevel < deterministic_level`, record `"loweringAttempted": true` and audit it at the next state-writing command. **It is not a refusal** — an honest lower estimate must not deadlock the workflow; the security property is that the attempt has *no effect*, and that is what the test asserts.

There is no code path anywhere in `sdle.py` that can produce a final level below `deterministic_level`. A19 pins this by property test over the full cross-product of signal subsets × proposed levels.

**D7 — Evidence persistence.** `governance.json` under the WorkItem runtime, written with `write_atomic`:

```
governanceVersion, workitem, recordedAt, executionId,
requirements: { sources: [{path, sha256}], digest },
quality:      { checks: [...12...], blocking: [...], result: "PASS"|"BLOCKED" },
classification: { type, flow, advisory: true },
risk: { signals, score, floorsApplied, deterministicLevel,
        proposedLevel, uncertainty, finalLevel, loweringAttempted },
wouldBeRequiredGates: [...],
policy: { source, sha256 }
```

plus a human-inspectable evidence document at `evidence/governance-<execution-id>.json`, matching the existing `migration-<execution-id>.json` convention. `requirements.digest` is a SHA-256 over the sorted `(repo-relative POSIX path, lowercase file sha)` pairs of `requirements/*` — deterministic, order-stable and platform-stable.

**Nothing is added to `state.json`.** See D12.

**D8 — Enforcement clause E1, inside `apply_advance`.** A third refusal, alongside `forward_jump` and `gate_not_approved`:

- `governance_missing` — the bound WorkItem has no `governance.json`;
- `governance_blocked` — the recorded `quality.result` is `BLOCKED`. The message lists the failing blocking check ids and their findings;
- `governance_stale` — the recorded `requirements.digest` differs from the current digest of `requirements/`. Remedy named in the message: re-run `governance assess`.

`apply_advance` is chosen because it is the single function all three phase-movement commands funnel through (`cmd_advance`, `cmd_gate_approve`, `cmd_skip`), so there is exactly one site to write and exactly one site to audit. `cmd_init` does **not** call it, which is why the 116 `"init"` call sites in the suite are untouched.

**Skipped when `paths.workitem is None`** — the transitional legacy `.workflow/` binding, which has no WorkItem to hold governance. This mirrors the identical, already-tested carve-out in `gate_precondition_hook`'s Spec Kit clause, and is a declared bounded residual that T11 removes together with the rung itself.

**D9 — The governed artifact review regime.**

- `artifact review --path <p> --type <reviewType> --result PASS|FAIL --actor-type human|agent|tool|test|system --actor-name <n> [--evidence <path>] [--comments <s>]`
  Fingerprints the artifact at review time, appends a record to `reviews.json`, writes an evidence document `evidence/review-<execution-id>-<n>.json`, and appends an `artifact_reviewed` audit entry.
- `artifact reviews [--path <p>]` — read-only listing with a per-artifact freshness verdict.

`reviews.json` is an **append-only list** of records keyed by repo-relative POSIX path:

```
{ "reviewsVersion": "1",
  "reviews": [ {path, sha256, reviewType, result, evidenceId,
                actor: {type, name}, comments, timestamp} , ... ] }
```

"Currently reviewed" is a derived predicate, never a stored flag: *there exists a record for this path whose `sha256` equals the artifact's current SHA and whose `result` is `PASS`*. A stored boolean would be a second source of truth for the same fact.

**Enforcement clause E2**, in a new `review_precondition(paths, state, gate_key, resolved)` called from **both** `cmd_gate_approve` and `_approve_drift`:

- `review_missing` — no review record for this artifact at all;
- `review_stale` — records exist but none matches the current SHA. The message names the reviewed SHA and the current SHA;
- `review_failed` — the newest record for the current SHA is `FAIL`.

`_approve_drift` is included deliberately: drift is precisely the case TP-011's staleness diagram describes, and approving drifted content against a review of the pre-drift content would be the exact violation. Skipped when `resolved` is `None` or `paths.workitem is None`, on the same grounds as E1.

**D10 — `ARTIFACT_REVIEWED` audit linkage without breaking a single existing entry.** `append_audit` gains two optional keyword arguments, `review` and `evidence_id`. When both are `None` the rendered block is **byte-identical to today**. When supplied, two lines are inserted **between `**Comments:**` and `**Prev:**`** — never after `**Prev:**`, because `tests/test_units_workitem_runtime.py` asserts the ledger ends with that field:

```
**Review:** architecture-review | PASS | agent:sdle-architect
**Evidence:** evidence/review-<execution-id>-3.json
```

The `decision` field is **not** reused for the review result, because `tests/test_integration_01_happy_path.py` asserts `**Gate Decision:** APPROVED` occurs exactly `len(GATES)` times.

§12's linkage fields map: `eventType` → the audit `event` (`artifact_reviewed`), `artifact` → `**Artifact:**`, `artifactSha` → `**Artifact SHA (SHA-256):**`, `reviewType`/`result`/`actor` → `**Review:**`, `evidenceId` → `**Evidence:**`.

**D11 — The would-be required gate set is computed and recorded, and nothing acts on it.** `required_gate_set(classification, final_risk, policy) -> list[gate_key]` is a pure function over the policy's gate map. Its output is stored in `governance.json` as `wouldBeRequiredGates` and reported by `governance gates`. A source-level test asserts that neither `apply_advance` nor any `cmd_gate*` / `cmd_advance*` function references `required_gate_set` or the string `wouldBeRequiredGates`; a differential test asserts two repositories whose governance differs only in risk level (`LOW` vs `CRITICAL`) produce **identical** traversals and identical `approvals`.

**D12 — No `workflow_version` bump, no migration row, no version-string edit.**

Governance and reviews live in new WorkItem runtime *files*, exactly as T03 put branch/SHA in `execution.json` rather than in `state.json` for the same reason. Consequences, all verifiable: `templates/state.json` stays byte-identical; `CURRENT_VERSION` stays `"1.15"`; `MIGRATIONS` stays at 15 tuples; `lint-skill` keeps reporting `15 migration rows` and `all four locations report v1.15`; and `test_the_scrubbed_state_comparison_still_has_teeth` (which asserts `workflow_version == "1.15"`) stays byte-unchanged.

This is also the correct *ownership* call: a governance record that must exist **before** `state.json` cannot be a field of `state.json`.

**D13 — Prompt and documentation layer.** `SKILL.md` Step 1 gains the governance step between `workitem create` and `init`, and names the three E1 refusals and the E2 review requirement; `modules/phase-execution.md` gains a **Governed Artifact Review (MANDATORY — before every gate)** block beside the existing Post-SpecKit Verification block; `modules/gate-protocol.md` gains the review-status line in the gate prompt preamble; `.claude/commands/sdle-start.md` and `sdle-approve.md` gain the corresponding invocation lines; `README.md` and `docs/SDLE-Reference-Guide.md` gain the governance and review sections; a new `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md` records the decisions and what was rejected.

**No constant table is edited.** No phase, no gate, no progress row, no migration row. `lint-skill` must be re-run after **each** document edit.

**Invariant 3 holds:** no `speckit-*` name and no `/speckit.*` command appears in any new subcommand, help string, refusal message or emitted key (A20).

**Invariant 8 holds:** §12's audit example names an actor `sdle-architect`. T06 **records an actor string supplied by the caller**; it does not create, register or invoke any subagent — that is T10. Reviews at T06 are performed in the parent session, and nothing holding a gate is delegated. `ADR-003` states this explicitly so T10 inherits a decision rather than an assumption.

### Preserved invariants

Each is pinned by a named acceptance criterion.

1. **State first / single writer (invariants 1, 6).** `state.json` and `audit.md` keep exactly their current writer set. `governance.json` and `reviews.json` have exactly one writer each. `write_atomic`, `save_state`, `read_state`, `append_audit`'s chaining order and `verify_audit_chain` are unchanged apart from D10's two optional arguments. (A9, A11)
2. **Gate discipline (invariant 2).** No gate becomes conditional; no gate is added or removed; `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE`, `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP` and `approvals` are byte-identical. `forward_jump` and `gate_not_approved` still fire first. (A6, A17)
3. **SpecKit opacity (invariant 3).** (A20)
4. **Gate content in conversation (invariant 4).** The gate prompt still displays artifact content; the review status is added to it, not substituted for it. (A21)
5. **Fail safe (invariant 5).** Every new failure path refuses and freezes; none advances a phase. `governance assess` persists the record **before** refusing `requirements_quality_blocked`, the same shape `cmd_artifact_record` already uses, so a blocked assessment is remediable rather than invisible. (A13)
6. **One source of truth (invariant 7).** No policy default value is restated outside `sdle.py`; `artifact_shas` is not overloaded; "currently reviewed" is derived, never stored. (A15, A9)
7. **Gates stay in the parent (invariant 8).** No subagent is created or invoked. (A20)
8. **The resolution ladder never guesses.** `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence` byte-identical. (A9)
9. **Legacy `.workflow/` dual-read still binds; `migrate-workflow` never mutates `.workflow/`; `init` still refuses `legacy_workflow_present` unconditionally.** (A16)
10. **Write fence, `SDLE_OWNED_PREFIXES`, hooks.** `.claude/hooks/`, `.claude/settings.json` and `SDLE_OWNED_PREFIXES` byte-identical; `.sdle/` still not SDLE-owned, so `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` passes unmodified. (A5, A9)
11. **Exit-code contract.** New failures are exit 1 (`Refused`) or exit 2 (`UsageError`) only. No new exit-3 path. (A14)

---

## Files expected to change

**Engine**

- `scripts/sdle.py` — D1–D12. Additive apart from: three inserted lines in `apply_advance`, one inserted call in `cmd_gate_approve` and one in `_approve_drift`, two optional parameters and two conditional lines in `append_audit`, two names appended to `workitem_runtime_member_names`, and three new `Paths` properties.

**Repository configuration**

- **None.** `.sdle/policies/` keeps only `.gitkeep`. The built-in policy is *not* written to disk by any command — writing it would restate `GOVERNANCE_POLICY_BUILTIN` in a second place and reproduce exactly the NB-3 drift surface. `config init` is **not** modified.

**Prompt layer / documentation**

- `.claude/skills/sdle/SKILL.md` (Step 1 prose only — **no constant table**)
- `.claude/skills/sdle/modules/phase-execution.md`
- `.claude/skills/sdle/modules/gate-protocol.md`
- `.claude/commands/sdle-start.md`, `.claude/commands/sdle-approve.md`
- `README.md`, `docs/SDLE-Reference-Guide.md`
- `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md` (new)

**Tests**

- New: `tests/test_units_governance.py`, `tests/test_units_artifact_review.py`
- Modified, and **only** as itemised in the anti-contradiction clause below.

**Control plane**

- `docs/transition/phases/T06-plan.md` (this file), `docs/transition/progress.md`, `docs/transition/phases/T06-handoff-a01.md`, `docs/transition/phases/T06-checkpoint-a01-NN.md`

**Must not change** — verify with `git diff --exit-code 475795a -- <paths>`:

`.claude/hooks/`, `.claude/settings.json`, `.claude/agents/`, `.claude/skills/sdle/templates/`, `.claude/skills/sdle/modules/security-review.md`, `.github/`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `scripts/README.md`, `.gitignore`, `.gitattributes`, `requirements/`, `docs/dry-runs/`, `docs/architecture/ADR-001-deterministic-core.md`, `docs/architecture/ADR-002-repository-configuration-boundary.md`, `.sdle/`, `tools/`, and everything under `docs/transition/` except this plan, `progress.md` and T06's own handoff/checkpoints.

`.gitignore` genuinely needs no edit: both `git check-ignore` probes exit 1 (evidence table).

`.claude/settings.local.json` is the user's Claude Code permission allowlist, is already modified in the working tree, and is **out of scope** — do not stage, revert or edit it.

### Anti-contradiction clause (binding)

This plan permits **exactly seven** changes to existing test files. Each is named, with its TP-003 category. **No other change to any existing test file is authorised.**

| # | File | Exact change | TP-003 |
|---|---|---|---|
| 0 | `tests/test_units_workitem_resolution.py` | add the literal `"governance"` to the frozenset asserted by `test_runtime_free_commands_is_a_closed_enumerated_set` — **the only edit permitted anywhere in that file** | 2 — `governance policy` is repository-scoped, so the closed set genuinely grew; it stays a closed set |
| 1 | `tests/test_units_repo_config.py` | add the literal `"governance_policy_file"` to the `CONFIG_MEMBERS` tuple | 2 — the member set genuinely grew; the assertion is not weakened |
| 2 | `tests/test_units_repo_config.py` | add `"read_governance_policy"` (and no other name) to `CONFIG_REFERENCE_SITES` | 2 — one new function legitimately reaches the boundary |
| 3 | `tests/test_units_repo_config.py` | in `test_the_runtime_member_names_are_derived_from_paths`, add `"governance.json"` and `"reviews.json"` to the expected runtime-name set | 2 — the runtime member set genuinely grew |
| 4 | `tests/test_units_repo_config.py` | rewrite `test_no_lifecycle_command_reads_the_repository_configuration` so it asserts the **policy** members are read only through `read_governance_policy`, and that no `cmd_*` function reads `config_file` | 2 — **genuinely superseded.** Its docstring scopes it to §11's "18-phase behaviour stays authoritative"; T06 is the phase §11/ADR-002 named as the one where policy becomes executable. It must be rewritten honestly, **not** evaded by hiding the read in a differently-named helper |
| 5 | `tests/conftest.py` | add a `Project.record_governance()` method, and **one** call to it inside the `started` fixture, immediately before `project.ok("init", …)` | 2 — a new mandatory lifecycle input |
| 6 | `tests/test_integration_01_happy_path.py` | in `run_happy_path` only: one `record_governance()` call before `init`, and one `artifact review` call before each of the eight `gate approve` calls | 2 — genuinely superseded by D8/D9 |

**`tests/conftest.py` may change in exactly the two ways in row 5 and no other.** `bare_project`, `project`, `git_project` and `isolated_git_identity` keep their exact current bodies; no fixture is added, removed, renamed or re-scoped. In particular **`project` is NOT modified** — `tests/test_units_workitem.py` overrides `project` back to `bare_project` and asserts exact registry contents, and `tests/test_units_repo_config.py` runs `sha_map` purity proofs over `bare_project` roots.

Beyond these seven, the implementer will find that some tests which approve gates or advance phases from an ad-hoc WorkItem (not via `started` and not via `run_happy_path`) require an inserted setup call. **The upper bound is the 49 `"approve"` literals across 8 files** (evidence table). That set is `UNKNOWN` at planning time and **must be derived at implementation, listed file-by-file in the handoff with the TP-003 category, and confined to inserted setup calls** — never to a relaxed assertion, a removed assertion, a `skip`, an `xfail` or a deletion. Each insertion is category 2.

If the implementer believes a change outside this frame is unavoidable, that is a **plan defect**: record it as a declared divergence with the reason and the category. Do not silently widen.

Nothing in this plan asserts an exact CLI subcommand set, an exact repository-root directory listing, or an exact `Paths` property set.

---

## Existing tests affected

| File | Scope | TP-003 category | Nature |
|---|---|---|---|
| `tests/test_units_workitem_resolution.py` | row 0 — one literal, plus any inserted setup call from the derived set | 2 | `RUNTIME_FREE_COMMANDS` gains exactly `"governance"`; the assertion stays a closed set. |
| `tests/test_units_repo_config.py` | rows 1–4 | 2 | The configuration-boundary containment suite grew a member and one authorised reader. Row 4 is the only *rewrite*; it stays a closed-set assertion. |
| `tests/conftest.py` | row 5 | 2 | One new method, one call site in `started`. |
| `tests/test_integration_01_happy_path.py` | row 6, inside `run_happy_path` only | 2 | One shared driver, 14 call sites across three files inherit the fix. |
| `tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py`, `tests/test_units_speckit_binding.py`, `tests/test_units_transitions.py`, `tests/test_units_infra.py`, `tests/test_units_workitem_runtime.py` | inserted setup calls only, at gate-approving / phase-advancing sites not covered by `started` or `run_happy_path` | 2 | Bounded above by 49 approve literals. Exact set derived at implementation and declared. |

**Expected `D` = 0. Expected `R` = 0. Expected `A` = 2** (`tests/test_units_governance.py`, `tests/test_units_artifact_review.py`).

No test may be weakened, skipped, xfailed or deleted.

Note for the implementer: a suite-wide `grep "skip\|xfail"` over `tests/` is **not** evidence of anything by itself. It matches a pre-existing `@pytest.mark.skipif(SH is None, …)` in `tests/test_units_infra.py`, the SDLE CLI flag `--skip-tests`, and the `skip` subcommand's own test names. Quote what the grep actually matched (T03 process lesson; a prior handoff got this wrong).

Tests that must remain **byte-unchanged and passing**, because they are the guardrails T06 is most likely to erode:

- `test_units_repo_config.py::test_an_uncommitted_boundary_is_not_treated_as_sdle_owned`
- `test_units_repo_config.py::test_the_scrubbed_state_comparison_still_has_teeth`
- `test_units_repo_config.py::test_the_two_boundaries_never_contain_one_another`, `::test_the_configuration_commands_never_touch_runtime_state`
- `test_units_workitem_resolution.py::test_workitem_rebinding_happens_only_at_the_declared_sites`, `::test_the_active_context_is_written_only_by_the_declared_setters`, `::test_no_rung_ever_returns_an_unregistered_workitem`, `::test_init_still_refuses_a_legacy_workflow_unconditionally` — and every other case in that file, whose **only** authorised edit is row 0's single literal
- every `test_units_workitem.py` case; every `test_hooks.py` case; every `test_lint_skill.py` case

---

## New tests required

Two new files. Every case names the deliverable it pins.

### `tests/test_units_governance.py`

**N1 — The three new `Paths` members are derived correctly.** For instances differing only in `workitem` (`None`, `"a"`, `"b"`): `governance_file` and `reviews_file` differ between `"a"` and `"b"` and live under `runtime`; `governance_policy_file` is **equal** across all three and equals `project_root/.sdle/policies/governance-policy.json`. AST proof that `governance_policy_file` references neither `workitem` nor `runtime`, and that neither runtime member references `config_root`.

**N2 — `governance.json` and `governance-policy.json` never share a basename.** `Paths.governance_file.name != Paths.governance_policy_file.name`, and the runtime/config name sets stay disjoint.

**N3 — Absent policy yields the built-in, and creates nothing.** `governance policy` in a repository with no `.sdle/` exits 0, reports `source == "builtin"`, and a recursive SHA map of the project root is byte-identical before and after.

**N4 — The policy reader is fail-closed.** Parameterised over: unreadable file (permission or directory-in-place-of-file), invalid JSON, JSON array, JSON scalar, unknown top-level key, wrong value type for each known key. Every case → exit 1, reason `policy_malformed`, **and nothing is written**. Plus an AST assertion that `read_governance_policy` has no `except` clause whose body returns a value.

**N5 — The override is monotone: six weakening shapes are refused.** One case per D2 bullet → exit 1, reason `policy_weakens_baseline`, with the offending key named in `data`. Six matching *strengthening* shapes → exit 0 and observably stricter behaviour.

**N6 — `governance policy` is runtime-free.** In a repository with two registered WorkItems and no `--workitem`, `governance policy` exits 0 while `state get` exits 1 with `workitem_ambiguous`; and `"governance" in sdle.RUNTIME_FREE_COMMANDS`.

**N7 — The twelve check ids are exactly §12's list.** Set equality against a literal in the test, so a rename or a dropped check fails loudly.

**N8 — Quality input validation refuses, one case per rule.** Missing id, extra id, bad `result` value, `NOT_APPLICABLE` on a non-optional id, `FAIL` with an empty finding, non-object input, wrong `governanceInputVersion`. Each → exit 1 with its own distinct reason.

**N9 — Severity comes from policy, not from input.** An input that adds a `"severity": "advisory"` key to a failing blocking check is refused (`quality_unknown_check` for the extra key), and an override that *removes* the check from `blocking_checks` is refused `policy_weakens_baseline`. Two independent doors, both closed.

**N10 — A blocking finding stops progression, and the record survives the refusal.** `governance assess` with a failing blocking check → exit 1 `requirements_quality_blocked`, **and** `governance.json` exists with `quality.result == "BLOCKED"` and the failing ids listed. Then `init` succeeds (governance is not an `init` precondition) but the first `advance` refuses `governance_blocked`, `current_phase` is unchanged, and `audit_sha` is unchanged. Re-assessing with the check passing then lets the same `advance` succeed.

**N11 — `governance_missing` and `governance_stale`.** (a) `init` then `advance` with no `governance.json` → exit 1 `governance_missing`, phase unchanged. (b) Assess, `init`, edit a file under `requirements/`, `advance` → exit 1 `governance_stale`, with both digests in `data`; re-assess → the same `advance` succeeds. (c) Adding a *new* file to `requirements/` also produces `governance_stale` (the digest covers the source set, not one file).

**N12 — E1 is skipped under the legacy binding, and only there.** In a repository with a `.workflow/state.json` and zero registered WorkItems, a full advance sequence runs with no governance record and no refusal; with one registered WorkItem, the same sequence refuses `governance_missing`. Pins the declared residual so T11 can find it.

**N13 — Classification is validated and inert.** Every valid `(type, flow)` pair round-trips into `governance.json` with `advisory: true`; every invalid value is refused `classification_invalid`; and two repositories differing only in `(type, flow)` produce identical traversals, identical `approvals` and identical ordered audit event sequences.

**N14 — Deterministic scoring.** Table-driven over signal subsets: score equals the summed policy weights, and level equals the highest threshold met. Unknown signal id → exit 1 `unknown_risk_signal`.

**N15 — Hard floors fire and are individually recorded.** One case per built-in floor rule; `floorsApplied` names the rule that fired; a floor raises the level even when the score alone would not.

**N16 — Claude cannot lower the floor.** Property test over the **full cross-product** of (every subset of the built-in signal set, capped to keep runtime sane) × (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) as `proposedLevel`: `LEVELS.index(final) >= LEVELS.index(deterministic)` in every case, and `final == max(deterministic, proposed)` exactly. Where `proposed < deterministic`, `loweringAttempted` is `true` and the command still exits 0.

**N17 — The lowering attempt is auditable.** After the first state-writing command following a lowering assessment, the ledger contains an entry naming the proposed and final levels; `audit verify` still passes.

**N18 — Uncertainty is persisted and can carry a floor.** `uncertainty` round-trips; an override adding an uncertainty floor raises the final level.

**N19 — Evidence completeness.** `governance.json` contains **every** §12 evidence item: requirements-quality result, classification, risk signals, deterministic score, hard floors, final risk, uncertainty. Asserted as a required-key set, so a later refactor that drops one fails.

**N20 — The would-be gate set is computed and never acted on.** (a) `governance gates` returns a subset of the eight registered gate keys for every classification × risk combination. (b) AST: no function named `apply_advance`, `cmd_advance*`, `cmd_gate*` or `cmd_approve*` references `required_gate_set` or the literal `wouldBeRequiredGates`. (c) A guard that the prefixes in (b) actually match something, so (b) cannot pass vacuously. (d) **Differential:** two identical repositories whose governance differs only in final risk (`LOW` vs `CRITICAL`) produce identical traversals equal to `EXPECTED_TRAVERSAL`, identical `approvals`, and identical ordered audit event sequences modulo the governance entries.

**N21 — Purity.** `governance policy`, `governance show` and `governance gates` leave a recursive SHA map of the whole project root byte-identical, and append no audit entry. `governance assess` writes **only** `governance.json` and one file under `evidence/`, and appends **no** audit entry (it may run pre-`init`).

**N22 — Governance is writable before `init` exists.** `workitem create` → `governance assess` → the record exists and `state.json` does not; then `init` succeeds and `audit verify` passes, proving the chain is unaffected by the pre-init write.

**N23 — Invariant 7 grep.** No policy default value (`blocking_checks`, `optional_checks`, any weight, any threshold, any floor level) appears anywhere outside `scripts/sdle.py` — not in `README.md`, not in the Reference Guide, not under `.sdle/`. Executed as a real content search in the test, not asserted by narrative.

### `tests/test_units_artifact_review.py`

**N24 — Register → review → eligible.** Write an artifact, `artifact review --result PASS`, then `gate approve` succeeds; `reviews.json` holds one record with the artifact's SHA, and the ledger holds one `artifact_reviewed` entry.

**N25 — `review_missing`.** `gate approve` with no review → exit 1 `review_missing`, phase unchanged, `approvals` unchanged, `artifact_shas` unchanged, `audit_sha` unchanged.

**N26 — `review_stale` is the §12 staleness rule, verbatim.** Review PASS, then modify the artifact by one byte, then `gate approve` → exit 1 `review_stale`, with `reviewed_sha != current_sha` both present in `data`. Re-review → approve succeeds.

**N27 — `review_failed`.** Newest record for the current SHA is `FAIL` → exit 1 `review_failed`. A later PASS on the same SHA clears it; an earlier PASS superseded by a later FAIL does not.

**N28 — Freshness is derived, never stored.** Hand-editing `reviews.json` to add any boolean "fresh"/"current" flag changes nothing; the predicate is recomputed from SHAs. Asserted by grepping the emitted record's key set and by a behavioural case.

**N29 — Drift re-approval is subject to the same rule.** Approve Gate 2, drift the artifact, `drift check --queue`, then `gate approve` → exit 1 `review_stale`; review the drifted content, then re-approval succeeds and re-baselines. This is the case §12's diagram is drawn for.

**N30 — The two SHA mechanisms stay separate.** After a full run: `artifact_shas` has exactly the eight gate keys and no review data; `reviews.json` has no gate keys and no approval data; and `artifact_shas`' writer set in `sdle.py` is unchanged from `475795a` (AST over assignment targets).

**N31 — Audit linkage carries every §12 minimum field**, and `audit verify` passes afterwards. `event`, artifact path, artifact SHA, review type, result, actor type and name, evidence id all resolve from the entry.

**N32 — The audit block is byte-identical when no review is supplied.** Two ledgers produced by identical command sequences, one under `475795a`'s `append_audit` semantics (asserted by regenerating with `review=None, evidence_id=None`), match byte for byte; and the `**Prev:**` field remains the last line of every entry.

**N33 — Actor validation.** `--actor-type` outside `{human, agent, tool, test, system}` is refused; the actor name is recorded verbatim; **no subagent is created or invoked** (asserted by AST: no new import, no `Task`/agent invocation in `sdle.py`).

**N34 — E2 is skipped under the legacy binding, and only there.** Same shape as N12.

**N35 — Windows/POSIX path stability.** A review recorded with a backslash-separated `--path` is stored and matched under the normalised repo-relative POSIX key, so the same artifact is never reviewed twice under two keys. SHA comparisons are lowercase-hex on both sides (the v1.12→v1.13 lesson).

---

## Failure modes

**F1 — `ENVIRONMENT_FLAKE` is VOID. Do not resurrect it.** `6e8af8c` fixed the `write_atomic` `WinError 5` flake and the suite is green at 569. **Every failure this phase is a presumed T06 regression** — investigate it; do not pattern-match it to the old signature, and do not touch `write_atomic`.

**F2 — The `rtk` shell proxy hands you a false green.** Plain `python -m pytest` prints `Pytest: No tests collected` and exits 0. Use `rtk proxy "python -m pytest …"`, and read the raw exit with no pipe between. `rtk` also truncates `git diff` and `grep`; `rtk proxy "<command>"` returns full output and changes nothing about what executes.

**F3 — The suite takes ~10–17 minutes and has grown every phase** (observed here: 616 s). Give every run a 600000 ms timeout. A truncated or timed-out run must never become a quoted figure.

**F4 — Test churn is the largest risk in this phase.** The bound is 49 approve literals plus the seven itemised edits. If the implementer finds itself editing an *assertion* rather than inserting a *setup call*, stop: that is either a plan defect or a design error in the enforcement placement.

**F5 — Enforcing in the wrong function.** E1 belongs in `apply_advance`, not in `cmd_advance` — putting it in `cmd_advance` would leave `gate approve` and `skip` unguarded, which is fail-open. E2 belongs in a function called from **both** `cmd_gate_approve` and `_approve_drift`.

**F6 — Evading the containment test instead of superseding it.** `test_no_lifecycle_command_reads_the_repository_configuration` matches on function-name prefixes. Hiding the policy read in a helper whose name does not start with `cmd_gate`/`cmd_advance` would make the test pass while the guardrail silently died. Row 4 of the anti-contradiction clause requires an honest rewrite.

**F7 — Restating the built-in policy on disk.** Writing a default `governance-policy.json` from `config init` would reproduce NB-3's drift surface at a security-relevant location. The plan forbids it; N23 detects it.

**F8 — A second SHA mechanism creeping in.** Any commit that adds a key to `artifact_shas`, or stores a "reviewed" boolean, violates invariant 7. N30 and N28 detect it.

**F9 — Adding audit lines after `**Prev:**`.** Breaks `test_units_workitem_runtime.py`'s chain-tail assertion and, worse, changes the digest input ordering. D10 fixes the insertion point; N32 pins it.

**F10 — `governance_stale` firing spuriously mid-run.** `tests/test_integration_02_to_05.py`'s Phase-5 cases edit files under `requirements/`. Those tests use `started` and do not advance afterwards, so they should be unaffected — but **verify, do not assume**. If any of them does advance, the correct response is an inserted re-assessment call, not a relaxed staleness rule.

**F11 — Line-ending renormalisation between assess and check** could false-stale the requirements digest on a checkout that renormalises. It fails **closed** (an extra re-assessment), which is the acceptable direction. Do not "fix" it by hashing normalised text — that would make two genuinely different files hash alike.

**F12 — Five agent runs in this migration have been killed mid-flight by API spend limits.** Persist `T06-checkpoint-a01-NN.md` after **every** milestone, recording the suite figure observed at that point, the exact files touched, and what remains. Checkpoints are **claims**, not evidence: a resuming agent must verify them against disk — `--collect-only -q` is the cheap check, and a prior phase's checkpoints were accurate about the engine and wrong about tests.

**F13 — Python 3.11 / CI.** `NOT_RUN` / `UNKNOWN`. T06 is standard-library-only and adds no syntax beyond what `sdle.py` already uses. Predict no outcome; never claim green.

---

## Rollback/recovery strategy

- **Rollback point: `475795a`.** `abee131` is control-plane only (evidence table), so reverting product state to `475795a` restores the exact T05 tree.
- **Per-milestone:** each milestone is a checkpoint with a green suite. Revert the working tree to the previous checkpoint's file set and re-run.
- **No irreversible data effect.** T06 creates two new files per WorkItem and reads one optional repository file. Deleting `workitems/<id>/.sdle/governance.json` and `reviews.json` returns a WorkItem to a pre-T06 posture on disk; with the T06 engine present, `advance` then refuses `governance_missing` — which is the intended fail-safe direction, not data loss. `state.json` and `audit.md` are never rewritten by any new code path, so no existing runtime is damaged by an abandoned attempt.
- **Existing repositories mid-lifecycle.** A WorkItem initialised before T06 has no `governance.json` and will refuse at its next `advance` with a message naming `governance assess`. This is deliberate: it is exactly §12's "before current planning/implementation begins", applied to a workflow already in flight, and the remedy is one command. It must be stated in the handoff, in `ADR-003` and in `README.md`.
- **Verification failure** returns findings to a fresh implementer under §24.5; the plan is immutable.

---

## Acceptance criteria

Every figure must come from a command run in the implementing context and be **quoted, not predicted**.

- [ ] **A1** `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` at the end of T06: **raw exit 0**; `--collect-only -q` count equals the passed count; `-rsxX` produces no short-summary section (zero skips, xfails, errors). Both figures quoted.
- [ ] **A2** Suite arithmetic stated explicitly: re-derived baseline **569** at `475795a`/`abee131`, plus the collected counts of `tests/test_units_governance.py` and `tests/test_units_artifact_review.py`, equals the final count — with every per-file delta in a modified file accounted for (insertions add no test; a changed per-file count must be explained).
- [ ] **A3** `python scripts/sdle.py lint-skill` raw exit 0, **22 PASS / 0 FAIL**, reporting `Parsed 19 phases, 8 gates, 15 migration rows` and `all four locations report v1.15`. Re-run after **each** document edit, not only at the end.
- [ ] **A4** `python tools/transition/validate.py` raw exit 0.
- [ ] **A5** `git diff --exit-code 475795a -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .claude/skills/sdle/modules/security-review.md .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ docs/architecture/ADR-001-deterministic-core.md docs/architecture/ADR-002-repository-configuration-boundary.md .sdle/ tools/` returns **exit 0**.
- [ ] **A6** No constant table changed: the four phase tables, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE`, `PROGRESS_MAP` and `VERSION_MIGRATION` are byte-identical to `475795a`; `templates/state.json` byte-identical; `CURRENT_VERSION == "1.15"`; `MIGRATIONS` has 15 tuples; no version string anywhere changed.
- [ ] **A7** `sdle.RUNTIME_FREE_COMMANDS` equals the `475795a` set **plus exactly `"governance"`** — 8 members, nothing removed.
- [ ] **A8** `.sdle/policies/` still contains **only** `.gitkeep`; no command writes `.sdle/`; `config init` and `config show` are byte-identical to `475795a`; `REPO_CONFIG_DEFAULTS` unchanged.
- [ ] **A9 — Guardrails byte-identical.** Extract-and-compare (not eyeballing) against `475795a` shows these unchanged: `write_atomic`, `save_state`, `read_state`, `verify_audit_chain`, `touch_lock`, `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, `cmd_init`, `cmd_migrate_workflow`, `cmd_implement_preflight`, `cmd_drift_check`, `cmd_drift_rebaseline`, `compute_drift`, `read_repo_config`, `repo_config_findings`, `cmd_config_init`, `cmd_config_show`, and the `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`, `INJECTION_PATTERNS` and `SECRET_PATTERNS` definitions. `append_audit` differs **only** by D10's two optional parameters and the two conditional lines. `apply_advance`, `cmd_gate_approve` and `_approve_drift` differ **only** by the enforcement insertions.
- [ ] **A10 — §12 exit criterion, driven through the real CLI in a scratch project.** A fresh WorkItem cannot reach `constitution_draft`'s advance without a governance record; with one, `governance.json` contains all seven §12 evidence items; and `governance show` reports it.
- [ ] **A11 — Audit integrity.** `audit verify` passes after: a pre-`init` assessment, a blocked assessment, a lowering assessment, eight artifact reviews and a full 18-phase run. The chain is walked, not assumed.
- [ ] **A12 — Claude cannot lower a floor.** N16's cross-product runs green, and a hand-crafted input with `proposedLevel: "LOW"` against a `CRITICAL` floor yields `finalLevel: "CRITICAL"`, `loweringAttempted: true`, exit 0.
- [ ] **A13 — Fail safe.** For each of `governance_missing`, `governance_blocked`, `governance_stale`, `review_missing`, `review_stale`, `review_failed`, `policy_malformed`, `policy_weakens_baseline`, `unknown_risk_signal`, `classification_invalid` and every `quality_*` reason: exit 1, `current_phase` unchanged, `status` not advanced, `approvals` unchanged, `artifact_shas` unchanged, `audit_sha` unchanged. Driven through the real CLI, one case each.
- [ ] **A14 — Exit-code contract.** No new code path returns exit 3. Every new failure is 1 or 2.
- [ ] **A15 — Invariant 7.** N23 passes: no policy default value is restated outside `scripts/sdle.py`. Additionally, a grep over the whole T06 diff shows no `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP`, `ARTIFACT_OWNERSHIP`, `PHASE_TO_GATE_KEY`, `rate_limits` or `approvals` value copied into any new file.
- [ ] **A16 — T02/T03/T04/T05 guarantees still hold**, each by its named existing test passing unmodified: the ladder never guesses; the legacy dual-read rung binds; `migrate-workflow` never mutates `.workflow/`; `init` refuses `legacy_workflow_present` unconditionally; the Spec Kit binding is unchanged; `.sdle/` is not SDLE-owned.
- [ ] **A17 — The non-behaviour-change proof.** Two identical scratch repositories whose governance differs **only** in classification and final risk produce identical 18-phase traversals equal to `EXPECTED_TRAVERSAL`, identical `approvals`, identical `artifact_shas` key sets, and identical ordered audit event sequences modulo governance/review entries. Gates remain unconditional.
- [ ] **A18 — The would-be gate set is inert.** N20(b)+(c) pass; `governance gates` produces a non-trivial, differing set across risk levels while A17 shows the traversal does not move.
- [ ] **A19 — Staleness enforcement is real.** N26 and N29 pass; a one-byte edit to an approved artifact after review blocks approval until re-review, both in the normal path and in the drift-re-approval path.
- [ ] **A20 — Invariants 3 and 8.** No `speckit-` or `/speckit.` string in any subcommand name, help text, refusal message or emitted key added by T06 (grep over the diff). No subagent is created, registered or invoked; `.claude/agents/` byte-identical; no gate-holding step is delegated.
- [ ] **A21 — Invariant 4.** `modules/gate-protocol.md` still displays artifact content at every gate; the review status is added to the prompt, not substituted for the content.
- [ ] **A22 — No future-phase leakage.** A grep over the diff for `conditional gate`, `gate_policy`, `flow_selection`, `flow routing`, `baseline.json`, `discovery`, `brownfield`, `subagent`, `sdle-architect` (outside `ADR-003`'s and `SKILL.md`'s descriptive prose about actor strings) returns nothing actionable; `.sdle/baseline.json` is still not written by any code path; `implementation-state/` is still empty; the `.workflow/` dual-read rung, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal are all still present.
- [ ] **A23 — TP-003.** `git diff --name-status 475795a -- tests/` shows **zero `D`**, **zero `R`**, exactly **two `A`/`??`**, and an `M` set that is a subset of the ten files named in "Existing tests affected". Every `M` hunk is an inserted setup call or one of the seven itemised edits (rows 0–6); each is listed in the handoff with its category. No test weakened, skipped, xfailed or deleted, with the grep's actual matches quoted.
- [ ] **A24** Python 3.11 and CI recorded as **NOT_RUN / UNKNOWN**, with no outcome predicted.

---

## Milestone sequence

T06 is the largest phase in this migration so far: four subsystems plus a standing regime, two new engine command groups, two new test files and the first enforcement change on the lifecycle path since T02. **It is not compressed and no contract scope is dropped.** It is sequenced so the suite is green at the end of **every** milestone, with the risky structural work first and its proof being that nothing else moves.

One `T06-checkpoint-a01-NN.md` per milestone, each recording the observed suite figure, the exact files touched and what remains.

| M | Content | Why the suite stays green | Existing-test edits |
|---|---|---|---|
| **M1** | D1 `Paths` seam, `workitem_runtime_member_names` extension, `GOVERNANCE_POLICY_BUILTIN`, D3 `read_governance_policy`, D2 monotonicity, `governance policy` subcommand, `RUNTIME_FREE_COMMANDS += "governance"`. New tests N1–N6, N23. | **The structural proof, in the same role as T02's `Paths` seam, T04's M1 and T05's M1: nothing in the lifecycle reads any of it.** If anything other than the four itemised literals moves here, the seam is wrong. | Rows 0, 1, 2, 3 |
| **M2** | D5 quality model + D7 record/evidence writing + `governance assess` / `governance show`. New tests N7–N9, N19, N21, N22. | Write path only; nothing enforces yet, so no existing behaviour moves. | none |
| **M3** | D6 risk engine + classification + D11 `required_gate_set` + `governance gates`. New tests N13–N16, N18, N20(a). | Pure computation recorded into a file nothing reads. | none |
| **M4** | **D8 enforcement E1 in `apply_advance`** + conftest row 5 + `run_happy_path` governance call (part of row 6) + the derived set of inserted setup calls. New tests N10–N12. | The first behaviour-changing milestone. The suite goes red the moment E1 lands and is green again by the end of the milestone; that red window is *within* one milestone, never across one. | Rows 5, 6a + the derived set |
| **M5** | D10 `append_audit` optional linkage + governance audit events (including the lowering entry). New tests N17, N32. | Two conditional lines; the no-review rendering is byte-identical, pinned before anything depends on it. | none |
| **M6** | **D9 review regime** — `artifact review`, `artifact reviews`, `reviews.json`, `review_precondition` at `cmd_gate_approve` **and** `_approve_drift` + row 6b's eight calls in `run_happy_path` + the remaining derived insertions. New tests N24–N31, N33–N35. | Same shape as M4: one contained red window inside the milestone. | Row 6b + the derived set |
| **M7** | The phase-level proofs, written **after** the engine is complete so they test what shipped: A17 differential, N20(b)(c)(d) containment, N30 separation, N28 derivation. | Test-only. | none |
| **M8** | D13 prompt layer + README + Reference Guide + `ADR-003` + row 4's honest rewrite + full suite, `lint-skill`, `validate.py`, the A1–A24 matrix, handoff. | `lint-skill` re-run after each document edit. | Row 4 |

**Safe stopping line.** If an agent is terminated mid-flight, **M3 is the natural resume boundary**: everything through M3 is additive, green and behaviour-neutral, and M4 is where enforcement begins. A resuming agent that finds M1–M3 present and green may start at M4 without re-deriving them — after verifying against disk, not against the checkpoint text.

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is PLANNED.** The judgements that could otherwise be re-opened mid-flight are pinned here.

1. **Policy format: JSON, stdlib-only, no dependency, no home-grown parser. DECIDED by the user at §11; do not re-open.** T06 is the first phase with an *executable* policy, and it honours the decision literally: `GOVERNANCE_POLICY_BUILTIN` is a Python dict, the optional override is `json.loads`, `SUPPORTED_POLICY_FORMATS` stays `("json",)`, and `sdle.py` gains no import outside the standard library.

2. **T05 NB-4 — how T06 reads policy safely. DECIDED: a separate, fail-closed reader (D3).** `read_repo_config`'s swallow is **not** inherited and `read_repo_config` is **not** modified — that finding stays open and owned by T09. A security-relevant floor that silently defaulted would be exactly the wrong failure direction, so `read_governance_policy` refuses on every malformed shape and returns the built-in **only** when the file is genuinely absent — which is safe precisely because D2 makes the built-in the weakest admissible policy.

3. **T05 NB-3 — the README restatement of `REPO_CONFIG_DEFAULTS`. DECIDED: not adopted, and not grown.** T06 adds **no** lint rule (that remains T09's, per the T05 verifier's recommendation) and adds **no** new restatement: `README.md` and the Reference Guide *describe* the governance policy in prose and name `governance policy` as the way to read it, but reproduce **no** default value. N23 and A15 enforce this mechanically, so T06 leaves the drift surface exactly the size it found it.

4. **Fencing `.sdle/policies/`. DECIDED: no hook fence, and the reasoning is recorded in `ADR-003`.** ADR-002 says *"the first phase that puts executable policy under `policies/` is the phase that must fence it"* — T06 is that phase, so the question is answered rather than deferred. It is answered **no**, for three reasons: (a) a policy override is human-authored by design, exactly like `config.json`, so a write fence would block the intended workflow; (b) D2's monotonicity means a hand edit **cannot weaken governance** — the only reachable outcomes are "stricter" or "refused `policy_weakens_baseline`" — so the property a fence would protect is already guaranteed at the choke point, which is where SDLE's guarantees are supposed to live; (c) `hooks.py`'s `in_dir(path, name)` matches `/{name}/` **anywhere**, so a bare `".sdle"` entry would also match `workitems/<id>/.sdle/` and shadow the existing `workitems` reason text — the hazard ADR-002 and T05 NB-7(a) both recorded. `.claude/hooks/hooks.py` is on the must-not-change list and its byte-identity is part of T06's proof.

5. **`SDLE_OWNED_PREFIXES` is deliberately NOT extended to `.sdle/`.** ADR-002's rejection stands and its precondition still holds: **nothing in T06 writes `.sdle/` mid-run.** The two files T06 writes during a run are under `workitems/`, which is already in that tuple. `test_an_uncommitted_boundary_is_not_treated_as_sdle_owned` must pass byte-unmodified.

6. **No `workflow_version` bump (D12).** The T03 `execution.json` precedent applies, and the decisive argument is ownership rather than convenience: a governance record that must exist **before** `state.json` cannot be a field of `state.json`. Consequence: `lint-skill`'s `migration_covers_every_state_field` is unaffected, and `test_the_scrubbed_state_comparison_still_has_teeth` stays byte-unchanged.

7. **The E1/E2 legacy-binding carve-out is a declared, bounded residual.** Under `paths.workitem is None` the governance and review preconditions are skipped, because the transitional `.workflow/` binding has no WorkItem to hold either record. It is bounded to a rung that only fires when **zero** WorkItems are registered, it regresses nothing (neither check existed before), it mirrors an identical carve-out already tested in `gate_precondition_hook`, and **T11 removes the rung**. N12 and N34 pin it in both directions so it cannot silently widen.

8. **`docs/dry-runs/` is NOT updated, and that is a recorded documentation debt.** The nine transcripts are conversation-level and none of them shows a CLI call, so nothing in them becomes *false*; but dry-run 01's Phase 1 narration ("Content scan passed. Requirements look good.") no longer describes everything phase 1 does, and no transcript shows a review before a gate. Editing nine transcripts would be a large diff with no change in executable coverage, and the executable specification T06 actually updates is the integration suite. **Owner: T11's documentation sweep**, alongside T04's N-6 residual.

9. **The exact set of existing tests needing an inserted setup call is `UNKNOWN` at planning time**, bounded above by the 49 `"approve"` literals across 8 files (OBSERVED). It must be derived at implementation and declared file-by-file. This is deliberately *not* guessed here: guessing it would be exactly the kind of unverified quantitative claim that has caused three narrative defects in prior handoffs.

10. **Unowned hygiene items — explicit decisions, all "not adopted".** T03-4 (`ACTIVE_CONTEXT_SETTERS` dead in production code), T03-5 (`cmd_workitem_use` not error-hardened), T03-6 (`workitem_required` reason-name collision), T03-7/8, T03-10, T04 N-3 (non-normalised fence carve-out), T04 N-4 (`SKILL.md` inaccuracy), T04 N-7 (`cmd_manifest_build` lacks the Spec Kit exclude), T05 NB-5/NB-6: **T06 adopts none.** None is incidental to any edit in this plan — T06 touches none of those functions, and A5/A9 require several of them to be byte-identical. Adopting any would dilute T06's central proofs. T04 N-2, T03-1, T02 NB-2/4/5 and T04 N-6 remain **T11's**.

11. **`docs/transition/RESUME.md` is stale** (`complete=5/12 next=T05`, contradicted by `validate.py`). It is non-authoritative by its own first paragraph, and refreshing it is not a planner write under §24.2. Flagged for the orchestrator.

12. **Python 3.11 and CI: `NOT_RUN` / `UNKNOWN`.** Branch is local-only; CI pins 3.11 on `ubuntu-latest` and `windows-latest`; this host runs 3.13. Predict no outcome. T06 is stdlib-only and 3.11-safe by construction, so a later CI failure could not invalidate the design — but it must never be claimed green.

13. **Every quantitative claim in a prior plan is unverified until re-derived.** `T00-plan.md`'s "21 top-level subcommands" is known wrong; a prior handoff quoted 436 insertions where the figure was 341; another quoted an empty grep that in fact matched. Re-derive; quote what a command actually printed.

---

## Scope exclusions

The following must **not** leak into T06. If the implementer finds an edit that seems to require one, that is a plan defect to declare, not a licence to widen.

- **T07 — declarative flow selection.** This is where lifecycle semantics intentionally change, and T06 must not anticipate it. **Do not** make any gate conditional; **do not** route by flow type; **do not** retire or reorder the fixed 18-phase sequence; **do not** let `classification.flow` influence any transition. Record the would-be gate set; do not act on it (A18).
- **T08 — brownfield discovery and `baseline.*`.** No `baseline.json` is written or read; `Paths.baseline_file` stays a named, unwritten slot; no discovery phase, artifact or command.
- **T09 — risk-adaptive gate policy.** The risk level is computed and recorded and changes **nothing** about which gates run (A17). No gate policy is consulted at any gate. T05 NB-3's README lint rule and T05 NB-4's `read_repo_config` hardening remain T09's.
- **T10 — progressive skills and specialist subagents.** No subagent is created, registered or invoked, and `.claude/agents/` is byte-identical. `sdle-architect` appears only as a *recorded actor name string* supplied by the caller (A20, N33).
- **T11 — legacy removal and hardening.** The `.workflow/` dual-read rung, `migrate-workflow` and `init`'s unconditional `legacy_workflow_present` refusal must all keep working (A16). The `branch_guard` fail-open window (T03-1), the Spec Kit tier-2 mtime cross-adoption (T04 N-2), the `.workflow/` documentation residual (T04 N-6), the migration crash coverage (T02 NB-5), and now the `docs/dry-runs/` residual (item 8) are **not** T06's.
- **`implementation-state/`** stays an empty documented slot with no schema, producer or consumer.
- **`.claude/settings.local.json`** is out of scope; do not stage, revert or edit it.
- **`write_atomic`** must not be touched. F1 is void.
