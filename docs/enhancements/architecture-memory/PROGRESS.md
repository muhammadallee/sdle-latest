# Project Architecture Memory — Progress Log

Resumability record for the enhancement described in
`sdle-architecture-memory-prompt-v3.md`. Updated at every checkpoint so a fresh
session can resume without re-deriving state.

**Current wave:** Wave C complete; Rounds 1–3 closed; T5 is the CI run recorded in `DELIVERY.md`.
Contracts approved by the human on 2026-09-29 at commit `566f48d` and amended
by the Round-1 review (amendments marked *(R1-nnn)* in that document).

The delivery report is [`DELIVERY.md`](DELIVERY.md); the independent review is
[`REVIEW-ROUND-1.md`](REVIEW-ROUND-1.md); nothing was rejected, recorded in
`claude-review-rejections.md` at the repository root.

### Checkpoint record

| Checkpoint | What ran | Result |
|---|---|---|
| T0 | `lint-skill`; `test_units_invariants.py` + `test_units_flow_model.py` | **PASS** (44 checks; 118 tests) |
| T1 | `lint-skill`; a purpose-built end-to-end smoke over a scratch repository (33 checks: uninitialized catalog → placement → gate → revision 1 → replay → stale → conflict → realize → abandon) | **PASS** |
| T2 | `lint-skill` (46 checks); `test_units_architecture.py` (53) | **PASS** |
| T3 | `test_dry_run_contracts.py` (146); `test_lint_skill.py` + `test_units_capabilities.py` + `test_units_state.py` + `test_units_transitions.py` (300) | **PASS** |
| Round 1 | independent reviewer, fresh context, Read/Grep/Glob only, reviewing the committed patch | 22 findings — 1 CRITICAL, 4 HIGH; **all accepted and fixed** |
| T4 | after the Round-1 fixes: `lint-skill`; the smoke; `test_units_architecture.py`; `test_units_invariants.py` | **PASS** |
| Round 2 | the same isolation, reviewing the updated patch and verifying every Round-1 disposition | 22 findings — 1 CRITICAL (a **regression** the Round-1 fix introduced), 3 HIGH; **all accepted and fixed** |
| T5 (first attempt) | CI on `d1b203a` | **FAILED** — 22 failed / 3323 passed on both jobs. See *Incident: Stage 0 reverted by the copy*. |
| Reconciliation | `fbd7e7f` restores Stage 0; `7600a03` fixes the architecture defects. Locally: `lint-skill`, then every module that failed in CI and every module previously listed as not re-run, in foreground batches | **PASS** (1202 + 351 + 170 + 397 + 230 tests in separate batches) |
| Round 3 | independent reviewer, fresh context, Read/Grep/Glob only, reviewing `git diff d1b203a..HEAD` | 8 findings — 1 HIGH (a regression the merge introduced, `R3-001`); 3 accepted, 5 rejected as pre-existing Stage 0 issues, recorded in `claude-review-rejections.md` |
| T5 | the full suite | **CI** — the run on the final commit is recorded in `DELIVERY.md` |

### Incident: Stage 0 reverted by the copy

The architecture work was built in a separate checkout (`archi-sdle-latest-main`)
whose base commit `3642ffb` has a tree identical to `main`. Its finished tree was
then copied over the tip of `feat/requirements-refinement`, which carries
Stage 0 (OPEN-01/02, commits `27c3be0..fca6c00`, CI-verified and owner-confirmed).
For the twelve files both lines of work had touched, the copy took the
architecture checkout's version and so **reverted Stage 0**: pre-init
`accept-content --path`, the durable acknowledgement store,
`data.acknowledgeable`, the `governance_content_unacknowledged` refusal, the
V2/V3 hardening, nineteen governance tests, the `sdle-start.md` scan step, the
`MAINTENANCE_RECORDS` widening and the dry-run 05 rewrite. CI on `d1b203a`
showed it as ten `test_units_startup_contract` failures and two
"restated outside sdle.py" scans, alongside eight genuine architecture defects.

Stage 1 (`fca6c00..65b75df`) added only records and fixtures, so nothing in it
was lost. **Resolution:** each affected file was three-way merged (base `main`,
ours `d1b203a`, theirs `65b75df`) in a forward commit — no force-push — and both
behaviours were kept in `cmd_gate_approve`, where every precondition, including
the acknowledgement validation, still runs before `architecture apply` and
before the first ledger append. The write-primitive pins were recounted against
the merged engine, not summed.

