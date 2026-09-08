# ADR-001 — A deterministic core for SDLE's guardrails

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-10 |
| **Version** | v1.12 → v1.13 (Wave A) |

## Context

SDLE v1.12 was 2,400 lines of markdown and no code. Its guardrails — the state machine, gate enforcement, SHA fingerprinting, the audit hash chain, drift detection, the session lock, rate limits — were **prose in a 906-line prompt, interpreted by a model on every turn**. The mechanism meant to constrain the model was advisory to it.

A guardrail a model can talk itself out of is not a guardrail.

Three consequences followed from the same root cause:

1. **Seven hand-synced constant tables**, plus a state template duplicated byte-for-byte in two files, plus a version string in four. `CLAUDE.md` documented the sync rules *for a human to follow by hand*. Every one of them was mechanically checkable — and one had already drifted (see D1).
2. **PowerShell-only embedded commands** (`Get-FileHash`, `New-Item -ItemType`, `%USERPROFILE%`) that blocked Linux, macOS and any CI.
3. **No automated test of any kind.** Validation was "run it and read the output."

## Decision

Move the mechanical layer into `scripts/sdle.py` — single file, Python 3.11+, standard library only — and put explicit commands and hooks in front of it, with externally identical behaviour to v1.12 apart from the divergences recorded below.

Four properties make it a guardrail rather than a suggestion:

- **It refuses; it does not warn.** Exit 1 with a machine-readable reason. The caller surfaces it and cannot override it.
- **JSON on stdout, prose on stderr.** The skill parses rather than interprets.
- **Atomic writes.** Temp file plus rename; a crash never leaves partial state.
- **It fails loudly, never open.** A constant table that will not parse raises. Returning an empty default would let `advance` compute a wrong next phase — the exact failure this exists to prevent.

### Where the constants live

`SKILL.md` remains the host; `sdle.py` **parses** the tables out of it rather than restating them. Two tables were reformatted so one parser handles all of them: `PHASE_SEQUENCE` became a table instead of a fenced list, and the version migration table gained explicit `from_version`/`to_version` columns. `GATE_PHASES` was deleted outright and is now derived from `PHASE_TO_GATE_KEY` — one fact, one place. The `N` in `N/18` is derived from `PHASE_SEQUENCE` and asserted nowhere.

### Alternatives rejected

**Constants owned by `sdle.py`, tables deleted from SKILL.md.** Architecturally cleaner — a table the model can read is a table it can reason around — and it would have shrunk SKILL.md further. Rejected because the wave's brief states the preference twice, and because a maintainer editing the workflow should be able to see its shape in the file they are editing. `lint-skill` closes the gap the other way: the tables cannot silently diverge from anything that restates them.

**PowerShell (`pwsh` 7) for the core.** It would have removed the Python requirement on Windows, the maintainer's platform. Rejected on three counts. It reverses the goal — the Windows-only dependency moves from the prompt files into the engine rather than disappearing. "PowerShell" is not one target: Windows ships 5.1, and `ConvertFrom-Json -AsHashtable` only exists from 6. And its JSON semantics are hostile to exactly this workload: `ConvertTo-Json` defaults to `-Depth 2`, shallower than `state.json`, and single-element arrays unwrap, so `drift_queue: ["gate_spec"]` can round-trip into a bare string. Silent state corruption in the component whose entire job is not corrupting state. Python's `json` has neither behaviour.

Note this reverses `CLAUDE.md`'s previous platform guidance; that file has been rewritten accordingly.

**A dependency (pydantic, click, pytest-only helpers).** Out of scope by the brief, and unnecessary — `hashlib`, `json`, `argparse`, `subprocess`, `pathlib`, `re` and `datetime` cover the whole surface.

**Delegating any of it to subagents.** Out of scope for this wave, and a gate can never be delegated regardless: it requires artifact content in the conversation for a human decision (invariant 8).

### Hooks are tripwires, not guarantees

Hooks enforce guardrails regardless of model decisions — four when this ADR was written, and a fifth (`product-agent-fence`) once product subagents arrived; see ADR-007. This ADR records a decision, not a count: the guard registry lives in `.claude/hooks/hooks.py` and is pinned by test, so read it there rather than here. But there is no tool event meaning "implementation finished" — `speckit-implement` is one Skill call spanning many writes — so a `PostToolUse` hook cannot be where the secrets scan lives.

The resolution generalises: **where a hook and the script overlap, the script refuses at the choke point.** `gate approve --gate gate_implement` rejects a manifest missing its secrets-scan or test-evidence section. Skipping the hook cannot get an unscanned implementation in front of a reviewer. The hook only surfaces the finding earlier, while the file is fresh.

## Deliberate divergences from v1.12

Per the acceptance criterion, every difference from `docs/dry-runs/01..09` is either a defect or a recorded decision. There is no third category. These are the recorded decisions.

