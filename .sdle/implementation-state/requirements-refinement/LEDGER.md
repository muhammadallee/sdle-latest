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

Format: id, source, description, reproduction, affected surfaces, dependencies, status, branch,
commits, tests (§9). The MAINTENANCE_RECORDS gap is not listed here — self-caused, fixed inline, per
the brief's own rule that a failure in the phase currently being worked is not a §9 defect.

### DEF-RR-006 — no path containment on several CLI path arguments (OPEN, out of scope)

- **Source:** Stage 0, third targeted-verification pass of the OPEN-01/02 fix (finding V3-04,
  `runs/20260928T031813-round2-codex-open-items-verify3.a1.review.json`).
- **Description:** `cmd_governance_assess`'s `--input`, `cmd_discovery_assess`'s `--input`, `cmd_sha`'s
  path argument, and `cmd_artifact_record`'s `--path` each join or open a user-supplied path with no
  containment check — no rejection of absolute paths, no rejection of `../` traversal, no symlink-escape
  check. `scripts/sdle.py`: `cmd_governance_assess` `target = Path(args.input)` / `target = paths.project_root
  / args.input` at lines 5436/5438; `cmd_discovery_assess`, the identical pattern at lines 6103/6105;
  `cmd_artifact_record` at `cmd_artifact_record` (line 9192); `cmd_sha` (line 12083).
- **Reproduction:** In a bound, otherwise-ordinary WorkItem, `sdle.sh governance assess --input
  ../outside-project/secret.json` (a file outside `project_root`) is read and its content validated —
  refused only for missing quality-check keys (`quality_incomplete`), never for the path leaving the
  repository. Confirmed live against `3bd64fc`.
- **Affected surfaces:** `cmd_governance_assess`, `cmd_discovery_assess`, `cmd_sha`, `cmd_artifact_record`
  — none of the DEF-RR-001..005 or later fixes touch any of these four functions.
- **Dependencies:** None. Independent of `safe_repo_path`/`_lexically_safe_path`, which this defect's own
  fix would presumably reuse, but nothing here depends on this session's other work to be fixed or to be
  reproduced.
- **Status:** OPEN. Owner decision (this session, 2026-09-28): record only, triage as its own piece of
  work — pre-existing (predates this entire body of work; `cmd_governance_assess` is original-engine
  code), and outside OPEN-01/02's mapped impact surface (the untrusted-content scan and its
  acknowledgement mechanism), so it is recorded with a reproduction and left unfixed in this change, per
  the brief's own defect-scoping rule (C8/§9: a pre-existing defect *outside* the impact surface is
  recorded, not fixed here).
- **Branch / commits:** None — not fixed in this change.
- **Tests:** None added — recorded, not regression-tested, since it is not being fixed here.

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

## Full suite — PASS, on CI

Two attempts: run `36346009675` @ `fd51a5c` failed all four cells on
`test_units_governance.py::test_no_policy_default_value_is_restated_outside_sdle_py` and
`test_units_discovery.py::test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py`, both flagging
`.sdle/implementation-state/open-items-01-02/runs/20260927T182716-p08-codex-open-items-round1.a1.events.jsonl`
(diagnosed via `check-runs/<id>/annotations`, since raw job-log download needs admin rights this token
does not have). Fixed by widening `MAINTENANCE_RECORDS` a third time (commit `84925f2`) — confirmed not
platform-specific: all four cells failed identically before the fix.

