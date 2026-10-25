# Example: a project design system

> **Example, not product.** SDLE ships no theme and loads nothing from this folder. A project keeps its own design system in a file, by default `design-system.md` at the repository root, and the plan names it on a `Theme:` line. The rules for how SDLE uses it are in `guidelines/ui-design.md` ("A project design system"), under `.claude/skills/sdle/`.

## Why a file

In a small pilot, a screen generated without one drew its chart data in the app's **status** green; with a design-system file that said status colours are not data colours, three runs out of three kept the chart in the app's primary colours. A file states the conventions once, where the generator, the design review and a person can all read them.

## Suggested structure

[`design-system.example.md`](design-system.example.md) is a neutral starter. Replace every value with the project's own. The parts that matter most:

| Part | What it says |
|---|---|
| Colour roles | each role, the token that holds it, and what it is for |
| Meanings | colours with a fixed meaning (status) and what data visualisation uses instead |
| Type, spacing, shape | the scales, and that no other values are used |
| Components to reuse | the shared components for lists, states and the page frame |
| Layout | breakpoints and how content reflows |

## How SDLE treats it

- It is project content: scanned before use, and never obeyed as instructions.
- It ranks below the requirements, the constitution and the architecture decisions, and above SDLE's guidelines.
- Its content is not protected by drift detection after the plan gate; the orchestrator re-checks its hash before design and implementation and asks you if it changed.
- For an existing application, its existing design system is the theme; changing it is a redesign the requirements must ask for.
