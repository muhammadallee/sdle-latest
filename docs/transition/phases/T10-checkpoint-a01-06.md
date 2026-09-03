# T10 checkpoint — attempt 01, milestone M6

**Phase:** T10 · **Attempt:** 1 · **Milestone:** M6 — documentation, the guardrail test slice, and the phase close
**Milestone status:** COMPLETE. **The phase is IMPLEMENTED.**
**HEAD:** `875b361` (OBSERVED). Nothing committed; all work is live in the working tree.

The full record is `docs/transition/phases/T10-handoff-a01.md`. This checkpoint
exists so a fresh context can tell, from disk alone, that M6 finished and what
it consisted of.

---

## What M6 added

### Documentation

- `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md`
  — **new**. §3 is D12's honesty table verbatim: five **SDLE**-enforced rows,
  two **Claude Code runtime — *not* SDLE** rows, three **Convention only** rows.
  §3.1 records the rejected `--actor` / `SDLE_ACTOR` attestation and why a
  caller-set flag refuses the compliant caller and lets the other through.
  §3.2 records that the approval path was deliberately not made agent-aware.
- `README.md` — install list is five items and names `.claude/agents/sdle-*`
  with an explicit "do not copy the `sdle-transition-*` files"; the layout tree
  gains the two capability files, an `agents/` entry and "Five guardrail hooks";
  the extension note says what adding a capability file costs. The v1.13 and
  v1.3 **version-history rows were not touched**.
- `docs/SDLE-Reference-Guide.md` §4.1 — the two capability files, the
  CAPABILITY_MAP note, and the product-agent block. The 1.2 history row is
  untouched.
- `CLAUDE.md` — capability files, `CAPABILITY_MAP`, `.claude/agents/`, five
  guardrail hooks, and a paragraph naming the two Claude Code runtime
  enforcement points and the three convention-only items, pointing at ADR-007 §3.
- `docs/architecture/ADR-001` was **deliberately left alone** where it says
  "Four hooks enforce guardrails": it is a historical record of a decision taken
  when there were four.

### Tests appended to `tests/test_units_capabilities.py`

`BASELINE = "adbdc5e"`, `at_baseline()`, `here()`, a reachability guard, and:
N20 (three integration files + all ten `docs/dry-runs/*.md`), N21 (GREENFIELD
against the AST literal at the baseline, and FLOW_PHASES parsed on both sides
with the engine's own parser), N22 (legacy dual-read and `migrate-workflow`),
N24 (schema numbers, plus the A18 write-primitive count comparison and its
non-vacuity guard), N26 (the 33 baseline check names written out, exact equality
against the 33 + 9 union), N27 (every pre-existing top-level definition in
`hooks.py` and `tests/test_hooks.py` byte-identical by AST), and the A25 slice:
the ADR row-by-row enforcement labels, CLAUDE.md's runtime attribution, an
overstatement scan across fourteen shipped files, and a needle non-vacuity
guard.

---

## Evidence — every figure re-derived in this context

| Measurement | Result |
|---|---|
| **Full suite** | **`1616 passed in 1543.13s (0:25:43)`, `RAW_EXIT=0`** |
| `short test summary` sections in that capture | **0** |
| `--collect-only` | **1616**, so collected == passed |
| Baseline `--collect-only` in a `git worktree` at `adbdc5e` | **1402**. Delta **+214**: `test_units_capabilities.py` 0→159, `test_hooks.py` 44→88, `test_lint_skill.py` 39→49, `test_units_gate_policy.py` 363→364. **No file decreased** |
| `lint-skill` | **42 checks, `failed: []`**, exit 0; `Parsed 21 phases, 8 gates, 16 migration rows.`; `all four locations report v1.16` |
| `lint-skill` at `adbdc5e`, in a worktree | **33 checks, `failed: []`**, exit 0 — the E3 baseline observed here, not inherited |
| `validate.py` | `TRANSITION_VALID: complete=10/12 next=T10`, exit 0, both before and after the `progress.md` update |
| `constants` | 21 `capability_map` rows; union = the five `modules/*.md` on disk; 15 rows of size 1, 6 of size 2 — every row a strict subset |
| `git diff --numstat --diff-filter=DR -- tests/` | **0** |
| Skip/xfail markers added | **0** (`pytest.mark.skip`, `pytest.mark.xfail`, `pytest.skip(`, `@pytest.mark.skipif` all 0 across the changed files) |
| Test functions removed | **0**. Two renames: `test_n31_no_t10_or_t11_leakage` (split, X1) and `test_t06_creates_no_subagent` (X2) |
| Python | 3.13.0. **Python 3.11: NOT_RUN. CI: NOT_RUN** |

## Live reproductions, all through the real CLI

1. **§16's exit criterion** — a brand-new OS process with no `--workitem`, no
   `--project-root`, no `--skill-root`, run from the project root *and* from a
   subdirectory: exit 0, identity/position/pending returned, `capabilities`
   `['modules/phase-execution.md']` — one of the five modules on disk.
2. **Refusals leave the ledger byte-identical.** At a planted
   `gate_constitution`: `gate approve` → `artifact_missing`, `gate omit` →
   `gate_required`, `gate reject` → `not_at_gate`, `skip` → `not_failed`,
   `advance` → usage. `audit.md` SHA-256 unchanged throughout; `audit verify`
   exit 0 after every one.
3. **The fence.** 4 agents × 12 payloads driven from each agent's own
   frontmatter command string: **48/48 denied**, every reason naming invariant 6
   and invariant 8, including the no-path and empty-payload cases.
4. **`lint-skill` fires**: a widened grant (`Bash`, then `Write`) fails
   `product_agents_are_read_only`; a stripped fence and a deleted fence line
   both fail `product_agents_declare_the_fence`. Clean before and after.
5. **The A25 honesty table cannot be softened**: promoting either runtime row or
   any convention row to `**SDLE**`, or deleting SKILL.md's "cannot verify it"
   caveat, each fails a test. Files restored byte-exactly.

---

## Phase state

- `docs/transition/phases/T10-handoff-a01.md` — written.
- `docs/transition/progress.md` — T10 row set to **IMPLEMENTED**, attempt 1,
  handoff linked, verification `-`. `validate.py` still exits 0.
- **No `T10-blocker.md`.** No material decision was required.
- **Nothing committed.** The next actor is the verifier.

The one judgement call this attempt had to make is recorded in full in
checkpoint 05 and in the handoff: T09's `test_n28_the_hooks_are_byte_identical`
was superseded by plan B4's fifth hook guard, classified **TP-003 category 2 /
X-GEN** rather than escalated to a blocker, re-valued without moving its
baseline or relaxing any assertion, and proved to still fire.
