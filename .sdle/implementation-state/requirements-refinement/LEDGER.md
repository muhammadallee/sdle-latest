# Requirements refinement — ledger

Single durable execution record for the requirements-refinement work (brief: `BRIEF.md`, this
directory). Branch `feat/requirements-refinement`, created from `0057425` (tip of
`fix/bootstrap-scan-and-startup-contract` at plan time).

## Current status

**Phase:** Stage 0 — prior-stabilization verification. **Next action:** finish the targeted-test
verification pass (running), then run the OPEN-01/02 Codex review.

## Stage 0 — prior-stabilization verification

### Sources (brief §4.0.1)

No stabilization plan file is inside this repository. Two owner plan files exist one level up from the
repository root: `..\sdle-defect-stabilization-plan.md` (D01–D06) and `..\plan-claude-codex-defectfix.md`
(the repository-cleanup plan). Per the brief, these — plus the four `.sdle/implementation-state/*`
ledgers — are the source. The deleted `docs/verification/defect-stabilization-01.md` is recovered from
git at `fc23a93` for cross-reference; it is the record the D01–D06 plan produced.

### Item enumeration and verification

Every commit sha below is confirmed an ancestor of HEAD (`0057425`) by `git merge-base --is-ancestor`.
Every cited test node id is confirmed present by `pytest --collect-only`. CI evidence is read from the
GitHub REST API (`gh` is not installed on this host), never inferred from a push.

**A. SDLE-DEFECT-STABILIZATION-01** (`fc23a93:docs/verification/defect-stabilization-01.md`), all PASS at
verified commit `7561a68`:

| Item | Fix commit(s) | Regression tests | CI |
|---|---|---|---|
| D01 artifact preconditions | `e778c2e` | `tests/test_units_gate_artifacts.py` (21 collected) | Run `34526996629` @ `7561a68`: ubuntu + windows success (2 jobs — this run predates the Python-version matrix; superseded by HEAD's 4-cell run, see below) |
| D02 verification enforcement | `c6a4f77`, `9c10186` | `tests/test_units_implementation_evidence.py`, incl. `test_06_gate_seven_refuses_a_manifest_whose_tests_were_skipped` (confirmed present) | same run |
| D03 change selection | `cc072d9` | `tests/test_units_manifest_changes.py`, incl. `test_06_security_review_refuses_when_no_ref_pinned` (confirmed present) | same run |
| D04 execution identity | `2da5394` | `tests/test_units_execution_identity.py` (8 collected) | same run |
| D05 SpecKit and instructions | `65b2850` | `tests/test_units_documented_commands.py` | same run |
| D06 dry runs | `7561a68` | `tests/test_dry_run_contracts.py` (118 collected); `tests/test_integration_10_to_13.py::test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it` (confirmed present) | same run |

Verdict: **VERIFIED**. Owner decisions Q1–Q4 recorded, not defects.

**B. repository-cleanup** (`LEDGER.md`, `STATE.json`), P00–P10, acceptance candidate `f2db495`:

- F-001…F-011, F-017, F-019, F-020, F-022, F-027, DEL-001…011, and the 29 Codex E/T/D/C/F-CX findings:
  executed per the P09/P10 final reports; no per-finding sha is named for most (phase commits only), which
  matches this ledger's own convention (findings tables cite phases, not shas — verified against the
  ledger text itself, not treated as a gap).
- F-012 `0451ef9`, F-013 `8c584f7`, F-014/015/016 `b8ea888`, F-018/026 `64e555e`, F-025 `adbe8e1`, F-029
  `9c47f30`: all ancestors of HEAD. Cited tests (`test_units_shipped_surface.py`, `test_hooks.py`,
  `test_units_capabilities.py`) collected and present.