Run [36347512584](https://github.com/muhammadallee/sdle-latest/actions/runs/36347512584) @ `84925f2`:

| job | conclusion |
|---|---|
| ubuntu-latest / Python 3.11 | success |
| ubuntu-latest / Python 3.13 | success |
| windows-latest / Python 3.11 | success |
| windows-latest / Python 3.13 | success |

This satisfies the brief's F12 ("CI passed means all four cells passed") and closes the local
full-suite run's interruption above — CI ran it (plus `lint-skill`) at `84925f2`, which contains every
DEF-RR-001..005 and MAINTENANCE_RECORDS commit.

## Stage 0 — verdict

**VERIFIED.** All five prior-stabilization ledgers check out (D01–D06, repository-cleanup,
workitem-isolation, workitem-docs-alignment, open-items-01-02 — the last conditional on the review and
fix above, now both done). Owner decisions (D-03, D-06, F-028, F-103) left with the owner, not defects.
Two reconciliation notes appended. Five defects (DEF-RR-001..005) found genuinely open by the missing
Codex review, fixed under §9, reviewed locally and on CI. Two further defects (the MAINTENANCE_RECORDS
gaps) were self-caused by this session's own evidence-writing and fixed inline, per the brief's own rule
that a failure in the phase currently being worked is not a §9 defect.

Next: Level 2 Codex review of the DEF-RR-001..005 fix (round 2 of the OPEN-01/02 review), then Stage 1.

## OPEN-01/02 — full closure

Both formal review rounds plus one targeted verification pass are complete:

| Stage | Result |
|---|---|
| Round 1 (Codex, candidate `0057425`) | 9 findings; all dispositioned (`round1.reply.md`); 5 registered as DEF-RR-001..005 |
| Owner decision | Shape (a): re-check at `governance assess` |
| DEF-RR-001..005 fix | New pre-init acknowledgement record, `accept-content --path`, the new `governance_content_unacknowledged` refusal, and five corrected surfaces (hook, `sdle-start.md`, dry-run 05, Reference Guide, GETTING-STARTED) |
| Round 2 (Codex, candidate `75187b6`, product-identical to the `6b6c1e6` the prompt named) | 4 dispositions REVISED, 4 new findings (R2-D01..D04); all fixed (`round2.dispositions.md`) — includes a real regression (bare `accept-content` silently stopped satisfying the new check) and a TOCTOU gap, both caught only because a second round ran |
| Targeted verification of the round-2 fix | 5 more findings (V-01..V-05), all fixed — a second, deeper TOCTOU the first fix missed, a missing-file edge case, a duplicate-audit bug, an atomicity-ordering bug, and an incomplete refusal-attribution list |
| CI (all four cells) | `36347512584` (round-2 fix) → `36362088912` (V-01..V-05 fix, failed on a self-caused historical-narration violation) → `36363773501` (fixed) — **success on all four cells** |

Every finding across three passes was verified against source or the live CLI before being accepted —
never taken on Codex's word, and two of the three passes found something the previous one missed. No
disagreement ever needed the owner beyond the one shape decision already made. OPEN-01 and OPEN-02 are
both genuinely closed, not merely tested-green.

## Stage 0 — final verdict

**VERIFIED.** All five prior-stabilization items check out; OPEN-01/02 specifically required real
engine, hook, prompt, doc and test work — five DEF-RR items, a real regression, two TOCTOU gaps, three
smaller bugs — none of which the original round-1 fix alone would have caught. Proceeding to Stage 1.

## Correction — 2026-09-28

The "Stage 0 — final verdict: VERIFIED" and "OPEN-01/02 — full closure" sections above were premature.
An independent second-look review (not a third formal Codex round — a self-review before committing to
that verdict) found six more real gaps in the targeted-verification fix itself, including a vacuous test
(V-01's own regression test passed against the pre-fix commit too — confirmed by running it there) and a
store that silently dropped a human decision instead of being append-only. All six fixed, verified
locally (461 + 190 tests), pushed at `2ef73de`. This is now "fixes applied, CI pending" — not verified —
until CI confirms and, per the review protocol, one narrow targeted Codex verification of this diff runs.
Nothing above is rewritten; this correction is appended, matching this ledger's own convention.

## OPEN-01/02 — closure, final (2026-09-28)

CI: `36374476221` @ `3bd64fc` — success on all four cells (the commit carrying V3-01/V3-03's fixes, the
last substantive change to this fix). Full arc, honestly stated this time — the `ee29b54` premature
verdict is not repeated: four verification passes ran (2 formal Codex rounds + 3 targeted follow-ups),
and each of the first three found genuine defects the previous pass missed. The pattern stopped only
when a targeted pass's own `closure_assessment` recommended owner escalation rather than another pass,
per the stopping rule this session adopted in advance of running it.

Fifteen distinct findings fixed and regression-tested across the four passes (DEF-RR-001..005, R2-D01..
04, V-01..05, V2-01..05, V3-01, V3-03), every fix's test confirmed red against the commit immediately
before its own fix. One item (V3-02) is a documented, engine-wide limitation — the code change Codex
itself suggested would not have closed it, explained in `safe_repo_path`'s own docstring. One item
(DEF-RR-006 / V3-04) is a real, pre-existing, out-of-scope finding, recorded in the defect register
above with a live reproduction, left unfixed here on the owner's explicit decision (2026-09-28).

**Owner decision (2026-09-28):** OPEN-01/02 is sufficiently closed to proceed to Stage 1. Recorded here
as the basis for that decision, not asserted independently by this session.

## Stage 0 — final verdict

**VERIFIED**, on the owner's confirmation above, following CI success on the actual final commit
(`36374476221` @ `3bd64fc`) — not asserted ahead of either, this time. Proceeding to Stage 1.

## Stage 1 — evaluation corpus (2026-09-28)

Built `tests/fixtures/requirements-quality/`: `clean-baseline.md` plus one `defect-<check-id>.md` per
of the twelve quality-check ids, each a ~55-60 line "Link Shortener Service" requirements document.
Labels (`labels.json`, the expected failing check ids per document) are kept outside the working tree
per this session's own discipline, so a subagent with Glob/Read cannot see them.

**Two live assessor pilot runs against the pre-fix corpus, at commit `d3d8794`, found two authorial bugs
before the corpus was trusted:**

1. `clean-baseline.md` run 1 of 3 was flagged `contradictions: FAIL` by a real fresh-context assessor:
   the shared Constraints sentence "Must authenticate every request against the existing internal SSO
   (SAML), no separate login." genuinely conflicts with the Security section's "redirection itself is
   unauthenticated" — present verbatim in 12 of 13 documents. Fixed by scoping the sentence to
   management-API requests and naming the redirect exception explicitly, in all 12 affected documents.
2. `defect-problem_statement.md` run 1 of 3 correctly flagged `problem_statement: FAIL` (the intended
   defect) but also flagged `ambiguity: FAIL` on "under normal load" in the latency NFR — present in 11
   of 13 documents (the twelfth, `defect-ambiguity.md`, uses vague load language deliberately as its own
   seeded defect and is untouched). Fixed by replacing the qualifier with a quantified figure ("at up to
   200 redirects per second") everywhere except that one document.

Both pilot runs are **discarded** — they assessed pre-fix document text and are not comparable to the
corrected corpus. Neither counts toward the 13×3 measurement plan.

**Two further defects found by self-review (not a live run) before any further dispatch, on the same
"authorial mistake in the shared template, not the labelled signal" standard as the two above:**

3. Every document's AC-2 specified an HTTP 301 (permanent, cacheable) redirect while also requiring
   `click_count` to increment and `AC-3` to require a live 410 on an expired link — a permanent redirect
   cached by the client after the first visit would make both unreachable. Fixed by adding
   `Cache-Control: no-store` to AC-2's redirect, in all 13 documents (AC-2 is otherwise absent only from
   `defect-acceptance_criteria.md`, whose seeded defect is precisely that AC-2 does not exist).
4. Every document's Constraints section claimed "expiry uses a database TTL" while running on Postgres
   14, which has no native row-TTL/auto-expiry feature, and while the Data Model's `expires_at` column
   and AC-3's 410-on-expired-link both presuppose the row still exists after expiry (a TTL auto-delete
   would make it a 404, not a 410). Fixed by rewording to read-time comparison against `expires_at`,
   with expired rows explicitly retained, in all 13 documents.
5. `defect-dependencies.md`'s Constraints line read "...using some shared infrastructure" — the word
   "some" is on the lint's vague-term list (§3.3), so this incidentally lint-flagged `ambiguity` on top
   of the document's actual seeded defect (a missing Dependencies section), which `labels.json` does not
   list. Fixed by naming the dependency concretely ("the shared Postgres instance"), matching every
   other document's Constraints wording.

**Verification after all five fixes**, against the corrected corpus (committed `9ec6d4a`):
- The lint prototype (`.sdle/implementation-state/requirements-refinement/lint-prototype.py`) produces
  `[]` on `clean-baseline.md` and on every document whose seeded defect the lint floor does not cover
  (§3.3 only floors `blocking_unknowns`, `ambiguity`, `acceptance_criteria`, `out_of_scope`, `nfrs` and
  duplicate-id `contradictions` — never `problem_statement`, `scope`, `constraints`,
  `security_data_implications`, `compatibility` or `dependencies`, so those six documents correctly lint
  clean even though their assessor-level defect is real). `check_missing_sections` only checking for
  the Acceptance and Out of Scope sections (not Purpose/Scope/Constraints) was checked against §3.3's
  text and is spec-correct, not a bug — those three sections' absence is a semantic (`problem_statement`
  / `scope` / `constraints`) finding, never a lint one.
