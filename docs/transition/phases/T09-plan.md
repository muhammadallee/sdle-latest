# T09 Plan — Risk-Adaptive Gate Policy

**Phase:** T09
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED

Contract: `docs/transition/transition.md` §15, executed under §24.2.
Planned at HEAD `44ae6d8671f6f2301c9baf8c14eb7a1aa48a873b`.

---

## Objective

Make **human approval at a gate policy-driven**, without weakening governance.

§15's exit criterion is that *"design/security are neither universally mandatory
nor casually skippable"* and that *"policy determines applicability"*. §12's
closing line is the sentence that makes this tractable and it is quoted here
because the whole design turns on it:

> Human approval remains policy-driven; review/validation is universal for
> governed artifacts.

So T09 changes exactly one thing: whether a gate the bound flow contains
**requires a human approval**. It changes nothing about whether the artifact is
generated, registered, hashed, reviewed, drift-checked or audited. Those stay
universal, because §12 says they are universal and §15's "preserve Wave A
guardrails" list says they survive.

Two gaps in the shipped implementation are closed as part of this, both named
by the orchestrator and both verified here against the source:

1. **Six hard floors shipped where §15 mandates nine**, and one shipped
   *below* the contract (`authentication_or_authorization` → `MEDIUM`, where
   §15 says HIGH). That is a live under-enforcement.
2. **`required_gate_set` computes a gate set nobody consults.** T06 wrote it
   for exactly this phase to consume. T09 consumes it; it does not build a
   parallel mechanism.

---

## Repository evidence

Every figure below came from a command run in this planning context, or from
reading the named symbol. Nothing is inherited from a prior agent's narrative.
Citations are by symbol or greppable anchor, never by bare line number.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | HEAD is `44ae6d8671f6f2301c9baf8c14eb7a1aa48a873b`; working tree clean apart from `.claude/settings.local.json` | OBSERVED | `git rev-parse HEAD`; `git status --short` = one ` M .claude/settings.local.json` |
| E2 | Transition state is `complete=9/12 next=T09`, exit 0 | OBSERVED | `python tools/transition/validate.py` printed `TRANSITION_VALID: complete=9/12 next=T09`, `exit=0` |
| E3 | `lint-skill` reports **32** checks, `failed: []` | OBSERVED | `python scripts/sdle.py lint-skill`, payload under `data`; check names enumerated (`tables_wellformed` … `doc_lists_every_phase_SDLE-Reference-Guide`) |
| E4 | Registry is 21 phases. Flow shapes (entries incl. `complete` / gate count): GREENFIELD 19/8, BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3. `version_chain` = 16 rows | OBSERVED | `python scripts/sdle.py constants` |
| E5 | HOTFIX's gate keys are exactly `gate_spec`, `gate_implement`, `gate_security` | OBSERVED | `constants` → `flows.HOTFIX.gate_keys` |
| E6 | Suite collects **1025** tests | OBSERVED | `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` → `1025 tests collected in 0.50s` |
| E7 | Suite **pass count and raw exit code at HEAD** | **UNKNOWN** | Not run in this planning context. `progress.md`'s T08 row records `1025 passed` observed by T08's verifier at `e1cf341`; that is *their* observation, not mine, and the implementer must re-derive it |
| E8 | `GOVERNANCE_POLICY_BUILTIN["hard_floors"]` has **6** rules: `payment_or_financial`→HIGH, `cryptography_or_secrets`→HIGH, `personal_or_sensitive_data`→HIGH, `authentication_or_authorization`→**MEDIUM**, uncertainty HIGH→HIGH, uncertainty CRITICAL→CRITICAL | OBSERVED | `scripts/sdle.py`, symbol `GOVERNANCE_POLICY_BUILTIN` |
| E9 | `risk_signals` has **12** entries; `risk_thresholds` = `{LOW:0, MEDIUM:2, HIGH:5, CRITICAL:9}` | OBSERVED | same symbol |
| E10 | `required_gates_always` = `[gate_constitution, gate_spec, gate_plan, gate_implement]`; `by_risk` LOW `[]`, MEDIUM `[gate_tasks]`, HIGH and CRITICAL both `[gate_tasks, gate_analyze, gate_design, gate_security]`; `by_type` defect `[gate_tasks]`, others `[]` | OBSERVED | same symbol |
| E11 | `required_gates_always` names `gate_constitution` and `gate_plan`, which **HOTFIX does not contain** (and `gate_constitution` is absent from ITERATIVE and DEFECT_FIX too) | OBSERVED | E5/E4 against E10 — the shipped "always" set predates T07's flows |
| E12 | `required_gate_set` is documented "Pure, and deliberately inert. Nothing on the phase-movement path calls it" | OBSERVED | `scripts/sdle.py`, symbol `required_gate_set` |
| E13 | `cmd_governance_gates` emits `"advisory": True` and a `note` saying every gate "still run[s] unconditionally … Making a gate conditional on risk is T09" | OBSERVED | `scripts/sdle.py`, symbol `cmd_governance_gates` |
| E14 | `apply_advance` refuses `gate_not_approved` whenever `approval_decision(state, gate_key) != "approved"` | OBSERVED | `scripts/sdle.py`, symbol `apply_advance` |
| E15 | `compute_drift` **skips** any gate whose `entry.get("decision") != "approved"` | OBSERVED | `scripts/sdle.py`, symbol `compute_drift` |
| E16 | `cmd_repo_staleness` collects timestamps only where `decision == "approved"` | OBSERVED | `scripts/sdle.py`, symbol `cmd_repo_staleness` |
| E17 | The completion summary's Approvals table prints `entry.get("decision")` verbatim per gate | OBSERVED | `scripts/sdle.py`, the `"### Approvals"` block |
| E18 | `MANDATORY_FLOW_PHASES` pins `security_review` and `gate_security` in **every** flow, and `gate_security` is the last gate before `complete` in all five | OBSERVED | `scripts/sdle.py`, symbol `MANDATORY_FLOW_PHASES`; cross-checked against E4's phase lists |
| E19 | `cmd_gate_approve` order: drift branch → `not_at_gate` → `artifact_missing` + SHA record → `gate_precondition_hook` → `review_precondition` → three pure-reader preconditions → write approval → `append_audit` → `apply_advance` | OBSERVED | `scripts/sdle.py`, symbol `cmd_gate_approve` |
| E20 | `governance_precondition` refuses `governance_missing` for any bound WorkItem with no record; it returns early (no enforcement) when `paths.workitem is None` (the legacy `.workflow/` rung) | OBSERVED | `scripts/sdle.py`, symbol `governance_precondition` |
| E21 | The fixture default governance is `signals: []`, `proposedLevel: "LOW"`, `uncertainty: "LOW"`, `type: enhancement`, `flow: GREENFIELD` → final risk **LOW** | OBSERVED | `tests/conftest.py`, `Project.record_governance` |
| E22 | `run_happy_path` approves **all eight** gates explicitly, one `gate approve` call per gate | OBSERVED | `tests/test_integration_01_happy_path.py`, `GATES` and the body of `run_happy_path` |
| E23 | `test_risk_and_type_change_no_lifecycle_behaviour` drives four variants (LOW/LOW/CRITICAL/CRITICAL) through `run_happy_path` and asserts identical traversal, approvals, SHA key set and lifecycle audit events; its clause 3 asserts `advisory is True` | OBSERVED | `tests/test_units_governance.py` |
| E24 | `test_no_phase_movement_function_consults_the_would_be_gate_set` asserts no `cmd_gate*`/`apply_advance`/`cmd_advance`/`cmd_skip` function references `required_gate_set` or the string `wouldBeRequiredGates` | OBSERVED | `tests/test_units_governance.py` |
| E25 | `test_n34_no_gate_is_conditional_on_risk_or_classification` asserts `required_gate_set`'s callers are exactly `{cmd_governance_assess, cmd_governance_gates}` and that `governance gates` is advisory | OBSERVED | `tests/test_units_baseline.py` |
| E26 | `policy_identifiers()` derives its needle set from `BUILTIN["risk_signals"]` and the signal-bearing `hard_floors`; `_searchable_files()` includes `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md`, `.claude/skills`, `.claude/commands`, `.claude/hooks`, `.sdle`, **and `docs/architecture`** | OBSERVED | `tests/test_units_governance.py` |
| E27 | No risk-signal id appears in any prompt or documentation file today; the vocabulary reaches the prompt layer through `governance policy` | OBSERVED | `grep -rn 'external_api_surface\|persistent_data_store\|risk_signals' --include=*.md .claude docs/architecture README.md` → no signal-id hit; `SKILL.md` says "every check id `sdle.sh governance policy` reports" |
| E28 | `README.md` states `governance gates` is "Advisory: nothing consumes it, and every gate the bound flow contains runs unconditionally"; `docs/SDLE-Reference-Guide.md` states "all eight gates run unconditionally regardless of classification or risk" | OBSERVED | `grep -rn 'unconditional\|advisory' README.md docs/SDLE-Reference-Guide.md .claude` |
| E29 | `SKILL.md` states "The WorkItem *type* and the risk level are still recorded and still route nothing" | OBSERVED | same grep, SKILL.md governance section |
| E30 | `read_repo_config` returns `REPO_CONFIG_DEFAULTS` from inside `except (OSError, json.JSONDecodeError, ValueError)` — fail-open | OBSERVED | `scripts/sdle.py`, symbol `read_repo_config` |
| E31 | `tests/test_units_baseline.py::test_n15_the_baseline_reader_never_swallows_and_defaults` **asserts that `read_repo_config` is fail-open** ("the positive half … `swallowed`") | OBSERVED | that file |
| E32 | `README.md` restates `REPO_CONFIG_DEFAULTS` as a literal fenced JSON block (`{"configVersion": "1", "policyFormat": "json"}`); no lint check binds them | OBSERVED | README config section; `lint-skill`'s 32 check names (E3) contain no such rule |
| E33 | `migration_covers_every_state_field` inspects **top-level template keys only**, against a hardcoded `base` set that already contains `approvals` | OBSERVED | `scripts/sdle.py`, symbol `_check_migration_covers_state_fields` |
| E34 | `RUNTIME_FREE_COMMANDS` is a closed enumerated set that does **not** contain `gate` | OBSERVED | `tests/test_units_workitem_resolution.py::test_runtime_free_commands_is_a_closed_enumerated_set` |
| E35 | `GOVERNANCE_RECORD_VERSION = "1"` and no reader validates it — `read_governance_record` checks only that the JSON parses to a dict | OBSERVED | `scripts/sdle.py`, symbols `GOVERNANCE_RECORD_VERSION`, `read_governance_record` |
| E36 | The `gate` parser group registers exactly `show`, `approve`, `reject` | OBSERVED | `scripts/sdle.py`, the `gate_p = subparsers.add_parser("gate", …)` block |
| E37 | No WorkItem is committed to the repository (`git ls-files workitems/` is empty; no `workitems/` directory on disk) | OBSERVED | `git ls-files workitems/`; `ls workitems` |
| E38 | §17's mandatory hardening-test list already names **"gate omission evidence"** | OBSERVED | `docs/transition/transition.md` §17 |
| E39 | ADRs 001–005 exist; the next number is **006** | OBSERVED | `ls docs/architecture/` |
| E40 | Python 3.11 behaviour and CI outcome | **UNKNOWN** | Never observed on this branch. Not run here |