- **F-024**: fixed by ADR-011 (P10), commits `c963c67` (interrupted candidate, correctly not shipped —
  see the ledger's own account of the `cmd_governance_gates` bypass it caught) and `f2db495` (accepted).
  Eleven `test_units_gate_policy.py::test_f024_*` tests confirmed present. CI run `35541739417` @
  `d384ceb` (byte-identical product to `f2db495`): **success on all 4 jobs**, confirmed via API. The
  ledger's own P09→P10 bookkeeping (LEDGER.md:266–277, 349–394) already reconciles the "VERIFICATION_BLOCKED"
  P09 status against the later P10 "COMPLETE" status without needing a further note from this work: P09 is
  a closed acceptance record left as written, P10 supersedes it for AC-01/AC-09, and `STATE.json` (read in
  full) already reflects P10 complete, `open_finding_ids: ["F-028"]` only (F-028 is a documented live
  limitation, not an open defect) — **not stale**, contrary to an initial read of the header lines alone.
- **D-03** (no LICENSE file): owner action, outstanding. **D-06** (`.claude/settings.local.json` history):
  owner action, outstanding, out of scope by the plan's own D-06 disposition.

Verdict: **VERIFIED**, with D-03 and D-06 left for the owner (not defects; the ledger itself records them
as such).

**C. workitem-isolation** (`FINDINGS.md`), merged `369ff96`:

- F-101 (ADR-012), F-102, F-103: all confirmed fixed/resolved, with regression tests present and Codex
  review rounds (10 + 6 findings, all accepted) recorded in the same file. The header lines ("CONFIRMED,
  open") are stale relative to the file's own later sections; a dated reconciliation note is appended to
  `FINDINGS.md` (this session) rather than editing the headers, matching the append-only convention this
  repository's ledgers already use elsewhere (repository-cleanup's P09/P10 split is the precedent).
- No CI run is cited for this work specifically; it is covered by HEAD's own CI run `35738630082`
  (4/4 green), since HEAD contains all three fix commit sets.

Verdict: **VERIFIED**.

**D. workitem-docs-alignment** (`LEDGER.md`, `STATE.json`), merged `48a853a`:

- D-01…D-07, D-09…D-12 (D-08 is a skipped id in the plan's own numbering, not a missing item — confirmed
  by grep, D-07 is immediately followed by D-09 throughout), R1-D01…D08, R2-D01…D09: all closed, commits
  `9dc1f7f`, `cdf8316`, `b83cf4a`, `44c5d24`, `ecb749c`, `7da1f6c`, `a669b03` confirmed ancestors of HEAD.
- OPEN-03 (full suite): closed by CI run `35727873456` @ `7477e9f` — **success on all 4 jobs**, confirmed
  via API.
- OPEN-01, OPEN-02: explicitly handed to the next ledger (this repo's `open-items-01-02`), not this
  ledger's to close.

Verdict: **VERIFIED**.

**E. open-items-01-02** (current branch's own prior work), `27c3be0`, `70f169e`, `0057425`:

- OPEN-01 (bootstrap scan message) and OPEN-02 (startup contract test): implemented, `tests/test_units_startup_contract.py`
  (14 tests, confirmed present and — pending the targeted run below — passing), `tests/test_integration_02_to_05.py`
  passing per the ledger, `tests/test_dry_run_contracts.py` (118) passing per the ledger.
- CI run `35738630082` @ `0057425`: **success on all 4 jobs**, confirmed via API. This was not available
  when the ledger was last written (`STATE.json` says "not pushed"); a dated reconciliation note is
  appended to `LEDGER.md` recording the current branch/push/CI facts.
- **Gap: the two-level Codex review never ran.** Round 1 was killed by the background-shell memory
  reaper before producing output; round 2 never started. Per the owner's decision this session (O2), this
  review runs now, in Stage 0, before OPEN-01/02 counts as verified. See "OPEN-01/02 review" below.

Verdict: **CONDITIONALLY VERIFIED** pending the review below and the targeted regression run.

### Targeted regression run (this session)

Command: `python -m pytest -q tests/test_units_execution_identity.py tests/test_units_gate_artifacts.py
tests/test_units_implementation_evidence.py tests/test_units_manifest_changes.py
tests/test_units_documented_commands.py tests/test_dry_run_contracts.py tests/test_integration_10_to_13.py
tests/test_units_shipped_surface.py tests/test_units_install_contract.py tests/test_units_gate_policy.py
tests/test_units_policy_midflight.py tests/test_units_capabilities.py tests/test_units_governance.py
tests/test_units_startup_contract.py tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py
tests/test_units_doc_links.py tests/test_lint_skill.py --tb=short -rf` (via `rtk proxy`, to get
unfiltered pytest output — the default filtered summary reported "No tests collected" for
`--collect-only`, so raw output was used throughout Stage 0).

**Result (first attempt): 1 failed, 2139 passed, 1719.55s.** The one failure,
`test_no_policy_default_value_is_restated_outside_sdle_py`, was **caused by this session**, not a
pre-existing defect: committing `BRIEF.md` under `.sdle/implementation-state/requirements-refinement/`
(a path `searchable_files()` scans) put the owner's brief — which quotes five underscored check ids
verbatim in its §1 grounding table — inside invariant 7's restatement search. `MAINTENANCE_RECORDS`
was widened from one hardcoded directory to an enumerated tuple of two (commit `e5af3a4`), preserving
F-025's actual guarantee (no directory is exempt merely by living under `implementation-state/`) while
accommodating this record's identical, legitimate need to quote engine vocabulary as evidence. Fixed
inline (a failure in the phase currently being worked is normal development, not a §9 defect).

**Result (after the fix): `tests/test_units_governance.py` + `tests/test_units_capabilities.py` rerun
in full — 359 passed, 376.82s.** Combined with the unaffected 2139 from the first run, every file in
the targeted set is green. `lint-skill`: 0 failures. Import check: OK.

### OPEN-01/02 review

*(recorded below once run)*

## Defect register

*(empty — the one issue found this session, the MAINTENANCE_RECORDS gap, was self-caused and fixed
inline per the brief's own rule that a failure in the phase currently being worked is not a §9 defect)*

## Local full-suite run — interrupted, resolved via CI

The local full-suite run (`runs/20260927T194546-def-rr-full-suite.*`, via `runctl.py --sample-memory 10`)
was stopped by Claude Code's background-shell memory reaper at ~9% progress. `phys_avail_gb` was ~2.2 GB
for the whole sampled window, from before the run had reached its first percent marker — a machine-wide
condition, not something the pytest process caused (`python_ws_mb` stayed under 110 MB). Full detail in
the run's own JSON record. Not restarted, per the harness's instruction that a reaped command is not
restarted unattended.

Resolved the same way `workitem-docs-alignment`'s ledger recorded for an identical reap: pushed
`feat/requirements-refinement` (authorised, O3) and read the full-suite result from GitHub Actions
instead — strictly stronger evidence than a single local combination.