- All 13 documents re-verified clean under `sdle.scan_text()` (the injection-pattern scanner).
- `tests/fixtures/` is outside `searchable_files()`'s scan roots (`conftest.py:586`), so the corpus needs
  no `MAINTENANCE_RECORDS` entry; the two restatement-guard tests
  (`test_no_policy_default_value_is_restated_outside_sdle_py`,
  `test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py`) and
  `test_the_restatement_search_skips_only_the_maintenance_records` all pass unchanged.

Corpus and the `sdle-requirements-review` assessor prompt draft committed at `9ec6d4a`, so every
forthcoming assessor run can cite the exact document SHA it assessed. Next: pilot `clean-baseline.md`
×3 as a gate before the remaining 36 dispatches, judging any recurring finding on its own merits rather
than editing the corpus until an assessor says PASS (per this session's own "converge on evidence, not
verdict" discipline, restated by the advisor for this exact step).

## Stage 1 — corpus measurement results (2026-09-28)

Gate passed: 3 pilot runs on the corrected `clean-baseline.md` came back 2/3 fully clean, 1/3 with a
single non-blocking `security_data_implications` FAIL (a defensible per-resource-authorization
judgment call, not a corpus defect — kept as data, not chased away, per the advisor's explicit
instruction). Proceeded to the remaining 12 documents times 3 runs = 36 dispatches, all against corpus
commit `9ec6d4a`, each dispatch prompt containing only the document text (no filename, no check-id
hint) with an explicit "use no tools" instruction, capped at 4 concurrent Agent calls at a time. All 39
raw results are saved under `runs/assessor-<check-id>-run<n>.json`, each citing the document's blob SHA.

### Assessor precision/recall per check (39 runs total: 13 documents times 3 runs)

| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 3 | 0 | 3 | 0 | 0.00 | undefined, no positive predictions |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 6 | 6 | 0 | 3 | 1.00 | 0.67 |
| contradictions | 3 | 3 | 0 | 2 | 1.00 | 0.60 |
| constraints | 3 | 0 | 3 | 0 | 0.00 | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 2 | 1 | 1 | 0.67 | 0.67 |
| compatibility | 3 | 0 | 3 | 0 | 0.00 | undefined |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 1 | 1.00 | 0.75 |

`ambiguity` and `nfrs` each have 6 positive instances because `labels.json` labels both
`defect-ambiguity.md` and `defect-nfrs.md` for both checks — the vague-NFR defect naturally trips both,
noted in `labels.json`'s own `_notes` before any run occurred.

### The headline finding: a systemic recall gap on whole-section absence

Four checks were missed unanimously, 3 of 3, on every single run of their labeled document: `scope`,
`compatibility`, `constraints`, `dependencies`. In every one of these four cases the seeded defect is
the same shape: the entire relevant section (or, for `scope`, the entire "In scope:" list) is absent
from the document, with no other section pointing at or alluding to it. The assessor consistently read
the surrounding context (Data Model, Dependencies mentioning SSO/Postgres, Acceptance criteria, the
Purpose paragraph) as sufficient and passed the check, rather than noticing the structural absence.

This contrasts sharply with `out_of_scope` (3/3 caught) and `problem_statement` (3/3 caught), which are
also whole-content-absence defects but differ in one respect: `out_of_scope`'s document still has an
"In scope:" list immediately above where "Out of scope:" should be, giving the assessor a structural
cue (an unpaired sibling) to notice the gap; `problem_statement`'s document opens cold on "## Scope"
with no introduction at all, which is a much louder signal than a missing later section. The
`security_data_implications` document is the clearest confirming case: this session's own earlier
wording fix (scoping the SSO-authentication constraint) added the sentence "Redirect requests are the
one exception, per Security and Data Handling below" to every document's Constraints section, and in
that document specifically, that phrase is a dangling cross-reference to a section that does not
exist. 2 of 3 runs caught the defect specifically by following that broken reference; the third run,
which read the document without fixating on the cross-reference, missed it. That is a real, unplanned
but informative interaction between an earlier corpus fix and a seeded defect, not a flaw in either.

Conclusion for the assessor design (Stage 3 relevance): the LLM assessor is reliable at catching
textual problems (contradictions, vagueness, unmeasured NFRs, weak acceptance criteria) but has near
zero recall for structural absence when nothing else in the document points at the missing content. A
section-presence check for the five section-shaped quality checks (`out_of_scope`, `constraints`,
`compatibility`, `dependencies`, `security_data_implications`) would be cheap, high-precision,
deterministic, and would close exactly this gap — worth flagging as a candidate lint rule addition for
a later revision of §3.3, separate from and additional to the six rules already specified there (which
do not cover this gap, since §3.3 explicitly scopes "missing sections the checks presuppose" to only
`acceptance_criteria` and `out_of_scope`).

### Agreement rate across the 3 runs per document (full 12-key vector, identical bytes)

9 of 13 documents (69%) produced byte-identical verdict vectors across all three fresh-context runs.
The 4 that did not:

- `clean-baseline.md`: 1/3 runs added an unlabeled `security_data_implications` FAIL (a defensible
  authorization-scoping judgment call).
- `defect-blocking_unknowns.md`: 2/3 runs added an unlabeled `contradictions` FAIL (the HTTP-301
  caching-vs-click-tracking concern this session partially mitigated with `Cache-Control: no-store`,
  which 2 of 3 readers judged an insufficient guarantee against caching bots).
- `defect-security_data_implications.md`: split 2/1 on the labeled `security_data_implications` FAIL
  itself, described above.
- `defect-acceptance_criteria.md` (not a disagreement, but worth noting): all 3 runs unanimously added
  an unlabeled `ambiguity` FAIL alongside the labeled `acceptance_criteria` FAIL — a natural, expected
  overlap, same pattern as `labels.json`'s own documented ambiguity/nfrs overlap.

This is the honest measurement of `quality_verdict_flip`'s real-world trigger rate on unchanged text:
roughly 1 in 3 documents produces some inter-run variance, concentrated in borderline judgment calls
(residual-risk framing, caching semantics) rather than in the clearly-labeled primary defects, which
were never missed across all three runs of any document where the assessor caught them at all — recall
failures were unanimous misses (0/3), not split votes, for every check that had a miss.

### Lint prototype precision/recall (deterministic, one measurement per document, not three)

Re-run fresh against the corrected corpus. Findings (rule-level, mapped to check ids per §3.3):

clean-baseline.md: none. defect-acceptance_criteria.md: acceptance_criteria. defect-ambiguity.md:
ambiguity, nfrs. defect-blocking_unknowns.md: blocking_unknowns. defect-compatibility.md: none.
defect-constraints.md: none. defect-contradictions.md: none. defect-dependencies.md: none.
defect-nfrs.md: ambiguity (not nfrs — see below). defect-out_of_scope.md: out_of_scope.
defect-problem_statement.md: none. defect-scope.md: none. defect-security_data_implications.md: none.

For the six checks §3.3 designs the lint to cover: `blocking_unknowns` 1/1, `out_of_scope` 1/1,
`acceptance_criteria` 1/1 and `ambiguity` 2/2 are all perfect (precision 1.0, recall 1.0, zero false
positives on any of the 13 documents including the clean baseline — the floor-eligibility requirement
in §3.3 is met by all four). `nfrs` is 1/2 (recall 0.5): `check_quant_nfrs_without_measure` correctly
fires on `defect-ambiguity.md`'s NFR wording but not on `defect-nfrs.md`'s ("Redirects must be fast
enough that users do not notice any delay" / "handle a high volume... without degrading") — the
`QUANT_ATTR` keyword regex apparently does not match this exact phrasing while the vague-terms list
does, so the document is floored via `ambiguity` but not via `nfrs` itself. This is a real gap in the
`nfrs` rule's keyword coverage, worth a follow-up fixture and regex tightening in Stage 3 rather than a
blast-radius concern (advisory-only status means this gap costs nothing today). The sixth lint rule
(duplicate ids to `contradictions`) has no positive fixture in this corpus and is untested here — a gap
in the corpus, not in the rule; a duplicate-id fixture pair should be added before Stage 3 uses this
corpus as the lint's regression suite.

Lint's zero false-positive rate on `clean-baseline.md` and on every document whose seeded defect it
does not target (the six checks it does not attempt) confirms the §3.3 floor-eligibility requirement
in the Option-3/D7 corpus this design was measured against.

Discarded: the 2 pilot runs against pre-fix document text (`clean-baseline.md` run 1,
`defect-problem_statement.md` run 1, both from before commit `9ec6d4a`) are not part of the above
tables — they assessed stale bytes and are superseded by the clean-baseline gate's 3 fresh runs and
`defect-problem_statement.md`'s 3 runs recorded above.

## Stage 1 — corpus measurement, adjudication pass (2026-09-28)

Advisor review of the 39-run measurement above found the "0.00 recall on 4 checks" headline needed
checking against `assessor-prompt-draft.md`'s own check definitions, not against `labels.json` alone,
and that two of this session's own earlier corpus edits had bled adjacent content into the affected
documents, potentially inflating or deflating specific findings:

1. `defect-dependencies.md`: the same-session fix that replaced its deliberately vague "some shared
   infrastructure" with a concretely-named dependency (applied to fix an incidental lint/ambiguity
   trigger) had incidentally strengthened the document's own dependency-naming and undermined its
   seeded defect. Reverted to the original vague wording; the ambiguity trigger is accepted and the
   document dual-labeled (`dependencies`, `ambiguity`), matching the existing ambiguity/nfrs overlap
   pattern already in `labels.json`.
2. `defect-security_data_implications.md`: an earlier corpus-wide wording fix (the auth/redirect
   contradiction fix, applied uniformly across all 13 documents) had added "Redirect requests are the
   one exception, per Security and Data Handling below" to this document's Constraints section — a
   dangling cross-reference to a section this document deliberately omits, an unintended structural cue
   pointing straight at the gap. Removed; the sentence now ends at "...no separate login."
3. `defect-constraints.md` / `defect-compatibility.md`: each document's Dependencies section carried a
   clause ("version already pinned by platform team" / "no schema changes to other services' tables")
   reading as compatibility- or constraint-flavored detail once the document's own dedicated section for
   that check is removed. Trimmed to bare dependency names (still enough to satisfy each document's
   own dependencies check, which is not its seeded defect there).
4. `defect-acceptance_criteria.md`'s vague replacement text ("The feature is done when it works well and
   users are satisfied with how it behaves") meets `ambiguity`'s own definition (vague, unmeasurable
   normative language). All 3 original runs correctly caught this alongside the labeled
   `acceptance_criteria` FAIL — a label gap, not an assessor false positive. Relabeled dual
   (`acceptance_criteria`, `ambiguity`).
