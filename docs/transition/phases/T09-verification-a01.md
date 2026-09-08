# T09 Independent Verification — Attempt a01

**Phase:** T09 — Risk-Adaptive Gate Policy (contract §15)
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Everything below was observed in this
> context, from this repository, at HEAD `6318541`. Nothing is inherited from
> the handoff, the checkpoints or `progress.md`.

**Identity.** HEAD `63185419a2587f2b3b41a200953c218075c1c492` ("T09:
risk-adaptive gate policy (IMPLEMENTED, NOT YET VERIFIED)"), branch
`transition/workitem-v1`. Rollback point `e1cf341` (T08 implementation, verified
PASS at `44ae6d8`). Plan commit `ad08d4b`. Product baseline `f8fdaa0`.
`git status --porcelain` = one ` M .claude/settings.local.json`, which is
declared out of scope and pre-existing.

**Diff scope actually verified.** `git diff --name-status ad08d4b..6318541` is
21 paths: `scripts/sdle.py`, four prompt/documentation files, the new
`docs/architecture/ADR-006-*`, `docs/transition/progress.md`, seven T09 control
files, six test files (one new). Zero `D`, zero `R` across the whole range —
confirmed by `git diff --diff-filter=DR --name-status e1cf341..6318541`
returning nothing.

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| A1 | PASS | Loaded `GOVERNANCE_POLICY_BUILTIN` from the shipped module: `risk_signals` **17**, `hard_floors` **12**, `risk_thresholds` `{LOW:0, MEDIUM:2, HIGH:5, CRITICAL:9}`, `required_gates_always` `[gate_constitution, gate_spec, gate_plan, gate_implement]`, `required_gates_by_risk` LOW `[]` / MEDIUM `[gate_tasks, gate_design]` / HIGH and CRITICAL `[gate_tasks, gate_analyze, gate_design, gate_security]`, `required_gates_by_type` `{enhancement:[], defect:[gate_tasks], hotfix:[], chore:[]}`. Diffed against `GOVERNANCE_POLICY_BUILTIN` parsed by AST out of `git show e1cf341:scripts/sdle.py`: thresholds, `required_gates_always`, `required_gates_by_type`, `quality_checks` and `policyVersion` all byte-equal |
| A2 | PASS | All nine §15 floors present at or above the mandated level (read §15's own list out of `transition.md` and matched signal by signal). Driven through the real CLI: `governance assess` with `signals: ["authentication_or_authorization"]` alone yields `finalLevel: HIGH` and `floorsApplied` naming that rule |
| A3 | PASS | Machine-compared the shipped policy against the one parsed from `git show e1cf341:scripts/sdle.py` — not against the test's literals. Zero weakenings: no signal weight dropped or disappeared, no floor level fell or disappeared, no threshold rose, no `required_gates_*` entry was removed. The only in-place change is `authentication_or_authorization` MEDIUM → HIGH; six floor rules and five signals were appended |
| A4 | PASS | Wrote `.sdle/policies/governance-policy.json` restating `authentication_or_authorization` → MEDIUM alongside the other eleven rules: `governance policy` exit **1** `policy_weakens_baseline`; `gate omit` in the same repository also exit **1** `policy_weakens_baseline` |
| A5 | PASS | Reproduced through the CLI at HIGH: `gate omit --gate gate_design` exit **1** `gate_required`; `gate omit --gate gate_security` exit **1** `gate_required` with reasons `['terminal_gate']` at LOW and `['risk:HIGH','terminal_gate']` at HIGH; SHA-256 of `audit.md` identical before and after each. Cross product over 5 flows × 4 levels × 4 types computed directly from `gate_requirements`: the terminal gate is `required` in all 80 cells |
| A6 | PASS | Two full end-to-end CLI runs. HIGH-risk GREENFIELD at `gate_design`: `gate omit` → 1 `gate_required`, `advance --to implement` → 1 `gate_not_approved`, `skip` → 1 `not_failed`, `skip --confirm` → 1 `no_pending_confirmation`, a hand-written `omitted_by_policy` in `state.json` → `advance` 1 `gate_omission_invalidated`. LOW-risk GREENFIELD: `gate omit --gate gate_design` exit 0 recording `{decision: omitted_by_policy, risk_level: LOW, reasons: [], policy_sha256: null}`, one `gate_omitted` ledger entry, `**Gate Decision:** OMITTED`, `audit verify` exit 0 `chain_ok: true`; `gate omit --gate gate_security` still refused `gate_required`; the run reached `complete`/`completed` only after `gate approve --gate gate_security` |
| A7 | PASS | HOTFIX `omittable_gates` is `[]` at every level and every type (16 cells). Its terminal gate is `gate_security`, `required` in all 16. `required_not_in_flow` for HOTFIX is `['gate_constitution','gate_plan']` — non-empty, so the inert report is not vacuous |
| A8 | PASS | Ledger SHA-256 identical before/after for `gate_required` (`gate omit`), `artifact_missing` (`gate omit`), `review_missing` (`gate omit`), `gate_omission_invalidated` at `apply_advance`, and `gate_omission_invalidated` at the terminal gate's `gate approve`. `audit verify` exit 0 `chain_ok: true` after each |
| A9 | PASS | For an omitted gate: `state["artifact_shas"]["gate_design"]` is populated; `drift check` returns `[]` while the artifact is unchanged and `['gate_design']` after mutating it — drift protection survives omission. `audit verify` exit 0. `compute_drift` and `cmd_repo_staleness` both filter on `BASELINED_GATE_DECISIONS = ("approved", GATE_OMITTED_DECISION)`; `grep` shows those are the only two use sites. `implement preflight` and `manifest build` were exercised unchanged in both runs |
| A10 | PASS | `.claude/skills/sdle/templates/state.json`, `.claude/hooks/`, `.claude/settings.json` and `.gitignore` do not appear in `git diff --name-status e1cf341..6318541` at all. `lint-skill` `version_string_consistent` passes; `constants` reports `version_chain` = **16** rows; `approvals` still has 8 keys (state template untouched) |
| A11 | PASS | `tests/test_integration_01_happy_path.py` and `docs/dry-runs/` do not appear in the commit-to-commit name-status diff |
| A12 | PASS | Built a legacy `.workflow/` project with no WorkItem: `gate omit` refuses (`workitem_required`, the ladder rung, before `governance_workitem_required`). `migrate-workflow --workitem <id>` exit 0 and a recursive path+content SHA of `.workflow/` is identical before and after |
| A13 | PASS | `GREENFIELD_V1_PHASES` is a 19-entry `tuple`; `FLOW_PHASES` is not exported at module level and the flow registry is built from SKILL.md — `consts.flow('GREENFIELD').phases` equals the frozen tuple element-wise. Flow shapes: GREENFIELD 19/8, BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3 — identical to the plan's E4 |
| A14 | PASS | Re-implemented the needle search independently (22 needles: 17 signal ids + 5 underscored check ids) over `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md`, `.claude/skills`, `.claude/commands`, `.claude/hooks`, `.sdle`, `docs/architecture`. **Zero offenders**, ADR-006 included. Also searched the same set for the five policy table names (`required_gates_by_risk`, `required_gates_always`, `required_gates_by_type`, `risk_thresholds`, `hard_floors`) — zero hits |
| A15 | PASS | Scanned all 4247 added (`^+`) lines of `ad08d4b..6318541` for `speckit-` and `/speckit.`: 5 hits, all inside the handoff prose and the assertion text of the guard test itself; none in a prompt or documentation file. No product subagent or skill was added (`.claude/skills` is still `sdle` plus the migration `apply-sdle-transition`) |
| A16 | PASS | AST enumeration of the refusals raised directly in the new code: `cmd_gate_omit` raises `drift_pending`, `not_at_gate`, `governance_workitem_required`, `governance_missing`, `gate_required`, `artifact_missing`; `apply_advance` gains `gate_omission_invalidated`; `revalidate_recorded_omissions` raises the same reason; `read_governance_record` raises `IntegrityError`. Every one raises; none warns. All observed exit codes are 1, or 3 for the integrity path |
| A17 | PASS | `lint-skill` raw exit **0**, `ok: true`, **33 checks**, `failed: []`. Enumerated the names: the 32 from the plan's E3 are all present and passing, plus `repo_config_defaults_match_documentation`. A regex sweep of the `sdle.py` diff for `Check(`, `checks.append` and `_check_` shows only additions — no check removed, renamed or weakened |
| A18 | PASS | `read_repo_config` has no `Return` inside any `ExceptHandler` (AST). Called directly with a non-object `config.json` it raises `Refused("config_malformed")`; `config show` on a malformed file still exits **1** with reason `config_malformed` |
| A19 | PASS | The string `so an inference can never be read as an observation` is gone from `README.md`; the replacing sentence names what the engine checks and what it cannot |
| A20 | PASS | ADR-006 §3 carries both halves. **Guaranteed** includes "could **not** have been chosen for a gate the policy required, at any risk level, under any policy, by any caller". **Not guaranteed** includes "The engine cannot tell whether a human being or the orchestrator issued any gate command" *and* "Nor does it judge whether the governance record's declared risk signals are an accurate description of the work" |
| A21 | PASS | Re-run in this context, not inherited. `rtk proxy python -m pytest -q -p no:cacheprovider --junitxml=...` → **`1402 passed in 1418.89s (0:23:38)`**, `PYTEST_RAW_EXIT=0` read with no pipe. JUnit root: `tests=1402 failures=0 errors=0 skipped=0`. Occurrences of `short test summary` in the captured run = **0**. `--collect-only -q` = **1402 tests collected**, so collected equals passed |
| A22 | PASS | `python tools/transition/validate.py` raw exit **0**, `TRANSITION_VALID: complete=9/12 next=T09`. The T09 row (before this verification's edit) contained no literal pipe inside a cell |
| A23 | **PARTIAL** | No test deleted, `skip`ped, `xfail`ed or weakened — verified independently (zero `D`/`R` under `tests/`; the only `pytest.mark.skipif` in the suite is the pre-existing POSIX-`sh` guard in `test_units_infra.py`; `test_units_baseline.py` 41 → 41 and `test_units_governance.py` 72 → 72 test functions). Every change is recorded in the handoff with its TP-003 category. **But the changed set is not a subset of the plan's X table**: five functions across two files the X table does not name changed. See finding NB-1 |
| A24 | PASS | No `.claude/agents/` product subagent (the four `sdle-transition-*` files are pre-existing migration control plane), no skill split, no new product skill. `current_feature_id`, `legacy_workflow` and the legacy rung all still present; `SDLE_OWNED_PREFIXES` still lacks `.sdle/` and `cmd_manifest_build`'s exclusion is untouched, so T04 N-7 / T05 NB-7(b) remains open and unowned as the plan requires. `version_string_consistent` still v1.16 |
| A25 | PASS | Recorded below as NOT_RUN / UNKNOWN. No outcome predicted |

---

## Regression evidence

The five reproductions the orchestrator named were driven through the real CLI
in scratch projects built from the shipped skill root, engine, hooks and
`settings.json` — a realistic install, not a monkey-patched module. All
invocations were real subprocesses.

**1. A HIGH-risk WorkItem cannot omit design or security.** GREENFIELD,
`signals: ["authentication_or_authorization"]` → `finalLevel HIGH`. Driven to
`gate_design`, then attacked by every route constructible:

| Route | Result |
|---|---|
| `gate omit --gate gate_design` | exit 1 `gate_required`, ledger byte-identical |
| `advance --to implement` | exit 1 `gate_not_approved`, ledger byte-identical |
| `skip` | exit 1 `not_failed`, ledger byte-identical |
| `skip --confirm` | exit 1 `no_pending_confirmation`, ledger byte-identical |
| hand-written `omitted_by_policy` in `state.json`, then `advance` | exit 1 `gate_omission_invalidated` |
| policy override emptying `hard_floors` and the required-gate lists | `governance policy` and `gate omit` both exit 1 `policy_weakens_baseline` |
| policy override lowering only the auth floor to MEDIUM | both exit 1 `policy_weakens_baseline` |
| hand-edited `governance.json` (`finalLevel` forced to LOW, signals emptied) | `gate omit` still exit 1 |
| `gate omit --gate gate_security` at HIGH and at LOW | exit 1 `gate_required`, reasons include `terminal_gate` |

No route reached `complete` without approving `gate_security`. The only route
that made `gate_design` omittable was a **fresh `governance assess` declaring no
risk signals** — see finding NB-2.

**2. The floor asymmetry.** Every floor and weight was compared against the
policy parsed out of `git show e1cf341:scripts/sdle.py`, not against the new
test's literals: zero weakenings, one raise, six appended floor rules, five
appended signals. Lowering a floor is refused at the only reachable boundary
(`read_governance_policy` → `_refuse_weakening` → `policy_weakens_baseline`),
which is engine code; no prompt file restates a policy value at all (A14), so
there is nothing prompt-side to talk around.

**3. The derived terminal-gate rule.** `terminal_gate_key(flow)` returns
`flow.gate_keys[-1]` — positional, in no dictionary. `gate_security` is terminal
in all five flows. Over the whole 5 × 4 × 4 cross product it is `required` with
`terminal_gate` among its reasons in every cell, and every `required` entry has
at least one reason. I attempted removal through an override: the policy schema
exposes only `required_gates_always`, `required_gates_by_risk` and
`required_gates_by_type`, all of which are checked for monotone domination, and
none of which the terminal rule reads — an override that empties all three is
refused `policy_weakens_baseline`, and even were it accepted the rule would
still fire because it is appended after the dictionary lookup. Structurally
unremovable, as claimed.

**4. Omitted gates still raise drift.** Omitted `gate_design` at LOW; the
baseline SHA was recorded in `artifact_shas`; `drift check` returned `[]` clean
and `['gate_design']` after mutating `design/app/app-design.md`.
`BASELINED_GATE_DECISIONS` has exactly two use sites, `compute_drift` and
`cmd_repo_staleness`.

**5. `gate omit` semantics.** Refuses `artifact_missing` when the artifact is
absent and `review_missing` without a current PASS review — TP-011 unrelaxed.
`cmd_gate_approve`'s directly-raised refusals are exactly `artifact_missing` and
`not_at_gate` (AST), it makes no call to `gate_requirements*` or
`required_gate_set`, and `gate approve --gate gate_design` on an omittable gate
exits 0 recording `"approved"` — approving is always still permitted. An
omission produces one real audit entry: `event gate_omitted`,
`**Gate Decision:** OMITTED`, a message naming the gate number, the policy
source, the final risk level, the flow, "No human approved this gate", and the
baseline SHA.

**6. Refusals leave `audit.md` byte-identical.** Reproduced at `gate approve`
(`gate_omission_invalidated` at the terminal gate — ledger SHA identical,
`audit verify` exit 0) and at `skip` (`not_failed` — ledger SHA identical). The
D10 revalidation was driven end to end: omit `gate_design` at LOW, re-assess to
HIGH, drive to `gate_security`, `gate approve` → exit 1
`gate_omission_invalidated` naming `invalidated: ['gate_design']`, ledger
byte-identical, `advance --to complete` then exit 1 `gate_not_approved`, ledger
still byte-identical, `audit verify` exit 0.

**7. §15's preserve list.** Drift protection (verified above), gate artifact SHA
(recorded for omitted gates too), test evidence and secret scan (`implement
preflight` / `manifest build` unchanged and exercised in both runs),
implementation diff baseline (untouched by the diff), audit chain (`audit verify`
exit 0 after every scenario), retry/remediation caps (untouched), fail-safe
transitions (every new path refuses and freezes; `apply_advance` remains the
choke point and its two original refusals still fire first).

### The three judgements

**A — `read_repo_config` became fail-closed (T05 NB-4). Correct, and the test
change is a legitimate TP-003 category 2.** The old shape returned
`REPO_CONFIG_DEFAULTS` from inside `except (OSError, JSONDecodeError,
ValueError)`. It is replaced by "decide the problem, then raise once" —
`Refused("config_malformed", …)`. Observable behaviour is unchanged: `config
show` on `{not json` still exits 1 with reason `config_malformed`, because
`repo_config_findings` still runs first and is still the single soundness
predicate. The X8 edit is confined exactly as the anti-contradiction clause
required — the `read_baseline` half above it is untouched, and the replacement
**adds** a non-vacuity guard (`assert handlers, …`) that the fail-open version
did not have. Inverting an assertion whose subject the phase deliberately
changed is category 2, not a weakening; the new assertion is strictly stronger
than the one it replaced.

**B — the new lint check's absent-document skip is a principled fix, not a
relaxation.** I exercised the predicate directly in a scratch project rather
than reading the code:

| Case | Result |
|---|---|
| neither `README.md` nor the Reference Guide present | **passes**, message "no repository documentation in this project" |
| README present, no fenced `json` block | **fails**, "the check would pass vacuously" |
| README present, a `json` object without `configVersion` | **fails**, same guard |
| README present, `configVersion` block with wrong values | **fails**, names both dicts |
| README present, block matching `REPO_CONFIG_DEFAULTS` | passes, "1 documented configuration block(s) equal" |
| README present, unparseable `json` block | **fails**, quotes the parse error |
| the real repository | passes, 1 block examined |

The present-but-empty case genuinely still fails, which is the drift D15 exists
to catch. The claim that this matches `_check_doc_phase_tables` is accurate:
that function does `if not path.is_file(): continue`. `lint-skill` is
`RUNTIME_FREE` and must answer in a project with no README, so firing on absence
would have been a false positive, not a guarantee. Four firing tests in
`test_lint_skill.py` pin all four halves, including a case that deletes the
block from a README that stays on disk. Verdict: principled.

**C — ADR-006 re-read in full against the shipped engine.** Its floor
arithmetic is now correct and the engine agrees: four §15 floors map onto
signals the policy already had (`authentication_or_authorization`,
`personal_or_sensitive_data`, `backward_incompatible_change`,
`payment_or_financial`) and five are new signals — confirmed by set-differencing
the shipped `risk_signals` against `e1cf341`'s. "One existing floor was raised"
matches the single in-place level change. §2.4's positional rule, §2.6's
"nothing is stored" (state template and migration chain unchanged), §2.7's two
revalidations, §2.8's re-pointed guardrails and the derived
`all_gates_approved`, §2.9's absence of any `--force` / `--reason` flag (the
`gate omit` parser takes only `--gate`), §5's "state schema, migration chain,
state template and version string are all unchanged" — every one checked against
the engine and true. §7's "no policy value, risk-signal identifier or
gate-requirement table appears in any prompt or documentation file, including
this one" — verified by an independent 22-needle search. I found **no
inaccuracy** in ADR-006. Note that §3's "Not guaranteed" paragraph is the
document that discloses NB-2 below, which is why NB-2 is non-blocking.

### The document sweep for overstatement

I read every changed sentence in `README.md`, `docs/SDLE-Reference-Guide.md`,
`SKILL.md`, `modules/gate-protocol.md` and `.claude/commands/sdle-approve.md`
against the engine. The four falsified Reference Guide statements were corrected
narrowly and correctly: the glossary's definition of a Gate, §9's "three
responses are recognized", §12.4's description of the record's gate set, and the
role table's "sole authority … at every gate" (now scoped to "every gate the
governance policy requires", with the omission alternative and the
always-permitted stricter approval both stated). `governance gates` no longer
claims to be advisory in either the README table or the Reference Guide command
table. The completion-summary sentence now says `all_gates_approved` is derived.
`gate-protocol.md` step 5 tells the orchestrator to ask the engine and to treat
`required: null` as required — fail-closed. I found **no remaining sentence that
overstates what policy controls or what the engine guarantees**. The one
statement I tested hardest — Reference Guide §9's "`omit` … is the only way to
pass a gate without a decision by a human" — holds: `cmd_skip` funnels through
`apply_advance`, which still refuses `gate_not_approved` at a gate.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy python -m pytest -q -p no:cacheprovider --junitxml=<scratch>` (background, unpiped `$?`) | raw exit **0** | **`1402 passed in 1418.89s (0:23:38)`**. JUnit root `tests=1402 failures=0 errors=0 skipped=0`. `grep -c 'short test summary'` over the captured output = **0** |
| `rtk proxy python -m pytest --collect-only -q -p no:cacheprovider` | exit 0 | **1402 tests collected in 0.66s** — collected equals passed |
| `rtk proxy python scripts/sdle.py lint-skill` | raw exit **0** | `ok: true`, **33 checks**, `failed: []`. All 32 pre-T09 names present and passing plus `repo_config_defaults_match_documentation` |
| `rtk proxy python scripts/sdle.py constants` | exit 0 | `version_chain` **16** rows; `phase_sequence` 21; flow shapes 19/8, 20/8, 17/7, 15/6, 11/3 |
| `rtk proxy python tools/transition/validate.py` | raw exit **0** | `TRANSITION_VALID: complete=9/12 next=T09` |
| `git status --porcelain` at the end of verification | — | one ` M .claude/settings.local.json`; nothing of mine reached the repository |
| Python 3.11 | **NOT_RUN** | Only Python 3.13 is present in this environment |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN / UNKNOWN** | Nothing pushed; no outcome predicted |

The F1 `ENVIRONMENT_FLAKE` procedure was treated as VOID: a green run was
required, not explained.

---

## Future-phase leakage check

**None found.**

- **T10 (§16).** No `.claude/agents/` product subagent — the directory holds
  only the four pre-existing `sdle-transition-*` migration agents, which the
  plan's scope exclusion names as control plane. `.claude/skills/` holds `sdle`
  and `apply-sdle-transition`, both pre-existing; the product skill is still
  undivided. No `sdle-design-review` or `sdle-security-review`. Gate content
  stays in the parent — `gate-protocol.md` Step 6b displays artifact content
  before offering either option (invariant 8, invariant 4).
- **T11 (§17).** The legacy `.workflow/` rung still binds and `migrate-workflow`
  still works and still does not mutate the source (verified by a recursive
  path+content hash). `current_feature_id` still present. `SDLE_OWNED_PREFIXES`
  is unchanged and still lacks `.sdle/`, and `cmd_manifest_build`'s exclusion is
  untouched, so T04 N-7 / T05 NB-7(b) stays open. Version still v1.16 in all
  four locations; no version bump. §17's "gate omission evidence" hardening
  matrix was not pre-empted — T09 ships unit and integration coverage only.
- **Only the three named findings were adopted:** T05 NB-3 (the lint binding),
  T05 NB-4 (fail-closed `read_repo_config`) and T08 NB-3 (the README clause). I
  looked for the others and they are all still open: `hooks.py::in_dir`
  unchanged, `branch_guard` unchanged, no change to Spec Kit tier-2 discovery,
  no change to the write-fence carve-out, and the stale runtime paths in
  `phase-execution.md` and the transcripts are untouched.

---

## Test weakening / deletion check

- **Zero deletions, zero renames-away** under `tests/` across the whole
  `e1cf341..6318541` range (`git diff --diff-filter=DR`).
- **No `xfail`, no `pytest.skip(`, no `@pytest.mark.skip`** anywhere in `tests/`;
  the single `skipif` in the tree is the pre-existing POSIX-`sh` guard in
  `test_units_infra.py`, untouched.
- **Test-function counts preserved** in the two files where the plan authorised
  inversions: `test_units_baseline.py` 41 → 41, `test_units_governance.py`
  72 → 72 (parsed by AST at `e1cf341` and at HEAD). The two apparent
  disappearances are the authorised in-place renames of X1 and X6.
- `tests/conftest.py` **unchanged** — absent from the diff, so the
  anti-contradiction clause's tightest constraint held with room to spare.
- I read every changed assertion. Each is an inversion or a one-name growth of a
  **closed set**, and every closed set stayed closed:
  `governance_precondition` callers `{apply_advance, cmd_gate_approve, cmd_skip}`
  → plus `cmd_gate_omit`; `apply_advance` callers likewise; the `artifact_shas`
  writer set likewise; the `final_level` reader set likewise, with the
  *producer* assertion (`producers == {"evaluate_risk"}`) unchanged;
  `BRANCH_CRITICAL_ACTIONS` 9 → 10 with `gate omit` added to
  `CRITICAL_INVOCATIONS`. Every one of these is a change **without which the
  phase would have been weaker**, not stronger — omitting the `artifact_shas`
  row, for instance, is exactly the F2 silent regression.
- The X8 replacement and both inversions (X1, X6) retain or add a non-vacuity
  guard.
- The new `tests/test_units_gate_policy.py` (71 test functions, 363 collected
  cases) is genuine coverage, not narration: it drives the CLI for N11/N12/N13,
  compares the frozen files against `git show e1cf341:` with line endings
  normalised, and guards its own non-vacuity (`test_the_rollback_point_is_reachable`,
  `test_n5_is_not_vacuous_something_really_is_omittable_at_low`,
  `test_n3_the_inert_report_is_not_vacuous_today`).

---

## Deterministic guardrail check

- **The core refuses; it does not warn.** Every new branch raises `Refused` or
  `IntegrityError`. No new advisory string, no new "warning" path.
- **Fail-closed by construction.** `gate_requirements_for_state` returns `None`
  when the model cannot be derived, and every caller treats `None` as "nothing
  may be omitted": `apply_advance` refuses, `cmd_gate_omit` refuses,
  `gate show` reports `required: null` and `gate-protocol.md` instructs the
  orchestrator to treat `null` as required.
- **No stored requirement set.** Derived at every decision point; the state
  template, the migration chain (16 rows) and the `approvals` key set (8) are
  untouched — verified against `e1cf341` and by `lint-skill`.
- **`gate omit` has no escape hatch.** The parser takes `--gate` and nothing
  else; no `--force`, `--reason`, `--override` or environment variable.
- **Single writer.** `GATE_OMITTED_DECISION` is *assigned into* `approvals` by
  exactly one function, `cmd_gate_omit`; the other three references
  (`apply_advance`, `revalidate_recorded_omissions`, `write_completion_summary`)
  are reads.
- **No conditional lifecycle construct.** No phase was added, removed, reordered
  or made conditional; `PHASE_SEQUENCE` is still 21 and the five flows are
  element-wise unchanged. A gate requirement is a boolean over three inputs, as
  §13 requires.

---

## State / audit / evidence integrity check

- `audit verify` exits 0 with `chain_ok: true` and `matches: true` after every
  scenario driven here, including after an omission and after each refusal.
- Every refusal introduced by T09 was byte-compared on `audit.md` and left it
  identical (A8).
- An omission writes exactly one ledger entry, with `**Gate Decision:** OMITTED`,
  the artifact path, the artifact SHA and a message that explains *why* no human
  approved it — §15's gate-evidence clause satisfied for the "omitted" state.
  "required" is explainable via `gate show` / `governance gates` reasons,
  "approved" and "rejected" are unchanged, and "excepted" has no producer by
  design (ADR-006 §2.9).
- The governance record now declares `governanceVersion: "2"` and carries
  `requiredGates` / `omittableGates`; `read_governance_record` refuses an
  unrecognised version as an `IntegrityError`. A `"1"` record is still accepted.
- Evidence documents and `reviews.json` are unaffected; the review regime is
  enforced identically for `gate omit` and `gate approve`.

---

## Cross-platform / path handling check

- The changed engine code adds no `os.sep` literal, no drive-letter assumption
  and no shell invocation. `terminal_gate_key`, `gate_requirements` and
  `_policy_gate_reasons` are pure; `gate_requirements_for_state` reads through
  `Paths` properties only.
- `lint-skill`'s `no_powershell_only_cmdlets` check still passes, so the new
  prompt-layer prose introduced no PowerShell-only cmdlet.
- All byte-identity assertions in the new test file normalise `\r\n` → `\n`
  before comparing, and are guarded by `test_the_rollback_point_is_reachable` so
  they cannot pass by comparing `None` to `None`. My own comparisons used
  commit-to-commit `git diff --name-status`, which is line-ending agnostic.
- Everything was verified on Windows (win32, Python 3.13). POSIX and CI are
  UNKNOWN and no outcome is predicted.

---

## Artifact review/SHA freshness check

- `gate omit` records the artifact's SHA-256 into `artifact_shas` exactly as
  `gate approve` does — confirmed on disk after a real omission — so the omitted
  gate participates in drift detection on equal terms.
- TP-011 is not relaxed: `gate omit` refuses `review_missing` without a current
  PASS review of the exact current content (reproduced), and refuses
  `artifact_missing` when the file is gone (reproduced).
- `lint-skill` reports the new `repo_config_defaults_match_documentation` as
  passing with one examined block; the README literal now equals
  `REPO_CONFIG_DEFAULTS` and is bound both by the linter and by a suite test.
- ADR-006 is new at this commit and was read in full against the engine in this
  context; no governed-artifact SHA or review record applies to it.

---

## Findings

### Blocking

**None.**

### Non-blocking

**NB-1 — five test functions changed outside the plan's X table, and no blocker
was written.** The plan's "Existing tests affected" section says *"If a change
is needed outside this table, that is a plan defect — stop and write
`T09-blocker.md`"* and *"No other test file outside the tables above may
change"*. Two test files not named in the X table changed:
`tests/test_units_artifact_review.py` (the `artifact_shas` writer set) and
`tests/test_units_workitem_resolution.py` (`BRANCH_CRITICAL_ACTIONS` 9 → 10 and
`CRITICAL_INVOCATIONS`), plus three unlisted functions inside files that are
named (`test_the_classification_flag_no_longer_claims_to_be_advisory`,
`test_only_evaluate_risk_produces_a_final_level`,
`test_the_clause_has_exactly_one_enforcement_site`). The implementer recorded
all five as X13–X17 with rationale rather than stopping. **A23 is therefore
PARTIAL and this is a real deviation from an immutable plan.** It is
non-blocking because every one of the five is mechanically forced by the plan's
own D8 (adding `cmd_gate_omit`), every one is a one-name growth of a closed set
that stays closed, and every one is a **tightening** — leaving any of them
unchanged would have made the phase weaker, not stronger, and in the
`artifact_shas` case would have been precisely the F2 regression the plan warns
about. Nothing was deleted, skipped, xfailed or relaxed, which is the property
A23 exists to protect. **Recommendation for the orchestrator:** future plans
should carry a generic X row for "closed-set assertions that must name a newly
added command", so this class of change is authorised rather than requiring a
judgement call mid-flight.

**NB-2 — a downward re-assessment is the practical route to omitting a gate
that was required, and nothing in the plan or the prompt layer says so.**
Reproduced end to end: a GREENFIELD WorkItem assessed HIGH on
`authentication_or_authorization`, standing at `gate_design` and correctly
refused `gate_required`, was re-assessed through the real CLI with an input
declaring no signals. `governance assess` accepted it (exit 0, `finalLevel LOW`),
`gate_design` immediately became `omittable`, `gate omit` succeeded, and the run
completed. The engine's floors were never lowered — the *inputs* changed. This
is the pre-existing §12 trust model (Claude authors the risk proposal; the
engine only scores it and refuses a lowered *proposed* level), it is fully
auditable (two `governance_recorded` ledger entries with the signal sets, plus
the `gate_omitted` entry; `audit verify` exit 0), and **ADR-006 §3 explicitly
discloses it**: *"Nor does it judge whether the governance record's declared risk
signals are an accurate description of the work."* That disclosure is why this
is not blocking. What is worth naming is the asymmetry: D10's revalidation
deliberately catches LOW → HIGH re-assessment, and there is no equivalent
treatment of HIGH → LOW, which is the direction that *unlocks* an omission.
`SKILL.md` and `gate-protocol.md` tell the orchestrator to ask the engine about a
requirement but say nothing about re-assessing to change the answer.
**Recommendation for T11:** consider a distinct ledger event (or a refusal) when
a re-assessment lowers the final level below a level already recorded for the
same WorkItem, and a sentence in the prompt layer forbidding re-assessment as a
means of clearing a gate.

**NB-3 — §15's HIGH default names "documentation review", which no gate
implements.** §15's HIGH list has eight items; seven map onto existing gates or
universal mechanisms, and "documentation review" maps onto nothing — there is no
such phase in the 21-phase registry, so the requirement model cannot express it
at any level. T09 could not have added one (flow membership is T07's and the
plan's scope exclusion forbids it), and the plan does not mention the gap. Not a
weakening — nothing was removed — but §15's HIGH default is not fully realised
and no phase currently owns closing it. Should be named explicitly in T11 or
deferred on the record.

**NB-4 — pre-existing: `skip` at a gate phase appends to `audit.md` before it
refuses.** With `state["status"] == "failed"` at a gate phase, `skip` then
`skip --confirm` appends the `skipped` entry and *then* calls `apply_advance`,
which refuses `gate_not_approved`. The gate is **not** bypassed (verified: the
phase did not move), but the ledger grows by an orphan entry and `audit verify`
then exits **3** with `matches: false`. This is the B1/NB-6 shape for a refusal
`cmd_skip` reaches through `apply_advance` rather than through its own
pure-reader block. **It is not a T09 regression:** `cmd_skip` does not appear in
the `e1cf341..6318541` diff at all (26 hunks in `scripts/sdle.py`, none touching
it), and the same sequence behaves identically at the rollback point. Recorded
here because T09's own refusals now share that code path and a future phase
adding a refusal inside `apply_advance` would inherit the defect. T11 hardening
candidate.

**NB-5 — the new lint rule's non-vacuity guard is repository-wide, not
per-document.** `_check_repo_config_defaults_documented` fires its guard only
when *no* document contains a `configVersion` block. With `README.md` present
and correct, `docs/SDLE-Reference-Guide.md` could lose a block (it has none
today) or a future block could be deleted from it without the rule firing. Every
block that *is* present is still compared, so the drift the rule exists to catch
is caught. Cosmetic; noted so a later phase does not assume per-document
coverage.

**NB-6 — a cosmetically vacuous assertion in the new test file.**
`test_no_new_way_past_a_gate_was_added_to_advance_or_skip` builds
`{node.value for node in ast.walk(advance) if isinstance(node, ast.Constant) and
node.value == "approved"}` and asserts it equals `{"approved"}`. That
comprehension can only ever be `{}` or `{"approved"}`, so it cannot detect a
*new* accepted decision literal in `apply_advance` — which is the thing the
docstring claims it pins. The property is genuinely covered elsewhere (N11, N13
and N15 drive it through the CLI, and the `cmd_skip` half of the same test is
sound), so no coverage is missing; the assertion is simply weaker than it reads.

**NB-7 — a disclosed plan deviation: `write_completion_summary` changed.** D11
states *"The completion summary (E17) needs no code change"* and the plan's
file-change table does not list that function, but `all_gates_approved` moved
from the literal `True` to a derived value. It is a tightening (a run with an
omission would otherwise have claimed every gate was approved), it is declared
in checkpoints 02, 03 and 05 and in the handoff, it is covered by two tests in
opposite directions, and the Reference Guide and `gate-protocol.md` were updated
to match. Recorded as a disclosed deviation, not a defect.

---

## Final result rationale

**PASS.**

§15's danger is that a green suite proves nothing, because a weakened rule and a
correct one both pass tests written against the weakened rule. I therefore did
not rely on the suite for the governance properties. I compared the shipped
`GOVERNANCE_POLICY_BUILTIN` field by field against the one parsed out of
`git show e1cf341:scripts/sdle.py` — not against the new test's literals — and
found **zero weakenings**: no weight dropped, no floor fell or disappeared, no
threshold rose, no required-gate entry was removed. The only in-place edit is
the one §15 demands (`authentication_or_authorization` MEDIUM → HIGH), and all
nine of §15's floors are now present at or above the mandated level.

I then drove §15's exit criterion through the real CLI in scratch installs and
attacked it by every route I could construct — `gate omit`, `advance`, `skip`
with and without a forced `failed` status, a hand-written `omitted_by_policy` in
`state.json`, a policy override emptying the floors, an override lowering only
the auth floor, and a hand-edited governance record. **Every route was refused.**
The terminal gate is required in all 80 cells of the 5 × 4 × 4 cross product with
`terminal_gate` among its reasons, it is derived positionally so no override can
reach it, and the omittable set shrinks monotonically as risk rises and is empty
at HIGH, at CRITICAL and for HOTFIX at every level. Drift protection follows an
omitted gate (mutating an omitted gate's artifact raises drift), TP-011 is
unrelaxed, the artifact SHA is baselined, and every new refusal leaves `audit.md`
byte-identical with `audit verify` at exit 0.

The three judgements all hold up. The fail-closed `read_repo_config` change is
right and its test edit is a category-2 inversion that *added* a non-vacuity
guard. The lint check's absent-document skip is a principled fix, not a
relaxation — I exercised all six cases directly and the present-but-empty case
genuinely still fails. ADR-006, re-read line by line against the engine, contains
no inaccuracy I could find, names none of the 22 policy identifiers, and its §3
"Not guaranteed" paragraph is the honest disclosure that keeps NB-2
non-blocking. The document sweep found no remaining sentence that overstates
what policy controls.

The full suite was re-run here: **1402 passed, raw exit 0**, JUnit
`failures=0 errors=0 skipped=0`, `--collect-only` = 1402. `lint-skill` exit 0
with 33 checks and `failed: []`, no check removed or weakened. No T10 or T11
leakage; only the three findings the plan named were adopted. Zero test
deletions, zero relaxations, `conftest.py` untouched, the frozen happy path and
the nine transcripts absent from the diff.

Seven non-blocking findings are recorded. The two that matter are NB-1 (five
test functions changed outside an immutable plan's X table, so A23 is PARTIAL)
and NB-2 (a downward re-assessment unlocks an omission). Neither is a governance
weakening: NB-1's five changes are each a tightening mechanically forced by the
plan's own decision to add `cmd_gate_omit`, and NB-2 is the pre-existing §12
trust model, fully audited and explicitly disclosed in ADR-006 §3. Failing the
phase on either would cost one of three attempts for no governance benefit,
while the property the phase exists to protect — that design and security are
neither universally mandatory nor casually skippable — is verified to hold under
direct attack.

The verdict is PASS. T09 is COMPLETE.