Round 3's own first finding was a miss in this restoration (dry-run 05 still
carried `/18`); the only reason it was caught before CI was that an independent
reader looked. The local sweep above did not include `test_dry_run_contracts`.

### Test-module repair log

The lifecycle change moves an ordinal in a great many pinned expectations.
Modules re-run green in this session, in batches:

`test_units_invariants` · `test_units_flow_model` · `test_units_architecture`
(new, 58) · `test_dry_run_contracts` (186, incl. 2 new prose checks) ·
`test_lint_skill` · `test_units_capabilities` · `test_units_state` ·
`test_units_transitions` · `test_units_gate_policy` · `test_units_governance` ·
`test_integration_01` · `test_integration_02_to_05` · `test_integration_06_to_09`
· `test_integration_10_to_13` · `test_hooks` · `test_units_baseline` ·
`test_units_workitem_runtime` · the three `test_units_repo_config` boundary
pins · the two `test_units_speckit_binding` drivers.

**Not re-run here** (the last batch was still going when the session ended):
the remainder of `test_units_repo_config`, `test_units_speckit_binding`,
`test_units_hardening`, `test_units_manifest_changes`,
`test_units_implementation_evidence`, `test_units_doc_links`,
`test_units_documented_commands`, `test_units_retired_names`,
`test_units_shipped_surface`, `test_units_workitem_resolution`,
`test_units_discovery`, `test_units_artifact_review`,
`test_units_gate_artifacts`, `test_units_execution_identity`,
`test_units_cli`, `test_units_infra`, `test_units_install_contract`,
`test_units_policy_midflight`, `test_units_workitem`.

**The repair pattern, for whoever picks the rest up.** Nearly every failure is
one of four shapes, and none of them is an engine defect:

1. a hardcoded GREENFIELD ordinal or fraction — `N/18` → the engine's `N/20`,
   `Gate k` → `k+1` for `k ≥ 2`;
2. a driver that advances from `gate_constitution` (or `impact_analysis`)
   straight to the specification — insert `project.pass_architecture_gate()`,
   the `conftest.py` helper added for exactly this;
3. a hand-built catalog fixture with no `introducedBy` — the validator now
   requires it on every entity;
4. a pin on `SDLE_OWNED_PREFIXES` containing `.sdle/` — it now contains the
   three engine-written members instead.

### Decisions taken at the Wave B checkpoint

| Question | Answer |
|---|---|
| Freeze the contracts and start Wave C | **Approved** |
| D10 — narrow `SDLE_OWNED_PREFIXES`'s `.sdle/` entry (Part 11 item 3) | **Approved.** `.sdle/config.json` and `.sdle/policies/` become visible to the dirty-tree guard; `baseline.json`, `implementation-state/` and the new `architecture/` stay owned. |
| §8.2 reviewer isolation (Part 11 item 6) | **Patch file + Read/Grep/Glob agent.** The implementer commits, writes `git diff main...HEAD` to a scratch patch, and hands a fresh agent the patch plus HEAD paths with a Read/Grep/Glob-only grant. No command execution by the reviewer. |
| Part 11 item 5 — `.sdle/baseline.json` referencing the catalog | **No** (implementer recommendation, not contested). The catalog carries its own revision counter; a baseline pointer would add a second staleness axis with no consumer. |
| Synthetic `main` baseline | Accepted implicitly with the above; recorded here because it is a deviation from §6.1's `git pull`. |

---

## T0 — Baseline

| Fact | Value |
|---|---|
| Date | 2026-09-28 |
| Branch | `feature/project-architecture-memory` |
| Baseline commit (`main`) | `3642ffb685fe6cc3ce826b11a1867705d326c7cd` |
| Engine version | `CURRENT_VERSION = "1.17"` |
| `scripts/sdle.py` | 12 135 lines |
| `scripts/sdle.sh lint-skill` | **PASS** — 44/44 checks |
| `pytest -q tests/test_units_invariants.py tests/test_units_flow_model.py` | **PASS** — exit 0, no failures, 10 m 26 s (count not captured; output was truncated) |
| Full suite | **Deferred to CI** — see *Deviations* below |

### Environment findings

1. **The checkout was not a Git repository.** `sdle-latest-main` is a GitHub zip
   snapshot; there was no `main` to `git checkout && git pull`. `git init -b main`
   was run and the entire tree — including `sdle-architecture-memory-prompt-v3.md`,
   so the prompt itself stays out of the enhancement diff — was committed as the
   synthetic baseline above. Every downstream rule that needs a base ref
   (§6.5 commits, §8.2 `git diff main...HEAD`) now works. **This is a synthetic
   baseline of a snapshot, not a fetch of upstream `main`.**