| # | Divergence | Why | Transcripts touched |
|---|---|---|---|
| D1 | `templates/state.json` is the only state template; the copy embedded in SKILL.md Step 9 is deleted | The two had already diverged — the embedded copy carried `"<inferred from requirements or ask user>"` and `"<ISO-8601 timestamp>"` where the template had `null`. This is the hand-sync failure the wave exists to prevent, found on contact | none |
| D2 | Gate 7 refuses a manifest without secrets-scan and test-evidence sections; the manifest carries real test output when a runner is detectable | Improvement item 11. An implementation whose tests never ran could previously be approved — the largest correctness hole in v1.12 | 01, 06 |
| D3 | The security review diffs against `implementation_base_ref`, pinned at Phase 15 start, instead of `HEAD~1` | Improvement item 3. `HEAD~1` is correct only when the implementation was exactly one commit; it is usually zero (uncommitted) or several, so the review's evidence could miss the implementation entirely | none |
| D4 | Drift prompts include `git diff` for git-tracked artifacts | Improvement item 12. Fingerprints tell a reviewer *that* something changed; re-approval requires knowing *what* | 04 |
| D5 | Rate-limit halts name audited commands (`limit set`, `limit reset`) instead of instructing the user to edit `state.json` | Improvement item 6. Telling users to hand-edit state defeats the audit chain the same version hardens, and violates the single-writer invariant | 02, 03 |
| D6 | Recorded SHAs are lowercase hex; migration rewrites existing uppercase values | `hashlib` emits lowercase, PowerShell's hashing cmdlet emitted uppercase. Without normalising, every approved gate would false-drift on the first v1.13 run | none |
| D7 | The audit ledger carries a per-entry `Prev` hash in addition to the whole-file `audit_sha` | Required by the wave brief. The file hash catches any edit; the entry chain identifies *which* entry broke. `accept audit` re-chains, and the acknowledgement entry recording the edit is appended after the repair, so it is covered by the new chain | none |
| D8 | The secrets pattern `sk-[A-Za-z0-9]{20,}` widened to `sk-[A-Za-z0-9_-]{20,}` | The original does not match the current `sk-proj-…` key format — the hyphen ends the character class four characters in | none |
| D9 | Gates 1–3 gained blocks in `phase-execution.md` | Gates 4–8 had them and 1–3 did not. Surfaced by `lint-skill` on its first run; the blocks mirror the existing ones and change no behaviour | none |
| D10 | Nine slash commands; the natural-language dispatcher is reduced to aliases | Wave brief. Purely additive — every v1.12 phrasing still routes | none |

### Hooks are Python, not shell

The first implementation used `sh` scripts. They passed 23 tests and **never fired**: `sh` does not resolve on Windows outside Git Bash, and `.claude/settings.json` invoked it directly. The tests had exercised the script by locating `sh.exe` themselves — a path production never takes. A guardrail that does not run is not a guardrail, and a test that proves the wrong thing is worse than no test.

Rewritten as one `hooks.py`, registered as `python .claude/hooks/hooks.py <guard>`. Python is already a hard requirement, and it resolves in cmd, PowerShell and sh alike. Two further benefits: the hooks now **import** the injection and secret patterns from `sdle.py` rather than restating them — the shell versions had forked a fact that is supposed to live in one place (invariant 7) — and the fragile `sed`-based JSON extraction is gone.

The hook tests now drive the exact command string from `settings.json`, and one test asserts that the interpreter it names actually resolves on PATH.

## Defects found by writing the tests

Not divergences — bugs the tests exposed:

- **The write fence never blocked `.workflow/`.** It keyed on the directory name `workflow`, but the directory is `.workflow`. The single most important fence in the product matched nothing. Caught the moment the tests started driving the registered command.
- **Three state fields had no sanctioned writer.** `verbose`, `clarification_phase` and `speckit_skill_prefix` were set by prompt instructions telling the model to edit `state.json` — which the new write fence correctly denies, and which violates single-writer. Added `state set`, whitelisted to exactly those three fields and audited; every other field stays engine-derived. `preflight` now persists the discovered SpecKit prefix itself.
- **`retry` while drift was pending was prompt-only.** Now `sdle.py retry` refuses mechanically.

And in v1.12 itself:

- **`git status --short` collapses an untracked directory to `?? src/`.** Every file inside escaped both the dirty-tree guard and the secrets scan. A whole new folder of generated code would have been scanned as nothing. Fixed with `-uall`.
- **Repo staleness compared ISO strings.** Git reports a local offset (`+04:00`); approvals record `Z`. Any afternoon commit looked newer than any morning approval. Now compares parsed instants.
- **Hooks received JSON-escaped Windows paths** (`C:\\Users\\…`), which POSIX `test -f` cannot resolve, so every hook silently passed on the platform SDLE ships on.

## Consequences

**Gained.** Guardrails that execute. 180+ tests, nine of them derived from the dry-run transcripts, green on Linux and Windows. Cross-file sync checked mechanically instead of by hand. SKILL.md from 906 to 268 lines with no behaviour lost. A foundation Waves B and C can extend without hand-syncing seven tables and hoping a prompt is obeyed.

**Paid.** SDLE now requires Python 3.11+ where it previously required nothing — mitigated by a resolver that tries `py -3`, `python3`, `python`, then `uv run` (which every SpecKit user already has). And the install story is larger: copying `.claude/skills/sdle/` alone no longer installs the engine, because the script, commands and hooks live outside it. Documented in the README; `preflight` refuses with a clear message when the script is unreachable.

## Open questions, deliberately not resolved here

Recorded during analysis and left for a decision rather than settled silently:

- After `approve`, does SDLE execute the next phase immediately (as transcript 01 shows) or ask "Shall I proceed?" (as `gate-protocol.md` says)? The script supports either; the skill currently proposes.
- Should `lock acquire` **refuse** on a fresh foreign lock, as the wave's subcommand table implies, or **warn**, as v1.12 and transcript 07 do? Implemented as warn-only, preserving v1.12 behaviour.
- `reset to <phase>` is offered in two halt messages but exists in no command. Either a missing command or dead text.
- A skipped phase can land on a gate with `current_artifact: null` — a gate with nothing to display. Reachable, and undefined.