5. `defect-scope.md` was not re-seeded: the Purpose paragraph and the four AC-* criteria (both
   required elsewhere for `problem_statement`/`acceptance_criteria` reasons, and shared boilerplate
   across the corpus) already describe what is being built in concrete enough terms that a reasonable
   reader could argue `scope`'s own definition ("states what is being built, concretely enough to bound
   the work") is satisfied without a dedicated "In scope:" list. Stripping that content to force a
   cleaner scope-only defect would corrupt this document's non-defects on two other checks. Any
   assessor PASS on this document's `scope` check is recorded as a contested, defensible read, not
   folded into the clean-recall-failure count below.

All four edited documents re-verified clean under `sdle.scan_text()` and the lint prototype, committed
at `eefc661`. The four edited documents (`dependencies`, `security_data_implications`, `constraints`,
`compatibility`) were then re-dispatched, 3 fresh-context runs each (12 new dispatches), against this
corrected text. The prior 3 runs for each are kept on disk, renamed `*-superseded.json`, not deleted —
this ledger entry is the record of why they no longer count.

Provenance note: every run JSON's `dispatched_at` field is a placeholder ("00:00:00Z" or "not
recorded") — actual per-dispatch wall-clock times were not captured during either measurement pass.
Treat the field as absent, not as a real timestamp; nothing in this session's conclusions depends on it.

