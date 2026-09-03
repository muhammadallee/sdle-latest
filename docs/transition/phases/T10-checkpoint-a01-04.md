# T10 checkpoint — attempt 01, milestone M4

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M4 — `sdle resume`, the §16 exit criterion
**Milestone status:** COMPLETE
**HEAD:** `875b361009e2c16d66c2a99ebda0d734a45915db` (OBSERVED). Nothing committed; all work is live in the working tree.
**Rollback to end of M3:** `git checkout -- scripts/sdle.py .claude/skills/sdle/SKILL.md .claude/commands/` and drop the M4 slice from `tests/test_units_capabilities.py` (it starts at the banner `# \`sdle resume\` — §16's exit criterion, driven`).

This is the plan's **declared safe resume boundary**, with one amendment: X1's
first half landed at M3, so it is no longer true that "M1–M4 amend no existing
test". `tests/test_units_gate_policy.py` is amended. The boundary is still safe
in the sense that matters — the tree is green, no window is open, and every
milestone so far is coherent on its own.

---

## What M4 changed

### `scripts/sdle.py`

1. **`gate_disposition(paths, consts, state, gate_key)` extracted** out of
   `cmd_gate_show`, whose body now calls it. The §15 comment moved into the
   new function's docstring unchanged. This is the F5 defence: two derivations
   of "does this gate need a human approval, and why" would be a second source
   of truth introduced by the phase whose job is defending invariant 7.
2. **`cmd_resume`** — read-only, placed beside the other reporters, immediately
   before `cmd_state_dump`. It composes only: `render_header` for the header,
   `flow_for_state` + `Flow` for position/traversal, `gate_disposition` for the
   requirement model, `approval_decision` for the recorded decision,
   `branch_mismatch` for the branch, `Constants.capabilities_for` for what to
   load. It renders nothing of its own.
3. **The `resume` parser entry**, registered next to `header`. It is
   deliberately **not** in `RUNTIME_FREE_COMMANDS`, so it goes through
   `bind_workitem` and refuses exactly where its read-only siblings do.

Payload keys: `workitem`, `flow`, `current_phase`, `status`, `progress`,
`position`, `next_phase`, `label`, `header`, `gate`, `pending`,
`branch_mismatch`, `capabilities`.

### Prompt and command layer

- `SKILL.md` — the one `CAPABILITY_MAP` sentence checkpoint 02 flagged now
  names the command: *"`sdle.sh resume` reports the row for the current
  phase"*. The three forward references M3's checkpoint recorded
  (`design-review.md`, `code-review.md`, `phase-execution.md`, plus Step 5) are
  **all now true** — `resume` exists.
- `.claude/commands/sdle-continue.md` — `sdle.sh state get` plus a prose
  decision about which module to load is replaced by `sdle.sh resume` plus
  *"load exactly what `capabilities` names and no others"*, with the
  floor-not-ceiling rule stated once. **No module is named in prose any more.**
- `.claude/commands/sdle-start.md` — the resume branch calls `sdle.sh resume`
  after `migrate`/`header` and loads what it names.

### Tests — additive only

175 lines appended to `tests/test_units_capabilities.py`: `place_at`,
`RESUME_CASES`, and N9, N10, N11, N12, N12b, N23. No existing test was touched
in M4.

**One deviation from the staged draft, and it is a strengthening.** The draft
parametrised N9 over GREENFIELD and HOTFIX. A non-vacuity guard added here —
`test_the_resume_matrix_covers_every_registry_phase` — failed, because those two
flows between them never reach `discovery`: §14 declares it in
BROWNFIELD_DISCOVERY alone, which is the property
`discovery_is_declared_by_exactly_one_flow` already pins in `lint-skill`. A6
asks for *every phase in the registry*, so the matrix now runs **three** flows —
GREENFIELD, BROWNFIELD_DISCOVERY, HOTFIX — and the guard asserts their union is
exactly the 21-phase registry. The guard was kept rather than relaxed; the
matrix grew to satisfy it.

---

## The exit criterion, driven through the real CLI

§16's exit criterion is *"a fresh Claude session can resume a WorkItem safely
and load only relevant phase context."* It was driven, not asserted, in two
independent ways.

**1. As a live CLI probe** (`<scratchpad>/t10/live_resume.py`): a realistic
install built in a temp directory, a WorkItem created and initialised through
the ordinary commands, then `python scripts/sdle.py resume` invoked as a
**brand-new OS process with no `--workitem` and no history of any kind**.
Observed verbatim:

```
RESUME exit code: 0
  "workitem": "cold-start-item",
  "flow": "GREENFIELD",
  "current_phase": "constitution_draft",
  "status": "pending",
  "progress": "2/18",
  "position": 2,
  "next_phase": "gate_constitution",
  "label": "Generate Constitution",
  "header": "<!-- SDLE_STATE phase=constitution_draft status=pending progress=2/18 -->…",
  "gate": null,
  "pending": { drift_queue, pending_confirm_action, pending_phase,
               phase_checkpoint, clarification_phase },
  "branch_mismatch": null,
  "capabilities": ["modules/phase-execution.md"]
capabilities exist on disk: True
```

