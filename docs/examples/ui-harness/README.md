# Example: a browser-check harness for the implementation manifest

> **Example, not product.** Verified once on a pilot Angular application (pilot baseline commit `8c2947a`) with Playwright 1.64.0 and Node 22.16.0, on Windows, against the application's dev server and a mock API. It is **not exercised by SDLE's CI**, and SDLE has no dependency on it.

SDLE runs one test command at the manifest build and records its exit code and a JUnit report. A browser check is therefore ordinary evidence: this folder shows a harness that keeps to the contract in `guidelines/ui-design.md` (shipped under `.claude/skills/sdle/`).

## Files

| File | What it is |
|---|---|
| `run-ui-checks.mjs` | The one command. Preflight, then the checks, then one JUnit report |
| `ui-harness.config.sample.json` | Where the app is, where the specs are, where the report and artifacts go |
| `example.spec.ts` | One sample check, with a case name that cites a screen id and a state |
| `accessibility.spec.ts` | One sample automated accessibility scan (axe), scoped to the screen's own element; needs `@axe-core/playwright` |

## Behaviour (what was verified)

| Situation | Result |
|---|---|
| App not serving, or browser not installed | exit **78**, no check run; a report is still written, holding one errored case named `environment preflight` |
| All checks pass | exit 0; one merged JUnit report at `junitPath`; screenshots under `outputDir/artifacts` |
| A check or the unit command fails | exit 1, with the failing case in the merged report |

The report from an earlier run is deleted first, so it can never stand in for the current one. `unitCommand` (an array: program and arguments) is optional; when set, `unitJunitPath` is required. The unit suite runs first, both suites always run, and the two reports are merged into one. A suite that writes no report with test cases is itself a failure: the merged report gets an errored case named `harness completeness` and the exit is 1.

The engine records 78 as a failed run with that exit code and the gate refuses it; telling an environment failure from a defect is the orchestrator's convention, not an engine classification.

## Use

1. Copy the three files into the project, install `@playwright/test`, and download the browser it names.
2. Add the report and artifact folders to `.gitignore` (the sample config uses `ui-test-output/`). Output left in the tracked tree changes the tree the evidence was taken from.
3. Write checks whose case names cite the plan's screen ids.
4. Give the harness to the manifest build as the one test command, and the report as `--junit`.

Everything the harness touches must be synthetic: test-only accounts, seeded data, no real personal data in a screenshot.

## The accessibility scan

`accessibility.spec.ts` runs axe on a screen at both viewports and fails on any WCAG 2 A or AA violation inside the screen's element. In the pilot it was run against four screens SDLE had generated: a text-contrast defect seeded into each was caught in **4 of 4**, and **3 of the 4 clean screens already failed** with real contrast violations that the generated functional checks had not noticed. It does not establish keyboard or screen-reader behaviour; those need their own checks.