### Result: the headline finding survives, refined

- `dependencies`: confirmed clean 0/3 on the re-verified document (previously contaminated by this
  session's own dependencies-naming mistake — now a genuine, uncontaminated miss). `ambiguity` correctly
  caught 3/3 as expected from the dual-label.
- `constraints`: confirmed clean 0/3, unaffected by trimming the adjacent Dependencies detail. One
  run (3) additionally caught an unlabeled `contradictions` FAIL — see below.
- `compatibility`: confirmed clean 0/3, unaffected by trimming the adjacent Dependencies detail. The
  assessor still appears to credit AC-2's HTTP-301 mention (shared boilerplate present in every
  document, not removable without corrupting `acceptance_criteria`) as partial compatibility coverage.
- `security_data_implications`: recall fell from the original 0.67 (2/3) to 0.33 (1/3) once the
  dangling cross-reference was removed — direct confirmation that the cue was inflating detection, and
  the true difficulty of this document's seeded defect (a wholly absent section with no remaining
  pointer to it) is closer to the `compatibility`/`constraints`/`dependencies` pattern than the original
  number suggested. The one catch (run 2) found the defect via a different, legitimate angle
  (authorization/ownership gap) than the intended reason (section absence) — both count as the check
  correctly failing.
- `scope`: left at the original 0/3, but now flagged contested rather than confirmed per point 5
  above — do not cite this as a clean recall failure without noting the caveat.

