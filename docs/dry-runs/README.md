# SDLE Dry-Run Conversation Transcripts

Simulated, end-to-end conversation flows for **SDLE v1.13**, showing exactly what the orchestrator says and does in each notable scenario. These are *dry runs*: no SpecKit was invoked and no artifacts were generated — every SDLE turn is derived from the skill files (`SKILL.md`, `modules/*.md`) and reproduces their specified output formats verbatim (status assertion headers, gate prompts, halt messages, confirmation flows).

Use them as:

- **Onboarding** — read `01-happy-path.md` first to see the whole 18-phase / 8-gate flow.
- **Acceptance spec** — each transcript is the expected conversational behavior for its scenario; a deviation in a real run is a bug in either the run or the skill files.
- **Test fixtures** — `tests/test_integration_01..09` derive their asserted state transitions from these transcripts. Deliberate v1.13 divergences are marked inline and recorded in `../architecture/ADR-001-deterministic-core.md`; there is no third category.
- **Guardrail reference** — scenarios 02–09 each exercise specific guardrails (item numbers refer to the gap analysis recovered at `git show 22f3f3b^:improvements.md`).

All transcripts use the repo's test fixture (`requirements/todo-api.md` — Todo List REST API) as the subject project. Hashes are illustrative and truncated; artifact bodies are abridged (`[... abridged ...]`) because the transcripts document *orchestration behavior*, not SpecKit output quality.

## Scenarios

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

## Disposition under the flow model (v1.16)

All nine transcripts remain **valid and byte-identical**, and all nine are `GREENFIELD` runs. `GREENFIELD` is the frozen pre-flow lifecycle, so every phase, progress fraction and gate number these transcripts show is still exactly what the engine produces — which is the point. The compatibility translation is that a workflow predating the flow model traversed `GREENFIELD`, and `tests/test_integration_01..09` still assert these transitions with no edits at all. `impact_analysis` appears in none of them, correctly: it is not a GREENFIELD phase.

**No transcript is authored for `ITERATIVE`, `DEFECT_FIX`, `HOTFIX` or `BROWNFIELD_DISCOVERY`, deliberately.** A dry run is a *conversational* artifact containing simulated SpecKit output; four more would multiply the documentation these files already carry without adding one executable guarantee. Non-GREENFIELD traversal is pinned instead by end-to-end tests in `tests/test_units_flow_model.py` that drive the real CLI through every flow, which is stronger evidence than prose. Removing the legacy fixed-sequence structures these transcripts still describe is separate, later work and is not done here.

## How to read a transcript

Each file has three sections:

1. **Scenario header** — purpose, guardrails exercised, and the starting state (fresh project, or a `state.json` snapshot for mid-workflow scenarios).
2. **Transcript** — alternating `User:` / `SDLE:` turns. Every SDLE turn begins with the two-line state assertion header when state exists:
   ```
   <!-- SDLE_STATE phase=<id> status=<status> progress=<N/18> -->
   📋 SDLE Status: Phase N/18 — <Label> [STATUS]
   ```
3. **State & audit notes** — the `state.json` transitions and `audit.md` entries the scenario produces.
