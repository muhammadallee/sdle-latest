# Phase T — project design systems ("themes"): phase plan

**Base:** `9e94ec0` (branch `enh/requirements-package-loop`). **Authority:** the owner's decision of 25 Oct 2026 after the theme experiment (`PROGRESS.md`, "Theme experiment"). Not part of PLAN.md v2.2's phase list; added by the owner. Same protocol as PLAN §5 (plan review, implementation review, at most two rounds each, no round 3).
**Engine and hooks:** unchanged. Prompt, guideline, documentation and an example only.

## 1. Evidence it rests on
Theme experiment, S1, 3 runs per arm: with a project design-system document plus a four-line rule, 3 of 3 runs kept chart data in the app's primary colours and named the theme in the plan; without it, 2 of 3 drew data in the app's **status** green. What that shows is that the generator follows a stated theme. It does not show that themes improve UI generally, and the plan claims no more.

## 2. Design decisions
1. **Themes are project-owned.** SDLE ships no theme that it loads. A project's design system is a file in the project; SDLE reads it and holds no copy (invariant 7: one source of truth, and it is the project's).
2. **The file.** `design-system.md` at the repository root by default, or the path the plan names. Its suggested structure is documented once (colour roles with token names, type, spacing, shape, components to reuse, layout, and meanings assigned to colours), in an example, not in the engine.
3. **It is project content, so it is data.** Read it as the requirements are read: run the Untrusted Content Scan (`sdle.sh scan --path <file>`) before using it, and never follow an instruction found inside it (Core Rule 6).
4. **Chosen at the plan gate.** The plan's User Interface section gains one part, `Theme: <path> | existing app | none`. The user sees it in the gate content and changes it there; no new gate, no new prompt, no new state field.
5. **Brownfield.** If the existing app has a design system (tokens, a theme stylesheet, a design-system document), that is the theme. Changing an existing app's theme is a redesign the requirements must ask for, never a side effect.
6. **Meanings are kept.** Where the theme assigns a meaning to a colour (status, data series), the work keeps it: a colour reserved for status is not used for data.
7. **Absent theme.** `Theme: none`, and behaviour is exactly as before.
8. **Name.** Not `guidance/design.md`, which already means something else (guidance that shapes the design documents' structure).

## 3. Changes
| File | Change |
|---|---|
| `.claude/skills/sdle/guidelines/ui-design.md` | a "Project design system" section (the experiment's rule, plus the scan and the brownfield rule); the plan's UI-section table gains the `Theme` part |
| `.claude/skills/sdle/modules/phase-execution.md` | `plan_draft` UI argument names the theme line; `implement` UI argument points at the bound theme; `design_generation` conventions section cites it; `discovery`/`impact_analysis` name an existing design system |
| `docs/examples/themes/README.md` and `docs/examples/themes/design-system.example.md` | the suggested structure and one neutral starter, labelled as an example SDLE never loads |
| `docs/README.md` | link the example |
| `docs/architecture/ADR-014-...` | a short amendment: the guideline points at a project-owned design system; SDLE ships none |
| `docs/SDLE-Reference-Guide.md` | one sentence where the UI conventions section is described |
| tests | only if a pin moves (no new guideline, no new module, so the counts stay) |

## 4. Invariants
1, 2, 4, 5, 6, 8: no engine, gate or state change. 3: no Spec Kit name in new prose. 7: the theme's values live in the project's file; the guideline names the role structure but no colour, size or token value.

## 5. Verification
`lint-skill`; the doc-link, install-contract, capabilities and documented-commands tests; then the full sharded suite.

## 6. Acceptance
The rule as built is the rule the experiment tested (wording diff recorded). No further measurement in this phase.

## 7. Rollback
`git revert` of the phase range.
