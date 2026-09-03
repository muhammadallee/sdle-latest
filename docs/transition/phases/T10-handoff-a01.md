# T10 Implementation Handoff — Attempt a01

**Phase:** T10 — Progressive Claude Skills and Specialist Subagents
**Attempt:** 1
**Implementer context:** fresh/isolated (this handoff written by a **resuming**
implementer; attempt 1 was **not** incremented — the previous run was terminated
by an API session limit, which §24.6 classes as an interruption, not a
verification FAIL)
**Planned at / rollback point:** `adbdc5e`. Product files at `adbdc5e` are
byte-identical to `6318541` (T09's implementation commit) because `adbdc5e`
touched only `docs/transition/`.
**HEAD while implementing:** `875b361009e2c16d66c2a99ebda0d734a45915db`
(OBSERVED, `git log --oneline -3`). Nothing was committed; all work is live in
the working tree.
**Status recommendation:** IMPLEMENTED

---

## Inputs read from disk

`CLAUDE.md`; `docs/transition/transition.md` §16, §22, §24.3, §24.6, TP-003,
TP-011; `docs/transition/progress.md`; `docs/transition/phases/T10-plan.md`
(593 lines, immutable); `T10-checkpoint-a01-01..04`; `T09-verification-a01.md`
(for NB-1); the actual source and tests; `git diff` / `git status`.

**Checkpoint 04 was stale on one point and this was verified against disk before
any edit.** Its resume instruction said `.claude/agents/` "must still show only
the four `sdle-transition-*` files — that is what makes the next milestone M5."
`ls .claude/agents/` showed the four product agents already present, `cmd_resume`
already existed, `lint-skill` already reported 42 checks, and the six test files
M5 amends were already modified. M5 was substantially applied before the cut,
with exactly one thing outstanding: the single failure diagnosed below.

---

## Changes made

Milestones M1–M4 landed in the previous context and are described in
`T10-checkpoint-a01-01..04`. M5 was substantially applied there too. **This
context finished M5 (closing its red window) and did all of M6.** The whole
phase's change set, as it stands on disk:

### `scripts/sdle.py` (+421 / −20)

- `Paths.modules_dir` and `Paths.agents_dir`.
- `Constants.capability_map`, its `parse_md_table(skill_md, "CAPABILITY_MAP")`
  loop in `load_constants`, and its `cmd_constants` key.
- `Constants.capabilities_for(phase)`.
- `gate_disposition(paths, consts, state, gate_key)` — **extracted** out of
  `cmd_gate_show`, whose body now calls it. Two derivations of "does this gate
  need a human approval, and why" would be a second source of truth introduced
  by the phase whose job is defending invariant 7.
- `cmd_resume` + the `resume` parser entry. Read-only; deliberately **not** in
  `RUNTIME_FREE_COMMANDS`, so it refuses exactly where its read-only siblings
  refuse.
- `_skill_files` becomes **derived**: `SKILL.md` + `sorted(modules/*.md)` +
  `product_agent_files(paths)`.
- `product_agent_files(paths)` — `.claude/agents/sdle-*.md` minus
  `sdle-transition-*`.
- Nine new `lint-skill` checks (`_check_capability_map`, `_check_product_agents`).

### Prompt and command layer

- `SKILL.md` (+45 / −3): the `CAPABILITY_MAP` table (21 rows); Step 5 renamed
  *"Capabilities — What to Load"*; Step 6 loads what `capabilities` names; new
  Step 6b on product subagents, carrying the honest sentence
  *"`--actor-name` is a string you supply: the engine records it faithfully and
  cannot verify it."*
- `modules/design-review.md`, `modules/code-review.md` — **new**.
- `modules/gate-protocol.md` (+3 / −2) and `modules/phase-execution.md`
  (+2 / −1): pointer edits only. No block added, removed or renumbered.
- `.claude/commands/sdle-continue.md` (+8 / −3), `sdle-start.md` (+4 / −2):
  call `sdle.sh resume` and load exactly what it names. **Neither names a module
  in prose any more** (`grep -rn 'modules/' .claude/commands/` matches only
  `sdle-approve.md`, which is pre-existing, unchanged and outside the plan's
  file list).

### Agents and hooks

- `.claude/agents/sdle-{discovery,design-review,code-review,security-review}.md`
  — **new**. Each declares `tools: Read, Grep, Glob`, `model: inherit`, and a
  `PreToolUse` hook `python .claude/hooks/hooks.py product-agent-fence` matching
  `Write|Edit|MultiEdit|NotebookEdit|Bash`.
- `.claude/hooks/hooks.py` (+37 / −2): `PRODUCT_AGENT_FENCE_REASON`,
  `product_agent_fence` and the `GUARDS` entry. The guard is **unconditional**.
  `.claude/settings.json` is byte-identical to `adbdc5e` — the fence is
  registered per agent, on purpose.

### Documentation (M6, this context)

- `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md`
  — **new**. §3 carries D12's honesty table verbatim, all ten rows.
- `README.md` (+28 / −5): install list is now five items and names
  `.claude/agents/sdle-*` with an explicit "do not copy the
  `sdle-transition-*` files"; the file-layout tree gains the two capability
  files, the `agents/` entry and "Five guardrail hooks"; the extension note
  after the tree says what adding a capability file costs. **The v1.13 and v1.3
  version-history rows are untouched — they are historical records.**
- `docs/SDLE-Reference-Guide.md` (+20 / −0): §4.1 component tree gains the two
  capability files, the CAPABILITY_MAP note and the product-agent block.
  **The 1.2 history row is untouched.**
- `CLAUDE.md` (+8 / −1): the capability files, `CAPABILITY_MAP`,
  `.claude/agents/`, five guardrail hooks, and an explicit paragraph naming the
  two **Claude Code runtime** enforcement points and the three **convention
  only** items, pointing at ADR-007 §3.

---

## Deliberate behavior changes

| # | Change |
|---|---|
| B1 | `SKILL.md` gains `CAPABILITY_MAP`; Steps 5/6 stop naming a module in prose |
| B2 | `modules/design-review.md` and `modules/code-review.md` exist |
| B3 | Four read-only product subagents exist, fenced by a per-agent hook |
| B4 | `hooks.py` gains a fifth guard, `product-agent-fence`, which denies everything it matches |
| B5 | `sdle resume` — one new **read-only** command |
| B6 | `lint-skill`'s three content checks widen from four hardcoded paths to every capability file and every product agent prompt |
| B7 | `/sdle-continue` and `/sdle-start`'s resume branch call `sdle.sh resume` |
| B8 | ADR-007 plus the README / Reference Guide / CLAUDE.md updates |
| B9 | X1 and X2 amended under TP-003 category 2 |
| B10 | `_searchable_files()` (both copies) gains `.claude/agents/` product prompts |

**What T10 did NOT add, which is the acceptance criterion of the phase:** no
state field, no `VERSION_MIGRATION` row, no version bump, no gate, no gate
semantics change, no policy value, **no mutating command and no new writer.**

---

## Preserved behavior / invariants

| Invariant | Evidence in this context |
|---|---|
| 1 state first | `resume` returns the header verbatim; byte-compared against `header`'s `rendered` (N11) |
| 2 gate discipline | `gate approve/omit/reject` and `advance` untouched. Live: at a planted `gate_constitution`, `gate approve` → `artifact_missing`, `gate omit` → `gate_required`, `advance` → usage, all exit ≠ 0 |
| 3 SpecKit opacity | N28 over every new prompt file; a case-insensitive `speckit` grep over the four agents and the two new capability files matches **nothing** |
| 4 gate content in conversation | Gate presentation stays in `gate-protocol.md`, loaded in the parent. No agent is mapped to, invoked at, or named in a gate decision path (N25) |
| 5 fail safe | `resume` is read-only; no new failure path |
| 6 single writer | **Zero** `write_atomic` / `save_state` / `append_audit` / `.write_text(` / `.write_bytes(` / `os.replace` / `.mkdir(` occurrences changed in `sdle.py` — counts identical at `adbdc5e` and now (30/46/47/0/0/3/6). The fence denies every write a product agent could attempt |
| 7 one source of truth | `CAPABILITY_MAP` exists once; `resume` composes; `gate_disposition` extracted rather than copied; `_skill_files` derived; both `_searchable_files()` copies widened identically |
| 8 gates stay in the parent | Grant + fence + three lint checks + the marker-clause check. The three gate verbs appear in an agent prompt only inside the sentence forbidding them; the test removes that sentence and requires the rest to be silent |
| Claude cannot lower a deterministic floor | No policy value is read, written or restated by anything T10 adds; `test_no_policy_default_value_is_restated_outside_sdle_py` passes with `.claude/agents/` now in its search set |
| GREENFIELD frozen | `GREENFIELD_V1_PHASES` == the AST-extracted literal at `adbdc5e`, 19 entries; `FLOW_PHASES` parsed at `adbdc5e` == parsed now |
| Transcripts / integrations byte-identical | The three integration files and all ten `docs/dry-runs/*.md` compared to `adbdc5e`, line endings normalised |
| Legacy dual-read; `migrate-workflow` never mutates `.workflow/` | N22 drives both |
| Core refuses, does not warn | `lint-skill` exits 1 with a named failing check; the fence returns `deny` |

---

## Test changes and TP-003 classification

**Three categories only. Zero `D` and zero `R` under `tests/`**
(`git diff --numstat --diff-filter=DR -- tests/` → 0 lines). Zero
`pytest.mark.skip`, `pytest.mark.xfail`, `pytest.skip(` or `@pytest.mark.skipif`
added anywhere. No test function was removed; the two that disappear by name
were **renamed**, and both renames are recorded below.

| Test | X row | Category | Rationale |
|---|---|---|---|
| `test_units_gate_policy.py::test_n31_no_t10_or_t11_leakage` → `test_t10_ships_exactly_the_declared_agents_skills_and_modules` + `test_n31_no_t11_leakage` | X1 | **2 — deliberately superseded** | It asserted T10's *absence*. T10 has landed. Split as the plan directs; the T11 half moved verbatim, message strings included |
| `test_units_artifact_review.py::test_t06_creates_no_subagent` → `test_the_engine_invokes_no_agent` | X2 | **2** | The bare `"subagent"` substring ban is retired (linting agent files honestly needs the word) and replaced by a **structural** AST assertion: the set of functions containing a spawn call is exactly `["git", "run_tests"]`, and no string argument to any of them names `claude`, `agent` or `Task`. `Task(`, `launch_agent` and the stdlib-only assertion all stay |
| `test_units_governance.py::_searchable_files()` | X3 | **2** | `.claude/agents/` added. `sdle-transition-*` excluded, with the reason recorded in the helper: `sdle-transition-planner.md` legitimately uses the transition contract's OBSERVED/INFERRED/UNKNOWN vocabulary, spelled exactly like §14's classifications |
| `test_units_discovery.py` `searchable_files()` | X4 | **2** | Followed X3 so the two copies do not diverge |
| `test_lint_skill.py::repo` fixture | X5 | **2** | Copies `.claude/agents/`; without it the three agent checks pass vacuously |
| `test_lint_skill.py::test_the_repo_passes_every_check` | X6 | — | **No change needed**, as the plan predicted. Recorded so the verifier knows it was considered |
| `test_hooks.py` | X7 | **1 — additive** | A `frontmatter_command()` sibling to `registered()`. The settings.json-based resolvers are unchanged |
| `test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical` | **X-GEN** | **2** | See the section below — the only item this context had to decide |
| `tests/test_units_capabilities.py` | new file | **1 — additive** | 159 collected cases |

### X-GEN-1 — the one failure, its category, and the call

Observed here **before touching anything**, `rtk proxy "python -m pytest
tests/test_units_gate_policy.py -q -p no:cacheprovider"`, redirected, `$?` read
with no pipe: **`RAW_EXIT=1`, `1 failed, 363 passed in 149.94s`.** One failure,
naming one file:

```
FAILED tests/test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical
E  AssertionError: .claude/hooks/hooks.py
E  - Four guardrails that execute regardless of what the model decides.
E  + Five guardrails that execute regardless of what the model decides. …
```

It is **T09's** test, pinning the whole `.claude/hooks/` directory to
`ROLLBACK = "e1cf341"` with the docstring *"hooks are tripwires and T09 added no
fence."* T10's plan **B4** requires a fifth guard in `hooks.py`, so the
assertion is false **by design**: **TP-003 category 2**, not a regression.

**Classified X-GEN, deliberately, and not a blocker.** X-GEN's shape is *"any
test that enumerates a closed set this phase legitimately grows"*; this pins a
closed set — the inventory and content of `.claude/hooks/` — that B4
legitimately grows by exactly one guard, and the examples listed after X-GEN's
dash are illustrative of that shape rather than an exhaustive allow-list. All
three X-GEN conditions are met: **(a)** the assertion keeps its shape, exact
equality against a written-out set, never relaxed to a subset, a prefix or an
`any`; **(b)** the literals are recorded verbatim below; **(c)** nothing is
deleted, only re-valued and subdivided. **No `T10-blocker.md` is warranted**
because there is no material decision: the plan mandates the fifth guard and
simultaneously mandates (F2, N27) that no hook change go unnoticed, which leaves
exactly one defensible resolution.

**On T09 NB-1.** NB-1 found T09's implementer recording extra X rows instead of
escalating, and its own recommendation to the orchestrator was that *"future
plans should carry a generic X row for closed-set assertions that must name a
newly added command, so this class of change is authorised rather than requiring
a judgement call mid-flight."* T10's plan carries exactly that row. Using it is
following NB-1's remedy; the error at T09 was that no such row existed.

**Old literal, verbatim:**

```python
def test_n28_the_hooks_are_byte_identical():
    """A10: hooks are tripwires and T09 added no fence. Whole directory, so a
    new hook file would fail here rather than pass unnoticed."""
    hooks = sorted((REPO_ROOT / ".claude" / "hooks").rglob("*"))
    present = sorted(p.relative_to(REPO_ROOT).as_posix()
                     for p in hooks if p.is_file())
    assert present, "the hooks directory has gone missing"
    for relative in present:
        original = at_rollback(relative)
        assert original is not None, relative
        assert here(relative) == original, relative
```

**New literal, verbatim** — same function name, same file, **same
`ROLLBACK = "e1cf341"`** (the baseline is *not* moved; every other user of it —
`FROZEN_FILES`, the dry-run transcripts, `test_the_rollback_point_is_reachable`
— is untouched):

```python
HOOKS_FILE = ".claude/hooks/hooks.py"
HOOK_FILES = (HOOKS_FILE,)
T09_GUARDS = ("write-fence", "untrusted-read", "dirty-tree", "secrets-scan")
T10_GUARD_ADDITIONS = ("product-agent-fence",)
T10_HOOK_ADDITIONS = ("PRODUCT_AGENT_FENCE_REASON", "product_agent_fence")
```

1. `assert present == sorted(HOOK_FILES)` — the file list. T10 adds no hook
   file, so the original sentence survives intact and is now **stronger**: it
   was `assert present, "…"`, a non-emptiness test that would have accepted a
   new file, and it is now an enumeration.
2. Every hook file **other than** `hooks.py` still byte-identical to
   `at_rollback(relative)` — unchanged assertion, unchanged baseline.
3. Inside `hooks.py`, AST-parsed top-level definitions: the **name set** is
   exactly T09's plus `T10_HOOK_ADDITIONS`, and every definition T09 pinned is
   compared **byte-for-byte one at a time** via `ast.get_source_segment`.
   `GUARDS` is the single exemption and is pinned by rule 4.
4. `_registered_guards(...) == list(T09_GUARDS + T10_GUARD_ADDITIONS)` — by name
   **and order**, read out of the source rather than by importing, so a guard
   that is defined but never wired still fails.

**Proved to still fire** (`<scratchpad>/fire_n28.py` — mutate the real tree, run
the one test, restore in a `finally`, verify by SHA-256):

```
baseline sha256: 78528b8d6ad82740b0643ef7821ef26e614bf82ca4b1ef1458de01ca49c62494
UNMUTATED: (0, '1 passed in 0.45s')
A stray hook file       -> (1, '1 failed in 0.30s')
An edited write_fence   -> (1, '1 failed in 0.48s')
Fence defined not wired -> (1, '1 failed in 0.54s')
A stray module constant -> (1, '1 failed in 0.45s')
restored sha256: 78528b8d6ad82740b0643ef7821ef26e614bf82ca4b1ef1458de01ca49c62494 MATCH
RESTORED: (0, '1 passed in 0.31s')
```

### X1's literals, recorded to the same standard

Old: `stray = [name for name in agents if not name.startswith("sdle-transition-")]`
then `assert stray == [], stray`; and
`assert modules == ["gate-protocol.md", "phase-execution.md", "security-review.md"], modules`.

New: `assert agents == ["sdle-code-review.md", "sdle-design-review.md",
"sdle-discovery.md", "sdle-security-review.md", "sdle-transition-implementer.md",
"sdle-transition-orchestrator.md", "sdle-transition-planner.md",
"sdle-transition-verifier.md"], agents`; and
`assert modules == ["code-review.md", "design-review.md", "gate-protocol.md",
"phase-execution.md", "security-review.md"], modules`.
`skills == ["apply-sdle-transition", "sdle"]` is **unchanged** — T10 adds no
skill directory. The agent assertion is strictly stronger than what it replaced:
`stray == []` said nothing about which control-plane files exist.

### X2's literals

Old: `for forbidden in ("Task(", "subagent", "launch_agent"):`
New: `for forbidden in ("Task(", "launch_agent"):`, **plus** the structural
assertion `sorted({where for where, _, _ in sites}) == ["git", "run_tests"]` and
`named == []`.

---

## Commands actually run

Every pytest invocation went through `rtk proxy`, redirected to a file, with
`$?` read on the next line and **no pipe**. Nothing else ran while the full
suite was in flight.

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider"` (**full suite, final**) | **`1616 passed in 1543.13s (0:25:43)`, `RAW_EXIT=0`** | `grep -c 'short test summary'` over the capture = **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **1616 tests collected in 1.08s**, `RAW_EXIT=0` | collected == passed |
| Same, in a `git worktree` at `adbdc5e` | **1402 tests collected in 0.44s**, exit 0 | The baseline re-derived here, not inherited. Delta **+214**, entirely from four files: `test_units_capabilities.py` 0→159, `test_hooks.py` 44→88, `test_lint_skill.py` 39→49, `test_units_gate_policy.py` 363→364. **No file decreased.** |
| `rtk proxy "python -m pytest tests/test_units_gate_policy.py -q -p no:cacheprovider"` (before the fix) | `1 failed, 363 passed in 149.94s`, `RAW_EXIT=1` | The X-GEN-1 failure, observed first-hand |
| M5 targeted: `test_units_gate_policy.py test_units_artifact_review.py test_hooks.py test_lint_skill.py test_units_capabilities.py test_units_governance.py test_units_discovery.py` | **907 passed in 571.41s**, `RAW_EXIT=0` | red window closed |
| `rtk proxy "python -m pytest tests/test_units_capabilities.py -q -p no:cacheprovider"` | **159 passed in 112.04s**, `RAW_EXIT=0` | after the M6 slice |
| `rtk proxy "python scripts/sdle.py lint-skill"` | **42 checks, `failed: []`**, `LINT_EXIT=0` | `Parsed 21 phases, 8 gates, 16 migration rows.`; `all four locations report v1.16` |
| Same, in a worktree at `adbdc5e` | **33 checks, `failed: []`**, exit 0 | the E3 baseline re-derived here; 33 + 9 = 42, and all 33 names are still present |
| `rtk proxy "python tools/transition/validate.py"` | `TRANSITION_VALID: complete=10/12 next=T10`, `VALIDATE_EXIT=0` | run before the `progress.md` update; re-run after (below) |
| `rtk proxy "python scripts/sdle.py constants"` | 21 `capability_map` rows; union = the five `modules/*.md` on disk; 15 rows of size 1, 6 of size 2 | every row a **strict** subset of a 5-member union |
| `<scratchpad>/live_t10.py` | see "Reproductions" | the §16 exit criterion, the refusal/ledger property, the fence battery, and `lint-skill` firing — all through the real CLI |
| `<scratchpad>/live_gate.py` | see "Reproductions" | the same refusal property with the state actually **at** a gate |
| `<scratchpad>/fire_n28.py` | 4/4 mutations fail, tree restored byte-exactly | X-GEN-1 still fires |
| `<scratchpad>/fire_a25.py` | 4/4 softenings fail, files restored byte-exactly | the honesty table cannot be quietly upgraded |
| **Python 3.11** | **NOT_RUN** | this machine is Python **3.13.0** |
| **CI (`ubuntu-latest` / `windows-latest`)** | **NOT_RUN** | never observed at any point in this migration; no outcome predicted |

### Reproductions, verbatim

**1. §16's exit criterion — a brand-new OS process, no arguments of any kind.**
A realistic install built in a temp directory (skill root, engine, hooks,
agents, `settings.json`), a WorkItem created and initialised through the
ordinary commands, then `python scripts/sdle.py resume` invoked as a fresh
process with **no `--workitem`, no `--project-root`, no `--skill-root`** and no
history:

```
exit: 0
  workitem: 'cold-start-item'      flow: 'GREENFIELD'
  current_phase: 'constitution_draft'   status: 'pending'
  progress: '2/18'   position: 2   next_phase: 'gate_constitution'
  label: 'Generate Constitution'   branch_mismatch: None   gate: None
  capabilities: ['modules/phase-execution.md']
  header: <!-- SDLE_STATE phase=constitution_draft status=pending progress=2/18 -->…
  pending keys: ['clarification_phase', 'drift_queue', 'pending_confirm_action',
                 'pending_phase', 'phase_checkpoint']
  every capability exists on disk: [('modules/phase-execution.md', True)]
  modules on disk: ['code-review.md','design-review.md','gate-protocol.md',
                    'phase-execution.md','security-review.md']
  loaded a strict subset: True
```

and again launched from a **subdirectory** with no flags: `exit 0`, phase
`constitution_draft`. *Only relevant phase context* is not a claim here; it is
one of five files.

With the state planted at `gate_constitution`:

```
resume: exit 0  capabilities ['modules/gate-protocol.md']
gate: {"gate":"gate_constitution","gate_number":1,"gate_total":8,
       "decision":null,"required":true,"requirement_reasons":["always"]}
```

**2. A refusal leaves `audit.md` byte-identical; `audit verify` exits 0.**
Driven at `gate approve` and `skip` as required, and at three more verbs:

```
audit.md sha256 before: 9ee784ec9acf20a1c626f7eb32cbe969de6f57f7c904b9ea28e6c9cff0be6c7a
  gate approve --gate gate_spec              exit=1 not_at_gate            identical=True verify=0
  gate approve --gate gate_constitution      exit=1 artifact_missing       identical=True verify=0
  gate omit    --gate gate_constitution      exit=1 gate_required          identical=True verify=0
  gate reject  --gate gate_spec --reason no  exit=1 not_at_gate            identical=True verify=0
  skip                                       exit=1 not_failed             identical=True verify=0
  advance                                    exit=2 (usage)                identical=True verify=0
audit.md sha256 after : 9ee784ec9acf20a1c626f7eb32cbe969de6f57f7c904b9ea28e6c9cff0be6c7a
```

(and, before initialisation, `skip --confirm` → `no_pending_confirmation`,
`advance --to implement` → `forward_jump`, both ledger-identical, verify 0.)

**3. The fence denies, driven from the exact frontmatter command string.**
For each of the four agents the frontmatter command was extracted by regex and
run as a real subprocess against a 12-payload battery — `Write` to
`state.json`, `Edit` to `audit.md`, `Write` to `workitems/index.md`, `Write` to
an ordinary source file, `Bash` running `gate approve`, `gate omit`, `advance`,
`echo hello`, `MultiEdit`, `NotebookEdit`, a `Write` with **no path**, and an
**empty payload**:

```
product agents: ['sdle-code-review.md','sdle-design-review.md',
                 'sdle-discovery.md','sdle-security-review.md']
  each: command='python .claude/hooks/hooks.py product-agent-fence'
        every payload denied: True   n = 12   not denied: []
```

Every one returned exit 0 with `permissionDecision == "deny"` and a reason
naming **both** invariant 6 and invariant 8. It never fails open.

**4. `lint-skill` fires when a grant widens or the fence is stripped.**

```
  clean:                      exit=0 checks=42 failed=[]
  grant widened to Bash       exit=1 checks=42 failed=['product_agents_are_read_only']
  grant widened to Write      exit=1 checks=42 failed=['product_agents_are_read_only']
  fence stripped              exit=1 checks=42 failed=['product_agents_declare_the_fence']
  fence line deleted          exit=1 checks=42 failed=['product_agents_declare_the_fence']
  restored:                   exit=0 checks=42 failed=[]
```

---

## Git evidence

- **HEAD:** `875b361009e2c16d66c2a99ebda0d734a45915db` on
  `transition/workitem-v1`. **Nothing committed by this phase.**
- **Working tree — modified (`git diff --numstat`):**
  `.claude/commands/sdle-continue.md 8 3`; `.claude/commands/sdle-start.md 4 2`;
  `.claude/hooks/hooks.py 37 2`; `.claude/skills/sdle/SKILL.md 45 3`;
  `.claude/skills/sdle/modules/gate-protocol.md 3 2`;
  `.claude/skills/sdle/modules/phase-execution.md 2 1`; `CLAUDE.md 8 1`;
  `README.md 28 5`; `docs/SDLE-Reference-Guide.md 20 0`; `scripts/sdle.py 421 20`;
  `tests/test_hooks.py 120 0`; `tests/test_lint_skill.py 129 0`;
  `tests/test_units_artifact_review.py 64 5`;
  `tests/test_units_discovery.py 14 0`; `tests/test_units_gate_policy.py 122 20`;
  `tests/test_units_governance.py 14 0`.
- **Working tree — untracked:** the four `.claude/agents/sdle-*.md` product
  agents; `.claude/skills/sdle/modules/{code-review,design-review}.md`;
  `docs/architecture/ADR-007-…md`; `tests/test_units_capabilities.py`;
  `docs/transition/phases/T10-checkpoint-a01-01..05.md`; this handoff.
- **Out of scope and not touched by this phase:** `.claude/settings.local.json`
  (untracked local state; it was already modified when this context started).
- **Byte-identical to `adbdc5e`, asserted by test and re-checked here:**
  `.claude/settings.json`, `.claude/skills/sdle/templates/state.json`,
  `.gitignore`, the three `tests/test_integration_*.py`, all ten
  `docs/dry-runs/*.md`.
- **Diff scope:** no file outside the plan's "Files expected to change" list was
  modified. Nothing under `tools/`, `.github/`, `.claude/agents/sdle-transition-*`
  or `docs/transition/phases/T00..T09-*` changed.

---

## Acceptance criteria

| # | Verdict | Evidence |
|---|---|---|
| A1 | **PASS** | `constants` reports `capability_map` with **21** rows, one per registry phase; `lint-skill` fails loudly on a missing/unknown row and on a renamed or emptied heading (N1, N8, and two `assert_only_failure` fire-tests) |
| A2 | **PASS** | Every path exists; `SKILL.md` is never a value, and naming it fires `capability_map_never_names_the_orchestrator` |
| A3 | **PASS** | Union = exactly the five `modules/*.md` on disk; max row size 2 < 5; 15 rows of size 1; an orphan module fires `every_capability_file_is_linted` |
| A4 | **PASS** | Every gate phase's row contains `modules/gate-protocol.md`; no non-gate phase's does (N4) |
| A5 | **PASS** | `capability_cross_references_are_mapped_files`; a pointer at an unmapped file fires it |
| A6 | **PASS** | N9 runs a fresh subprocess for **every phase of three flows** — GREENFIELD, BROWNFIELD_DISCOVERY, HOTFIX — whose union is asserted to be exactly the 21-phase registry; plus the live cold-start probe above |
| A7 | **PASS** | N10 over all 8 gate phases; live at a planted gate, `required: true`, `requirement_reasons: ["always"]`, identical to `gate show` |
| A8 | **PASS** | N11 byte-compares the header and every shared field; `gate_disposition` is extracted, not copied |
| A9 | **PASS** | N12 (whole-tree SHA map, `audit.md` bytes, a planted `workflow_version: "1.15"` still `"1.15"` afterwards), N23, and the live refusal battery |
| A10 | **PASS** | `grep -rn 'modules/' .claude/commands/` matches only `sdle-approve.md`, which is pre-existing and outside the plan's file list. Neither `/sdle-continue` nor `/sdle-start` names a module in prose |
| A11 | **PASS** | 12-payload battery × 4 agents, all `deny`, driven from each agent's own frontmatter string — as a test and again live |
| A12 | **PASS** | No path, empty payload, malformed payload, unknown tool: all deny. The guard is unconditional and has no early return |
| A13 | **PASS** | All four grant exactly `Read, Grep, Glob`; none names `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Agent` or `Task` |
| A14 | **PASS** | `assert_only_failure` fire-tests for all three agent checks, plus the live four-mutation probe |
| A15 | **PASS** | N19 both halves: the real tree has exactly 4 + 4 agents; with `.claude/agents/` removed the three checks are **absent**, and `with_agents - names == agent_checks` proves nothing else vanished |
| A16 | **PASS** | `test_the_engine_invokes_no_agent`: spawn sites confined to `git` and `run_tests`; no spawn argument names `claude`, `agent` or `Task`; stdlib-only; `Task(` and `launch_agent` still banned |
| A17 | **PASS** | N25 over every agent prompt and every capability row |
| A18 | **PASS** | Occurrence counts of eight write primitives in `sdle.py` **identical** at `adbdc5e` and now; `add_parser` names gained exactly `{"resume"}` and lost none; no state field, no migration row, no version bump |
| A19 | **PASS** | All 33 baseline checks present by name (enumerated literal, exact equality against the 33 + 9 union) and passing; `failed: []` |
| A20 | **PASS** | `_skill_files` derived; covers `SKILL.md`, every module and all four product agents; excludes the control plane by prefix |
| A21 | **PASS** | Both `_searchable_files()` copies cover the product agents. **The narrowing is documented**, in the helper and here: `sdle-transition-*` is excluded because `sdle-transition-planner.md` legitimately uses the transition contract's OBSERVED/INFERRED/UNKNOWN vocabulary |
| A22 | **PASS** | The three integration files and all ten dry-run files byte-identical to `adbdc5e`, line endings normalised |
| A23 | **PASS** | `settings.json`, `templates/state.json`, `.gitignore` byte-identical; v1.16; 16 migration rows; 8 approvals keys == the gate-key set; 21 phases; 8 gates; `GREENFIELD_V1_PHASES` == the AST literal at `adbdc5e`, 19 entries; `FLOW_PHASES` parsed at `adbdc5e` == parsed now |
| A24 | **PASS** | N28 (no `speckit` in any new prompt file); `test_hooks.py`'s pre-existing cases unmodified — every baseline definition byte-identical by AST; N22 for the legacy rung |
| A25 | **PASS** | ADR-007 §3 carries all ten D12 rows; the three "convention only" rows are intact; the two runtime rows say **Claude Code runtime — *not* SDLE**. `CLAUDE.md` names both runtime points and the three conventions. `SDLE_ACTOR` is recorded as rejected. Four softening mutations each fail a test |
| A26 | **PASS** | Full suite `1616 passed`, `RAW_EXIT=0`; `lint-skill` `failed: []`, exit 0; `validate.py` exit 0. All redirected, `$?` read with no pipe |
| A27 | **PASS** | Every changed test is in X1–X7 or matches X-GEN. The one X-GEN item records old and new literals verbatim above |

---

## Known limitations / risks

1. **Two of the three enforcement layers are not SDLE's, and the documentation
   says so rather than hiding it.** That a declared `tools:` list is applied and
   that a frontmatter `PreToolUse` hook fires are **Claude Code runtime**
   guarantees. Both were observed live during this migration (the T10 planner
   session was refused verbatim by `agent_guard.py`, and its own tool set was
   exactly its declared list), but neither is assertable from the suite. If a
   future runtime ignored either, the suite would stay green. ADR-007 §3,
   `CLAUDE.md` and `test_a25_*` are the whole mitigation.
2. **Three things remain convention only** and T10 changed none of them: that
   the parent delegates at all; that `--actor-name` truthfully names the
   producer; that a human rather than the orchestrator typed `approve`. Two
   predate T10 (ADR-003, ADR-006). The risk T10 introduces is *perceptual* —
   named specialist agents make a reader think those rows moved. They did not.
3. **`sdle-approve.md` still names two module paths in prose.** Pre-existing,
   unchanged, outside the plan's file list, and A10 binds only `/sdle-continue`
   and `/sdle-start`. Recorded as an observation, not adopted.
4. **Python 3.11 and CI are `NOT_RUN`.** No outcome is predicted for either.
   T10 adds no dependency and no new syntax level.
5. **`ADR-001` still says "Four hooks enforce guardrails".** It is a historical
   record of a decision taken when there were four, and rewriting an accepted
   ADR retroactively would be worse than leaving it. ADR-007 extends it.
   Likewise the `README` v1.13/v1.3 rows and the Reference Guide 1.2 row.
6. **The full suite takes ~26 minutes** and its wall clock varies ~4× with CPU
   contention. Nothing else was run while it was in flight.

---

## Claims for the verifier to independently check

1. **The diff contains no new writer.** Re-derive it: occurrence counts of
   `write_atomic`, `save_state`, `append_audit`, `record_audit`, `.write_text(`,
   `.write_bytes(`, `os.replace`, `.mkdir(` in `scripts/sdle.py` at `adbdc5e`
   and now — `write_atomic` 30, `save_state` 46, `append_audit` 47,
   `record_audit` 0, `.write_text(` 0, `.write_bytes(` 0, `os.replace` 3,
   `.mkdir(` 6, identical on both sides. `add_parser` gained exactly `resume`.
2. **The exit criterion through the real CLI**, not through the fixture: build an
   install, create and init a WorkItem, then run `python scripts/sdle.py resume`
   as a fresh process from the project root *and* from a subdirectory with no
   flags.
3. **The fence battery**, driven from the frontmatter string rather than from a
   literal in the test.
4. **`lint-skill` fires** on a widened grant and a stripped fence, and the three
   agent checks go **absent** (not passing) when `.claude/agents/` is removed.
5. **X-GEN-1 still fires**: add a stray file to `.claude/hooks/`, edit
   `write_fence`, unwire the fence from `GUARDS`, add a module-level constant —
   each must fail `test_n28_the_hooks_are_byte_identical`.
6. **A25 cannot be softened**: promote any "Convention only" or "Claude Code
   runtime" row in ADR-007 §3 to `**SDLE**`, or delete SKILL.md's "cannot verify
   it" caveat — each must fail.
7. **Zero `D`/`R` under `tests/`**, zero skips/xfails added, and the per-file
   collected delta 1402 → 1616 with no file decreasing.
8. **No T11 leakage**: `legacy_workflow`, `current_feature_id` and
   `SDLE_OWNED_PREFIXES` still present; `.sdle` still absent from
   `SDLE_OWNED_PREFIXES`; the `branch_guard` window, the HIGH→LOW asymmetry and
   `phase-execution.md`'s stale `.workflow/` path all untouched.

## Blocker

**None.** No material decision was required. The single failure encountered was
a foreseeable, plan-authorised closed-set re-valuation (X-GEN-1), resolved
without weakening any assertion.
