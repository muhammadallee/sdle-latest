# SDLE Dry-Run Conversation Transcripts

**Applies to:** SDLE v1.17

End-to-end conversation flows showing what the orchestrator says and does in each notable
scenario, for **every one of the five shipped flows**, plus focused scenarios for the
defects fixed in SDLE-DEFECT-STABILIZATION-01.

## What is simulated and what is executed

Each transcript separates two kinds of content, and labels them:

- **SIMULATED** — the conversation itself. It is written from the skill files and
  the engine's real messages; no model or SpecKit run produced it. Hashes are
  illustrative and shortened, and artifact bodies are abridged. Where a
  transcript quotes a refusal "as the engine prints it", the text was captured
  by driving the real CLI through the suite's fixtures.
- **PASS / FAIL / BLOCKED / NOT RUN** — the executable checks. Every transcript
  ends with an *Executable coverage* table naming the test nodes that assert its
  claims. [verification-matrix.md](verification-matrix.md) records, per scenario,
  the command that was run, the commit it ran against, and the actual result.

A deviation between a real run and a transcript is a bug in the run, the skill files,
or the transcript — and since the transcripts' claims are checked by
`tests/test_dry_run_contracts.py`, a transcript that disagrees with the engine fails
the build rather than drifting silently.

## Scenarios

### `GREENFIELD` — the new-project flow and its guardrails

| File | Scenario | Defects |
|---|---|---|
| [01-happy-path.md](01-happy-path.md) | DR-01 · Full success run: identity → preflight → governance → 18 phases → 8 approvals → `complete` and the repository baseline | D02, D03, D05 |
| [02-gate-rejection-remediation.md](02-gate-rejection-remediation.md) | DR-02 · Gate rejected, remediated, approved; then the remediation rate limit | — |
| [03-technical-failure-retry-skip.md](03-technical-failure-retry-skip.md) | DR-03 · Generation fails; retries exhaust; two-step skip | — |
| [04-artifact-drift-reapproval.md](04-artifact-drift-reapproval.md) | DR-04 · Approved artifact edited; drift, re-approve, reject, and the deleted-artifact refusal | D01 |
| [05-untrusted-content-scan.md](05-untrusted-content-scan.md) | DR-05 · Prompt-injection text in requirements and guidance | D05 |
| [06-secrets-and-dirty-tree.md](06-secrets-and-dirty-tree.md) | DR-06 · Dirty tree halts implement; secrets and test evidence at Gate 7 | D02, D03 |
| [07-audit-integrity-and-session-lock.md](07-audit-integrity-and-session-lock.md) | DR-07 · Foreign lock, edited ledger, stale repository | D05 |
| [08-restart-reset-state-jump.md](08-restart-reset-state-jump.md) | DR-08 · Restart, forward-jump refusal, state jump, reset | — |
| [09-bootstrap-failures.md](09-bootstrap-failures.md) | DR-09 · No WorkItem, no requirements, no SpecKit, no skills | D05 |

### The other four flows

| File | Flow | Size | What it pins |
|---|---|---|---|
| [10-brownfield-discovery.md](10-brownfield-discovery.md) | `BROWNFIELD_DISCOVERY` | 19 phases, 8 gates | DR-10 · The gateless `discovery` phase, finding classification, `discovery_missing`, the baseline at the final gate |
| [11-iterative.md](11-iterative.md) | `ITERATIVE` | 16 phases, 7 gates | DR-11 · Brownfield → iterative continuation, `baseline_present`, baseline reuse without rewriting, invalid vs stale baselines, Gate 1 of 7 |
| [12-defect-fix.md](12-defect-fix.md) | `DEFECT_FIX` | 14 phases, 6 gates | DR-12 · The impact analysis and its three refusals; the reproducing test verifying the fix |
| [13-hotfix.md](13-hotfix.md) | `HOTFIX` | 10 phases, 3 gates | DR-13 · The floor, the gates the policy could not have, and urgency never turning a failed run into a pass |

### Focused defect scenarios

| File | Scenario | Defects |
|---|---|---|
| [14-gate-evidence-refusals.md](14-gate-evidence-refusals.md) | DR-14 · Missing/unresolved artifacts and unsuccessful verification refused, then recovered | D01, D02 |
| [15-committed-change-manifest.md](15-committed-change-manifest.md) | DR-15 · Committed, staged, unstaged, untracked, renamed, deleted and binary changes, one change set for both consumers | D03 |
| [16-execution-evidence-collision.md](16-execution-evidence-collision.md) | DR-16 · Same-second executions keep separate evidence and ledger entries | D04 |

Flow sizes are stated as the engine reports them: executable phases,
excluding the terminal `complete`, which is the number in the progress header.
`lint-skill`'s `doc_flow_counts_match_engine` checks every one of them.

## Reproducing a scenario

1. **The executable form** — always available, no SpecKit needed:
   `python -m pytest <node ids from the transcript's coverage table>`. The suite
   generates its fixtures at runtime and simulates generation by writing an
   artifact over the size floor.
2. **By hand** — each transcript's *Setup* section builds a disposable
   repository with the README's tested SpecKit v1.0.6 command, and its
   *Cleanup* section removes it. Commands use global options before the
   subcommand: `sdle.sh --workitem <id> --session <token> <command>`.

## How a transcript is laid out

1. A metadata table: scenario id, flow, purpose, defect ids, runtime, starting
   conditions, guardrails.
2. **Setup** — fixtures and reproducible preparation.
3. **Transcript** — `User:` / `SDLE:` turns. Each SDLE turn that has state
   begins with the assertion header:
   ```
   <!-- SDLE_STATE phase=<id> status=<status> progress=<N/M> -->
   📋 SDLE Status: Phase N/M — <Label> [STATUS]
   ```
   `M` is the **bound flow's** phase count: 18 for GREENFIELD, 19, 16, 14 and 10
   for the other four. Gate numbers are flow-relative the same way. Italic notes
   name the real CLI commands behind each state change.
4. **Artifacts, state and audit** — where things were written.
5. **Negative cases** — refusals, and proof that each left state unchanged.
6. **Cleanup**.
7. **Executable coverage** — the test nodes, mapped claim by claim.

## History

Transcripts 01–09 were once byte-pinned against a historical commit. By
SDLE-DEFECT-STABILIZATION-01 they described Spec Kit paths, fingerprints,
bootstrap steps and a Gate 7 the engine no longer had, and a byte pin cannot
tell a correct file from a merely unchanged one. The pins were released
deliberately, and each transcript's claims are now recomputed from the engine
instead. The record of that decision is in
[`../verification/defect-stabilization-01.md`](../verification/defect-stabilization-01.md).