2. **`pytest` was not installed.** `pip install -r requirements-dev.txt`
   installed the pinned versions (pytest 9.1.1).
3. **The full suite is very slow on this machine.** Two `test_units_*` files
   alone took 10 m 26 s; the whole suite had not finished after 50 minutes. The
   harness caps a single foreground call at 600 s, so any full-suite run is
   force-backgrounded.

### Deviations from the prompt (§0.2 SHOULD-deviations, recorded with reasons)

| Prompt clause | Deviation | Reason |
|---|---|---|
| §7.1 / §7.2 — full suite foreground at every checkpoint | Full suite is **not** run at T1–T5 in-session. `lint-skill` (seconds) plus focused test files are the in-session signal; the full suite runs in CI. | Operator instruction, 2026-09-28: *"stop the tests altogether … will run the full test at the end only via ci/cd."* The suite exceeds the harness's 600 s foreground ceiling, so an in-session "foreground full suite" is not achievable here anyway. CI already runs `pytest -q` and `lint-skill` on `ubuntu-latest` and `windows-latest`. |
| §8.2 / Appendix B — paste Part 2 and the contracts into the reviewer prompt | Round 3 pointed the reviewer at both by file path instead. | Both are files at HEAD that the Read-only reviewer can open; pasting 778 lines of contracts into the prompt would only have made it a second copy. |
| §12.1 — final verification `python -m pytest -q` captured in-session | Final counts will come from the CI run, not from a local capture. | Same instruction. `DELIVERY.md` will cite the CI run rather than claim a local pass. |

---

## Wave A — As-is map

Everything below was read on the baseline commit. Where this prompt's names and
the repository's differ, the repository wins (§0.3.1) and the mapping is recorded.

### A1 — Deterministic core and state model (`scripts/sdle.py`)

| Thing | Where | Note |
|---|---|---|
| `GREENFIELD_V1_PHASES` | `sdle.py:566` | Frozen 19-entry tuple (18 + `complete`). Editing it is the deliberately loud way to change GREENFIELD. |
| `DEFAULT_FLOW = "GREENFIELD"` | `sdle.py:~585` | |
| `MANDATORY_FLOW_PHASES` | `sdle.py:605` | 10 phases. The governance floor every flow keeps. |
| `GATE_NUMBER_PLACEHOLDER = "{gate_number}"` | `sdle.py:~620` | |
| `class Flow` | `sdle.py:~625` | `phase_count` excludes `complete` — the N in `N/18`. |
| `CURRENT_VERSION = "1.17"` | `sdle.py:1176` | |
| `write_atomic(path, text)` | `sdle.py:1063` | The only write primitive; uses `os.replace`. |
| `Refused` / `UsageError` / `IntegrityError` | `sdle.py:84–99` | Exit 1 / 2 / 3. |
| `reserve_evidence` | — | The only function that opens a file with mode `"x"` (pinned by `test_units_invariants.py`). |
| `SDLE_OWNED_PREFIXES` | `sdle.py:9683` | **See A3 — this is the D10 conflict.** |
| `cmd_implement_preflight` | `sdle.py:9688` | Dirty-tree guard. |
| `cmd_restart` | `sdle.py:9312` | Two-step confirm; clears downstream approvals + `artifact_shas`, trims `phase_history`. **D14 hook point (a).** |
| `cmd_reset` | `sdle.py:9400` | Two-step confirm; deletes `state.json`, `audit.md`, `lock`. **D14 hook point (b).** |
| `cmd_gate_approve` | `sdle.py:7628` | **D6/D7 hook point** for `architecture apply`. |
| `gate_precondition_hook` | `sdle.py:8880` | Gate-specific refusals at the choke point. Where `architecture_artifact_binding_invalid` belongs. |
| `review_precondition` | `sdle.py:7052` | TP-011 enforcement: `review_missing` / `review_stale` / `review_failed`. **D15 model.** |
| `cmd_artifact_review` | `sdle.py:7106` | Records `{path, sha256, reviewType, result, actor, …}`. |
| `establish_baseline` / `baseline_descriptor` | `sdle.py:~6170` | Called inside the final gate approval. **Model for `architecture realize` at `gate_implement`.** |