### Derived facts (INFERRED, with the evidence named)

| # | Inference | From |
|---|---|---|
| I1 | Under the current defaults a **LOW-risk WorkItem is the common case**: the fixture default and any WorkItem naming no signal scores 0 → LOW | E9, E21 |
| I2 | Because `run_happy_path` approves every gate explicitly (E22), a design in which *not-required* means *may be omitted* rather than *is omitted* leaves `test_integration_01_happy_path.py` and E23's differential **passing unchanged** | E22, E23 |
| I3 | `gate_security` is the terminal human gate of every declared flow, and it is also where the completion summary and the repository baseline are written | E18, E19 |
| I4 | A policy that requires a gate the bound flow does not contain is currently **silently inert** — the shipped `required_gates_always` is already in that state for three of five flows | E10, E11 |
| I5 | Adding risk signals cannot break an existing override: `_merge_policy` merges dict-valued keys key-by-key, so built-in keys the override omits survive | `scripts/sdle.py`, symbol `_merge_policy` |
| I6 | Adding a risk-signal id to any ADR, README or Reference Guide sentence would **fail** `test_no_policy_default_value_is_restated_outside_sdle_py`, because `docs/architecture` is inside `_searchable_files()` | E26 |
| I7 | No state-schema change is needed: the requirement set is re-derived at each decision point, and the only state written is a new *value* inside the existing `approvals[gate]` object | E33 |

---

## Design decisions

### D1 — Policy decides whether a gate **requires** approval; it never decides whether work happens

The unit T09 makes conditional is the **human approval**, and nothing else.
Artifact generation, `artifact record`, the artifact SHA baseline, TP-011
review/validation, the drift queue, the secrets scan, the test evidence, the
implementation diff baseline, the audit chain, the retry/remediation caps and
the fail-safe transitions are all untouched and all still universal. §12 says
so in as many words (Objective), and §15's "preserve Wave A guardrails" list
says so again.

Concretely: a gate that is not required still has its artifact generated by the
preceding phase, still has that artifact registered and reviewed, still records
a baseline SHA, and still participates in drift detection. What it does not
require is a human pressing *approve*.

### D2 — "Not required" means **omittable**, not **omitted**

A gate the policy does not require is still a gate. It can be:

* **approved** by a human exactly as today — always permitted, always stricter
  than the policy demands, and therefore never refused; or
* **omitted** by the engine through a new `gate omit --gate <key>`, which
  **refuses `gate_required`** unless the effective policy says the gate is not
  required for this WorkItem.

This is the single most consequential decision in the phase and it is chosen for
three reasons:

1. **It cannot weaken anything by default.** Every existing driver, transcript
   and integration test approves every gate (E22), so a run that approves
   everything behaves identically at every risk level (I2). The phase's
   *default* behaviour is byte-identical to T08's.
2. **It puts the floor in the engine and the presentation in the prompt.**
   `gate omit` is refused when the gate is required, so Claude can *ask* to omit
   and be told no. Claude can never omit a required gate, at any risk level,
   under any policy. This is the CLAUDE.md split verbatim: hooks and prompts are
   tripwires, the script's refusal at the choke point is the guarantee.
3. **Omission becomes an explicit, auditable event** rather than an absence.
   §15 requires that every omitted gate be explainable and auditable, and an
   automatic omission produces no event to explain.

The rejected alternative — auto-satisfying a not-required gate inside `advance`
— is recorded in "Alternatives considered" with why it was rejected.

### D3 — Three distinguishable states, never conflated

T07 introduced "the flow does not contain this phase". T09 introduces "the
policy does not require this gate". The orchestrator brief is explicit that
these must stay distinguishable, so the disposition vocabulary is closed and
each value has exactly one meaning:

| disposition | meaning | where it shows |
|---|---|---|
| `required` | the gate is in the bound flow and the policy requires a human approval | `governance gates`, `gate show`, the ledger |
| `omittable` | the gate is in the bound flow and the policy does not require approval; it may be approved or omitted | same |
| `not_in_flow` | the policy names the gate but the bound flow does not contain the phase; the requirement is inert **and is reported as inert** | `governance gates` only |

`not_in_flow` is reported, never silently dropped (I4). With the built-in policy
and HOTFIX it is non-empty today, which makes the report testable rather than
theoretical.

Each `required` entry carries an ordered list of **reasons**, so "why did this
gate stop me" always has a machine-readable answer:

```
always | risk:<LEVEL> | type:<TYPE> | terminal_gate
```

### D4 — The terminal gate of the bound flow is **always required**, and the reason is named

`gate_security` is not in `required_gates_always` and `required_gates_by_risk`
is empty at LOW (E10), so without an extra rule a LOW WorkItem could omit the
final gate — which would auto-complete the workflow, write the completion
summary and establish the repository baseline with no terminal human decision.
§15's **LOW** list explicitly requires *"final human review"*, so that is
forbidden by the contract at every risk level.

Therefore: **the last gate phase before `complete` in the bound flow is required
unconditionally**, with reason `terminal_gate`.

This is deliberately expressed as a *derived positional rule over the bound
flow*, not as a row added to `required_gates_always`, because:

* it names the real reason. `gate_security` is required because it is the
  terminal human gate (I3), not because security review is universally
  mandatory. §15's exit criterion is about the latter, and stating it as
  "security is always required" would be stating a guarantee under the wrong
  name — the T08 NB-3 failure mode;
* it survives a future flow whose terminal gate is some other key;
* **a repository policy override cannot remove it.** Overrides can only add to
  the policy dictionaries; a derived rule is not in a dictionary at all, so
  monotonicity is not merely enforced for it, it is structurally unavailable.