and again with the state planted at a gate:

```
RESUME AT A GATE exit code: 0
  current_phase: gate_spec
  gate: {"gate": "gate_spec", "gate_number": 2, "gate_total": 8,
         "decision": null, "required": null, "requirement_reasons": null}
  capabilities: ['modules/gate-protocol.md']
  gate show agrees on required/reasons: True
  header byte-identical to `header`.rendered: True
```

`required: null` is the engine correctly saying *it has no answer* — this probe
registered no governance record — and `gate show` returns the same `null`, which
is the composition property observed live rather than only in a fixture.

**2. As tests.** N9 is a `run_cli` case (a real subprocess) for **every phase of
three flows**, asserting identity, position, progress, next phase, the header
prefix, the five-key pending set, and that every capability it names exists on
disk. N11 byte-compares `resume`'s `header` against `header`'s `rendered` and
its phase/flow/progress/position/next_phase/label/branch_mismatch against
`state get` and `flow show`. N10 compares the gate block against `gate show`
for all 8 gate phases.

---

## Evidence — every figure re-derived in this context

| Measurement | Result |
|---|---|
| Full suite, **end of M4** | **1502 passed in 1500.93 s, `RAW_EXIT=0`** (`rtk proxy python -m pytest -q -p no:cacheprovider`, redirected, `$?` read with no pipe) |
| `short test summary` sections in that capture | **0** |
| Collected delta M3 → M4 | 1439 → 1502 (+63: the resume matrix and its five siblings) |
| Targeted: `test_units_capabilities.py` | 99 passed, 106.66 s, `RAW_EXIT=0` |
| Targeted: `test_units_cli.py test_units_state.py test_units_flow_model.py test_units_governance.py test_lint_skill.py` | **377 passed**, 333.86 s, `RAW_EXIT=0` |
| `lint-skill` | **39 checks, `failed: []`, exit 0** |
| `git diff --numstat` (in scope) | `sdle-continue.md 8 3`; `sdle-start.md 4 2`; `SKILL.md 45 3`; `gate-protocol.md 3 2`; `phase-execution.md 2 1`; `sdle.py 306 20`; `test_units_gate_policy.py 40 16` |
| Untracked, in scope | `modules/code-review.md`, `modules/design-review.md`, `tests/test_units_capabilities.py` |
| Out of scope, untouched | `.claude/settings.local.json` |
| Python | 3.13.0. Python 3.11: `NOT_RUN` |
| CI | `NOT_RUN` |

## A18 held at M4 — the acceptance criterion of the whole phase

`resume` is the only new command and it writes nothing. Checked three ways:

- N12 takes a SHA map of the **whole project tree** before and after, requires
  it identical, requires `audit.md` byte-identical, requires a planted
  `workflow_version: "1.15"` to still be `"1.15"` afterwards and the absent
  `flow` field still absent — `resume` **reports** GREENFIELD for a pre-v1.16
  state without **migrating** it — and requires `audit verify` to still pass.
- N23 drives a refusal (`workitem_unknown`) and requires `audit.md`
  byte-identical and `audit verify` exit 0.
- No state field, no `VERSION_MIGRATION` row, no version bump, no gate change:
  `lint-skill` still reports `Parsed 21 phases, 8 gates, 16 migration rows` and
  v1.16 at all four locations.

---

## Remaining

- **M5** — the four product agents; `product-agent-fence` in `hooks.py`; the
  three agent lint checks; X1's agents re-valuation; X2; X3; X4; X5; X7;
  N13–N19, N25. Scripts, all dry-run against disk in this context and all
  anchors matching: `m5a_v2.py` (agents + X2), `m5a_x1_agents.py`,
  `m5b_fence.py`, `m5c_firetests.py`. **The single declared red window opens
  and closes inside M5**, before its checkpoint: create the agents, apply
  `m5a_x1_agents.py`, then run
  `pytest tests/test_units_gate_policy.py tests/test_units_artifact_review.py`
  immediately.
- **M6** — `m6_docs.py` + `adr007.md`; the guardrail slice of the test file
  (N20–N22, N24, N26, N27, A20, A21, A25); full suite; `lint-skill`;
  `validate.py`; the acceptance matrix; `T10-handoff-a01.md`; `progress.md` →
  `IMPLEMENTED`.

## Exact resume instruction for a fresh context

1. `git rev-parse HEAD` = `875b361`; `git status --porcelain` matches the list
   above.
2. `python scripts/sdle.py lint-skill` → **39 checks, `failed: []`**.
3. `grep -n "def cmd_resume" scripts/sdle.py` must find it; `ls .claude/agents/`
   must still show **only** the four `sdle-transition-*` files — that is what
   makes the next milestone M5.
4. Re-read each M5 script against disk (`check_anchors.py` dry-runs them all
   without writing), then apply them in the order listed above.

Never run another command while a full suite is in flight: two runs in this
context differed by 4× in wall clock purely from CPU contention.