**There is no central refusal-reason registry in code.** Reasons are string
literals passed to `Refused(...)`. §3.11's "existing reason registry" maps to
**`docs/troubleshooting/README.md`**, which is the enumerated home, plus the
per-reason tests. Wave C adds the new reasons there, not to a new Python table.

### A2 — Lifecycle constants, gates, governance-gates policy

| Table | Home | Parsed by |
|---|---|---|
| `PHASE_SEQUENCE` (21 rows) | `SKILL.md` | `load_constants`, `sdle.py:968` |
| `FLOW_PHASES` (4 rows; GREENFIELD absent by design) | `SKILL.md` | `sdle.py:1009` |
| `NEXT_PHASE` | `SKILL.md` | `sdle.py:973` |
| `PHASE_TO_GATE_KEY` (8 gates) | `SKILL.md` | `sdle.py:978` |
| `ARTIFACT_OWNERSHIP` | `SKILL.md` | `sdle.py:987` |
| `PHASE_LABEL_MAP` | `SKILL.md` | `sdle.py:993` |
| `PROGRESS_MAP` (GREENFIELD view, `/18`) | `SKILL.md` | `sdle.py:998` |
| `CAPABILITY_MAP` (21 rows, 5 capability files) | `SKILL.md` | `sdle.py:1016` |
| **`GATE_TO_EXECUTION_PHASE`** | **`modules/gate-protocol.md`, not `SKILL.md`** | `sdle.py:1029` |
| `GATE_PHASES` | *derived* from `PHASE_TO_GATE_KEY` | never stored |

**Gate requirement derivation.** `gate_requirements` (`sdle.py:5075`) is the one
decider. Per gate it collects reasons from `_policy_gate_reasons`
(`required_gates_always`, `required_gates_by_risk`, `required_gates_by_type`) and
then, at `sdle.py:5102`:

```python
if gate_key == terminal:
    reasons.append("terminal_gate")
```

`disposition = "required" if reasons else "omittable"`. **That unconditional
`terminal_gate` reason is the exact model for a universally non-omittable
`gate_architecture`** — a derived reason no policy dictionary can remove.
`requirement_model` (`sdle.py:5243`) wraps it with the ADR-011 pin, which only
ever ANDs toward *more* required.

`cmd_gate_omit` (`sdle.py:7813`) re-derives the same model rather than trusting
`governance gates` output, so one added reason closes both doors.

### A3 — Requirements binding, baseline, discovery, ADR-012, dirty tree

- **`requirements bind` / `requirements show`** — `sdle.py:8581` / `8678`.
  Placement reads the binding; it never globs `requirements/` (D8).
- **Baseline** — `BASELINE_REQUIRED_KEYS`, `BASELINE_REFERENCE_KINDS =
  ("constitution", "architecture", "adrs")`, `sdle.py:6120–6126`.
  `baseline_descriptor` already collects a constitution reference, the
  `gate_design` design document as `architecture`, and ADR references harvested
  from OBSERVED discovery findings in category `adrs`. **This is exactly the
  evidence source D13's legacy `bootstrapDelta` draws on.**
- **Discovery** — `discovery schema` / `discovery assess --input` / `discovery
  show` at `sdle.py:5934` / `5968` / `6046`. **This is the command triple D7 says
  to mirror.** Note the design point stated in `cmd_discovery_assess`'s
  docstring: *every refusal fires before the first write*, unlike
  `governance assess` which persists a blocked record on purpose. Architecture
  placement follows **discovery's** rule (§3.5: "all mechanically detectable
  refusal conditions must run before the first state/audit mutation").
- **Dirty tree — the D10 conflict, and the one thing Wave B changes in existing
  behaviour.** `SDLE_OWNED_PREFIXES` (`sdle.py:9683`) is today:

  ```python
  (".workflow/", ".sdle/", "workitems/", ".specify/", "design/", "reviews/",
   "clarifications/", "guidance/", "requirements/")
  ```

  Two consequences:
  1. **§3.4.1's question is already answered: `workitems/<id>/` content is
     already SDLE-owned.** No new rule is needed for the WorkItem placement
     artifacts, and adding one would be redundant.
  2. **`.sdle/` is already owned *whole*.** D10 says `.sdle/config.json` and
     `.sdle/policies/` "must remain visible to dirty-tree checks" — today they
     are **not**. Satisfying D10 therefore means *narrowing* an existing prefix,
     which makes the guard **stricter**, not weaker. The in-code rationale for
     the current breadth must be preserved: `.sdle/baseline.json` and
     `.sdle/implementation-state/` are engine-written during a lifecycle and
     must stay owned, or one WorkItem's baseline write trips another WorkItem's
     guard. See the contracts document, §"Dirty-tree treatment", for the exact
     replacement tuple. **This is a Part 11 item 3 disclosure.**