### D5 — §15's CRITICAL clauses are satisfied by construction, and proved by test rather than by code

§15's CRITICAL is *"HIGH plus: human approval before implementation; human
approval before completion"*. That is a positional claim about the bound flow,
not a gate list, so it is checked positionally:

* *approval before completion* — D4's `terminal_gate` rule, at every level.
* *approval before implementation* — the last gate phase preceding `implement`
  in each flow is GREENFIELD/BROWNFIELD_DISCOVERY/ITERATIVE `gate_design`,
  DEFECT_FIX `gate_analyze`, HOTFIX `gate_spec`. At CRITICAL, `gate_design` and
  `gate_analyze` are in `required_gates_by_risk["CRITICAL"]` and `gate_spec` is
  in `required_gates_always` (E10). All three are already required.

So the property **holds by construction** for every declared flow, and because a
repository override can only *add* required gates, no repository can break it.
Writing a runtime rule for it would ship dead code — the invariant-7 smell T03-4
already recorded once. It is therefore asserted as a test over the cross product
of all five flows and all four levels (N14), not implemented as a branch.

**Stated plainly, because it would be dishonest to imply otherwise:** under the
built-in policy CRITICAL's required gate set is *equal* to HIGH's. §15 says
"HIGH plus", and what CRITICAL adds is satisfied structurally rather than by an
extra list entry. A repository that wants more may add to
`required_gates_by_risk["CRITICAL"]`, monotonically.

An acknowledgement flag on the two positional gates was considered and rejected
— see "Alternatives considered".

### D6 — The nine §15 hard floors, mapped signal by signal

§15's minimum list is nine floors. Five map onto an existing signal; four do
not, because no existing signal's *definition entails* the §15 condition. The
rule applied throughout: **reuse an existing signal only when naming that signal
necessarily means the §15 condition is present.**

| §15 floor | signal | new? | level | why |
|---|---|---|---|---|
| authentication/authorization/security control → HIGH | `authentication_or_authorization` | existing | **HIGH** (raised from MEDIUM) | Direct match. The shipped MEDIUM is below contract |
| sensitive/regulated data → HIGH | `personal_or_sensitive_data` | existing | HIGH (unchanged) | Direct match for the *sensitive* half; the *regulated* half is covered by the next row |
| regulatory/compliance → HIGH | `regulatory_or_compliance` | **new** | HIGH | No existing signal entails it. "Touches personal data" and "is subject to a regulatory regime" are independent facts |
| destructive/irreversible migration → HIGH | `destructive_or_irreversible_migration` | **new** | HIGH | `schema_or_data_migration` does not entail *destructive*. Flooring every migration at HIGH would be blunt over-enforcement; the honest reading is a distinct fact. `schema_or_data_migration` keeps its weight 3 and gains no floor |
| breaking external/public contract → HIGH | `backward_incompatible_change` | existing | **HIGH** (new floor) | Naming a backward-incompatible change *is* breaking a contract. `external_api_surface` is not a fit — it means "there is an API", not "it broke" |
| financial transaction correctness → HIGH | `payment_or_financial` | existing | HIGH (unchanged) | Direct match |
| production security boundary → HIGH | `production_security_boundary` | **new** | HIGH | `public_network_exposure` is one boundary among several (IAM, trust zones, deployment topology) and does not entail the general case; the general case does not entail network exposure. `public_network_exposure` keeps weight 3 and gains no floor |
| catastrophic blast radius → CRITICAL | `catastrophic_blast_radius` | **new** | CRITICAL | Nothing entails it. Blast radius is orthogonal to every existing signal |
| credential/private-key exposure → CRITICAL | `credential_or_key_exposure` | **new** | CRITICAL | `cryptography_or_secrets` means "uses crypto or handles secrets", which is far broader than "exposes a credential". Raising the whole signal to CRITICAL would make routine secret handling CRITICAL — over-broad. `cryptography_or_secrets` keeps its HIGH floor |

**Resulting built-in.** `risk_signals` gains five entries (12 → 17):

```
destructive_or_irreversible_migration : 4
regulatory_or_compliance              : 4
production_security_boundary          : 4
credential_or_key_exposure            : 5
catastrophic_blast_radius             : 5
```

`hard_floors` goes from 6 rules to 12. **The existing six rules keep their
current order and positions**; only the `authentication_or_authorization`
rule's `level` is edited in place, and the six new rules are appended. This is
load-bearing: `tests/test_units_governance.py` indexes `BUILTIN["hard_floors"][0]`
(E29), and appending rather than reordering keeps that stable.

Final `hard_floors`, in order: `payment_or_financial`→HIGH,
`cryptography_or_secrets`→HIGH, `personal_or_sensitive_data`→HIGH,
`authentication_or_authorization`→**HIGH**, uncertainty HIGH→HIGH, uncertainty
CRITICAL→CRITICAL, then `destructive_or_irreversible_migration`→HIGH,
`backward_incompatible_change`→HIGH, `regulatory_or_compliance`→HIGH,
`production_security_boundary`→HIGH, `credential_or_key_exposure`→CRITICAL,
`catastrophic_blast_radius`→CRITICAL.

`risk_thresholds` is **unchanged**. Weights are chosen so each new signal alone
reaches at least its own floor by score too, which keeps the floor a floor
rather than the only thing holding the level up.

**Every one of these edits is a tightening.** No weight drops, no threshold
rises, no floor falls, no floor is removed. `_refuse_weakening` compares an
override against the built-in, so a repository whose override *restated* the old
`authentication_or_authorization`→MEDIUM floor will now be refused
`policy_weakens_baseline`. That is correct — it is the same refusal an attempt
to lower it would get — and no such repository exists (E37).

`policyVersion` stays `"1"`: the schema did not change, only the values. Bumping
it would refuse every existing override, which is the opposite of the intent.

### D7 — The gate requirement map, and the two default-set corrections

`required_gates_always` is **unchanged**: `gate_constitution`, `gate_spec`,
`gate_plan`, `gate_implement`. Removing anything from it would be a weakening
and is out of the question; §15's per-level lists are minima ("Require at
least"), so requiring more than §15's LOW list is permitted.

`required_gates_by_risk` changes in exactly one cell:

| level | shipped | T09 | why |
|---|---|---|---|
| LOW | `[]` | `[]` | unchanged |
| MEDIUM | `[gate_tasks]` | `[gate_tasks, gate_design]` | §15 MEDIUM: *"Add: design review"*. The shipped default omits it — an under-enforcement against §15, tightened here |
| HIGH | `[gate_tasks, gate_analyze, gate_design, gate_security]` | unchanged | §15 HIGH's list, already satisfied. `gate_analyze` is HIGH-only because §15 hedges checklist/analysis at MEDIUM with *"as applicable"* |
| CRITICAL | same as HIGH | unchanged | D5 |

`required_gates_by_type` is **unchanged**.

**Net effect on what is omittable**, per flow, with the built-in policy:

| flow | LOW | MEDIUM | HIGH / CRITICAL |
|---|---|---|---|
| GREENFIELD / BROWNFIELD_DISCOVERY | `gate_tasks`, `gate_analyze`, `gate_design` | `gate_analyze` | — (none) |
| ITERATIVE | `gate_tasks`, `gate_analyze`, `gate_design` | `gate_analyze` | — |
| DEFECT_FIX (type `defect`) | `gate_analyze` | `gate_analyze` | — |
| HOTFIX | — (none) | — | — |

**HOTFIX has no omittable gate at any risk level**, because its three gates are
`gate_spec` (always), `gate_implement` (always) and `gate_security` (terminal).
§13's *"shorter but never ungoverned"* survives as an identity, not a judgement,
and §15's LOW list cannot make HOTFIX unsatisfiable because it never subtracts
from a flow that is already minimal.

### D8 — `gate omit`: the command, and its refusal stack

```
scripts/sdle.sh --workitem <id> gate omit --gate <gate_key>
```

Its precondition stack mirrors `cmd_gate_approve` (E19) exactly, in the same
order, with one insertion:

1. drift queue pending → refuse (reuse the existing behaviour: an omission
   cannot jump a pending re-approval);
2. `not_at_gate` if `current_phase` is not the gate's phase;
3. **`gate_required`** (exit 1) if the effective policy requires this gate.
   Payload names the gate, the final risk level, the reasons, the policy source
   and its sha256. *This is the refusal that makes the phase safe.*
4. `artifact_missing` if the gate's artifact does not exist; otherwise record
   its SHA into `artifact_shas` exactly as approval does — a gate is a decision
   about specific content whether the decision is "approve" or "omit", and the
   baseline is what keeps drift detection working;
