# T08 Plan — Brownfield Discovery and Greenfield/Brownfield Convergence

**Phase:** T08 (transition contract §14, executed under §24.2)
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED
**Repo:** `D:\Learning\AI\sdle-git-repo\sdle-latest`, branch `transition/workitem-v1`
**HEAD when planned:** `451f440`
**Rollback point:** `c80f341` (T07 implementation)
**Product baseline:** `f8fdaa0`

---

## Objective

Give `BROWNFIELD_DISCOVERY` its real shape, and make the repository baseline a
real, deterministic artifact so that discovery happens **once** and every later
WorkItem converges onto `ITERATIVE`.

Four deliverables, in the contract's own words:

1. **§14 discovery output** — a structured discovery record covering the
   fourteen categories §14 names, where **every finding carries an
   `OBSERVED` / `INFERRED` / `UNKNOWN` classification** and the engine refuses a
   record that omits, invents or misuses one.
2. **§14 baseline** — `.sdle/baseline.json`, the slot T05 deliberately left
   empty, carrying the nine facts §14 lists and **referencing canonical
   artifacts instead of copying them**.
3. **§14 convergence invariant** — after *either* greenfield completion *or*
   brownfield discovery completion, the repository has the same minimum
   baseline shape.
4. **§14 exit criterion** — the second WorkItem against the same valid baseline
   does **not** rerun full brownfield discovery, proved end-to-end through the
   real CLI.

T08 does **not** make any gate conditional on risk (T09), introduce any product
skill or subagent (T10), or remove any legacy scaffolding (T11).

---

## Repository evidence

