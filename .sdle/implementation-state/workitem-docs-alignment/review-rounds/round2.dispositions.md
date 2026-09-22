# Round 2 dispositions — the final round

There is no round 3. This record exists because the reply has nowhere to be sent: it is the account of
what was decided, and it is what the handoff summarises.

**Candidate reviewed:** `bd56045`. **Candidate after these fixes:** `a669b03`.

Codex returned **nine defects, three preferences, no questions**. Every defect was **accepted**, none
disputed, and all three preferences were adopted. Every factual claim was re-verified against the
running CLI before being written down — **9 of 9 held**, as 6 of 6 did in round 1.

---

## Defects

| ID | Sev | Disposition | What was done |
|---|---|---|---|
| R2-D01 | high | Accepted, **verified** | Documentation corrected; the underlying behaviour is raised as **OPEN-01** |
| R2-D02 | high | Accepted, **verified** | Tutorials made runnable |
| R2-D03 | medium | Accepted, **verified** | The impossible header removed from seven documents |
| R2-D04 | medium | Accepted | Directory-wide language removed from SKILL.md; "binding changed" → "bound source set changed" |
| R2-D05 | medium | Accepted, **verified** | `guidance/` added to every enumeration; "share nothing" scoped to records |
| R2-D06 | medium | Accepted, **verified** | The invariant-6 violation I introduced, removed |
| R2-D07 | medium | Accepted | Records frozen at the candidate |
| R2-D08 | medium | Accepted, **verified** | A gate is passed by a recorded decision, not always a human one |
| R2-D09 | low | Accepted, **verified** | `requirements show` exits 0; binding is not limited to `requirements/` |

### R2-D01 — `accept content` does not exist at bootstrap

Reproduced exactly: `cmd_scan` records `pending_confirm_action` only when `state.json` already exists,
and `cmd_accept_content` calls `read_state` unconditionally, so before `init` it exits **3
`state_unreadable`**. Dry-run 05's Path B had documented `accept content` succeeding at precisely that
point, which cannot happen.

The document now shows **edit-and-re-scan** at bootstrap and states why, naming the two functions. The
acknowledgement route is real but only once a workflow exists — the guidance-file and clarification
cases, mid-workflow.

Codex was explicit that if bootstrap acceptance is *intended*, that is an engine change and an owner
decision, not a prose correction. I agree, and have not made one. It is **OPEN-01** below.

### R2-D02 — the tutorials were not runnable

Three separate faults, all confirmed:

- **Brownfield** listed a repository tree with no `requirements/` directory, then bound
  `requirements/stock-reservations.md`. Copied as written it refuses `requirements_source_missing`. The
  tree now shows the document, and a note distinguishes it from the adjacent `requirements.txt`, which
  is pip's and which SDLE never reads.
- **Iterative** bound one document and then displayed two in `init`. It now binds both, with
  `--primary`, and explains why two are right for that work. Its third WorkItem showed `init` with no
  binding step at all; it now shows create → bind → preflight → scan → assess → init, and says
  explicitly that binding inherits nothing from the two WorkItems before it.
- **Every** tutorial's `init` payload showed bare filenames (`link-shortener.md`) where `cmd_init`
  emits `bound_sources(paths)` — repository-relative paths. All five corrected.

### R2-D03 — a state no run can persist

`Phase 1/N — Requirements Check [IN PROGRESS]` appeared in the root README, the Reference Guide's
Appendix A and dry runs 01, 05, 09, 10, 12 and 13. Driven through the CLI: `init` returns
`current_phase: constitution_draft`, `progress: 2/18`. `requirements_check` is completed *within*
`init` and never persisted, and before `init` there is no `state.json` for a header to read. So that
header is unreachable from both sides.

Replaced with an explicit "no status header: `init` has not run", and, where a header belongs, the real
first phase. Codex's observation that this defect *concealed* R2-D01 — by making pre-init
`accept content` look as though it had state to write to — is correct and is why the two were fixed
together.

### R2-D06 — an invariant-6 violation I introduced

The worst finding of the round, because it was mine. My new troubleshooting §16 told users to **delete**
`workitems/<id>/.sdle/requirements.json` and bind again. That directory is engine-owned, only `sdle.py`
writes there (invariant 6), and the write fence exists to stop exactly that. It was also unnecessary:
`requirements bind` replaces a corrupt binding deliberately and reports the new one — verified, exit 0.

The same section claimed the stale refusal's `data` distinguishes the three freshness cases. It does
not: an ordinary `advance` refusal carries `workitem`, `recorded_digest`, `current_digest` and
`requirements` only. `rebound`, `missing_sources` and `assessed_without_a_binding` are reported by
`governance show`. Both corrected, and the correction propagated to SKILL.md and ADR-012 §8.

### R2-D07 — the records did not describe the candidate

Correct, and correct again about the specifics: `STATE.json` still named `b83cf4a`, `round_2` still read
`not_started`, and the ledger's phase log stopped at a working tree. Also correct that my "measured"
diff sizes were wrong — 1,446/86 and 1,246/87, not 1,423 and 1,223. They were measured, but at an
earlier commit, and then quoted after two more commits had landed. Measuring once and quoting later is
the same failure as not measuring.