5. `gate_precondition_hook` and `review_precondition` — **TP-011 is not
   relaxed**. A governed artifact must still hold a current `PASS` review. §12:
   review/validation is universal;
6. the three pure-reader preconditions (`governance_precondition(paths)`,
   `flow_precondition`, `discovery_precondition`), evaluated with no `state`,
   ahead of the first `append_audit` — the B1/NB-6 property;
7. write `approvals[gate] = {"decision": "omitted_by_policy", "comments": None,
   "timestamp": <stamp>, "risk_level": <final>, "reasons": [...],
   "policy_sha256": <sha or null>}`;
8. `append_audit(event="gate_omitted", decision="OMITTED", …)` with a message
   naming the gate, the final risk level, the policy source and the fact that
   no human approval was required;
9. `apply_advance` to the next phase, as approval does.

Because the terminal gate is always required (D4), `gate omit` can never reach
the completion branch. That is asserted, not assumed (N11).

Under the legacy `.workflow/` binding there is no WorkItem and therefore no
governance record; `bind_for_governance` refuses, so **omission is unreachable
on the legacy path** and legacy dual-read behaviour is unchanged.

### D9 — `apply_advance` accepts two passing decisions, and re-derives rather than trusts

E14's check becomes: the recorded decision must be `approved`, **or**
`omitted_by_policy` *and the gate must still be omittable under the policy read
right now*. If a recorded omission is no longer permitted, refuse
`gate_omission_invalidated` (exit 1) naming the gate and the remedy
(`gate approve` it, or `restart --to <phase>`).

Re-deriving instead of trusting the stored decision closes the hand-edited-state
path and any window between omission and advance. `apply_advance` is the choke
point; CLAUDE.md's design is that the choke-point refusal is the guarantee.

### D10 — A second, end-of-flow revalidation at the terminal gate

An omission recorded at LOW must not survive a later re-assessment that raises
the level. Because gates already passed are not revisited, the check is placed
where the workflow is declared finished: **the terminal gate's approval refuses
`gate_omission_invalidated` if any gate omitted earlier in this run would be
required under the current record and policy.** Remedy named in the message:
re-approve it via `restart --to <phase>`, or re-assess.

Placed among `cmd_gate_approve`'s pure-reader preconditions (step 6 of E19), so
a refusal leaves `audit.md` byte-identical.

### D11 — Guardrails that must be re-pointed, not merely "preserved"

Two functions filter on `decision == "approved"` and would silently exclude
omitted gates. Leaving them would be a real regression against §15's preserve
list, dressed as "no change":

* **`compute_drift` (E15)** — must treat `omitted_by_policy` as a baselined
  decision. Otherwise an omitted gate's artifact could change after the fact
  with no drift raised. **This is drift protection, item 1 of §15's list.**
* **`cmd_repo_staleness` (E16)** — same, for the same reason: the omission
  carries a timestamp and a baselined artifact.

The completion summary (E17) needs no code change: it prints the recorded
decision, so an omitted gate reads `omitted_by_policy` in the Approvals table.
Its format is deliberately left alone; the *explanation* lives in the ledger,
which is what §15 asks for.

### D12 — Reporting: extend what exists, add no second reporter

* **`governance gates`** loses `advisory`/`note`/`would_be_required_gates` and
  gains `flow`, `flow_source`, `final_risk`, `classification`, `dispositions`
  (per gate: `gate`, `gate_phase`, `disposition`, `reasons`), `required_gates`,
  `omittable_gates`, `required_not_in_flow`, and `policy`. It resolves the flow
  from `state.json` when present and from the record's `classification.flow`
  otherwise, reporting which (`flow_source: "state" | "record"`), so it stays
  answerable before `init` as it is today.
* **`gate show`** gains `required` (bool) and `requirement_reasons`.
* **`required_gate_set`** keeps its name and signature and becomes the
  policy-lookup half of the new `gate_requirements(...)`; T06 built it for this
  (E12) and it is reused, not duplicated.
* The persisted record's `wouldBeRequiredGates` is renamed to `requiredGates`
  and joined by `omittableGates`, both computed against the record's *proposed*
  flow. `GOVERNANCE_RECORD_VERSION` becomes `"2"` and — closing E35's smell
  rather than adding to it — `read_governance_record` gains a real reader:
  `GOVERNANCE_RECORD_VERSIONS = ("1", "2")`, anything else is an
  `IntegrityError`. A `"1"` record stays valid; its stale key is never read for
  a decision, because every decision re-derives (I7).

### D13 — Where nothing is stored

The requirement set is **never written to `state.json`**. It is derived at each
decision point from (bound flow, governance record, effective policy). A stored
table would be a second source of truth able to authorise an omission the
current policy forbids — and it would need a schema field, a migration row and a
template change. Deriving costs nothing and buys D9/D10 for free. **The state
template stays byte-identical and the migration chain stays at 16 rows** (E33,
I7).

### D14 — T05 NB-4 is adopted: `read_repo_config` becomes fail-closed

T09 was named its owner and the reason given was exactly this phase: a fail-open
read feeding gate policy would be a silent governance weakening. The governance
policy reader is already fail-closed and does not touch `read_repo_config`, so
the risk here is latent rather than live — but leaving a fail-open reader in the
file while shipping a phase whose entire subject is "do not weaken governance
silently" is not defensible.

The fix removes the `except …: return config` shape and raises the same
`config_malformed` refusal `repo_config_findings` produces. **Observable
behaviour does not change**: the only caller, `cmd_config_show`, runs
`repo_config_findings` first and already refuses on every condition the handler
swallowed (E30 vs `repo_config_findings`). It is pure hardening, proved the way
T08 proved `read_baseline`: by AST, no `Return` inside an `ExceptHandler`.

**This contradicts a shipped assertion** — see the anti-contradiction clause.

### D15 — T05 NB-3 is adopted: the README literal is bound by a lint check