Net: three of the four originally-flagged checks (`compatibility`, `constraints`, `dependencies`) are
now more rigorously confirmed misses, not artifacts of corpus construction. `security_data_implications`
turned out worse than first measured, not better. Only `scope` remains genuinely unresolved. The
headline conclusion in the prior section — the assessor has near-zero recall for structural absence when
nothing else in the document points at the gap, and reliably catches everything else — stands,
strengthened rather than weakened by this adjudication pass.

### Adjudicated precision/recall table (supersedes the table in the prior section)

| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 3 | 0 | 3 | 0 | 0.00 (contested, not re-tested) | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 3 | 0 | 3 | 0 | 0.00 | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 1 | 2 | 1 | 0.33 | 0.50 |
| compatibility | 3 | 0 | 3 | 0 | 0.00 | undefined |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 1 | 1.00 | 0.75 |

`ambiguity`'s positive-instance count grew from 6 to 12 (adding `defect-acceptance_criteria.md` and
`defect-dependencies.md` per points 1 and 4 above), all 12 caught, and its 3 original false positives
(all from `defect-acceptance_criteria.md`) are now correctly counted as true positives — precision rose
to 1.00. `contradictions`'s false-positive count rose from 2 to 3 (the new `defect-constraints.md` run 3
catch), precision fell to 0.50.

