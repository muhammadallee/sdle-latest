# T11 checkpoint a01-05 — M5 complete

**Phase:** T11 · **Attempt:** 01 (resumed after an API-limit interruption, §24.6 —
not a verification FAIL, so the attempt is not incremented)
**Milestone:** M5 (schema, version, branch-guard fail-open)
**Status at this boundary:** M5 GREEN. Safe resume point.
**Written before:** M6 begins.

---

## 1. What was already on disk when this context resumed

M5 was **partly landed** by the interrupted context and has been preserved, not
redone. Verified against disk in this context:

| Landed before the interruption | Anchor |
|---|---|
| D13 `pending_branch_ack` in `templates/state.json` and in `branch_guard` | `branch_guard`, comment `# T11 D13: the acknowledgement was for a different checkout` |
| D13's `resume` surfacing of the field | `cmd_resume`, `"pending_branch_ack": state.get(...)` |
| D14 version bump to `1.17` in all locations + `_mig_1_16` + the `("1.16","1.17")` `MIGRATIONS` row + the `1.16 → 1.17` `VERSION_MIGRATION` row in `SKILL.md` | `CURRENT_VERSION`, `_mig_1_16` |
| F6 — `sdle.py::CURRENT_VERSION` added to `_check_version_consistency` rather than hand-edited | `_check_version_consistency` docstring "One version string, six locations" |
| The README v1.17 row, inserted **above** `**v1.16**` | `README.md` version-history table |
| X6 — `templates/state.json` pulled out of both `FROZEN` tuples and pinned instead by `test_t11_the_state_template_changed_only_as_declared` | `tests/test_units_capabilities.py` |
| N22/N23 test bodies (written, **never executed**) | `tests/test_units_transitions.py` |
| Part of X11 (`test_units_state.py`, `test_units_repo_config.py`, `test_lint_skill.py`, `test_units_gate_policy.py::test_n28_the_state_schema_did_not_move`) | those files |

`lint-skill` reports **`all 7 locations report v1.17`** — seven, not six.
`_check_version_consistency` reads the template, `sdle.py::CURRENT_VERSION`, the
`SKILL.md` frontmatter, the `SKILL.md` heading, the README title, the README
version table and the Reference Guide header.

## 2. What this context finished

### 2.1 X11 completed — and the X6-vs-X11 fork resolved without a blocker

Two tests were failing on resume, both pinning `template["workflow_version"] ==
"1.16"`. The orchestrator's brief attributed them to **X6** and instructed a
blocker if X6 did not cover them. Read against the plan, **X6 does not cover
them and X11 does**, verbatim:

> **X11** | *Any test asserting the v1.16 string or the 16-row migration chain* |
> 2 — D14 | X-GEN re-valuation to `1.17` / 17 rows

X11 is listed in M5's own scope in §4. So there is no plan defect and no
material decision: the plan authorises exactly this re-valuation, under a
different row number than the brief named. **No `T11-blocker.md` was written**,
per "do not trust the orchestrator's prose as repository truth".

Re-valued under X11 (TP-003 category 2, X-GEN, exact-equality shape kept, old
and new literals recorded, nothing relaxed to `in`/`>=`):

| File | Test | Old | New |
|---|---|---|---|
| `test_units_flow_model.py` | `test_the_state_template_carries_the_flow_field` | `"1.16"` | `"1.17"` |
| `test_units_flow_model.py` | `test_the_state_schema_did_not_move` | `"1.16"`; `"v1.16"`; `version_chain) == 16` | `"1.17"`; `"v1.17"`; `== 17` |
| `test_units_capabilities.py` | `test_n24_the_schema_did_not_move` | `"1.16"`; `len(CONSTS.version_chain) == 16`; `"v1.16"` | `"1.17"`; `== 17`; `"v1.17"` |

Every other assertion in those three tests is untouched, and each still carries
its original phase's claim: eight approval keys equal to `PHASE_TO_GATE_KEY`'s
values, `progress == "1/18"`, no `discovery`/`baseline` field, 21 registry
phases, 8 gate phases. No test was deleted.

A whole-repo sweep for `1.16` confirms every remaining occurrence in `tests/` is
either a **chain-step literal** (`"1.15->1.16"`, `"1.16->1.17"`), an X6
substitution literal, or historical prose — no current-version pin survives.

### 2.2 The N22/N23 tests were broken as written; fixed, not weakened

The interrupted context wrote them but never ran them. Six failed. All six were
**test defects, category 3 in the sense that the defect was in the new test, not
the product**; the product behaviour they describe was correct throughout:

| Defect | Fix |
|---|---|
| 11 invocations of `project.run("skip", "--reason", "x" * 20)` — `skip` has no `--reason` flag, so every one was an argparse **usage error (exit 2)** that never reached the branch guard | `project.run("skip", session=SESSION)`, matching `CRITICAL_INVOCATIONS` |
| `execution.json["branch"]` — the recorded branch lives at `execution.json["git"]["branch"]` (`recorded_branch`) | corrected |
| `BRANCH_TWO_STEP` declared and never used | turned into the parametrisation of a **new** test, below |

**New test added in this context:**
`test_n22_every_two_step_command_refuses_a_stale_acknowledgement`, parametrised
over all four commands N22 names — `skip`, `reset`, `restart --to 1`,
`implement preflight` — asserting for each: exit 1, `branch_mismatch`,
`data["acknowledged"] == "feature/b"`, `data["current"] == "feature/c"`,
`data["recorded"]` still the execution's branch, `data["action"]` the action
name, `current_phase`/`approvals`/`status` unmoved, `branch_ack_stale` in the
ledger, no `branch_mismatch_accepted`, and `audit verify` exit 0. N22 named four
commands and only `skip` had been covered.

