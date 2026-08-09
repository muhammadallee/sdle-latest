# `scripts/` — the SDLE deterministic core

`sdle.py` is the mechanical layer of SDLE: the state machine, gate enforcement,
SHA fingerprinting, audit hash chain, drift detection, locking and rate limits.
It exists so those guardrails execute rather than being interpreted by a model
on every turn.

Python 3.11+, standard library only, cross-platform.

## Call the launcher, not the script

| Caller | Use |
|---|---|
| POSIX sh, bash, Git Bash | `scripts/sdle.sh <subcommand> [...]` |
| PowerShell | `scripts/sdle.ps1 <subcommand> [...]` |
| Tests, CI | `python scripts/sdle.py <subcommand> [...]` |

Hooks and slash commands must go through a launcher. They cannot ask `sdle.py`
where Python is, so interpreter resolution has to happen before it runs.

### Interpreter resolution

`py -3` → `python3` → `python` → `uv run --python 3.11` → refuse.

A candidate qualifies only if it **successfully reports** a version ≥ 3.11.
Gating on a reported version rather than on the command merely being found is
what disposes of the Windows Store stub, which resolves on `PATH` but is not an
interpreter. The `uv` fallback matters because SpecKit is installed with `uvx`,
so every SDLE user already has `uv` — but `uv` ships its own private Python and
does not imply a system one.

Set `SDLE_PYTHON` to bypass resolution entirely (used by tests and exotic
environments).

If nothing resolves, the launcher refuses with the same JSON envelope every
other refusal uses, so callers parse the failure identically.

## Output contract

**JSON object on stdout. Human-readable text on stderr.** The caller parses; it
does not interpret prose.

```json
{ "ok": true, "command": "advance", "reason": null, "data": { } }
```

A refusal adds `message` and sets `reason` to a code from a closed set
(`forward_jump`, `gate_not_approved`, `rate_limit_exceeded`, `drift_pending`,
`artifact_too_small`, `dirty_tree`, `manifest_incomplete`, `content_flagged`,
`lock_conflict`, `audit_chain_broken`, …).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | **Refused** — a precondition failed. Not an error; a decision. |
| `2` | Usage error |
| `3` | Integrity failure — state unreadable, audit chain broken, lock conflict |

**The script refuses; it does not warn.** A refusal is exit 1 with a
machine-readable reason. The caller surfaces it. The caller cannot override it.

## Where the constants live

The seven constant tables (`PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_TO_GATE_KEY`,
`ARTIFACT_OWNERSHIP`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`, plus
`GATE_TO_EXECUTION_PHASE` in `modules/gate-protocol.md`) live in the skill's
markdown and are **parsed** from it. They are never restated in Python.

`GATE_PHASES` is derived from `PHASE_TO_GATE_KEY`; the phase count behind
`N/18` is derived from `PHASE_SEQUENCE`. Neither is stored.

A table that fails to parse raises — it never yields an empty default. A
constant table that silently parsed to nothing would let `advance` compute a
wrong next phase and fail *open*, which is the exact failure this engine exists
to prevent.

Run `sdle.py constants` to see what was parsed, and `sdle.py lint-skill` to
verify every cross-file sync rule.
