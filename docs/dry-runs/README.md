# SDLE Dry-Run Conversation Transcripts

**Applies to:** SDLE v1.17

Simulated, end-to-end conversation flows showing exactly what the orchestrator says and does in each notable scenario. These are *dry runs*: no SpecKit was invoked and no artifacts were generated — every SDLE turn is derived from the skill files (`SKILL.md`, `modules/*.md`) and reproduces their specified output formats verbatim (status assertion headers, gate prompts, halt messages, confirmation flows).

Use them as:

- **Onboarding** — read `01-happy-path.md` first to see a whole flow end to end.
- **Acceptance spec** — each transcript is the expected conversational behavior for its scenario; a deviation in a real run is a bug in either the run or the skill files.
- **Test fixtures** — `tests/test_integration_01..09` and `tests/test_integration_10_to_13.py` derive their asserted state transitions from these transcripts. Deliberate divergences from pre-v1.13 behaviour are marked inline and recorded in `../architecture/ADR-001-deterministic-core.md`; there is no third category.
- **Guardrail reference** — scenarios 02–09 each exercise specific guardrails (item numbers refer to the gap analysis recovered at `git show 22f3f3b^:improvements.md`); scenarios 10–13 each exercise one flow's own rules.

Transcripts 01–09 use the repo's test fixture (`requirements/todo-api.md` — Todo List REST API) as the subject project. Hashes are illustrative and truncated; artifact bodies are abridged (`[... abridged ...]`) because the transcripts document *orchestration behavior*, not SpecKit output quality.

## Scenarios

### Guardrails — `GREENFIELD`

| File | Scenario | Guardrails exercised |
|---|---|---|
| [01-happy-path.md](01-happy-path.md) | Full success run: `start workflow` → 18 phases → 8 approvals → `complete` | Baseline: status headers, gate discipline, clarification persistence, completion summary |
| [02-gate-rejection-remediation.md](02-gate-rejection-remediation.md) | Gate rejected, remediated, approved; then remediation rate limit hit | Rejection protocol, feedback canonicalization, remediation rate limit |
| [03-technical-failure-retry-skip.md](03-technical-failure-retry-skip.md) | Generation step fails; retries exhaust; two-step skip | Post-SpecKit Verification, retry rate limit, `confirm skip` (item 15) |
| [04-artifact-drift-reapproval.md](04-artifact-drift-reapproval.md) | Approved artifact hand-edited; drift detected; re-approve and reject paths | Drift detection, re-approval queue, baseline re-fingerprinting |
| [05-untrusted-content-scan.md](05-untrusted-content-scan.md) | Requirements file contains prompt-injection text; guidance-file variant | Untrusted Content Scan, `accept content` (item 1) |
| [06-secrets-and-dirty-tree.md](06-secrets-and-dirty-tree.md) | Dirty working tree halts implement; manifest flags a hardcoded key at Gate 7 | Dirty-tree guard, `confirm implement` (item 8); secrets scan in manifest (item 2) |
| [07-audit-integrity-and-session-lock.md](07-audit-integrity-and-session-lock.md) | Resume in a new session: foreign lock, edited audit log, stale repo | Session lock (item 7), audit hash chain + `accept audit` (item 5), staleness warning (item 14) |
| [08-restart-reset-state-jump.md](08-restart-reset-state-jump.md) | Rollback, forward-jump refusal, manual state edit, full reset | `restart phase N` confirm flow, forward-jump guard, `accept state`, `confirm reset`, stale-confirmation guard |
| [09-bootstrap-failures.md](09-bootstrap-failures.md) | Starting without requirements, without SpecKit, or without SpecKit skills | Step 1b/1c/2 preflight halts |

### The other four flows

| File | Flow | Size | What it pins that 01–09 cannot |
|---|---|---|---|
| [10-brownfield-discovery.md](10-brownfield-discovery.md) | `BROWNFIELD_DISCOVERY` | 19 phases, 8 gates | The gateless `discovery` phase, finding classification, `discovery_missing`, the baseline written at the final gate |
| [11-iterative.md](11-iterative.md) | `ITERATIVE` | 16 phases, 7 gates | `baseline_required`, and flow-relative gate numbering — `gate_spec` is **Gate 1 of 7** here, not Gate 2 of 8 |
| [12-defect-fix.md](12-defect-fix.md) | `DEFECT_FIX` | 14 phases, 6 gates | The gateless `impact_analysis` phase and all three ways it refuses; `gate_tasks` kept by change *type*; `gate_design` absent |
| [13-hotfix.md](13-hotfix.md) | `HOTFIX` | 10 phases, 3 gates | The mandatory floor, the gates the risk policy asked for and could not have, and the terminal gate no override can lower |

The flow sizes above are stated as the engine reports them — executable phases,
excluding the terminal `complete`, which is the number in the progress header
(`Phase 2/14`). `lint-skill`'s `doc_flow_counts_match_engine` checks every one
of them.

## Coverage: every shipped flow now has a transcript

Transcripts 01–09 are all `GREENFIELD` runs, and remain **valid and byte-identical** under the flow model. `GREENFIELD` is the frozen pre-flow lifecycle, so every phase, progress fraction and gate number they show is still exactly what the engine produces — which is the point. The compatibility translation is that a workflow predating the flow model traversed `GREENFIELD`, and `tests/test_integration_01..09` still assert those transitions with no edits at all.

**Transcripts 10–13 close a gap that was previously an accepted one.** Until they existed, four of the five shipped flows had no conversational specification: their traversal was pinned by `tests/test_units_flow_model.py`, which drives the real CLI through every flow, but nothing pinned *what a user sees* — the progress fraction, the flow-relative gate number, the disposition of a gate the flow does not contain, or which refusal comes back when a governed record is missing. A traversal test passes while all four of those are wrong.

The earlier position was that four more transcripts "would multiply the documentation without adding one executable guarantee". That turned out to be false in the specific way that matters: each of the four carries assertions that no existing test made, and `tests/test_integration_10_to_13.py` now makes them. Its last test is parametrized over `ALL_FLOWS` and fails if a flow ships without a transcript, so a sixth flow added later cannot arrive undocumented.

## How to read a transcript

Each file has three sections:

1. **Scenario header** — purpose, guardrails exercised, and the starting state (fresh project, or a `state.json` snapshot for mid-workflow scenarios).
2. **Transcript** — alternating `User:` / `SDLE:` turns. Every SDLE turn begins with the two-line state assertion header when state exists:
   ```
   <!-- SDLE_STATE phase=<id> status=<status> progress=<N/M> -->
   📋 SDLE Status: Phase N/M — <Label> [STATUS]
   ```
   `M` is the **bound flow's** phase count, not a constant: it is 18 in transcripts 01–09 and 19, 16, 14 and 10 in transcripts 10–13. Gate numbers are flow-relative in exactly the same way. Never carry a fraction or a gate ordinal from one transcript to another.
3. **State & audit notes** — the `state.json` transitions and `audit.md` entries the scenario produces.
