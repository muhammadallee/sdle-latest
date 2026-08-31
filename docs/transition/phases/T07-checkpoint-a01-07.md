# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 07

**Phase:** T07
**Attempt:** 01 (resumed after an API session limit — an interruption per §24.6,
**not** a verification FAIL; the attempt number is unchanged)
**Milestone completed:** **M7** — `flow show`, `constants.flows`, the remaining
prompt and documentation layer, ADR-004, the dry-run disposition, `sdle-restart.md`.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M7 is complete and green. Next objective is **M8**: the full suite, `lint-skill`,
`validate.py`, the must-not-change `git diff --exit-code`, the write-fence probe
(F7), the A1–A26 acceptance matrix, then `T07-handoff-a01.md` and `progress.md`
→ `IMPLEMENTED`.

## What was already on disk when this context started, and what it added

The previous context was cut **inside** M7, not at its start. Reconstructed from
the working tree rather than from prose, the following M7 deliverables were
already present and were **verified, not redone**:

| M7 item | State on arrival | Verified how |
|---|---|---|
| `cmd_flow_show` + its `flow`/`show` parser registration | present | `grep -n cmd_flow_show scripts/sdle.py` → definition at the `cmd_sha`/`cmd_constants` boundary and `flow_show.set_defaults(handler=cmd_flow_show)` in `build_parser` |
| `constants` gains `flows` | present | the `"flows": {name: built.as_dict() …}` key in `cmd_constants` |
| N25 (`flow show`) tests | present, 4 of them | `grep -n "flow show" tests/test_units_flow_model.py` → `test_flow_show_reports_the_bound_flow_and_where_it_is`, `…_makes_a_disagreement_visible_before_it_refuses`, `…_writes_nothing`, `…_before_init_says_so_and_writes_nothing`; `flow show` is also in `test_no_read_only_command_writes_the_flow`'s sweep, as checkpoint 06 required |
| `docs/architecture/ADR-004-declarative-flow-model.md` | present, complete | read in full: all seven decisions, every rejected alternative, both human decisions, the declared divergences |
| `docs/dry-runs/README.md` disposition | present | `git diff` shows **+6 / −0**, a single appended `## Disposition under the flow model (v1.16)` section; no transcript touched |
| `.claude/commands/sdle-restart.md` | present | `argument-hint` is `"<phase number>"`; the restated `1-18` is gone (E42/D16) |
| SKILL.md flow paragraph, `### FLOW_PHASES`, retitled heading | present | in `git diff` |
| `phase-execution.md` traversal instruction | present | the `> **Execute only the phases the bound flow contains.**` block |
| `gate-protocol.md` `{gate_total}` | present (M5) | in `git diff` |
| `README.md` / Reference Guide flow sections | present | in `git diff` |
| **`CLAUDE.md`** | **absent — not started** | not in `git status` |

So M7's outstanding work was `CLAUDE.md` plus a sweep for prose the change makes
untrue that the earlier pass had not reached. Both are below.

### `CLAUDE.md` — the plan's one untouched documentation file

`git diff --numstat -- CLAUDE.md` = **22 / 7**. Five edits, each a fact T07
changes:

1. **The headline sentence** (E39 names this site). "a gated 18-phase SDLC
   workflow" loses the ordinal, and a new paragraph states the model: a
   20-entry registry, a flow as an ordered subset, five flows, GREENFIELD
   frozen in `GREENFIELD_V1_PHASES` *rather than declared in a table so a new
   registry row can never silently join it*, and the ten-phase mandatory floor.
   It points at ADR-004.
2. `scripts/sdle.py` "owns …" gains **flow selection** at the head of the list.
3. "nothing in the 18-phase flow reads it" → "nothing in any lifecycle flow
   reads it". `flow` is a defined term now; the old wording reads as a flow name.
4. **The cross-file sync list**, which is the file's operational content:
   - the old bullet "the four phase tables cover an identical phase set" is
     **split**, because they no longer do. NEXT_PHASE and PHASE_LABEL_MAP cover
     the registry; **PROGRESS_MAP covers the GREENFIELD flow**. Re-targeting
     that check was M2's work and this is the sentence that records it.
   - the denominator bullet is rewritten to what the two checks actually assert:
     `progress_denominator_matches_phase_count` compares PROGRESS_MAP's
     denominators to **GREENFIELD's** phase count, and
     `no_hardcoded_progress_outside_progress_map` forbids a literal fraction
     against **any** flow's denominator. *(This wording was corrected in-context
     after reading both check bodies — the first draft said "some flow's phase
     count", which is what only the second check means.)*
   - five bullets added for the remaining new checks.
