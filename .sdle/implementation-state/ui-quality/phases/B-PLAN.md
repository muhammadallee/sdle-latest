# Phase B — phase plan (written after the build; see the deviation)

**Base:** `863bcfb` (branch `enh/requirements-package-loop`). **Contract:** PLAN.md §6 Phase B rows 1–9.
**Engine and hooks:** unchanged. Prompt, guideline, documentation, an example and test pins only.

## Deviation from PLAN §5.1
The protocol puts the phase plan and its Codex plan review before implementation. This phase was built first, on the owner's "go ahead with (a)", and the plan is written from the diff. The plan review and the implementation review are therefore **one Codex round** over both, and a second round runs under the usual trigger. Recorded as an Owner-attention row.

## 1. References re-verified at `863bcfb`
| PLAN reference | Found | Result |
|---|---|---|
| `run_tests` `sdle.py:18477-18521`: no shell, exit code recorded, `FAILED` for a nonzero exit | `18477-18521`; command run with `subprocess.run`, status `FAILED` | holds |
| `cmd_manifest_build` `:18914-19082`; `--junit` hashed and parsed; `manifest_junit_missing` | holds; `junit` resolved with `safe_repo_path` against the project root | holds |
| `EVIDENCE_STATUS_CHANGED = "invalid_changed_during_run"` `:18821` | holds | holds |
| gate refusal `tests_not_passed` `:17172` | holds | holds |
| `phase-execution.md` `implement` manifest paragraph `:206-214` | the manifest, test-command, junit and report paragraphs; the new bullet sits before "Report the `secrets` and `tests` fields" | holds |
| `LOOP_INVENTORY_MAX` `:15996` | present; the guideline does **not** restate the number (invariant 7) | holds |
| `tests/test_units_tree_digest.py`, `tests/test_units_implementation_evidence.py` helpers (`ready`, `to_gate`, `approve`, `evidence_of`) | present | holds |

## 2. Deliverables
1. `guidelines/ui-design.md`: the harness contract (eleven rules, advisory) and the exit-78 convention.
2. `phase-execution.md` `implement`: one bullet for user-visible work with browser checks.
3. `docs/examples/ui-harness/`: `run-ui-checks.mjs`, `ui-harness.config.sample.json`, `example.spec.ts`, README; linked from `docs/README.md`.
4. Three pins in `tests/test_units_tree_digest.py`: (b1) a harness writing its report and screenshots to ignored paths gives valid evidence and approves; (b2) exit 78 is recorded as `FAILED` with the code and the gate refuses `tests_not_passed`; (b3) output left in an unignored folder gives `invalid_changed_during_run`.

## 3. Acceptance (PLAN row 4), what was and was not done
| Item | Status |
|---|---|
| Harness exercised on a real app: preflight 78, pass 0, failing check 1, JUnit with screen-id names | done once on the pilot Angular app (Playwright 1.64.0, Node 22.16.0, Windows) |
| 5 seeded objective defects in A's experiment implementations, detection count | **not done**: needs checks written per implementation |
| Five clean reruns, suite wall-clock against the timeout | **not done** |
| Harness run once through `manifest build` inside a full SDLE run | **not done** |

The go/no-go (PLAN row 9: at least 4 of 5 seeded defect classes detected, no flaky reruns) is therefore **not evaluated**; B is `built, unmeasured`.

## 4. Verification
`lint-skill` ok. Full suite, 18 shards, **4218 passed, 3 skipped, 0 failed** (`runs/b-full-*.json`). Pins: `-k test_b` 3 passed.

## 5. Rollback
`git revert` of the phase range. Nothing persisted in a new format; the example is a folder.