### 2.3 TR20 — verified explicitly, and the verdict is DEFERRED

The plan states TR20 as *"FIXED as a by-product of D13 — verify explicitly; if
it does not fall out, record as DEFERRED"*. **It does not fall out.**

`branch_guard` runs ahead of the command body and cannot know whether that body
will succeed, so `branch_mismatch_accepted` still precedes a later unrelated
refusal. D13 changes *which* acknowledgement is honoured, not *when* it is
written. Evidence is now a passing test rather than an argument:
`test_tr20_the_acknowledgement_is_still_ledgered_before_a_later_refusal` drives
`advance` twice on a mismatched branch, observes the second call refuse for a
non-branch reason with `branch_mismatch_accepted` in the ledger, and asserts the
phase did not move and `audit verify` exits 0.

What D13 *does* remove is the harm T03-8 pointed at: the entry is no longer a
standing permission, because the next invocation on a different checkout is
refused. **TR20 → DEFERRED, with the residual pinned by a test so it is visible
rather than silent. ADR-008 must carry it as DEFERRED, not FIXED.**

---

## 3. Declared plan deviation — D13 audits its refusal (B2)

§5.2 **B2** says *"Every new precondition (D10, D13) is a pure reader placed
ahead of the first `append_audit`."* That is accurate for D10. **It is not
accurate for D13 as implemented, deliberately.**

`branch_guard`'s stale-acknowledgement path appends `branch_ack_stale`, re-arms
`pending_branch_ack` against the current checkout, saves state, **and then**
raises `Refused`. Three reasons this is the correct shape and a pure reader
would be worse:

1. **It is the guard's pre-existing shape, not a new one.** `branch_guard`
   already appends `branch_mismatch_guard` before refusing, and
   `test_every_branch_critical_action_refuses_on_a_mismatched_branch` pins that
   at baseline. The branch guard is the engine's one *auditing* guard, per §9's
   "branch mismatch produces explicit warning/refusal". T11 keeps that shape
   instead of inventing a second one.
2. **T03-1's defect was an *unaudited* action.** Making the new rejection a
   silent refusal would reproduce exactly the category of defect D13 exists to
   close.
3. **Without the state write the user is dead-ended.** `pending_branch_ack`
   would stay pinned to the abandoned branch and every subsequent invocation on
   the current one would refuse forever. Re-arming is what keeps D13
   fail-*closed* rather than fail-*stuck*.

B2's guarantee for the rest of the engine is unaffected: this is one named,
pre-existing exception on one guard, not a general relaxation. **The verifier
should treat this paragraph as the declared deviation, not discover it.**

---

## 4. Evidence at the M5 boundary — all re-derived in this context

| Check | Command | Result |
|---|---|---|
| The three re-valued version tests | `rtk proxy "python -m pytest tests/test_units_flow_model.py::test_the_state_template_carries_the_flow_field tests/test_units_flow_model.py::test_the_state_schema_did_not_move tests/test_units_capabilities.py::test_n24_the_schema_did_not_move -q"` | **3 passed in 0.91s**, `EXIT=0` |
| N22 + N23 | `rtk proxy "python -m pytest tests/test_units_transitions.py -q -k \|n22 or n23\|"` | **15 passed, 24 deselected in 43.07s**, `EXIT=0` |
| Transitions + WorkItem resolution (the branch-guard home file) | `rtk proxy "python -m pytest tests/test_units_transitions.py tests/test_units_workitem_resolution.py -q --tb=short"` | **138 passed in 307.20s**, `EXIT=0` |
| TR20 evidence test | `rtk proxy "python -m pytest tests/test_units_transitions.py -q -k tr20"` | **1 passed**, `EXIT=0` |
| Earlier batch (before the N22 fixes) | `tests/test_units_transitions.py tests/test_units_state.py tests/test_lint_skill.py tests/test_units_repo_config.py` | 190 passed / **6 failed** — the six N22 defects above, all now green |
| `lint-skill` | `python scripts/sdle.py lint-skill` (stdout only; `2>&1` corrupts the JSON with the human-readable stderr) | **42 checks, `failed: []`**, `version_string_consistent`: `all 7 locations report v1.17` |

Note for whoever runs the suite next: the earlier 190/6 batch predates the N22
fixes and is retained only as the record of what was found.

---

## 5. Resuming from here

**Remaining:** M6 (N1–N16) · M7 (documentation, ADR-008 with all 26 TR rows,
D16/X7/N24, TR2/3/4/6/13/14/21/26) · M8 (D15, X10 — severable).

**Findings closed so far (12):** TR1, TR7, TR9, TR10, TR11, TR12, TR16, TR17,
TR18, TR22 (M1–M4), and from M5: **TR15** (D13/N22, closed) and **TR20**
(verified → **DEFERRED**, evidenced by a test).

**Carry forward:**

- `lint-skill` is still at **42** checks. A10 requires **43** once D16 lands in
  M7. `test_n26`'s exact-set equality must gain `T11_CHECKS =
  ("documentation_set_is_present",)` at the same time (X7).
- The full suite has **not** been run end-to-end since the resume. M6 must
  finish with it.
- `tests/conftest.py` is still **unmodified**; `Project.runtime` still carries
  its `workitem is None → .workflow` branch. §7.1 permits dropping it once no
  fixture uses it, and permits adding the fixtures N1/N7/N14/N15 need.
- Recoverability unchanged: M5 is additive over a green M4.