5. **"Adding a phase or gate"** now says the phase must be named in at least one
   `FLOW_PHASES` row, or `GREENFIELD_V1_PHASES` edited to put it in GREENFIELD —
   "deliberately a loud change". Without this the instruction is a trap: a new
   registry row and block passes every pre-T07 rule and fails
   `every_registry_phase_is_used_by_some_flow`.

The seven new check names were **re-derived in this context**, not copied:
`git archive 7dba4b6` into a scratch tree, `lint-skill` there, and `comm` against
the head run's names.

```
=== NEW (in head, not base) ===        === REMOVED ===
every_flow_is_an_ordered_subset_of_the_registry      (empty)
every_flow_retains_the_mandatory_phases
every_registry_phase_is_used_by_some_flow
execution_block_numbers_are_the_greenfield_positions
flow_table_covers_the_required_flows
gate_labels_are_flow_relative
progress_map_and_gate_numbers_are_the_derived_greenfield_views
```

Baseline check count **22**, head **29**, **zero removed** — A18's arithmetic,
independently reproduced.

### The prose sweep — six further sites, each one T07's own change made untrue

Found by `grep -rn -E '18 phases|18-[Pp]hase|8 approval gates|8 gates|/8\b|1-18|1–18'`
over `README.md`, `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`, `.claude/skills`
and `.claude/commands`, then judging every hit rather than rewriting every hit.

| Site | Change |
|---|---|
| `SKILL.md` frontmatter `description` | "Orchestrates a gated **18-phase** software delivery lifecycle" → "a gated software delivery lifecycle — one of five selectable flows over a 20-phase registry". This file is loaded every turn and is the skill's own self-description. **Every trigger keyword is untouched**; only the untrue clause moved. |
| `README.md` `## 18-Phase Workflow` | retitled `## The GREENFIELD Flow — 18 Phases, 8 Gates`, matching SKILL.md, as the plan's *Files expected to change* requires. Checked first that nothing links to it: the only `18-phase-workflow` anchor references in the repository are `README.md:98` and the Guide's own TOC, **both** pointing at the Reference Guide's §7, whose wording is deliberately preserved. The fenced block is otherwise byte-unchanged. |
| `README.md` `restart phase <N>` row | `(1–18)` removed — `restart` indexes the bound flow now (D16), and the refusal names the range. Same reason `sdle-restart.md`'s hint lost it. |
| `README.md` + Guide "Nothing in the 18-phase lifecycle reads this file" | → "any lifecycle flow". Two sites, one about `.sdle/config.json`. |
| Guide's architecture box, "Core rules, 18-phase table" | → "the phase registry and FLOW_PHASES". |
| Guide §12.3, the completion record | "Written exactly once, when **Gate 8** is approved … confirmation that **all 8 gates** were approved" → the bound flow's **final** gate (Gate 8 under GREENFIELD, Gate 3 under HOTFIX), the record now lists the **bound flow** (D14's new key), and the claim is scoped to that flow's gates. E39 names this paragraph explicitly. |

### Four further sites left deliberately unchanged, with the reason

- `README.md:445/467` and Guide `:917–1020` — `Gate 1/8`, `All 8 gates passed`
  in the **worked example transcripts**. Those are GREENFIELD runs and the
  output shown is exactly what the engine still produces.
- `README.md` v1.9 history row and the Guide's document-revision row —
  statements **about older versions**. Correct as history.
- Guide `:24` TOC and `:414` `## 7. The 18-Phase Workflow` — kept so existing
  deep links resolve; the new note directly under the heading says the numbered
  phases are GREENFIELD's. This is the plan's own choice, restated in the note.
- `README.md:94` `**8 approval gates total.**` — the last line of the
  GREENFIELD block, immediately above the paragraph that names the block as
  GREENFIELD. The plan says the block is "otherwise left intact".

### `flow show` reaches the operator documentation

`flow show` is a shipped command and both operator command tables enumerate the
governance commands, so it is now a row in each: `README.md`'s
`scripts/sdle.sh …` table and the Reference Guide's §-appendix table. Two
adjacent claims were corrected while there:

- README's `governance gates` row said "all eight gates run unconditionally" →
  "every gate **the bound flow contains** runs unconditionally". The *advisory*
  half of that sentence is unchanged and still true: `cmd_governance_gates`
  still emits `advisory: true` (T09's, not T07's).