Both records are now frozen at `a669b03`, carrying the round-2 findings, these dispositions, D-12 and
the verification disposition.

---

## Preferences — all three adopted

- **R2-P01** — the prohibition was safely over-conservative. Narrowed to non-excluded paths, while
  keeping the stricter "nobody else writes here" as the working advice and saying which is which,
  because judging exclusion path-by-path mid-task is how the mistake gets made.
- **R2-P02** — "checked on every advance, whatever phase" is now "every **otherwise-valid** phase
  transition", naming `forward_jump` and `gate_not_approved` as refusals that win first.
- **R2-P03** — the empty code fence in the brownfield tutorial is gone.

---

## Round-1 closure, as Codex assessed it

Closed: **R1-D05**, **R1-D07**, **R1-Q02**. Not closed at round 2, each for a reason now fixed:
R1-D01 (`guidance/`), R1-D02 (`requirements show` exit), R1-D03 (tutorials not runnable),
R1-D04 (SKILL.md), R1-D06 (wording elsewhere), R1-D08 (records). Every one of those is addressed above.

My own four findings: **D-09** substantively correct, refined by R2-P02. **D-12**'s two-list direction
**confirmed correct** by an independent read. **D-10** and **D-11** were not closed — R2-D06 and R2-D01
respectively — and both are now fixed.

---

## Open items for the owner

These are not disagreements. Codex and I agree on all three; they are decisions that are not mine.

### OPEN-01 (medium) — should `accept content` work before `init`?

- **The question.** A scan false positive on a *requirement* document can today be resolved only by
  editing the file. The acknowledgement route does not exist until a workflow does.
- **Both positions.** Codex: "If bootstrap acceptance is intended, that requires an engine change and
  owner decision, not a prose correction." Mine: identical. Documentation describes what the engine
  does; whether it should do something else is out of scope for an alignment pass.
- **Reproduction.** `workitem create` → `requirements bind` → `scan --path <document with
  instruction-like text>` exits 1 `content_flagged` and writes no state → `accept-content` exits 3
  `state_unreadable`. Recorded at `runs/bootstrap-accept-content.txt`.
- **User impact.** A user with a legitimate sentence about approving gates must edit their requirement
  document to proceed — plausibly rewording something they meant. Low frequency, high annoyance, and
  the current message does not explain it. The message is now correct in the docs but still terse in
  the engine.
- **Recommended resolution.** Leave the documentation as it is. If the behaviour should change, the
  smallest correct change is for `cmd_scan` to record the pending acknowledgement in a pre-init
  location, or for the refusal to say "edit and re-scan; acknowledgement is available after `init`".
  Either is an engine change with its own review.

### OPEN-02 (low) — the fixture auto-binds, so the suite cannot catch a missing bind step

- **The question.** `tests/conftest.py` binds during fixture setup, so a documented startup sequence
  that omits `requirements bind` passes the suite. Codex raised this in round 1 and, in its round-2
  closing paragraph, recommends an executable end-to-end startup contract covering fresh and
  registered-without-state starts including a flagged false positive.
- **Both positions.** Codex: such a test "would have exposed most of the unresolved defects above" —
  which is true; R2-D02 and R2-D03 would both have failed it. Mine: it is a test-design change, the same
  category I declined in round 1, and building it inside a documentation pass is scope creep.
- **User impact.** None directly. It is why documentation drift of this kind survives.
- **Recommended resolution.** Worth building, as its own task. It is the single highest-value follow-up
  from either round.

### OPEN-03 — RESOLVED by CI, not locally

- **The question.** Three attempts; none produced a result. The first was measuring a tree that changed
  underneath it and was killed deliberately. The second and third were stopped by Claude Code's
  background-shell memory reaper at ~4% and 11%.
- **User impact.** Seven checks pass against this candidate, but the full suite is the repository's
  stated gate and it is unmet.
- **Resolution.** The owner pushed the branch instead, which was the better answer and not one I could
  take unilaterally. `.github/workflows/ci.yml` triggers on every branch, so GitHub Actions ran the full
  suite plus `lint-skill` on **four** combinations — ubuntu-latest and windows-latest × Python 3.11 and
  3.13 — and **all four passed** at `7477e9f`, the exact candidate. That is strictly stronger than the
  single-combination local run it replaced. Recorded at `runs/full-suite-PASS-ci.txt`.

---

## Verification of this candidate

| Check | Result |
|---|---|
| `python scripts/sdle.py lint-skill` | PASS |
| `pytest test_dry_run_contracts + test_units_documented_commands + test_units_invariants + test_lint_skill` | PASS — 1124 |
| Guide replay, 13 blocks into an empty target | PASS — exit 0 |
| Binding scenarios through the real CLI | PASS — 7 |
| ADR-012 refusal probe | PASS — 7 claim groups |
| Deleted-bound-source probe | PASS |
| Round-2 claim probe | PASS — 9 of 9 reproduced |
| **Full suite** | **PASS** — CI run 35727873456 at `7477e9f`: 4 jobs (ubuntu + windows × Python 3.11 + 3.13), all success |

Two of those were caught *by* the checks rather than by review: removing dry-run 09's last progress
fraction broke `test_dry_run_contracts.py`, and the contract tests were re-run after the final dry-run
09 edits because the first result predated them.