### A4 — Tests, dry runs, verification matrix

- 35 test files under `tests/`. The count-bearing ones for this enhancement:
  `test_units_invariants.py` (GREENFIELD phase tuple, `STATE_FIELDS`,
  `WRITE_PRIMITIVE_COUNTS`, `COMMANDS`), `test_units_flow_model.py`,
  `test_units_gate_policy.py`, `test_lint_skill.py`, `test_dry_run_contracts.py`.
- `test_units_invariants.py` pins **write-primitive call-site counts**
  (`write_atomic: 26`, `save_state: 46`, `append_audit: 47`, `os.replace: 3`,
  `.mkdir(: 8`) and the **sorted sub-parser name set** `COMMANDS`. Both must be
  updated in the same commit as the engine change, with the reason written into
  the comment block, exactly as ADR-012's entry did.
- 16 dry runs, `docs/dry-runs/01..16` + `verification-matrix.md`. New scenarios
  continue at **17**.
- `tests/conftest.py` builds every git-backed fixture in `tmp_path` via
  `Project.init_git()`; `REPO_ROOT` is only a copytree source and a prose-search
  root, and `searchable_files()` never walks `.git/`. **`git init` at the
  repository root therefore cannot change any test outcome.**

### A5 — Docs and SpecKit integration points

- Documentation set (lint-enforced, `documentation_set_is_present`, 9 targets):
  `README.md`, `CLAUDE.md`, `docs/GETTING-STARTED.md`, `docs/architecture/`,
  `docs/workitems/`, `docs/lifecycle/`, `docs/risk-and-gates/`,
  `docs/brownfield/`, `docs/spec-kit-integration/`, `docs/troubleshooting/`.
- ADRs 001–012 exist. **Next free numbers: ADR-013 and ADR-014.**
- `lint-skill` version check reports **5 locations** carrying `v1.17`.
- Prompt files: `SKILL.md` + 5 modules (`phase-execution.md`,
  `gate-protocol.md`, `design-review.md`, `code-review.md`,
  `security-review.md`). `every_capability_file_is_linted` fails on an orphan
  module, so a new `modules/architecture-placement.md` and any
  `guidelines/*.md` must be reachable from `CAPABILITY_MAP`.
- 9 slash commands in `.claude/commands/`, 4 product agents in
  `.claude/agents/`, 5 hooks in `.claude/hooks/hooks.py`.

### Name mappings (§0.3.1)

| Prompt says | Repository has |
|---|---|
| "the existing reason registry" | no code registry; `docs/troubleshooting/README.md` + per-reason tests |
| `GATE_PHASES` as a table to update | derived from `PHASE_TO_GATE_KEY`; nothing to update |
| `GATE_TO_EXECUTION_PHASE` in `SKILL.md` | lives in `modules/gate-protocol.md` |
| "`workflow_version`/`CURRENT_VERSION`" | `templates/state.json` `workflow_version` + `sdle.py:1176` + 3 display copies (5 total, lint-checked) |
| §3.1 "18 → 20 phases, 8 → 9 gates" | GREENFIELD is 18 phases (excluding `complete`) / 8 gates today → **20 / 9** after the change. Confirmed against the engine, not the prose. |
| `docs/enhancements/…/PROGRESS.md` | created here; the repo's other convention (`.sdle/implementation-state/<name>/LEDGER.md`) is an execution-record format for a *maintenance run*, not a design log, and `.sdle/` is searched by the invariant-7 prose scan — so this log stays in `docs/`. |

---

## Open questions for the human

See the checkpoint presentation. In short:

1. Approve the synthetic `main` baseline (no upstream fetch was possible).
2. Approve narrowing `SDLE_OWNED_PREFIXES`'s `.sdle/` entry (D10 vs. current
   behaviour — Part 11 item 3).
3. Choose the reviewer-isolation mechanism for §8.2 (Part 11 item 6).
4. Part 11 item 5: should `.sdle/baseline.json` reference the architecture
   catalog? **Recommendation: no**, this iteration. The catalog has its own
   revision counter and its own lifecycle; a baseline pointer would create a
   second staleness axis with no consumer.