### Agreement rate, updated

8 of 13 documents (62%, down from the original 69%) now produce byte-identical 12-key verdict vectors
across all 3 fresh runs. `defect-constraints.md` moved from agreeing to disagreeing (run 3's unlabeled
contradictions catch); `defect-dependencies.md` and `defect-compatibility.md` remain agreeing (each
unanimous across their 3 re-verified runs); `defect-security_data_implications.md` remains disagreeing.

### A secondary, unplanned finding: the AC-2 caching fix did not fully resolve its own tension

This session's earlier fix for the 301-caching-vs-click-tracking concern (found during the original
clean-baseline pilot, the "Stage 1 — evaluation corpus" section above) added `Cache-Control: no-store`
to AC-2 rather than changing the redirect's status code, to preserve the Compatibility section's claim
that existing bots see the same 301 they always have. `defect-constraints.md` run 3 shows this did not
fully resolve the underlying tension — it relocated it into an explicit textual contradiction between
the Compatibility section (301, cached, "work exactly as they do") and AC-2 (301, `no-store`, "every
visit reaches the service"). This appeared in 1 of the 51 total dispatches run against text carrying
this fix, so it is rare but real, and is left as measured data rather than patched again — a third
editing pass risks the same kind of unintended confound already found twice in this section. Flagged
for the Stage 2 review, not resolved here.

## Correction — 2026-09-28: retracting the "confirmed / strengthened" verdict above

A second advisor review found that the adjudication pass above repeated the exact failure mode it was
meant to fix: it re-asserted "confirmed clean 0/3" for `compatibility` and `constraints` without
checking whether PASS was actually the *correct* answer under `assessor-prompt-draft.md`'s own
definitions, rather than only under `labels.json`. Nothing above this line is rewritten; this section
is the correction, per this ledger's own convention.

**The discriminating experiment (run, not argued):** `defect-compatibility.md`'s Purpose paragraph was
given a relevance cue — "It replaces the current ad-hoc shortener; links it issued over the last six
months are already embedded in docs and read by deployed link-preview bots" — with **no** compatibility
requirement added anywhere. 3 fresh dispatches: **3/3 caught it**, unprompted, citing exactly that
unaddressed migration/continuity question. This is decisive: the document's original 0/3 was not an
assessor blind spot for structural absence — it was a corpus-construction defect. Deleting the
Compatibility section had also deleted the only sentences establishing that compatibility was relevant
at all, and the assessor correctly declines to invent a concern the text never raises. **The cued text
is now the corpus's `defect-compatibility.md` fixture** (committed; old runs kept as
`*-superseded2.json`). There is no demonstrated structural blind spot. The narrow, real limitation —
worth one line in the Stage 3 `sdle-requirements-review` agent prompt — is that the assessor will not
infer relevance the document's own text never raises; it is not that the assessor fails to notice named
sections are missing.

**`constraints` and `scope` are not confirmed misses.** Both documents still carry content that a
generous, defensible reading of their check's own hedge ("where any genuinely apply") could credit:
`defect-constraints.md` has the 301 requirement, slug format, NFR numbers and the non-sequential-slug
rule scattered across other sections; `defect-scope.md` has its required Purpose paragraph and AC-*
criteria. The compatibility experiment proved this exact mechanism can flip a result from miss to catch
when it applies — no equivalent controlled test was run for these two, so neither is reported as a
confirmed recall failure. `labels.json` now marks both `_undetermined`; `recompute_metrics.py` excludes
each from the main table and reports them separately.