- README's governance-refusal paragraph and Guide §12.4 gain `flow_mismatch`:
  `classification.flow` is the one recorded value the lifecycle consumes, `init`
  binds it once, there is no re-binding command, and **the refusal writes
  nothing — `audit.md` is byte-identical after it**.

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` — on arrival, before any edit | **0** | 29 PASS / 0 FAIL, `"failed": []`, `Parsed 20 phases, 8 gates, 16 migration rows`, `all four locations report v1.16` |
| same, after the `CLAUDE.md` edit | **0** | 29 PASS / 0 FAIL |
| same, after the six-site prose sweep | **0** | 29 PASS / 0 FAIL |
| same, after the `flow show` command-table edits | **0** | 29 PASS / 0 FAIL |
| `lint-skill` in a scratch tree of `7dba4b6` (`git archive` + `tar`) | 0 | **22** checks — the baseline for A18 |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **0** | **901 tests collected** |
| `… tests/test_units_flow_model.py … --collect-only` | 0 | **98 collected** |
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_flow_model.py tests/test_units_governance.py -q -p no:cacheprovider -rsxX"` | **0** | **307 passed in 258.22s** |

`lint-skill` was re-run after **every** document edit, as F12/F14 require — four
runs above, one per edit batch.

The targeted three-file run is the right blast radius for a documentation
milestone: `test_lint_skill.py` copies `README.md` and the Reference Guide into
its scratch repository, `test_units_flow_model.py` does the same, and
`test_units_governance.py`'s N23 scans `README.md`, `CLAUDE.md`, the Reference
Guide, `.claude/**` and `docs/architecture/**` for restated policy identifiers —
so ADR-004 and every sentence added above are inside that test's subject.

## Files changed so far this phase

`git diff --numstat` in this context (`.claude/settings.local.json` is
pre-existing and **out of scope**):

```
  4    1  .claude/commands/sdle-restart.md
 57   32  .claude/skills/sdle/SKILL.md
  7    6  .claude/skills/sdle/modules/gate-protocol.md
 23   10  .claude/skills/sdle/modules/phase-execution.md
  2    1  .claude/skills/sdle/templates/state.json
 22    7  CLAUDE.md                    <- M7, new in this context
 19    7  README.md                    <- +10/+1 in this context
 35    7  docs/SDLE-Reference-Guide.md <- +5/+1 in this context
  6    0  docs/dry-runs/README.md
783   65  scripts/sdle.py
  7    1  tests/conftest.py
113    3  tests/test_lint_skill.py
  4    1  tests/test_units_cli.py
101   15  tests/test_units_governance.py
  2    1  tests/test_units_infra.py
  1    1  tests/test_units_repo_config.py
  2    2  tests/test_units_speckit_binding.py
  4    4  tests/test_units_state.py
  1    1  tests/test_units_transitions.py
  7    6  tests/test_units_workitem_runtime.py
?? docs/architecture/ADR-004-declarative-flow-model.md
?? tests/test_units_flow_model.py
?? docs/transition/phases/T07-checkpoint-a01-0{1..7}.md
```

**No test file and no engine file was edited in this context.** M7's whole
delta is documentation and prompt prose. `git diff --numstat -- tests/` and
`-- scripts/` are byte-for-byte what checkpoint 06 recorded.

Documents were patched by byte-preserving Python scripts written to the
scratchpad (heredocs mangle escapes, F-note), each aborting unless its anchor
matched **exactly once**, and each reading and writing `bytes` so a CRLF file
stays CRLF. `git diff --numstat` confirms line-level diffs, not whole-file
rewrites.

## Current failures

**None.**

## Constraints M8 must not undo

Everything in checkpoints 01–06, plus:

- **The Reference Guide's §7 heading and its TOC entry stay as they are.** Two
  in-repository links target that anchor. The qualification lives in the note
  under the heading, not in the heading.
- **`README.md`'s worked-example transcripts and the version-history rows are
  not "stale text".** They are GREENFIELD output and historical statements
  respectively; rewriting either would be wrong.
- **`SKILL.md`'s frontmatter trigger keywords are untouched.** Only the
  lifecycle clause of `description` changed. A future edit that "tidies" that
  field must keep every keyword.
- **README's `governance gates` row keeps "Advisory: nothing consumes it".**
  Only the gate-total half changed. Flipping the advisory claim would be T09
  leakage, exactly as flipping `cmd_governance_gates`'s own `advisory: True`
  would be.
- `CLAUDE.md`'s sync list must keep matching the checks by name. It is now a
  29-line-equivalent derived view of `run_sync_checks`; if a check is added or
  re-targeted, this list moves with it.