Every figure below came from a command run in *this* planning context, or from
a file read in it. Nothing is inherited from a prior agent's prose.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `451f440`; the only dirty path is `.claude/settings.local.json` | OBSERVED | `git log --oneline -8`, `git status --porcelain` |
| E2 | `python tools/transition/validate.py` prints `TRANSITION_VALID: complete=8/12 next=T08`, exit 0 | OBSERVED | ran it |
| E3 | T00–T07 are `COMPLETE`, attempt 1 except T06 (attempt 2); T07 commit `c80f341` | OBSERVED | `progress.md` rows T00–T07 |
| E4 | 901 tests collected | OBSERVED | `rtk proxy "python -m pytest --collect-only -q"` → `901 tests collected in 0.32s` |
| E5 | `lint-skill` reports **29** checks, all passing, exit 0; `version_string_consistent` says "all four locations report v1.16" | OBSERVED | `python scripts/sdle.py lint-skill`, and a JSON dump of `data.checks` |
| E6 | Flow shapes today, phases **including** terminal `complete` / gates: GREENFIELD 19/8, BROWNFIELD_DISCOVERY 19/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3. Excluding `complete` that is the familiar 18/8, 18/8, 16/7, 14/6, 10/3. | OBSERVED | `sdle.py constants` → `data.flows`, counted per flow |
| E7 | `GREENFIELD` and `BROWNFIELD_DISCOVERY` phase lists are **element-wise identical**; the registry has 20 entries; the only registry phase outside GREENFIELD is `impact_analysis` | OBSERVED | same dump: `g==b` → `True`; `len(phase_sequence)` → 20; `[p for p in phase_sequence if p not in g]` → `['impact_analysis']` |
| E8 | `Paths.baseline_file` resolves to `.sdle/baseline.json`; its docstring says "No engine path writes it at T05 — §14 owns its schema"; the only other references are the `config_names` leak-detector tuple and `config show`'s `members.baseline` | OBSERVED | `grep 'baseline_file\|baseline.json\|BASELINE' scripts/sdle.py` → 4 hits (lines near `def baseline_file`, `paths.baseline_file.name`, `"baseline": relative(paths.baseline_file)`); no file exists on disk |
| E9 | `test_brownfield_discovery_is_greenfield_until_t08_changes_it` names T08 as the owner of changing the equality, and `test_the_five_traversals_are_pairwise_distinct_except_the_declared_pair` asserts `equal_pairs == {("BROWNFIELD_DISCOVERY","GREENFIELD")}` | OBSERVED | `tests/test_units_flow_model.py`, those two function names |
| E10 | `impact_analysis` is the working precedent for a **gateless registry phase**: it has a `PHASE_SEQUENCE` row, a `NEXT_PHASE` row, a `PHASE_LABEL_MAP` row, **no** `PROGRESS_MAP` row, **no** `PHASE_TO_GATE_KEY` row, and a `**Phase \`impact_analysis\`` execution block with no ordinal | OBSERVED | `SKILL.md` tables at the `PHASE_SEQUENCE` / `NEXT_PHASE` / `PHASE_LABEL_MAP` / `PROGRESS_MAP` headings; `modules/phase-execution.md` block header |
| E11 | `every_phase_has_execution_block` accepts an ordinal-free header (`^\*\*Phase (?:(\d+) — )?\`([a-z_]+)\``) and exempts only `requirements_check` and `complete`; `execution_block_numbers_are_the_greenfield_positions` **rejects** an ordinal on a phase with no GREENFIELD position | OBSERVED | the two `Check(` bodies in `sdle.py` around `every_phase_has_execution_block` |
| E12 | `every_registry_phase_is_used_by_some_flow` fails on any registry phase no flow names | OBSERVED | its `Check(` body: `orphans = [p for p in consts.phase_sequence if p not in used]` |
| E13 | `_check_doc_phase_tables` requires every registry phase id to appear in `README.md` and `docs/SDLE-Reference-Guide.md` | OBSERVED | `_check_doc_phase_tables` body, `REPO_DOCS` loop |
| E14 | `cmd_init` binds `state["flow"]` from `classification.flow`, **before** `paths.workflow.mkdir(...)`, `write_execution_file` and the first `append_audit`; there is no `flow set` command | OBSERVED | `cmd_init` body; `flow_p` parser registers only `show` |
| E15 | `apply_advance` is the single choke point for `advance`, `gate approve` and `skip`; `governance_precondition` and `flow_precondition` sit there, and `flow_precondition` is documented as a **pure reader** placed ahead of every caller's first `append_audit` | OBSERVED | `apply_advance` body (three-step comment), `flow_precondition` docstring |
| E16 | The single completion choke point is the `is_final` branch of `cmd_gate_approve`, which calls `write_completion_summary` and then appends `workflow_complete` | OBSERVED | `cmd_gate_approve` tail; `grep write_completion_summary` → definition + exactly one call site |
| E17 | `read_governance_record` is **fail-closed** (absent → `None`; unreadable/unparseable/non-object → `IntegrityError`), and `read_repo_config` is **fail-open** (swallows `OSError`/`JSONDecodeError`/`ValueError` and returns defaults) | OBSERVED | both function bodies |
| E18 | `evaluate_classification` refuses any key outside `{"type","flow"}` and returns exactly `{"type","flow","advisory"}`; `test_units_governance.py` asserts that dict by **exact equality** | OBSERVED | `evaluate_classification` body; `assert record["classification"] == {"type": "enhancement", "flow": "GREENFIELD", "advisory": False}` |
| E19 | `read_governance_input` is the fail-closed structured-input precedent: unknown key, missing key, unsupported version, non-object section each refuse `governance_input_malformed`; nothing returns a default | OBSERVED | `read_governance_input` body |
| E20 | `.claude/hooks/hooks.py` fences `.workflow`, `workitems`, `requirements`, `guidance`. **`.sdle/` is not fenced.** `workitems/<id>/.sdle/` **is** fenced (only `workitems/<id>/specs/` is carved out) | OBSERVED | `FENCED`, `SPECS_CARVE_OUT`, `FENCE_REASONS` |
| E21 | `.gitignore` ignores `.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `workitems/*/.sdle/lock`, `workitems/.active-context.json`. **`.sdle/` is absent, so `.sdle/baseline.json` is tracked by default** | OBSERVED | `cat .gitignore` |
| E22 | `SDLE_OWNED_PREFIXES` (the `implement preflight` dirty-tree exclusion) is `.workflow/`, `workitems/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/` — **`.sdle/` is not in it**, and `cmd_manifest_build` excludes only `paths.runtime_relative` | OBSERVED | `SDLE_OWNED_PREFIXES` tuple; `runtime_prefix` comment in `cmd_manifest_build` |
| E23 | `test_integration_01_happy_path.py` asserts `verify.data["entries"] > len(EXPECTED_TRAVERSAL)` — a **strict inequality**, so one extra audit entry at completion does not break it | OBSERVED | `test_audit_chain_survives_the_whole_run` |
| E24 | `governanceVersion` is written into the record and read by **nothing** in `sdle.py`; the only test mention is a required-key-set assertion | OBSERVED | `grep governanceVersion scripts/sdle.py tests/*.py` → 1 write site, 1 key-set assertion |
| E25 | `cmd_artifact_record --phase` is a free-form string with no vocabulary check | OBSERVED | `recorded.add_argument("--phase")` and `phase = args.phase or state.get("current_phase")` |
| E26 | ADR-003 §10 established the precedent for adding new WorkItem runtime **files** (`governance.json`, `reviews.json`) with **no `workflow_version` bump**, arguing by ownership: a record that must exist before `state.json` cannot be a field of it | OBSERVED | ADR-003 §10 "No schema version bump" |
| E27 | ADR-003 §3 records that `read_governance_policy` deliberately did **not** inherit `read_repo_config`'s swallow-and-default, "a security-relevant floor that silently defaulted would be the wrong failure direction" | OBSERVED | ADR-003 §3 |
| E28 | ADR-003's "Alternatives rejected" forbids restating any policy default outside `sdle.py`, enforced by a real content search over README, CLAUDE.md, the Reference Guide, `.claude/skills`, `.claude/commands`, `.claude/hooks`, `.sdle/` and `docs/architecture/` | OBSERVED | ADR-003; `test_no_policy_default_value_is_restated_outside_sdle_py` and `_searchable_files` |
| E29 | ADR-004 "What this deliberately does not do" states T07 "does not give `BROWNFIELD_DISCOVERY` its real shape. That needs a repository baseline that does not exist yet." | OBSERVED | ADR-004 final section |
| E30 | ADR-004 §2's rejection of a ninth gate lists the exact cost: a `PHASE_TO_GATE_KEY` row, an `ARTIFACT_OWNERSHIP` row, a `GATE_TO_EXECUTION_PHASE` row, a ninth `approvals` key in the state template, and conditional gate numbering for every flow | OBSERVED | ADR-004 §2 |
| E31 | `SKILL.md` drives governance by telling Claude to use "every check id `sdle.sh governance policy` reports" — the established way a closed vocabulary reaches the prompt layer without being restated | OBSERVED | `SKILL.md` governance paragraph |
| E32 | `bare_project`, `project`, `started`, `git_project`, `started_git` are the conftest fixtures; `Project.record_governance(**over)` replaces whole input sections and deletes the transient input file after `assess` | OBSERVED | `tests/conftest.py` |
| E33 | The T07 verifier confirmed no `.sdle/baseline.*` is written or read, no baseline validity check exists "including for ITERATIVE", and that T08's edit to the BROWNFIELD row "cannot be silent" | OBSERVED | `T07-verification-a01.md` §"T08 (§14)" |
| E34 | T05's plan assigned baseline creation to T08 verbatim: "§11 calls it the 'future baseline' and §14 gives it a schema only T08 can produce" | OBSERVED | `T05-plan.md` |
| E35 | T05 finding NB-4 (fail-open `read_repo_config`) and NB-3 (`REPO_CONFIG_DEFAULTS` restated in README with no lint binding) are open and owned by T11 | OBSERVED | `RESUME.md` open-findings table; `README.md` `.sdle` tree block |
| E36 | Whether the suite passes on Python 3.11, and whether CI has ever run on this branch | **UNKNOWN** | Branch is local-only; CI pins 3.11; this host runs 3.13 (pycache files are `cpython-313`). Never observed. |
| E37 | "901 passed, raw exit 0" as an end-to-end result | **UNKNOWN in this context** | I collected 901 (E4) but did **not** run the suite — a planner should not burn ~17 minutes on it. The implementer must observe it. |

### Derived facts (INFERRED, with the evidence named)

| # | Claim | Evidence |
|---|---|---|
| I1 | Adding a registry phase `discovery` requires exactly: a `PHASE_SEQUENCE` row, a `NEXT_PHASE` row, a `PHASE_LABEL_MAP` row, membership in at least one `FLOW_PHASES` row, an ordinal-free `phase-execution.md` block, and the phase id appearing in `README.md` and the Reference Guide. It must **not** get a `PROGRESS_MAP` row (that table is the checked GREENFIELD view). | E10, E11, E12, E13 |
| I2 | T08 needs **no `workflow_version` bump and no `VERSION_MIGRATION` row**: it adds no `state.json` field and no ninth `approvals` key. Bumping would force a migration row plus a matching step in `sdle.py` for a schema that did not change. | E5, E26, E30 |
| I3 | The baseline write cannot be allowed to refuse: it lands inside `cmd_gate_approve` after `gate_approved` has already been appended, and an append cannot be undone by a later raise. | E15, E16, and the B1/NB-6 discipline recorded in ADR-004 §3 |
| I4 | A refusal at `cmd_init` placed before `paths.workflow.mkdir(...)` creates nothing at all — no runtime directory, no execution file, no audit entry. | E14 |
| I5 | `.sdle/baseline.json` written by the engine is compatible with the hooks as they stand (E20) and is tracked by Git as things stand (E21), so T08 needs **no** hook edit and **no** `.gitignore` edit. | E20, E21 |
| I6 | A second WorkItem's `implement preflight` and Gate 7 manifest **will** see an uncommitted `.sdle/baseline.json` as a working-tree entry, because `.sdle/` is in neither exclusion list. This is the same exposure T05 already created with `.sdle/config.json`. | E22 |

---

## Design decisions

Each decision names what was rejected and why. These are the plan's binding
content; the implementer must not silently substitute an alternative.

### D1 — `discovery` is a new registry phase, in `BROWNFIELD_DISCOVERY` only, and it is **gateless**

Registry position: **immediately after `requirements_check` and before
`impact_analysis`**, giving a 21-entry registry:
`requirements_check`, `discovery`, `impact_analysis`, `constitution_draft`, …

`BROWNFIELD_DISCOVERY`'s `FLOW_PHASES` row becomes GREENFIELD's list with
`discovery` inserted at position 2 → **19 phases / 8 gates** (20 entries
including `complete`). Every other flow row is byte-identical.

**Gateless, following ADR-004 §2's `impact_analysis` precedent exactly.** A
ninth gate would cost a `PHASE_TO_GATE_KEY` row, an `ARTIFACT_OWNERSHIP` row, a
`GATE_TO_EXECUTION_PHASE` row, a ninth `approvals` key in the state template and
therefore a schema migration, and it would make gate numbering conditional on
flow for every flow (E30). Discovery is not ungoverned: the engine refuses to
leave the phase without a validated record (D4), the record is durable evidence
in the WorkItem runtime, an audit event is appended, and the findings are
displayed in conversation before `gate_constitution` — the first gate downstream
— which is exactly how `impact_analysis` satisfies design invariant 4.

**Rejected — putting `discovery` in `MANDATORY_FLOW_PHASES`.** That floor is the
"shorter but never ungoverned" identity; adding `discovery` would force it into
GREENFIELD, `ITERATIVE`, `DEFECT_FIX` and `HOTFIX`, which is the opposite of
§14's intent.

**Rejected — a separate `BROWNFIELD_*` phase family.** §13's still-binding
constraint is "Do NOT build a generic BPM/workflow framework". One extra
registry row inside the existing ordered-subset model adds no new lifecycle
construct: no branching, no loops, no dynamic insertion, no policy DSL.

### D2 — `discovery assess --input <path>`, modelled on `governance assess`

A structured JSON document authored by Claude, evaluated deterministically, and
persisted as `workitems/<id>/.sdle/discovery.json` plus
`workitems/<id>/.sdle/evidence/discovery-<executionId>.json`.

Input envelope (fail-closed, mirroring E19):

```json
{
  "discoveryInputVersion": "1",
  "findings": [
    {
      "id": "F-001",
      "category": "<one of the fourteen closed ids>",
      "classification": "OBSERVED | INFERRED | UNKNOWN",
      "statement": "<prose>",
      "evidence": ["<repo-relative path>"],
      "basis": ["F-000"]
    }
  ]
}
```

Closed category vocabulary — §14's fourteen bullets, in §14's order:
`repository_inventory`, `modules_components`, `dependencies`, `architecture`,
`significant_patterns`, `conventions`, `apis`,
`persistence_data_architecture`, `test_practices`, `runtime_deployment`,
`security_patterns`, `adrs`, `constraints_non_negotiables`, `risks_debt`.

**Rejected — a Markdown discovery report as the governed artifact.** It would
have to live in `reviews/`, which is gitignored (E21), so the baseline would
reference a file that vanishes on a fresh clone. The record in the WorkItem
runtime is versioned by design.

**Rejected — copying the findings into the baseline descriptor.** §14 says the
baseline "references canonical artifacts instead of copying them". The
descriptor holds the record's path and SHA; `discovery.json` is the findings'
one home.

### D3 — What the engine can enforce about `OBSERVED` / `INFERRED` / `UNKNOWN`, stated honestly

This is the phase's integrity property and it is **split**. Say which half is
which, in the ADR and in the prompt layer.

**Engine-enforced (a guarantee).** `discovery assess` refuses — exit 1,
`discovery_input_malformed` or `discovery_incomplete` — when:

| # | Rule |
|---|---|
| R-a | unknown or missing top-level key; unsupported `discoveryInputVersion` |
| R-b | `findings` is not a non-empty list of objects |
| R-c | a duplicate finding `id`, or an `id` that is empty/not a string |
| R-d | `category` outside the closed fourteen |
| R-e | **`classification` missing, or outside `OBSERVED`/`INFERRED`/`UNKNOWN`** |
| R-f | `statement` missing or empty |
| R-g | `classification == "OBSERVED"` and `evidence` is empty, **or** any evidence entry is not an existing file/directory inside the repository, **or** any entry escapes the repository root |
| R-h | `classification == "INFERRED"` and `basis` is empty, **or** a basis id is not a declared finding, **or** a basis id names an `UNKNOWN` finding (an inference may not rest on an unknown) |
| R-i | `classification == "UNKNOWN"` and `evidence` is non-empty (a finding that cites evidence is one of the other two) |
| R-j | any of the fourteen categories has **zero** findings → `discovery_incomplete`, naming the missing ids. `UNKNOWN` is the honest answer where nothing is known, so this is always satisfiable without lying. |

**Not engine-enforced (a claim, not a guarantee), and it must be labelled as
such.** The engine cannot judge whether an `OBSERVED` statement is *true of* the
file it cites, whether an `INFERRED` conclusion follows from its basis, or
whether a finding is complete. Discovery is a judgement task; the deterministic
core cannot compute the findings. What it converts from prose to mechanism is:
*nothing is unclassified, an observation must point at something that exists, an
inference must name what it rests on, an unknown may not masquerade as evidence,
and no §14 category may be silently dropped.*

This is the T06 split verbatim (ADR-003: Claude proposes, deterministic policy
decides) and not a new pattern.

### D4 — Leaving `discovery` requires a validated record; the check is a pure reader at `apply_advance`

`discovery_precondition(paths, state)` refuses `discovery_missing` when the
bound flow contains `discovery`, `state["current_phase"] == "discovery"`, and
there is no `discovery.json` for this WorkItem with `result == "PASS"` and
`workitem == paths.workitem`.

It lives in `apply_advance` (E15), so `advance` **and** `skip` both hit it —
placing it in `cmd_advance` alone would let `skip` walk past discovery, which is
fail-open. It is a **pure reader**: no state write, no `append_audit`, so a
refused advance or skip leaves `audit.md` byte-identical (the B1/NB-6 property).
It is placed alongside `flow_precondition`, ahead of the accepted facts entering
the ledger.

No staleness mechanism is needed: `workitems/<id>/.sdle/` is write-fenced
(E20), so the record has one writer.

### D5 — `.sdle/baseline.json`: schema, and it references rather than copies

```json
{
  "baselineVersion": "1",
  "establishedAt": "<UTC ISO-8601>",
  "establishedBy": {"workitem": "<id>", "flow": "GREENFIELD|BROWNFIELD_DISCOVERY",
                    "executionId": "<prefix>-<UTC>"},
  "commit": "<sha or null>",
  "discovery": {"status": "PERFORMED|NOT_REQUIRED",
                "record": "workitems/<id>/.sdle/discovery.json | null",
                "recordSha256": "<sha> | null",
                "counts": {"OBSERVED": n, "INFERRED": n, "UNKNOWN": n} | null},
  "references": {"constitution": {"path": ..., "sha256": ...} | null,
                 "architecture": [{"path": ..., "sha256": ...}],
                 "adrs": [{"path": ..., "sha256": ...}]},
  "nonNegotiables": {"source": "<discovery record path> | null",
                     "findingIds": ["F-0nn"]},
  "supersedes": {"establishedAt": ..., "sha256": ...} | null
}
```

§14's nine required facts map one-to-one: baseline version → `baselineVersion`;
producing WorkItem → `establishedBy.workitem`; commit SHA → `commit`;
constitution reference → `references.constitution`; architecture/design
references → `references.architecture`; ADRs → `references.adrs`;
non-negotiables → `nonNegotiables`; discovery status → `discovery.status`;
timestamp → `establishedAt`.

Every reference is `{path, sha256}` — a pointer plus a fingerprint, never
content. `nonNegotiables` holds **finding ids** into the discovery record, not
prose.

Derivation, so nothing is invented and there is one home per fact:

- `references.constitution` — the resolved `gate_constitution` path from
  `ARTIFACT_OWNERSHIP`, when it exists on disk; else `null`.
- `references.architecture` — the resolved `gate_design` path from
  `ARTIFACT_OWNERSHIP`, when it exists; else `[]`. Deliberately not a
  hand-listed set of design documents: `ARTIFACT_OWNERSHIP` is the single home
  for "which file is this gate's artifact".
- `references.adrs` — the deduplicated, existing evidence paths cited by
  `OBSERVED` findings in the `adrs` category. Empty for a GREENFIELD-established
  baseline, which is honest: a new project has no ADRs to discover.
- `nonNegotiables.findingIds` — the ids of findings in the
  `constraints_non_negotiables` category. Empty under GREENFIELD.

### D6 — The baseline is written at exactly one choke point, by `GREENFIELD` and `BROWNFIELD_DISCOVERY` completion, and the write never refuses

Site: the `is_final` branch of `cmd_gate_approve` (E16), **first** in that
branch — before `write_completion_summary` and before the `workflow_complete`
audit entry — so an I/O failure produces the same failure shape
`write_completion_summary` already has today rather than a new one (I3).
One audit entry `baseline_established` is appended after `workflow_complete`;
E23 shows integration 01's strict `>` tolerates it.

The descriptor **builder never raises on missing inputs**: an absent
constitution yields `null`, an absent design document yields `[]`, an absent
discovery record yields `status: "NOT_REQUIRED"`. Validity is *derived later* by
`baseline_findings`, never asserted at write time. Writing must not be able to
block a human's final approval.

`discovery.status` is `PERFORMED` when the bound flow is
`BROWNFIELD_DISCOVERY`, `NOT_REQUIRED` when it is `GREENFIELD`. **That is the
convergence invariant made literal:** both completions produce a descriptor with
the same required key set; only the discovery-derived content differs.

**Rejected — writing/refreshing the baseline on `ITERATIVE`, `DEFECT_FIX` or
`HOTFIX` completion.** §14's convergence sentence names greenfield completion
and brownfield discovery completion, and nothing else. Extending it would let a
flow that performed no discovery establish a "discovered" baseline.

**Rejected — a `baseline establish` / `baseline set` command.** A second writer
of the baseline is the same governance bypass ADR-004 §3 refused for
`flow set`: it would let the model manufacture the fact that authorises
`ITERATIVE`.

### D7 — The reader is fail-closed, and validity/invalidation are derived by one predicate

`read_baseline(paths)` mirrors `read_governance_record` exactly (E17): absent →
`None`; unreadable, unparseable, non-object, or an unsupported
`baselineVersion` → `IntegrityError("baseline_invalid", …)`, exit 3. **It must
not inherit `read_repo_config`'s swallow-and-default (T05 NB-4, E17, E27).** A
silently-defaulted baseline would make the convergence invariant unprovable —
the exact failure direction ADR-003 §3 already rejected once.

`baseline_findings(paths)` is the **single** predicate, with two consumers
(`baseline show` / `baseline validate`, and `sdle validate`) — the
`repo_config_findings` shape, so two callers can never disagree about one
repository (invariant 7).

Derived status:

| Status | Condition |
|---|---|
| `ABSENT` | no file — **no finding is emitted**; most repositories have none |
| `INVALID` | ≥1 `error` finding — **this is §14's "material baseline invalidation"** |
| `STALE` | 0 errors, ≥1 `warning` finding |
| `VALID` | no findings |

Error findings (material invalidation), each with its own check id:

- `baseline_invalid` — malformed, non-object, unsupported version, or a missing
  required key;
- `baseline_producer_unregistered` — `establishedBy.workitem` is not in
  `workitems/index.md`;
- `baseline_reference_missing` — a referenced path (constitution, architecture,
  ADR, or the discovery record when `status == "PERFORMED"`) no longer exists.

Warning finding:

- `baseline_reference_changed` — a referenced path exists but its SHA-256
  differs from the recorded one.

**Why "changed" is a warning and "missing" is an error, decided and pinned.**
`design/app/app-design.md` is rewritten by `design_generation`, which
`ITERATIVE` runs. If a changed reference invalidated the baseline, the *third*
WorkItem in any repository would be forced back into full rediscovery — which
directly contradicts §26 item 22, "Full brownfield discovery is not repeated by
default". A **missing** reference is different in kind: the baseline's claims
can no longer be checked at all. A `STALE` baseline is reported by `validate`
and is a legitimate ground for a human to request rediscovery (D8), which is the
safe direction; it is never a refusal.

### D8 — Two `init`-time refusals, and one monotone opt-in

Both evaluate at `cmd_init` only — the single flow-binding site (E14) — placed
**before `paths.workflow.mkdir(...)`**, so a refusal creates nothing (I4).

| Id | Rule | Reason code |
|---|---|---|
| **R1** | Binding `BROWNFIELD_DISCOVERY` while `baseline_findings` reports `VALID` or `STALE`, and the record does not request rediscovery → refuse | `baseline_present` |
| **R2** | Binding `ITERATIVE` while status is `ABSENT` or `INVALID` → refuse | `baseline_required` |

**R1 is §14's exit criterion, enforced rather than asserted.** Remedies named in
the message: re-assess with `ITERATIVE`, or set
`classification.rediscovery: true`.

**R2 is §13's ITERATIVE definition made true** — "Use established repository
baseline. No full repository rediscovery." Without it, the convergence invariant
is decorative. `DEFECT_FIX` and `HOTFIX` are deliberately **not** covered: §13
gives them no baseline clause, and blocking an emergency hotfix on a
repository-level artifact would be a governance change T08 was not asked to
make.

**The opt-in.** `classification.rediscovery` becomes a third permitted key in
the governance input, boolean, optional, default `false`. It is monotone-safe in
exactly the sense ADR-003 uses: it can only ask for **more** work, never less,
so a model that proposes it cannot weaken anything. It is refused
(`classification_invalid`) with any flow other than `BROWNFIELD_DISCOVERY`,
because requesting rediscovery while binding something else is a contradiction.
`evaluate_classification`'s returned dict gains `"rediscovery": <bool>`;
`GOVERNANCE_RECORD_VERSION` is **not** bumped — it is written and read by nothing
(E24), and an absent key reads as `false`.

**Why only at `init`.** Re-checking at every `advance` would refuse a run
mid-flight over a repository-level fact the WorkItem cannot fix — for example
someone deleting a design document during an implementation. The flow binds
once; the baseline decision is made on the facts at binding time and recorded in
the `flow_selected` audit entry. Declared consequence, not a defect.

### D9 — "Significant existing source" stays a human/model judgement, deliberately

§14's first trigger is a conjunction: *significant existing source exists* **AND**
*no valid baseline exists*. T08 makes the second conjunct deterministic and
leaves the first where it is — expressed by the flow the human and Claude agree
on in the governance assessment.

**Rejected — a source-file-count threshold.** It would be an arbitrary magic
number at a governance-relevant location, it would need a policy key and a
default, it would misfire on monorepos and on generated code, and — the
disqualifying part — it would make the bare test fixture "not significant",
letting several new tests pass for the wrong reason. §14 gives no threshold and
T08 will not invent one.

### D10 — Vocabulary reaches the prompt layer through a command, never by restatement

New read-only `discovery schema` (writes nothing, needs no WorkItem) emits the
closed category vocabulary, the classification vocabulary, the envelope keys and
the rule ids. `phase-execution.md` says *"a finding for every category id
`sdle.sh discovery schema` reports"* — the exact shape `SKILL.md` already uses
for `governance policy` (E31). No category id, classification name or schema key
is written into any prompt or documentation file, and that is enforced by a
content search extending T06's N23 (E28) so T05's NB-3 drift surface is not
reproduced (E35).

### D11 — No `workflow_version` bump, no migration row, state template byte-identical

Reasoning in I2 and E26: T08 adds registry phases, new repository and WorkItem
**files**, and new commands. It adds no `state.json` field and no ninth
`approvals` key. `version_string_consistent` must still report v1.16 at all four
locations after the phase, and `migration_covers_every_state_field` must still
pass with 16 rows. Recorded as a residual for T11, which owns V1 convergence and
is the natural home for the version bump.

### D12 — What T08 deliberately does not touch

- **`.claude/hooks/`** — byte-identical. `.sdle/` is unfenced (E20) and the
  ADR-003 §4 hazard is unchanged: a bare `.sdle` fence entry would also match
  `workitems/<id>/.sdle/`.
- **`.gitignore`** — unchanged. `.sdle/baseline.json` is already tracked (E21).
- **`SDLE_OWNED_PREFIXES` and `cmd_manifest_build`'s exclusion** — unchanged.
  I6's cross-WorkItem exposure is real but is the same exposure T05 created with
  `.sdle/config.json`; widening a guard's exclusion set is a safety-reducing
  edit outside T08's goal. Recorded as a residual for T11 alongside T04 N-7.
- **`GREENFIELD_V1_PHASES`** — frozen, engine-held, not a `FLOW_PHASES` row.
- **The nine dry-run transcripts and `tests/test_integration_01_happy_path.py`**
  — byte-identical.
- **`required_gate_set` / `cmd_governance_gates`** — still inert, still
  `advisory: true`. T09 owns that.

---

## Behavioral delta

### Deliberate changes

1. The phase registry gains `discovery` (20 → 21 entries).
2. `BROWNFIELD_DISCOVERY` becomes 19 phases / 8 gates and is no longer identical
   to `GREENFIELD`; the other four flows are unchanged.
3. New commands: `discovery schema`, `discovery assess --input <path>`,
   `baseline show`, `baseline validate`.
4. New WorkItem runtime file `discovery.json` plus an evidence document.
5. New repository file `.sdle/baseline.json`, written at GREENFIELD and
   BROWNFIELD_DISCOVERY completion.
6. New audit event kinds: `discovery_recorded`, `baseline_established`.
7. New refusals: `discovery_input_malformed`, `discovery_incomplete`,
   `discovery_missing`, `baseline_present`, `baseline_required`,
   `baseline_not_valid` (exit 1); `baseline_invalid` (exit 3).
8. `sdle validate` reports baseline findings.
9. `classification.rediscovery` is accepted in the governance input and recorded.
10. `lint-skill` gains checks (see acceptance A6); none is removed or weakened.

### Preserved invariants

- **Gate discipline** — no gate is added, removed, renumbered or made
  conditional. All eight remain unconditional in every flow that has them.
- **Fail safe** — every new failure freezes; nothing advances a phase on error.
- **Single writer / refusal leaves the ledger untouched** — every new refusal is
  evaluated by a pure reader ahead of the caller's first `append_audit`; a
  refused `advance`, `gate approve`, `skip`, `init` or `discovery assess` leaves
  `audit.md` byte-identical, and a refused `init` creates no runtime at all.
- **The ladder never guesses** — WorkItem resolution is unchanged; `>1 plausible
  → ASK` still holds.
- **GREENFIELD** stays the frozen 19-entry `GREENFIELD_V1_PHASES`, engine-held,
  not derived from the registry, not a `FLOW_PHASES` row.
- `tests/test_integration_01_happy_path.py` and the nine dry-run transcripts
  stay byte-identical.
- Legacy `.workflow/` dual-read still works; `migrate-workflow` still never
  mutates `.workflow/`. Both new preconditions skip the legacy binding for the
  same reason `governance_precondition` does: there is no WorkItem to hold a
  record.
- **Invariant 3** (SpecKit opacity) — no `speckit-*` name enters any new user
  message. **Invariant 4** — the discovery findings are displayed in
  conversation before `gate_constitution`. **Invariant 7** — one home per fact;
  D10's content search enforces it. **Invariant 8** — nothing holding a gate is
  delegated; T08 creates no subagent.
- **The core refuses; it does not warn.** The one `warning`-severity output
  (`baseline_reference_changed`) is a `validate` finding, which is a diagnostic
  channel that already carries warnings — it is not a softened refusal.

---

## Files expected to change

| Path | Change |
|---|---|
| `scripts/sdle.py` | Registry-adjacent constants; `DISCOVERY_*` vocabulary and `BASELINE_*` constants; `read_discovery_input`, `evaluate_discovery`, `cmd_discovery_schema`, `cmd_discovery_assess`, `discovery_precondition`; `baseline_descriptor`, `read_baseline`, `baseline_findings`, `cmd_baseline_show`, `cmd_baseline_validate`; the `is_final` branch of `cmd_gate_approve`; `cmd_init` R1/R2; `evaluate_classification` `rediscovery`; `cmd_validate` wiring; new `lint-skill` checks; two parser groups |
| `.claude/skills/sdle/SKILL.md` | `PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_LABEL_MAP`, `FLOW_PHASES` (BROWNFIELD row only); one paragraph on discovery/baseline in the operating text. **No `PROGRESS_MAP` row.** |
| `.claude/skills/sdle/modules/phase-execution.md` | New ordinal-free `**Phase \`discovery\`` block; one bullet in `constitution_draft`/`gate_constitution` to display the findings before the first downstream gate |
| `README.md` | `discovery` in the phase narrative; the `.sdle/` tree at the `baseline.json` line stops saying "not created yet"; a sentence on discovery and convergence. **No version-table row** (D11) |
| `docs/SDLE-Reference-Guide.md` | `discovery` phase section; the flow table's `BROWNFIELD_DISCOVERY` row (18/8 → 19/8, new description); the `.sdle/` table's `baseline.json` cell; a baseline section |
| `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md` | **New.** Records D1–D12, the enforced/not-enforced split (D3) verbatim, and every rejected alternative |
| `tests/test_units_discovery.py` | **New** |
| `tests/test_units_baseline.py` | **New** |
| `tests/test_units_flow_model.py` | Updates listed under "Existing tests affected" |
| `tests/test_units_governance.py` | Updates listed under "Existing tests affected" |
| `tests/test_lint_skill.py` | A firing test per new lint check |
| `tests/conftest.py` | **Only** the two edits permitted by the anti-contradiction clause |
| `docs/transition/progress.md` | T08 row |
| `docs/transition/phases/T08-handoff-a01.md`, `T08-checkpoint-a01-*.md` | Written by the implementer |

Nothing under `.claude/hooks/`, `.claude/commands/`, `.claude/settings.json`,
`.claude/skills/sdle/templates/state.json`,
`.claude/skills/sdle/modules/gate-protocol.md`,
`.claude/skills/sdle/modules/security-review.md`, `.gitignore`, `docs/dry-runs/`,
`tools/transition/`, or any `T00`–`T07` artifact.

---

## Existing tests affected

Every row is TP-003 **category 2 — deliberately superseded behavior**, and the
handoff must record it as such with the reason. There is no category 4.

| Test (by name) | File | Why it must change |
|---|---|---|
| `test_brownfield_discovery_is_greenfield_until_t08_changes_it` | `test_units_flow_model.py` | Its own docstring says T08 owns changing it. Becomes a test that the two flows **differ** by exactly `discovery`. |
| `test_the_five_traversals_are_pairwise_distinct_except_the_declared_pair` | `test_units_flow_model.py` | `equal_pairs` becomes empty. Assert `equal_pairs == set()`. |
| `test_the_gateless_flow_denominators_are_the_declared_ones` | `test_units_flow_model.py` | `flows["BROWNFIELD_DISCOVERY"].phase_count` 18 → 19. GREENFIELD's 18 and ITERATIVE's 16 must be left alone. |
| `test_a_flow_traverses_exactly_its_declared_phases` (parametrised over `ALL_FLOWS`) | `test_units_flow_model.py` | `prepare()` gains a `discovery` arm; `bind()`/`drive()` gain a baseline for `ITERATIVE` (R2). |
| `test_iterative_never_reaches_the_constitution` | `test_units_flow_model.py` | Needs a baseline before `init` (R2). Its assertion is unchanged. |
| `test_units_governance.py` record-shape test asserting `record["classification"] == {"type","flow","advisory"}` | `test_units_governance.py` | Gains `"rediscovery": False`. |
| `FLOW_FIRST_GENERATION_PHASE` and the loop that inits all five flows | `test_units_governance.py` | `BROWNFIELD_DISCOVERY` lands on `discovery`, not `constitution_draft`; the "three distinct landings" assertion becomes four; `ITERATIVE` needs a baseline (R2). |
| Lint firing tests that edit the `BROWNFIELD_DISCOVERY` / `ITERATIVE` rows | `test_lint_skill.py` | Confirm they still fire; the row text changed. If a literal row string is embedded it must be re-derived, not re-typed. |

**Must not change, and this is checked:** `tests/test_integration_01_happy_path.py`,
`test_integration_02_to_05.py`, `test_integration_06_to_09.py`,
`tests/test_hooks.py`, `tests/test_units_state.py`,
`tests/test_units_transitions.py`, `tests/test_units_artifact_review.py`,
`tests/test_units_repo_config.py`, `tests/test_units_speckit_binding.py`,
`tests/test_units_workitem*.py`, `tests/test_units_cli.py`,
`tests/test_units_infra.py`.

### Anti-contradiction clause

The plan permits **exactly two** edits to `tests/conftest.py` and no others:

1. A new `Project.establish_baseline(...)` helper that writes
   `.sdle/baseline.json` by calling the engine's own `sdle.baseline_descriptor(...)`
   builder. It **must not** restate any schema key, default or vocabulary as a
   literal — the same discipline `record_governance` already follows by reading
   `sdle.GOVERNANCE_POLICY_BUILTIN`.
2. A new `Project.record_discovery(...)` helper that writes a valid discovery
   input, runs `discovery assess`, and removes the transient input file — the
   shape `record_governance` already uses. Its category list **must** be read
   from the engine (`discovery schema` or the module constant), never typed out.

No existing conftest fixture, helper or default may be modified. In particular
`record_governance`'s default `classification` stays
`{"type": "enhancement", "flow": "GREENFIELD"}`, because every existing
assertion depends on GREENFIELD being the fixture default.

If the implementer believes a third conftest edit or any other "must not change"
file is genuinely required, that is a **plan defect**: stop, write
`T08-blocker.md`, and return the decision. Do not widen the permission by
inference from this document.

---

## New tests required

### `tests/test_units_discovery.py`

| Id | Test |
|---|---|
| N1 | `discovery schema` writes nothing, needs no WorkItem, and emits exactly fourteen categories that are set-equal to §14's bullets and to the engine constant |
| N2 | The fourteen category ids and the three classification names are all underscored-or-uppercase identifiers, and there are exactly 14 / exactly 3 — guards N3 against passing vacuously |
| N3 | Rules R-a…R-j, one refusal test each, asserting the reason code, exit 1, and that the offending id is named in the payload |
| N4 | **The integrity property, isolated:** a finding with no `classification` key, and one with `classification: "PROBABLY"`, are each refused `discovery_input_malformed` naming that finding's id |
| N5 | An `OBSERVED` finding citing a path that does not exist is refused; the same finding with an existing path is accepted — the one part of "never present inference as observation" the engine actually checks |
| N6 | An `INFERRED` finding whose `basis` names an `UNKNOWN` finding is refused |
| N7 | An `UNKNOWN` finding carrying `evidence` is refused |
| N8 | Dropping one category is refused `discovery_incomplete` with that category named; a document where every category is a single `UNKNOWN` finding is **accepted** |
| N9 | A refused `discovery assess` leaves `audit.md` byte-identical, `state.json` byte-identical, and writes no `discovery.json` |
| N10 | An accepted assess writes `discovery.json` and an evidence document, appends exactly one `discovery_recorded` entry, and `audit verify` reports `chain_ok` |
| N11 | `advance` out of `discovery` without a record refuses `discovery_missing`; **and so does `skip`** — the fail-open case |
| N12 | `discovery_precondition` is a pure reader: the refusal in N11 leaves `audit.md` byte-identical for both `advance` and `skip` |
| N13 | `discovery.json` is refused as a WorkItem→repository leak if planted in `.sdle/`, and `baseline.json` planted in a WorkItem runtime is still refused `repository_config_in_workitem` (the existing derived leak detector inherits both) |
| N14 | Content search: no discovery category id, classification name or input key appears in any file of T06's `_searchable_files()` set (invariant 7 / T05 NB-3) |

### `tests/test_units_baseline.py`

| Id | Test |
|---|---|
| N15 | `read_baseline` is fail-closed: absent → `None`; `{not json`, `"a string"`, `[]`, and an unsupported `baselineVersion` each raise `IntegrityError`, exit 3. Explicitly contrasted with `read_repo_config`'s swallow (T05 NB-4) |
| N16 | `baseline show` on a repository with no baseline reports `ABSENT` and emits no finding; `sdle validate` is unchanged in that case |
| N17 | `baseline validate` exits 0 on `VALID` and 1 (`baseline_not_valid`) on `ABSENT`, `INVALID` and `STALE` |
| N18 | Each error check fires exactly once and by name: `baseline_invalid` (missing required key), `baseline_producer_unregistered`, `baseline_reference_missing` |
| N19 | `baseline_reference_changed` is a **warning** and yields `STALE`, not `INVALID` — the decision in D7, pinned so a later phase cannot flip it silently |
| N20 | `baseline_findings` has exactly two consumers and they agree: the `validate` finding set for a repository equals `baseline show`'s |
| N21 | The descriptor contains all nine §14 facts, and **no artifact content**: every reference is a `{path, sha256}` pair and no referenced file's body appears in `baseline.json` |
| N22 | The builder never raises when the constitution, design document and discovery record are all absent |

### Convergence and the exit criterion (end-to-end, real CLI)

| Id | Test |
|---|---|
| N23 | **Convergence invariant.** Drive GREENFIELD to `complete` in one repository and BROWNFIELD_DISCOVERY to `complete` in another. Both produce `.sdle/baseline.json`; both report `VALID`; the two descriptors have the **same required key set**; `discovery.status` is `NOT_REQUIRED` and `PERFORMED` respectively |
| N24 | **Exit criterion, §14.** In one repository: WI-A completes BROWNFIELD_DISCOVERY → baseline `VALID`. WI-B assessed `BROWNFIELD_DISCOVERY` → `init` refuses `baseline_present`, and **no runtime directory is created for WI-B**. WI-B re-assessed `ITERATIVE` → `init` succeeds, and driving it to completion never enters `discovery` — asserted on `state.phase_history` **and** on `audit.md` not containing the string `discovery` for that WorkItem |
| N25 | The rediscovery opt-in: `classification.rediscovery: true` with `BROWNFIELD_DISCOVERY` makes N24's first `init` succeed; with any other flow it is refused `classification_invalid` |
| N26 | R2: `ITERATIVE` with no baseline refuses `baseline_required`, creating no runtime; `DEFECT_FIX` and `HOTFIX` with no baseline are **not** refused |
| N27 | The baseline write cannot block completion: with `.sdle/` pre-populated in a way that leaves the constitution and design document absent, the final `gate approve` still completes, and the descriptor carries `null`/`[]` |
| N28 | A GREENFIELD run's completion emits exactly one `baseline_established` audit entry, `audit verify` reports `chain_ok`, and the completion summary is unchanged field-for-field |

### `tests/test_lint_skill.py`

| Id | Test |
|---|---|
| N29 | One firing test per new lint check, each planting a breakage that isolates that check |
| N30 | `discovery` has an execution block and it carries **no ordinal** — an ordinal on a phase with no GREENFIELD position must fail `execution_block_numbers_are_the_greenfield_positions` |

### Absence-of-change tests (the "nothing else moves" proof)

| Id | Test |
|---|---|
| N31 | GREENFIELD, ITERATIVE, DEFECT_FIX and HOTFIX phase lists are byte-identical to their pre-T08 values, pinned as literals in the test |
| N32 | `state.json`'s eight `approvals` keys are unchanged; the state template is byte-identical; `version_string_consistent` still reports v1.16 |
| N33 | `.claude/hooks/hooks.py`, `.gitignore`, `SDLE_OWNED_PREFIXES` and `GREENFIELD_V1_PHASES` are unchanged (assert on content/values, not on Git) |
| N34 | `cmd_governance_gates` still emits `advisory: true`; no gate is conditional on risk or classification (T09 leakage guard) |

---

## Implementation sequence

Five milestones. **The suite must be green at the end of each.** No deliberate
red window is planned; if one becomes unavoidable it must be confined inside a
single milestone and declared in that milestone's checkpoint.

**M1 — the structural change, first, with "nothing else moves" as its proof.**
Add `discovery` to the registry and to `BROWNFIELD_DISCOVERY`'s row; add the
`PHASE_LABEL_MAP` and `NEXT_PHASE` rows; add the ordinal-free
`phase-execution.md` block; update README and the Reference Guide enough for
`doc_lists_every_phase_*`. Update the two T07 pinning tests and the denominator
test. Add N31–N33. **Proof:** four of five flow traversals byte-identical,
`lint-skill` green, the nine transcripts and integration 01–09 untouched.

**M2 — discovery as a governed record.** `DISCOVERY_*` constants,
`discovery schema`, `read_discovery_input`, `evaluate_discovery`,
`cmd_discovery_assess`, `discovery_precondition` at `apply_advance`. Tests
N1–N14, N29–N30. `conftest` edit 2. Suite green.

**M3 — the baseline descriptor, read-only.** `baseline_descriptor`,
`read_baseline`, `baseline_findings`, `baseline show`, `baseline validate`,
`validate` wiring. **No writer yet**, so no flow behaviour changes. Tests
N15–N22. `conftest` edit 1. Suite green.

**M4 — establish the baseline at completion.** The `is_final` branch;
`baseline_established` audit event. Tests N23, N27, N28. Suite green.

**M5 — the refusals.** R1, R2, `classification.rediscovery`. Update the
`test_units_governance.py` rows. Tests N24, N25, N26, N34. Suite green.

**M6 — ADR-005 and the documentation sweep.** Write
`docs/architecture/ADR-005-brownfield-discovery-and-baseline.md` recording D1–D12
and D3's enforced/not-enforced split verbatim. Final full suite + `lint-skill` +
`validate.py`.

**Safe resume boundary: end of M4.** M1–M4 are additive — a new phase, new
commands, a new descriptor — and refuse nothing that was previously permitted.
**M5 is where enforcement begins**, which is the same shape T06 declared for its
own M3/M4 boundary. A fresh agent resuming mid-phase must restart at a milestone
boundary, verify claimed state against disk (`--collect-only` is the cheap
check), and never trust a checkpoint's claim that a test file exists.

One checkpoint per milestone: `T08-checkpoint-a01-01.md` … `-06.md`.

---

## Failure modes

| # | Failure | Detection | Response |
|---|---|---|---|
| F1 | A `SKILL.md` table edit stops parsing → `load_constants` raises and every command exits 3 | Any test; `lint-skill` reports the rule by name rather than defaulting | Revert the table edit; the tables are data, so the fix is textual |
| F2 | `discovery` orphaned, unlabelled, unchained, or given a `PROGRESS_MAP` row | `every_registry_phase_is_used_by_some_flow`, `phase_set_matches_next_phase`, `phase_set_matches_phase_label_map`, `phase_set_matches_progress_map`, `progress_map_and_gate_numbers_are_the_derived_greenfield_views` | Named lint failure; fix the table |
| F3 | The `discovery` block header carries an ordinal | `execution_block_numbers_are_the_greenfield_positions` (E11) | Remove the ordinal |
| F4 | The baseline write raises inside `cmd_gate_approve` after `gate_approved` was appended | N27; an I/O error surfaces as exit 3 | The builder is total by construction (D6). Placing the write first in the `is_final` branch means the failure shape is identical to `write_completion_summary`'s today — no new failure class |
| F5 | A new refusal appends to the ledger before raising | N9, N12; and a byte-comparison of `audit.md` around each refusal | Move the check to a pure reader ahead of the first `append_audit`. This is the B1/NB-6 regression the phase must not reintroduce |
| F6 | R2 breaks more existing tests than the table above lists | Full suite | Any additional breakage outside the listed set is a **plan defect**: stop and write `T08-blocker.md` rather than editing more tests |
| F7 | A category id or schema key is restated in a prompt/doc file | N14 content search | Replace with a reference to `discovery schema` (D10) |
| F8 | The baseline reader is written fail-open by habit, copying `read_repo_config` | N15 | Rewrite against `read_governance_record` (E17, E27) |
| F9 | `.sdle/baseline.json` appears in a later WorkItem's dirty-tree guard or Gate 7 manifest | I6 | **Not fixed in T08** (D12). Recorded as a residual for T11 next to T04 N-7 |
| F10 | A verifier reads "no version bump" as an omission | — | Pre-empted by D11 and acceptance A14 |
| F11 | The full suite is red | Full run | The F1 `ENVIRONMENT_FLAKE` procedure from T00/T01 is **VOID**. Any failure is a presumed real regression; investigate it, never pattern-match it to the old `WinError 5` signature |
| F12 | A false green from the shell proxy | — | Run `rtk proxy python -m pytest`, redirect to a file, read `$?` with no pipe. Reproduce any negative grep claim with `rtk proxy "grep -rnE ..."` or a Python walk. `sdle.py constants` nests its payload under `data`. The tree is CRLF and `git show` is LF — normalise before concluding a file differs |

---

## Rollback/recovery strategy

- **Rollback point: `c80f341`** (T07 implementation). `git diff c80f341 -- <path>`
  is the per-file recovery view; the T08 commit is a single revertable commit.
- **Per-milestone recovery.** Each milestone is independently revertable: M1 is
  confined to `SKILL.md` + `phase-execution.md` + docs + three tests; M2–M5 are
  additive engine surfaces plus their tests; M5 is the only milestone that
  changes what an existing, previously-permitted command does.
- **Runtime recovery for a user.** A corrupt `.sdle/baseline.json` halts with
  exit 3 and a message naming the file; deleting it returns the repository to
  `ABSENT`, which is a supported state. No workflow state is damaged: the
  baseline is repository-level and no `state.json` field points at it.
- **A half-written descriptor is impossible** — `write_atomic` is unchanged and
  is the only writer.
- **Interrupted agent.** Resume from disk: `progress.md`, the T08 checkpoints,
  and `git diff c80f341`. Never infer success from an interrupted run (§24.6).
  Ten agent runs in this migration have been killed mid-flight by API limits.

---

## Acceptance criteria

Objective, and each one checkable by a command the verifier can re-run.

- [ ] **A1** `python scripts/sdle.py constants` reports `phase_sequence` of
      length **21** containing `discovery`, and flow shapes GREENFIELD 19/8,
      BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3
      (entries **including** `complete`, the convention E6 established).
- [ ] **A2** `GREENFIELD`, `ITERATIVE`, `DEFECT_FIX` and `HOTFIX` phase lists are
      element-wise identical to their values at `c80f341`; only
      `BROWNFIELD_DISCOVERY` changed, and it changed by exactly one inserted
      element, `discovery`.
- [ ] **A3** `discovery` is not a gate: it has no `PHASE_TO_GATE_KEY` row, no
      `ARTIFACT_OWNERSHIP` row, no `GATE_TO_EXECUTION_PHASE` row, and
      `state.json`'s `approvals` still has exactly the eight pre-T07 keys.
- [ ] **A4** `discovery assess` refuses each of R-a…R-j with the stated reason
      code and exit 1, and a document whose every category is a single `UNKNOWN`
      finding is accepted.
- [ ] **A5** For each of `advance` and `skip` out of `discovery` without a
      record: exit 1, reason `discovery_missing`, and `audit.md` **byte-identical**
      before and after. Likewise for a refused `discovery assess`, a refused
      `init` (R1/R2 — which additionally creates no `workitems/<id>/.sdle/`), and
      `baseline validate` on a non-`VALID` repository.
- [ ] **A6** `lint-skill` exit 0 with **no check removed or weakened**: the 29
      checks observed at `451f440` all still present and passing, plus the new
      ones, each with a firing test in `test_lint_skill.py`.
- [ ] **A7** `read_baseline` raises `IntegrityError` (exit 3) on every malformed
      form and returns `None` only when the file is genuinely absent — proved by
      test, and by a source-level assertion that it contains no
      `return <default>` inside an exception handler.
- [ ] **A8** `.sdle/baseline.json` exists after GREENFIELD completion **and**
      after BROWNFIELD_DISCOVERY completion, both report `VALID`, and the two
      descriptors have the same required key set (N23).
- [ ] **A9** **§14's exit criterion, driven through the real CLI:** after WI-A
      completes BROWNFIELD_DISCOVERY, WI-B's `init` with `BROWNFIELD_DISCOVERY`
      refuses `baseline_present`; re-assessed as `ITERATIVE` it initialises and
      completes without ever entering `discovery`, asserted on
      `state.phase_history` and on WI-B's `audit.md` (N24).
- [ ] **A10** The descriptor carries all nine §14 facts and **no artifact
      content**: every reference is `{path, sha256}` and no referenced file's
      body appears in `baseline.json` (N21).
- [ ] **A11** "Material invalidation" is exactly the `INVALID` set:
      `baseline_invalid`, `baseline_producer_unregistered`,
      `baseline_reference_missing`. `baseline_reference_changed` yields `STALE`
      and refuses nothing (N19).
- [ ] **A12** No discovery category id, classification name or schema key
      appears in any file of T06's `_searchable_files()` set (N14).
- [ ] **A13** `tests/test_integration_01_happy_path.py` and all nine files under
      `docs/dry-runs/` are byte-identical to `c80f341` (compare with line
      endings normalised — F12).
- [ ] **A14** `.claude/skills/sdle/templates/state.json`, `.claude/hooks/`,
      `.claude/commands/`, `.claude/settings.json`, `.gitignore` and
      `modules/gate-protocol.md` are byte-identical to `c80f341`;
      `version_string_consistent` still reports **v1.16** at all four locations;
      the migration chain still has **16** rows.
- [ ] **A15** `tests/conftest.py` contains **exactly** the two additions the
      anti-contradiction clause permits, and no other line changed.
- [ ] **A16** Every test change is recorded in the handoff with its TP-003
      category and reason. No test is deleted, `skip`ped, `xfail`ed or weakened.
      The set of changed test functions is a subset of the table in "Existing
      tests affected".
- [ ] **A17** Full suite run and observed: collected count, passed count and the
      raw exit code, read with no pipe. 901 is the pre-T08 collected count (E4);
      the new count must equal 901 plus the number of tests actually added.
- [ ] **A18** `python tools/transition/validate.py` exit 0; `progress.md` has a
      T08 row with no literal `|` inside any cell.
- [ ] **A19** No T09/T10/T11 leakage: `cmd_governance_gates` still emits
      `advisory: true`; no gate is conditional on risk or classification; no
      `.claude/agents/` and no new product skill; the legacy `.workflow/`
      dual-read rung and `migrate-workflow` still work and still never mutate
      `.workflow/`; `GREENFIELD_V1_PHASES` is unchanged and is still not a
      `FLOW_PHASES` row.
- [ ] **A20** `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`
      exists and states D3's enforced/not-enforced split explicitly — which
      classification properties are guarantees and which are claims.

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is `PLANNED`.**

Every decision §14 forces has been made and pinned above: the baseline schema
(D5), what makes it valid (D7), what "material invalidation" concretely means
(D7/A11), where discovery's real content comes from (D2), what the engine can
and cannot enforce about classification (D3), and how the exit criterion is
proved (A9).

| # | Unknown | Class | Handling |
|---|---|---|---|
| U1 | Python 3.11 behaviour and CI outcome | **UNKNOWN** | Never observed on this branch (E36). Not material: T08 adds no new syntax or stdlib surface beyond what T05–T07 already use. Report as `NOT_RUN` / `UNKNOWN`; do not claim green on 3.11 |
| U2 | Whether real Spec Kit degrades under `BROWNFIELD_DISCOVERY` or `ITERATIVE` | **UNKNOWN** | Tests never invoke Spec Kit; unchanged from T07's U2. The `discovery` phase deliberately invokes no Spec Kit skill and creates no feature directory, so it cannot make this worse |
| U3 | What counts as "significant existing source" | **Deliberately not defined** | D9. §14 gives no threshold; the engine enforces only the baseline half of the conjunction. Recorded, not guessed |
| U4 | Whether a `STALE` baseline should ever force rediscovery | INFERRED, decided | D7. Warning-only, because the alternative contradicts §26 item 22. Pinned by N19 so a later phase must change it visibly |
| U5 | Whether `DEFECT_FIX` / `HOTFIX` should require a baseline | INFERRED, decided | No. §13 gives them no baseline clause; blocking a hotfix on a repository artifact is a governance change T08 was not asked to make. Pinned by N26 |
| U6 | Exact new `lint-skill` check count | Not yet determinable | A6 pins the invariant that matters (29 preserved, none weakened, each new one has a firing test) rather than a number the planner would have to guess |
| U7 | Whether the version should bump to v1.17 | INFERRED, decided | D11: no. Recorded as a T11 residual |

---

## Scope exclusions

Explicitly **not** in T08. If any appears in the diff it is future-phase
leakage and the verifier must fail the phase.

- **T09 — risk-adaptive gates (§15).** No gate becomes conditional on risk,
  classification or policy. `required_gate_set` stays inert and uncalled by any
  phase-movement function; `governance gates` still reports `advisory: true`. No
  hard risk floor is added, changed or consulted by anything T08 writes. T07
  selects which phases execute; T08 selects when discovery happens; **T09** makes
  gate *requirements* policy-driven.
- **T10 — skills and subagents (§16).** No product subagent, no
  `.claude/agents/`, no skill split, no `sdle-brownfield-discovery` skill.
  Discovery is performed in the parent session and recorded through the CLI.
  The `sdle-transition-*` migration agents remain control-plane scaffolding and
  are not evidence of T10.
- **T11 — hardening and legacy removal (§17).** The legacy `.workflow/`
  dual-read rung, `migrate-workflow`, `current_feature_id`'s residue, the fixed
  18-phase/8-gate assumptions in prose, and the version bump all stay.
- **The open T02–T05 findings** listed in `RESUME.md` — T04 N-2/N-3/N-4/N-6/N-7,
  T03-1/4/5/6/7/8/10, T02 NB-2/4/5, T05 NB-3/NB-4. **None is adopted by T08.**
  Two deserve a named statement because T08 touches adjacent ground:
  - **T05 NB-4 (fail-open `read_repo_config`)** — *not fixed*, and deliberately
    *not inherited*: `read_baseline` is written fail-closed against
    `read_governance_record` (D7). `read_repo_config` itself is untouched.
  - **T04 N-7 / I6 (`.sdle/` outside the dirty-tree and manifest exclusions)** —
    *not adopted* (D12). Recorded as a residual for T11 with the reasoning, so
    it is inherited as a decision rather than an oversight.
- **§27's deferred list** — release/build management, MCP, databases, knowledge
  graphs, cross-repository orchestration, distributed locks, OPA/Rego, a policy
  DSL, YAML. Policy and record formats stay **JSON, stdlib-only** (§11).
- **Any generic workflow construct.** §13's constraint is still binding: no
  conditional branching, no parallel phases, no loops, no dynamic phase
  insertion. `discovery` is one row in a fixed registry and one element in one
  ordered subset. If the implementation grows a construct capable of expressing
  a lifecycle SDLE does not currently need, that is a defect, not a feature.
