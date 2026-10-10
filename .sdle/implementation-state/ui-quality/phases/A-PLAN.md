# Phase A-build — phase plan

**Base commit:** `3cd3b19` (branch `enh/requirements-package-loop`; HEAD at the time of writing, 10 Oct 2026).
**Contract:** `PLAN.md` §6 Phase A rows 1–9. This file is the resume point (PLAN.md §5.1 step 1).
**Scope of this plan:** A-build only. A-measure needs decision D4 and is not started here.
**Engine and hooks:** unchanged. `scripts/sdle.py` and `.claude/hooks/` are not touched.

## 1. Reference re-verification against HEAD `3cd3b19`

Every Phase A reference in PLAN.md §6 was opened and read at HEAD. All hold; function names and headings are the anchors.

| PLAN.md reference | Found at HEAD | Result |
|---|---|---|
| `phase-execution.md` `spec_draft` `:99-109`, source-id instruction `:102` | `:99-109`; the "Source requirements" sentence is in the `speckit-specify` bullet at `:102` | holds |
| `phase-execution.md` `plan_draft` `:114-121` | `:114-121` (invocation at `:117`) | holds |
| `phase-execution.md` `tasks_draft` `:139-147` | `:139-147` (invocation at `:142`) | holds |
| `phase-execution.md` `design_generation` `:166-196`; Step A sections `:177-182`; read-for-context `:176` | holds | holds |
| `phase-execution.md` `implement` `:205`; manifest `:206-214`; loop `:216-220` | holds | holds |
| `phase-execution.md` `discovery` `:48-59`, `impact_analysis` `:61-69` | holds | holds |
| `SKILL.md` `CAPABILITY_MAP` rows `:279` (`spec_draft`), `:281`, `:284`, `:288`, `:290` | holds; `:279` is the `spec_draft` row and names only `modules/phase-execution.md` | holds |
| `guidelines/task-generation.md`, `guidelines/service-planning.md` | exist; 37 and 40 lines | holds |
| `modules/design-review.md` (assemble-evidence §1, finding list §3) | present | holds |
| `.claude/agents/sdle-design-review.md` ("What to look for") | present | holds |
| `.claude/agents/sdle-requirements-review.md` | present, **but** it answers only the checks the engine hands it and "no others" | see deviation D-A1 |
| `tests/test_units_install_contract.py:245-254` set, `:275-285` counts | `EXPECTED_SKILL_FILES` `:245-254`; the guide-count test `:275-285` uses the word `six`-style map and the phrase "`<n>` under `guidelines/`" | holds |
| `tests/test_units_gate_policy.py:1405-1411` | exact list of six guidelines `:1405-1411` | holds |
| `CLAUDE.md:57` ("six") | `CLAUDE.md:57` of the repository root of this clone | holds |
| `docs/GETTING-STARTED.md` §7 count | `:322`, "six under `guidelines/`" | holds |
| `tests/conftest.py:652-664` `MAINTENANCE_RECORDS` | `:652-664`, four entries | holds |
| `tests/test_units_capabilities.py:658` | `assert len(MAINTENANCE_RECORDS) == 4`; the docstring above says "set of four" | holds, plus docstring |
| `tests/test_units_doc_links.py:185`, `docs/README.md:104-108` | reachability test at `:185`; "Enhancement records" table in `docs/README.md` | holds |

### Surfaces found beyond PLAN.md (listed before editing, per the repository's defect-stabilisation rule)

| Surface | Disposition |
|---|---|
| `tests/test_units_capabilities.py` docstring of `test_the_restatement_search_skips_only_the_maintenance_records` says "set of four" / "All four" | update with the count |
| `docs/architecture/ADR-014-constitution-guidelines-and-precedence.md` §2 lists six guideline files | add a short amendment note (ADR-014 stays current; the list is its own derived claim) |
| `docs/architecture/architecture-memory-contracts.md` §15 tree and the CAPABILITY_MAP table (`:150-153`, `:735`) | **frozen contract** for ADR-013, written against the six-guideline set; not edited. Recorded here so a reader is not surprised |
| `SDLE-Reference-Guide.md` | no mention of `guidelines/` at all (grep); the phase 15 section `:734-736` lists app-design sections. One sentence on the conditional UI section is added there |
| `README.md` | no mention of guidelines; unchanged |

## 2. Deliverables (PLAN.md §6 Phase A rows 2–3b)

1. **New** `.claude/skills/sdle/guidelines/ui-design.md` — advisory. Spec journeys and states; plan User Interface section (impact marker, screen ids `UI-…`, reuse, viewports, test mapping, visual-concept decision); preview guidance; sizing guideline (3–5 states, 2 viewports); brownfield conventions; what is *not* claimed.
2. `phase-execution.md`: `spec_draft`, `plan_draft`, `tasks_draft`, `design_generation`, `implement`, `discovery`, `impact_analysis` blocks — each a short conditional pointer ("when the work is user-visible"), not a restatement of the guideline.
3. `SKILL.md` `CAPABILITY_MAP`: add `guidelines/ui-design.md` to `spec_draft`, `plan_draft`, `tasks_draft`, `design_generation`, `implement`.
4. `modules/design-review.md` and `.claude/agents/sdle-design-review.md`: check the conventions section against the plan's UI section.
5. `guidelines/task-generation.md` (UI test-task rule) and `guidelines/service-planning.md` (pointer).
6. Count and pin updates: `EXPECTED_SKILL_FILES`; guide count words; `test_units_gate_policy.py` list; `CLAUDE.md:57`; `docs/GETTING-STARTED.md:322`; ADR-014 note; Reference Guide sentence.

### Deviation D-A1 — `sdle-requirements-review.md` not modified

PLAN.md marks the change optional. The agent's contract is "answer every check you are given and no others", and the check list comes from the engine. Making it flag UI requirements without journeys would need a new engine check, which Phase A may not add. Left unchanged; recorded in LEDGER and PROGRESS.

## 3. Invariant check (CLAUDE.md eight)

| # | Held how |
|---|---|
| 1, 2, 5, 6, 8 | no engine, gate or state change; nothing is delegated across a gate |
| 3 | no `speckit-*` name appears in any new prose beyond what the phase blocks already carry |
| 4 | no new gate or artifact |
| 7 | the guideline states no engine constant, ordinal or threshold; its sizing numbers are labelled heuristics. Prompt files point at it rather than restating it |

## 4. Verification

`python scripts/sdle.py lint-skill`; targeted: `tests/test_units_capabilities.py`, `test_units_install_contract.py`, `test_units_gate_policy.py`, `test_lint_skill.py`, `test_units_doc_links.py`; then the **full suite in the foreground**. The baseline is R2 of PLAN.md (4190 passed, 24 skipped, ~9.5 min on Linux); this machine is Windows and the repository notes ~38 minutes, so counts are compared on counts, not duration.

## 5. Rollback

`git revert` of the phase range. Prompt-only, no persisted format.