A new `lint-skill` check, `repo_config_defaults_match_documentation`: for each of
`README.md` and `docs/SDLE-Reference-Guide.md`, parse every fenced ```json block
and, for any block that parses to a dict containing `configVersion`, assert it
equals `REPO_CONFIG_DEFAULTS`. This binds the drift surface without deleting a
useful example, is robust to the block moving, and fails loudly. It is the
mechanism the linter already exists to provide (CLAUDE.md: "run the linter, do
not check by hand").

### D16 — T08 NB-3 is adopted, narrowly

T09 edits `README.md` anyway. NB-3's sentence — *"…so an inference can never be
read as an observation"* — states a guarantee without its qualifier. It is
corrected to say what the engine actually checks (that the label is present and
is one of the closed three) and what it does not (that the author applied the
right one). Greppable criterion: the exact string no longer appears.

### D17 — What T09 deliberately does not do

* **No exception/waiver mechanism.** §15's evidence clause lists "excepted", but
  an exception path is a way to bypass a *required* gate — precisely "casually
  skippable". T09 ships no producer for that state, so there is nothing to
  audit. Recorded as a decision, not an oversight. `skip` remains what it is: a
  failed-step recovery that is already confirmed, warned and audited.
* **No change to flow membership.** Which phases exist is T07's; T09 never adds
  or removes a phase, and `GREENFIELD_V1_PHASES` stays the frozen 19-entry list
  and stays out of `FLOW_PHASES`.
* **No new gate, no ninth `approvals` key, no state field, no version bump.**
* **No prompt-side authority.** The prompt layer is told to *ask* the engine; it
  is never told a rule it could apply itself.

### Alternatives considered and rejected

| Alternative | Rejected because |
|---|---|
| Auto-satisfy a not-required gate inside `advance` | Produces no event to explain, so §15's "every omitted gate must be explainable and auditable" would be unmet; makes `advance` move two phases in one command; and would change the traversal of every LOW-risk existing test, including the frozen happy path |
| Put `gate_security` in `required_gates_always` instead of D4's derived rule | States the guarantee under the wrong name (implies security review is universally mandatory, which is what §15's exit criterion denies), and an override could later be read as able to reason about it. The derived rule is unremovable by construction |
| A `--acknowledge-critical` flag on the two CRITICAL positional gates | It would refuse `gate approve` for the CRITICAL variants of E23's differential, which drives the **frozen** `run_happy_path`. Buying a marginal acknowledgement by editing the one test file that must stay byte-identical is the wrong trade. D5's property is real and is proved by test instead |
| Raise `cryptography_or_secrets` to CRITICAL to cover credential exposure | Over-broad: every WorkItem that touches a secret would become CRITICAL. A dedicated signal is more faithful to §15's wording |
| Floor `schema_or_data_migration` at HIGH to cover destructive migration | Same over-breadth. §15 says *destructive/irreversible*, not *any* |
| Store the requirement set in `state.json` | Second source of truth; needs a schema field, migration row and template change; and defeats D9/D10 |

---

## Behavioral delta

### Deliberate changes

1. `authentication_or_authorization`'s hard floor rises MEDIUM → **HIGH**.
2. Five risk signals are added; six hard floors are added. §15's nine floors are
   all present. Risk levels rise for inputs naming the affected signals.
3. `required_gates_by_risk["MEDIUM"]` gains `gate_design`.
4. A gate in the bound flow is `required` or `omittable`; the terminal gate is
   always `required`.
5. New command `gate omit --gate <key>`; new refusals `gate_required` and
   `gate_omission_invalidated`; new audit event `gate_omitted`; new approval
   decision value `omitted_by_policy`.
6. `apply_advance` accepts `omitted_by_policy` **only** after re-deriving that
   the gate is still omittable.
7. The terminal gate's approval revalidates every earlier omission.
8. `compute_drift` and `cmd_repo_staleness` treat an omission as a baselined
   decision.
9. `governance gates` stops reporting `advisory: true` and reports dispositions;
   `gate show` reports `required` and reasons.
10. The record's `wouldBeRequiredGates` becomes `requiredGates` +
    `omittableGates`; `governanceVersion` becomes `"2"` with a real reader that
    still accepts `"1"`.
11. The `governance_recorded` ledger message gains a gate-disposition summary,
    **appended at the end** so existing prefix assertions survive.
12. `read_repo_config` becomes fail-closed (D14).
13. New lint check `repo_config_defaults_match_documentation` (D15).
14. Prose in `README.md`, `docs/SDLE-Reference-Guide.md` and `SKILL.md` that
    says gates run unconditionally and that risk routes nothing becomes true
    again (E28, E29); `modules/gate-protocol.md` gains an omission section;
    `docs/architecture/ADR-006-risk-adaptive-gate-policy.md` records D1–D17.

### Preserved invariants

Derived from the acceptance criteria below rather than maintained as a separate
list (T08 NB-1): each item here is the prose form of a lettered criterion.

| Guarantee | Held by |
|---|---|
| Gate discipline — no gate is passed without an explicit, recorded decision | A6, A7 |
| A required gate can never be omitted, by Claude or by anyone | A5, A6 |
| Claude cannot lower a deterministic floor — engine-enforced | A3, A4 |
| Fail safe — every new check refuses; none warns | A5, A6, A16 |
| Single writer — a refusal leaves `audit.md` **byte-identical** (B1/NB-6) | A8 |
| Drift protection, gate artifact SHA, test evidence, secret scan, implementation diff baseline, audit chain, retry/remediation caps, fail-safe transitions | A9 |
| `GREENFIELD_V1_PHASES` frozen at 19 entries, not derived, not a `FLOW_PHASES` row | A13 |
| `tests/test_integration_01_happy_path.py` and the nine dry-run transcripts byte-identical | A11 |
| Legacy `.workflow/` dual-read works; `migrate-workflow` never mutates it | A12 |
| State template byte-identical; 16 migration rows; v1.16 at all four locations; eight `approvals` keys | A10 |
| HOTFIX shorter but never ungoverned | A7 |
| Invariant 3 (SpecKit opacity), 4 (gate content in conversation), 7 (one source of truth), 8 (gates stay in the parent) | A14, A15 |
| The core refuses; it does not warn | A16 |

---

## Files expected to change

| Path | Change |
|---|---|
| `scripts/sdle.py` | `GOVERNANCE_POLICY_BUILTIN` (signals, floors, MEDIUM gate list); `GOVERNANCE_RECORD_VERSION` + `GOVERNANCE_RECORD_VERSIONS` + `read_governance_record`; `gate_requirements()` and the two positional helpers; `required_gate_set` reused; `cmd_gate_omit`; `gate omit` parser entry; `apply_advance`; `cmd_gate_approve` (D10 revalidation); `cmd_gate_show`; `cmd_governance_gates`; `cmd_governance_assess` record keys; `record_governance_audit` message; `compute_drift`; `cmd_repo_staleness`; `read_repo_config`; new lint check + its registration |
| `.claude/skills/sdle/SKILL.md` | Governance section: risk now routes gate requirements; the `gate requirement` question and `gate omit`; the two new refusal reasons; correct E29's sentence. **No policy value, signal id or gate list restated** |
| `.claude/skills/sdle/modules/gate-protocol.md` | A section for a gate the policy does not require: ask the engine, never decide; if omittable, state it in conversation, run `gate omit`, show the recorded reason; if required, the existing protocol is unchanged |
| `.claude/commands/sdle-approve.md` | Presentation only, if it needs to mention an omitted gate at all |
| `README.md` | The `governance gates` row (E28); a `gate omit` row; the risk-adaptive paragraph; the config JSON block stays but is now lint-bound; D16's sentence |
| `docs/SDLE-Reference-Guide.md` | The "all eight gates run unconditionally" paragraph (E28); `gate omit`; the disposition vocabulary |
| `docs/architecture/ADR-006-risk-adaptive-gate-policy.md` | **New.** D1–D17, the alternatives table, and the enforced/not-enforced split stated explicitly. **Must name no risk-signal id** (I6) |
| `tests/…` | See the two sections below |

**Must not change** (assert on content, not on Git):
`.claude/skills/sdle/templates/state.json`, `.claude/hooks/`,
`.claude/settings.json`, `.gitignore`, `tests/test_integration_01_happy_path.py`,
`docs/dry-runs/*`, `GREENFIELD_V1_PHASES`, `MANDATORY_FLOW_PHASES`,
`FLOW_PHASES`, `PHASE_SEQUENCE`, `PHASE_TO_GATE_KEY`, `SDLE_OWNED_PREFIXES`.

---

## Existing tests affected

Every row is a TP-003 category-2 change: the test asserts something the phase
deliberately changes. **No test may be deleted, `skip`ped, `xfail`ed or
weakened.** If a change is needed outside this table, that is a plan defect —
stop and write `T09-blocker.md`.

| # | File / test | Change | Why |
|---|---|---|---|
| X1 | `test_units_governance.py::test_no_phase_movement_function_consults_the_would_be_gate_set` | **Invert.** Assert instead that the phase-movement functions consult the requirement model, and that the *only* way past a required gate is an approval | E24 asserts precisely what T09 changes. Its companion `test_the_phase_movement_prefixes_actually_match_something` stays as the vacuity guard |
| X2 | `test_units_governance.py::test_the_would_be_gate_set_is_always_a_subset_of_the_registered_gates` | Rename the payload/record keys; drop `advisory is True`; keep the subset and non-emptiness assertions | D12 |
| X3 | `test_units_governance.py::test_the_would_be_gate_set_actually_differs_across_risk_levels` | Key rename only; `LOW < CRITICAL` still holds | D12 |
| X4 | `test_units_governance.py::test_risk_and_type_change_no_lifecycle_behaviour` | Clause 3 only: key rename, drop `advisory is True`. **Clauses 0–2 must not change** — they are the proof that approving every gate is still risk-independent | I2. Its docstring is updated to say what it now guarantees |
| X5 | `test_units_governance.py::test_a_floor_raises_the_level_the_score_alone_would_not_reach` | Docstring only (it says auth sits at MEDIUM) | D6 |
| X6 | `test_units_baseline.py::test_n34_no_gate_is_conditional_on_risk_or_classification` | **Invert.** It is T08's explicit T09-leakage guard and its subject is now the phase | E25 |
| X7 | `test_units_baseline.py::test_n34_every_flow_gate_set_is_structural_not_policy_driven` | Keep, sharpened: a flow's *gate membership* is still structural; what is policy-driven is the *requirement*. This is D3's distinction and the test is where it is pinned | E25 |
| X8 | `test_units_baseline.py::test_n15_the_baseline_reader_never_swallows_and_defaults` | The "positive half" contrast asserting `read_repo_config` is fail-open must go; replace with the same AST assertion applied to `read_repo_config` (no `Return` in a handler), keeping the `read_baseline` half intact | D14, E31 — **anti-contradiction clause** |
| X9 | `test_units_governance.py::test_the_policy_reader_has_no_handler_that_returns` | Docstring only (it cites `read_repo_config` as the fail-open example) | D14 |
| X10 | Any test asserting `governanceVersion == "1"` | Update to `"2"` and add the `"1"`-still-accepted case | D12 |
| X11 | Any test asserting the exact `governance_recorded` message | Adjust for the appended summary | Delta 11 |
| X12 | `test_lint_skill.py` | Add a firing test for `repo_config_defaults_match_documentation`; update the check-count assertion if one exists | D15 |

### Anti-contradiction clause

Two shipped tests assert the opposite of what this plan requires. They may be
edited **only** as specified, and the diff for each must be confined to the
lines named:

* **X8** — `tests/test_units_baseline.py::test_n15_…`: the final block
  (`swallower`, `swallowed`, and its `assert swallowed, "read_repo_config was
  expected to be fail-open (T05 NB-4)"`) is replaced by the inverse assertion.
  The `read_baseline` half above it is untouched.
* **X1/X6** — the two inertness guards. Each is *inverted in place*, keeping its
  name where the name still describes the subject, and keeping its vacuity
  guard.

`tests/conftest.py` may be edited **only** to add a governance-input helper that
takes an explicit risk level and/or signal list (the existing
`record_governance(**over)` already accepts overrides, so an addition may prove
unnecessary). No default in `record_governance` may change — E21's LOW/GREENFIELD
default is what keeps every existing driver byte-identical.

No other test file outside the tables above may change.

---

## New tests required

New file: **`tests/test_units_gate_policy.py`**, plus the additions noted.

**The requirement model**

| # | Test |
|---|---|
| N1 | For each of the five flows × four levels × four WorkItem types, `gate_requirements` returns a disposition for every gate in the flow and for no gate outside it; every disposition is in the closed vocabulary; every `required` entry has at least one reason |
| N2 | The terminal gate of every flow is `required` at **every** level and type, with `terminal_gate` among its reasons (D4) |
| N3 | `required_not_in_flow` is exactly the policy-named gates the flow lacks; with the built-in policy and HOTFIX it is **non-empty** (`gate_constitution`, `gate_plan`), so the report is not vacuous (D3/I4) |
| N4 | HOTFIX has **no** omittable gate at any level or type (D7) |
| N5 | The omittable set shrinks monotonically as the level rises: `omittable(LOW) ⊇ omittable(MEDIUM) ⊇ omittable(HIGH) = omittable(CRITICAL) = ∅` for every flow |
| N6 | `gate show` reports `required` and reasons consistent with `governance gates` for the same WorkItem |

**The floors and signals**

| # | Test |
|---|---|
| N7 | Each of §15's nine floors, driven through the real CLI: an input naming only that signal yields a `finalLevel` at or above the mandated level, and `floorsApplied` names the rule. Table-driven from `BUILTIN`, with an explicit nine-row expectation table in the test so a *removed* floor fails rather than silently shrinking the parametrisation |
| N8 | `authentication_or_authorization` alone yields **HIGH** (the regression this phase fixes) |
| N9 | Every built-in floor level is ≥ its value at `e1cf341`, and every built-in signal weight is ≥ its value there — a machine-checked "no floor was lowered while I was in here". The prior values are written literally in the test |
| N10 | An override restating `authentication_or_authorization`→MEDIUM is refused `policy_weakens_baseline` |

**Enforcement — the tests that make weakening detectable**

| # | Test |
|---|---|
| N11 | **The headline.** A HIGH-risk WorkItem cannot skip design or security: driven end to end through the CLI on GREENFIELD, `gate omit --gate gate_design` and `gate omit --gate gate_security` each exit **1** with reason `gate_required`, `advance` past them exits 1 `gate_not_approved`, and the only way through is `gate approve`. Repeated at CRITICAL |
| N12 | The same WorkItem at LOW: `gate omit --gate gate_design` exits 0, state records `omitted_by_policy` with the risk level, reasons and policy sha, `audit.md` gains exactly one `gate_omitted` entry, `audit verify` still passes, and the workflow reaches `complete` — where `gate_security` still required an approval |
| N13 | `gate omit` on the terminal gate is refused `gate_required` in **every** flow at **every** level, so no omission can reach the completion/baseline branch (D4, D8) |
| N14 | For every flow × every level: at CRITICAL the required set contains at least one gate strictly before `implement` and the terminal gate (D5). Non-vacuity guard: the "gate before implement" is asserted to exist for every flow |
| N15 | Hand-written `omitted_by_policy` in `state.json` for a gate the policy requires → `advance` refuses `gate_omission_invalidated` (D9) |
| N16 | Omit at LOW, re-assess at HIGH, drive to the terminal gate → its approval refuses `gate_omission_invalidated` naming the omitted gate (D10) |
| N17 | An override that adds the omittable gates to `required_gates_always` makes `gate omit` refuse for all of them — a repository can always tighten back to universal gates |
| N18 | `gate omit` under the legacy `.workflow/` binding refuses; the legacy traversal is unchanged (D8) |

**Guardrails**

| # | Test |
|---|---|
| N19 | After an omission, editing the artifact makes `drift check` report it — omission does not disable drift protection (D11) |
| N20 | `gate omit` refuses `artifact_missing` when the artifact is absent, and refuses when the artifact has no current `PASS` review (TP-011 unrelaxed) |
| N21 | **Ledger byte-identity.** For each of `gate_required`, `gate_omission_invalidated` (both sites), `artifact_missing` and the review refusal on `gate omit`: exit 1 and `audit.md` byte-identical before and after (B1/NB-6) |
| N22 | The completion summary lists an omitted gate as `omitted_by_policy`; the ledger holds its explanation |
| N23 | `omitted_by_policy` is written by **exactly one** function — asserted by AST over `scripts/sdle.py` |
| N24 | `governance gates` and `gate show` are read-only: SHA map of the repository unchanged across both |

**Record and reader**

| # | Test |
|---|---|
| N25 | A `governanceVersion: "1"` record still advances; an unknown version is an `IntegrityError` (exit 3) (D12) |
| N26 | `read_repo_config` has no `Return` inside any `ExceptHandler`; a malformed `config.json` still produces `config_malformed` from `config show` with the same reason and exit code as at `e1cf341` (D14) |

**Absence-of-change**

| # | Test |
|---|---|
| N27 | `tests/test_integration_01_happy_path.py` and the nine `docs/dry-runs/*.md` are byte-identical to `e1cf341` (line endings normalised) |
| N28 | `.claude/skills/sdle/templates/state.json`, `.claude/hooks/`, `.claude/settings.json`, `.gitignore` byte-identical to `e1cf341`; `version_string_consistent` still v1.16; 16 migration rows; eight `approvals` keys |
| N29 | `GREENFIELD_V1_PHASES` is the same 19-entry tuple, is not a `FLOW_PHASES` row, and every flow's phase list is element-wise identical to its value at `e1cf341` |
| N30 | No risk-signal id, and no new policy identifier, appears anywhere in `_searchable_files()` — including `docs/architecture/ADR-006-*` (I6). This is the existing `test_no_policy_default_value_is_restated_outside_sdle_py`, which picks up the new signals automatically; N30 asserts it still passes with a needle count of **17 + underscored check ids** |
| N31 | T10/T11 leakage: no `.claude/agents/`, no new product skill, legacy dual-read and `migrate-workflow` still work and still never mutate `.workflow/`, `current_feature_id` still present, version still v1.16 |

---

## Implementation sequence

Five milestones. **The suite must be green at the end of each.** No deliberate
red window is planned; if one becomes unavoidable it must be confined inside a
single milestone and declared in that milestone's checkpoint.

**M1 — the policy data, first, with "nothing routes yet" as its proof.**
`GOVERNANCE_POLICY_BUILTIN`: five signals appended, the
`authentication_or_authorization` floor edited in place, six floors appended,
`required_gates_by_risk["MEDIUM"]` gains `gate_design`. Tests N7–N10. X5 and any
docstring drift. **Proof:** `governance gates` still reports `advisory: true`,
the traversal of every existing test is unchanged, and the only observable delta
is recorded risk levels and the would-be set.

**M2 — the requirement model, read-only.** `gate_requirements()`, the two
positional helpers, `required_gate_set` reused as its policy half; extend
`governance gates` and `gate show`; rename the record keys and add the version
reader. Tests N1–N6, N24, N25. X2, X3, X4-clause-3, X10, X11. **Still nothing
routes**: `apply_advance` is untouched, so every gate still requires approval.

**M3 — enforcement.** `cmd_gate_omit` and its parser entry; `apply_advance`
accepts and re-derives; the D10 terminal revalidation; `compute_drift` and
`cmd_repo_staleness`; the `governance_recorded` message. Tests N11–N23. X1, X6,
X7. **This is the milestone where governance could be weakened**, so N11 and N21
must be written before the enforcement code, not after.

**M4 — inherited findings.** D14 (`read_repo_config` fail-closed + X8, X9, N26),
D15 (the new lint check + X12), D16 (README sentence). Independently revertable
and touching nothing M1–M3 touched.

**M5 — prompt layer, documentation, ADR-006.** SKILL.md, gate-protocol.md,
`sdle-approve.md`, README, Reference Guide, `ADR-006-risk-adaptive-gate-policy.md`.
Tests N27–N31. Final full suite + `lint-skill` + `validate.py`.

**Safe resume boundary: end of M2.** M1 and M2 change no routing — every gate
still requires an approval and the traversal of every flow is what T08 shipped.
M3 is where enforcement changes. A fresh agent resuming mid-phase must restart
at a milestone boundary, verify claimed state against disk (`--collect-only` is
the cheap check), and never trust a checkpoint's claim that a test file exists.

One checkpoint per milestone: `T09-checkpoint-a01-01.md` … `-05.md`. Twelve agent
runs in this migration have been killed mid-flight by API limits, one of them by
a weekly limit; write the checkpoint before starting the next milestone, not
after finishing it.

---

## Failure modes

| # | Failure | Detection | Response |
|---|---|---|---|
| F1 | **Governance is weakened without anyone noticing** — the phase's defining risk | N9 (no floor or weight below its `e1cf341` value), N11 (HIGH cannot skip design or security), N5 (the omittable set only shrinks with risk), N13 (terminal gate never omittable) | Any of these failing is a stop-the-phase event, not a test to adjust |
| F2 | An omitted gate escapes drift protection | N19 | D11 — `compute_drift` must accept `omitted_by_policy`. This is the most likely silent regression in the phase |
| F3 | A new refusal appends to the ledger before raising | N21, and a byte comparison of `audit.md` around each refusal | Move the check into the pure-reader block ahead of the first `append_audit`. This is the B1/NB-6 property fixed at `0a9b8c7`/`c0775b3` and it must not regress |
| F4 | Raising the auth floor cascades into more failing tests than X-table predicts | Full suite | Expected breakage is confined to tests that pin a *level*. Anything outside the X table is a **plan defect**: stop and write `T09-blocker.md` |
| F5 | A new signal id or policy default is written into a doc, prompt or **ADR-006** | `test_no_policy_default_value_is_restated_outside_sdle_py` (N30) | I6 — `docs/architecture` is inside `_searchable_files()`. Describe the floors in ADR-006 in prose that names no identifier, and point at `governance policy` |
| F6 | `test_integration_01_happy_path.py` or a transcript is touched | N27 | Revert. The design (D2) exists precisely so they need not change |
| F7 | The requirement set gets stored in `state.json` "for convenience" | N28 (template byte-identical, 16 migration rows) | D13. Re-derive |
| F8 | `gate omit` grows a `--force`, `--reason` or override flag | Code review; N23 | Any operator-supplied way past `gate_required` is the exception mechanism D17 refuses |
| F9 | The prompt layer is given a rule it can apply itself (e.g. a restated risk→gate table) | N30 and reading | The prompt asks the engine. One source of truth (invariant 7) |
| F10 | `lint-skill` loses or weakens a check | A17 | The 32 checks observed at HEAD (E3) must all still be present and passing |
| F11 | The full suite is red | Full run | The F1 `ENVIRONMENT_FLAKE` procedure from T00/T01 is **VOID**. Any failure is a presumed real regression; investigate it, never pattern-match it to the old `WinError 5` signature |
| F12 | A false green from the shell proxy | — | Run `rtk proxy python -m pytest`, redirect to a file, read `$?` with **no pipe**. Reproduce any negative grep claim with `rtk proxy "grep -rnE …"` or a Python walk — a plain `grep -rn` has produced a false negative on a real line in this repository. `sdle.py constants` and `lint-skill` nest their payload under `data`. The tree is CRLF and `git show` is LF; normalise before concluding a file differs |
| F13 | `progress.md` becomes unparseable | `validate.py` exit 3 | A literal `\|` inside a table cell breaks it. Escape or reword |

---

## Rollback/recovery strategy

* **Rollback point: `e1cf341`** (T08 implementation). Product baseline `f8fdaa0`.
  `git diff e1cf341 -- <path>` is the per-file recovery view; the T09
  implementation is a single revertable commit.
* **Per-milestone recovery.** M1 is data-only inside one dict. M2 is additive
  and read-only. M3 is the only milestone that changes what an existing,
  previously-permitted command does. M4 and M5 are independent of all three.
* **Runtime recovery for a user.** No state schema changed (D13), so nothing a
  user holds becomes unreadable. A WorkItem that recorded an omission and then
  hits `gate_omission_invalidated` has two named remedies in the refusal
  message. Deleting a repository policy override returns the repository to the
  built-in, which is by construction the weakest admissible policy.
* **A half-written state is impossible** — `write_atomic` is unchanged and is
  still the only writer.
* **Interrupted agent.** Resume from disk: `progress.md`, the T09 checkpoints and
  `git diff e1cf341`. Never infer success from an interrupted run (§24.6).

---

## Acceptance criteria

Objective, each checkable by a command the verifier can re-run.

- [ ] **A1** `python scripts/sdle.py governance policy` in a repository with no
      override reports **17** risk signals, **12** hard-floor rules, and
      `required_gates_by_risk` = `{LOW: [], MEDIUM: [gate_tasks, gate_design],
      HIGH: [gate_tasks, gate_analyze, gate_design, gate_security], CRITICAL:
      same as HIGH}`. `risk_thresholds`, `required_gates_always` and
      `required_gates_by_type` are unchanged from `e1cf341`.
- [ ] **A2** All nine §15 floors are present and at or above §15's level, proved
      by driving each through `governance assess` (N7). Specifically
      `authentication_or_authorization` alone yields `finalLevel` **HIGH** (N8).
- [ ] **A3** No built-in floor level and no signal weight is below its value at
      `e1cf341`, machine-checked against literals in the test (N9).
- [ ] **A4** An override that restates the old MEDIUM auth floor is refused
      `policy_weakens_baseline`, exit 1 (N10).
- [ ] **A5** `gate omit` on a **required** gate exits **1** with reason
      `gate_required`, in every flow, at every risk level where the gate is
      required, and leaves `audit.md` byte-identical (N11, N13, N21).
- [ ] **A6** **§15's exit criterion, driven through the real CLI.** A HIGH-risk
      GREENFIELD WorkItem cannot reach `complete` without approving
      `gate_design` and `gate_security`; a LOW-risk one may omit `gate_design`
      but still cannot omit `gate_security`; both facts asserted on
      `state.phase_history`, `state.approvals` and `audit.md` (N11, N12).
- [ ] **A7** HOTFIX has no omittable gate at any level or type, and its terminal
      gate is required in every case (N4, N2, N13).
- [ ] **A8** For each of `gate_required`, `gate_omission_invalidated` at
      `apply_advance`, `gate_omission_invalidated` at the terminal gate,
      `artifact_missing` on `gate omit`, and the review refusal on `gate omit`:
      exit 1 and `audit.md` **byte-identical** before and after (N21).
- [ ] **A9** Every §15 "preserve" guardrail demonstrated intact **for an omitted
      gate**: its artifact SHA is baselined, editing the artifact is reported by
      `drift check`, `audit verify` passes, the secrets scan and test evidence at
      `implement` are unchanged, and the implementation diff baseline is
      unchanged (N19, N12, N20).
- [ ] **A10** `.claude/skills/sdle/templates/state.json`, `.claude/hooks/`,
      `.claude/settings.json` and `.gitignore` are byte-identical to `e1cf341`;
      `version_string_consistent` still reports **v1.16**; the migration chain
      still has **16** rows; `approvals` still has exactly **8** keys (N28).
- [ ] **A11** `tests/test_integration_01_happy_path.py` and all nine files under
      `docs/dry-runs/` are byte-identical to `e1cf341` (line endings normalised
      — F12) (N27).
- [ ] **A12** The legacy `.workflow/` dual-read still binds when no WorkItem is
      registered; `migrate-workflow` still leaves `.workflow/` byte-for-byte
      untouched; `gate omit` is unreachable on that path (N18, N31).
- [ ] **A13** `GREENFIELD_V1_PHASES` is the same 19-entry tuple, is still not a
      `FLOW_PHASES` row, and all five flows' phase lists are element-wise
      identical to `e1cf341` (N29).
- [ ] **A14** No policy value, risk-signal id or gate-requirement table is
      restated outside `scripts/sdle.py` — content search over
      `_searchable_files()`, **including `docs/architecture/ADR-006-*`** (N30).
- [ ] **A15** No `speckit-*` name or `/speckit.*` command appears in any added
      (`^+`) line of the T09 diff outside the existing verbose carve-outs
      (invariant 3); nothing holding a gate is delegated to a subagent
      (invariant 8).
- [ ] **A16** Every new code path **refuses**; none warns. Asserted by reading
      each new branch and by the exit codes in N11, N13, N15, N16, N18, N20.
- [ ] **A17** `lint-skill` exit 0 with **no check removed or weakened**: the 32
      checks observed at HEAD (E3) all still present and passing, plus
      `repo_config_defaults_match_documentation`, which has a firing test in
      `test_lint_skill.py` (N26/X12).
- [ ] **A18** `read_repo_config` contains no `Return` inside any
      `ExceptHandler`, and `config show` on a malformed `config.json` produces
      the same reason and exit code as at `e1cf341` (N26).
- [ ] **A19** The string `so an inference can never be read as an observation`
      no longer appears in `README.md`, and the sentence replacing it names the
      qualifier (D16).
- [ ] **A20** `docs/architecture/ADR-006-risk-adaptive-gate-policy.md` exists and
      states explicitly what the engine guarantees about an omission (it was
      permitted by a deterministic policy, is recorded, is auditable, and could
      not have been chosen for a required gate) **and what it does not** (the
      engine cannot tell whether a human or Claude issued any gate command; that
      trust model is unchanged from every other gate).
- [ ] **A21** Full suite run and observed: collected count, passed count and the
      **raw exit code**, read with no pipe. The pre-T09 collected count observed
      in this planning context is **1025** (E6); the new count must equal 1025
      plus the number of tests actually added. The pre-T09 *pass* count is
      `UNKNOWN` to this plan (E7) and must be re-derived, not inherited.
- [ ] **A22** `python tools/transition/validate.py` exit 0; `progress.md` has a
      T09 row with no literal `|` inside any cell.
- [ ] **A23** Every test change is recorded in the handoff with its TP-003
      category and reason. No test is deleted, `skip`ped, `xfail`ed or weakened.
      The set of changed test functions is a subset of the X table, and
      `tests/conftest.py` changed only as the anti-contradiction clause permits.
- [ ] **A24** No T10/T11 leakage: no `.claude/agents/`, no product subagent, no
      skill split, no new product skill file; `current_feature_id`, the legacy
      rung and the fixed-8-gate prose that T11 owns all still present; version
      still v1.16 (N31).
- [ ] **A25** Python 3.11 and CI recorded as `NOT_RUN` / `UNKNOWN`. No outcome
      predicted.

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is `PLANNED`.**

Both gaps the orchestrator named are resolved explicitly: the nine floors are
mapped signal by signal with four new signals justified individually (D6), the
auth floor is raised deliberately rather than as a side effect (D6, M1, A2), and
T06's existing `required_gate_set` / `required_gates_*` map is the mechanism
T09 consumes rather than a parallel one (D12, M2). §15's per-level intent is
checked against the shipped defaults and corrected in one cell (D7), and
CRITICAL's two extra approvals are resolved as positional properties with the
alternative named and rejected (D5).

| # | Unknown | Class | Handling |
|---|---|---|---|
| U1 | Suite pass count and raw exit code at HEAD | **UNKNOWN** | Not run in this planning context (E7). `1025` is the *collected* count I observed. A21 requires the implementer to observe the pass count and exit code directly rather than inherit `progress.md`'s figure |
| U2 | Python 3.11 behaviour and CI outcome | **UNKNOWN** | Never observed on this branch (E40). Not material: T09 adds no new syntax or stdlib surface beyond what T05–T08 already use |
| U3 | Whether real Spec Kit behaves differently when a gate is omitted | **UNKNOWN** | Tests never invoke Spec Kit. Unchanged from T07/T08's equivalent unknown. An omitted gate still runs its preceding generation phase, so no Spec Kit invocation is skipped — the risk is structurally bounded |
| U4 | Exact new `lint-skill` check count | Not determinable in advance | A17 pins the invariant that matters (32 preserved and passing, none weakened, the new one has a firing test) rather than a number the planner would have to guess |
| U5 | Whether `required_gates_by_risk["MEDIUM"]` should also gain `gate_analyze` | INFERRED, decided | No. §15 hedges checklist/analysis at MEDIUM with *"as applicable"* and states it flatly at HIGH; `gate_analyze` is therefore HIGH-and-above. Pinned by A1 and N5, so a later phase must change it visibly |
| U6 | Whether the dry-run transcripts become stale documentation for a LOW-risk GREENFIELD run | INFERRED, decided | Yes, mildly: they show all eight gates, which is still a *valid* run (approving an omittable gate is always permitted) but no longer the only one. They stay byte-identical (A11) and the staleness joins T04 N-6's documented transcript residual for **T11**'s documentation sweep |
| U7 | Whether an operator should be able to force a gate back on per-WorkItem | INFERRED, decided | Out of scope. The repository policy override already tightens (N17), and a per-WorkItem loosening is D17's rejected exception mechanism |
| U8 | Whether `governanceVersion` should have been versioned per-record at all | INFERRED, decided | D12 closes E35's smell by giving the field a reader that accepts `"1"` and `"2"` and refuses anything else, rather than adding a second unread field |

---

## Scope exclusions

Explicitly **not** in T09. If any appears in the diff it is future-phase leakage
and the verifier must fail the phase.

- **T10 — progressive skills and specialist subagents (§16).** No
  `.claude/agents/`, no product subagent, no skill split, no
  `sdle-design-review` / `sdle-security-review` skill. Gate content stays in the
  parent session (invariant 8). The `sdle-transition-*` migration agents remain
  control-plane scaffolding and are not evidence of T10.
- **T11 — hardening, cleanup and convergence (§17).** The legacy `.workflow/`
  dual-read rung, the repo-global lock, WorkItem-less initialisation,
  `current_feature_id`, the fixed 18-phase/8-gate assumptions still embedded in
  prose, the transitional dual-path code and the version bump all stay. §17's
  mandatory "gate omission evidence" hardening test is T11's; T09 ships the
  unit and integration coverage listed above, not §17's matrix.
- **The open T02–T08 findings.** Not adopted, with three named exceptions:
  - **T05 NB-4 (fail-open `read_repo_config`) — ADOPTED** (D14). T09 was named
    its owner and the named reason is this phase's subject.
  - **T05 NB-3 (`REPO_CONFIG_DEFAULTS` restated in README) — ADOPTED** (D15),
    by binding lint check rather than by deleting the example.
  - **T08 NB-3 (one README clause without its qualifier) — ADOPTED** (D16),
    because T09 edits that file anyway.
  Everything else stays open and unowned by T09, explicitly including: **`.sdle/`
  is in neither `SDLE_OWNED_PREFIXES` nor `cmd_manifest_build`'s exclusion**
  (T04 N-7 / T05 NB-7(b)) — *not adopted*, still T11's; T04 N-2 (Spec Kit tier-2
  discovery by newest mtime), N-3 (non-normalised write-fence carve-out), N-4,
  N-6 (stale runtime paths in `phase-execution.md`, `gate-protocol.md` and the
  transcripts); T03-1 (the `branch_guard` fail-open window), T03-4/5/6, T03-7/8,
  T03-10; T02 NB-2/4/5; T05 NB-5, NB-6, NB-7(a) (`hooks.py::in_dir` matching
  `/{name}/` anywhere — T09 adds nothing to `FENCED`, so it is inherited intact).
- **Any change to flow membership or the phase registry.** T07 owns which phases
  execute. T09 owns whether a gate that exists requires approval. No phase is
  added, removed, reordered or made conditional; `PHASE_SEQUENCE` stays at 21 and
  `FLOW_PHASES` is untouched.
- **§27's deferred list** — release/build management, MCP, databases, knowledge
  graphs, cross-repository orchestration, distributed locks, OPA/Rego, a policy
  DSL, YAML. Policy and record formats stay **JSON, stdlib-only** (§11).
- **Any generic workflow construct.** §13's constraint is still binding: no
  conditional branching, no parallel phases, no loops, no dynamic phase
  insertion. A gate requirement is a boolean derived from three inputs, not a
  branch in a lifecycle. If the implementation grows a construct capable of
  expressing a lifecycle SDLE does not currently need, that is a defect, not a
  feature.