**`dependencies`: this session's own run-file notes were factually wrong.** They claimed "no external
dependency named" — false; the Constraints section names both the Kubernetes cluster and the internal
SSO. `note_correction` fields were added to all three `assessor-dependencies-run*.json` files rather
than rewriting the original notes. The document is reliably blocked (3/3, via `ambiguity`), so the
`dependencies` check specifically not firing is an attribution result, not a demonstrated gap in the
assessor's ability to notice a missing dependency treatment.

**`contradictions` false positives all trace to the same known cause**, not three independent findings:
2 of 3 come from `defect-blocking_unknowns.md` and 1 from `defect-constraints.md`, all the same
301/`no-store` tension described above. Reported both ways below, not chosen between.

**Agreement rate: 69% (9/13), unchanged from the original section above.** The prior correction's "62%
(8/13)" was an arithmetic error, not a re-measurement — `recompute_metrics.py` (below) shows
`defect-constraints.md` was already one of the 4 disagreeing documents before this adjudication pass
touched anything, not a fifth added by it.

**What does hold up, unimpeached, is the document-level blocking table** — whether *any* check (labeled
or not) fails, which is what the loop's stall/regression logic actually acts on, independent of which
specific check id fires. On that measure: `defect-scope.md` is the only document never blocked in any
observed run (0/3). Every other document — including `compatibility` after the fix, `dependencies` (via
`ambiguity`, not `dependencies`), and `constraints`/`security_data_implications` (1/3 each) — is blocked
at least once. `scope` being both the sole 0/3-blocked document and one of the two `_undetermined`
labels is itself informative, not resolved.

**The PLAN.md §3.c "prompt-level remedy versus documented limitation" owner question is withdrawn.**
There is no demonstrated blind spot to choose a remedy for.

### `recompute_metrics.py` output (verbatim, current corpus + run files)

```
Main table (excludes each _undetermined document's OWN labeled check - see below):
| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 0 | 0 | 0 | 0 | n/a | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 0 | 0 | 0 | 0 | n/a | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 1 | 2 | 1 | 0.33 | 0.50 |
| compatibility | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 0 | 1.00 | 1.00 |

contradictions, excluding the known shared-template 301/no-store tension FPs:
  raw: FP=3, precision=0.50
  excluding template tension: FP=0, precision=1.00

Undetermined documents (own labeled check reported separately, not scored):
  defect-constraints.md / constraints: caught 0/3 runs
  defect-scope.md / scope: caught 0/3 runs

False positives by check (document#run):
  contradictions: ['defect-blocking_unknowns.md#run2', 'defect-blocking_unknowns.md#run3', 'defect-constraints.md#run3']
  security_data_implications: ['clean-baseline.md#run1']

Agreement rate (byte-identical 12-key verdict vector across all runs of a document):
  clean-baseline.md: DISAGREE (3 runs)
  defect-acceptance_criteria.md: AGREE (3 runs)
  defect-ambiguity.md: AGREE (3 runs)
  defect-blocking_unknowns.md: DISAGREE (3 runs)
  defect-compatibility.md: AGREE (3 runs)
  defect-constraints.md: DISAGREE (3 runs)
  defect-contradictions.md: AGREE (3 runs)
  defect-dependencies.md: AGREE (3 runs)
  defect-nfrs.md: AGREE (3 runs)
  defect-out_of_scope.md: AGREE (3 runs)
  defect-problem_statement.md: AGREE (3 runs)
  defect-scope.md: AGREE (3 runs)
  defect-security_data_implications.md: DISAGREE (3 runs)
Agreement: 9/13 (69%)

Document-level blocking (any check FAIL, labeled or not - what the loop actually acts on):
  clean-baseline.md: blocked in 1/3 runs
  defect-acceptance_criteria.md: blocked in 3/3 runs
  defect-ambiguity.md: blocked in 3/3 runs
  defect-blocking_unknowns.md: blocked in 3/3 runs
  defect-compatibility.md: blocked in 3/3 runs
  defect-constraints.md: blocked in 1/3 runs
  defect-contradictions.md: blocked in 3/3 runs
  defect-dependencies.md: blocked in 3/3 runs
  defect-nfrs.md: blocked in 3/3 runs
  defect-out_of_scope.md: blocked in 3/3 runs
  defect-problem_statement.md: blocked in 3/3 runs
  defect-scope.md: blocked in 0/3 runs
  defect-security_data_implications.md: blocked in 1/3 runs
```

Script: `runs/recompute_metrics.py`. Re-run it directly against `runs/assessor-*.json` (excluding
`*-superseded*.json`) and `labels.json` to reproduce this output; Stage 2's Codex review should do so
rather than trust the numbers above.
