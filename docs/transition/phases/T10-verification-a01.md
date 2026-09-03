# T10 Independent Verification — Attempt a01

**Phase:** T10
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

**Commit under verification:** `11363d9` (HEAD, `git rev-parse HEAD` OBSERVED)
**Prior-phase baseline:** `adbdc5e` (T09 verified PASS); product files at `adbdc5e` are byte-identical to `6318541`
**Working tree at verification:** clean except ` M .claude/settings.local.json` (out of scope, pre-existing)

> The handoff is a claim set, not proof. Every row below was re-derived in this context. Nothing was accepted on the handoff's word.

---

## The single question

§16: *"Optimize reasoning quality/context **without moving authority back into prompts**."* The plan's own test: **if the diff contains a new writer, the phase failed regardless of the tests.**

I answered this by my own AST comparison of `git show adbdc5e:scripts/sdle.py` against HEAD, not by re-reading the handoff's counts.

| Probe | Result |
|---|---|
| Call sites of `write_atomic` | 27 at `adbdc5e`, **27** at HEAD |
| Call sites of `save_state` | 45 at `adbdc5e`, **45** at HEAD |
| Call sites of `append_audit` | 41 at `adbdc5e`, **41** at HEAD |
| Functions **newly** containing any write/spawn primitive (`open`, `write`, `replace`, `unlink`, `rmdir`, `mkdir`, `move`, `run`, `dump`, `flush`) | **empty set** — every primitive's per-primitive count and its owning-function set are identical on both sides |
| `add_parser(...)` registrations | 94 → **95**; added `['resume']`; removed `[]` |
| New `def` names in `sdle.py` | exactly 11: `modules_dir`, `agents_dir`, `capabilities_for`, `cmd_resume`, `gate_disposition`, `product_agent_files`, `agent_frontmatter`, `agent_tools`, `_capability_values`, `_check_capability_map`, `_check_product_agents`. Zero removed |
| Any path from subagent output to `state.json` / `audit.md` / `execution.json` / the review registry other than `artifact review --actor-type agent` | **none found**. The engine gained no command, no field, no refusal on that path; `cmd_artifact_review` and the review registry are untouched by the diff |
| `--actor` / `SDLE_ACTOR` (D9, rejected) | **absent** from the engine (all four spellings probed). `--actor-type` / `--actor-name` unchanged |

`cmd_resume` calls `load_constants`, `read_state`, `flow_for_state`, `gate_key_for`, `gate_disposition`, `approval_decision`, `render_header`, `branch_mismatch`, `Constants.capabilities_for`, `emit`. Nothing else. `gate_disposition` is an extraction out of `cmd_gate_show`, not a copy — `cmd_gate_show` now calls it.

**Verdict on the phase's defining risk: no new authority, no new writer.**

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| A1 `capability_map` for all 21 phases; lint fails loudly on a missing/unknown row | PASS | `sdle.py constants` → 21 rows, `set(rows) == set(phase_sequence)`. Mutation M9 (row for `analyze` removed) → `failed: ['capability_map_covers_every_registry_phase']`, exit 1. Mutation M4 (heading renamed to `### CAPABILITY_TABLE`) → exit 1, `failed: ['tables_wellformed']` and 41 downstream checks **absent** — it fails loudly, it does not default to an empty map |
| A2 every capability path exists; `SKILL.md` never a value | PASS | All 5 union paths resolve under the skill root. M7 (delete `code-review.md`) → `every_capability_file_exists` + `capability_cross_references_are_mapped_files`. M6 (add `SKILL.md` to a row) → `capability_map_never_names_the_orchestrator` |
| A3 every row a strict subset of the union; union == `modules/*.md` on disk; no orphan | PASS | Union = the 5 files on disk exactly; row sizes `{1: 15, 2: 6}`; no row equals the union. M8 (a row given the whole union) → `every_row_is_a_strict_subset_of_the_capability_set`. M5 (`modules/orphan.md` on disk) → `every_capability_file_is_linted` |
| A4 every gate phase maps `gate-protocol.md`, no non-gate does | PASS | Computed over all 21 phases against the 8 registered gates: **zero mismatches** |
| A5 every cross-reference resolves and is itself mapped | PASS | `capability_cross_references_are_mapped_files` green on the real tree; fires under M7 |
| A6 fresh process, every registry phase, ≥2 flows | PASS | Drove `sdle.sh resume` as a real `subprocess` in a scratch install: exit 0, payload keys `workitem, flow, current_phase, status, progress, position, next_phase, label, header, gate, pending, branch_mismatch, capabilities`. Suite's own matrix (`RESUME_CASES`) covers 3 flows × every registry phase and is guarded against subset-vacuity by `test_the_resume_matrix_covers_every_registry_phase` |
| A7 at a gate, same requirement and reasons as `gate show` | PASS | Structural: `cmd_gate_show` and `cmd_resume` both call the single extracted `gate_disposition`. There is only one derivation to disagree with |
| A8 `resume` composes, never re-derives | PASS | `resume.header` **byte-identical** to `header.rendered`; `current_phase`/`progress` equal `state get`; `flow` equals `flow show`'s `name` |
| A9 writes nothing, migrates nothing, audits nothing | PASS | SHA-256 map of the **whole project tree** before and after a cold `resume` subprocess: **no file changed**. On a legacy `.workflow/` state pinned at `workflow_version 1.13`, `resume` returns exit 0 and leaves `workflow_version` at `1.13` and `state.json` byte-identical |
| A10 `/sdle-continue` and `/sdle-start` load what `resume` names, and name no module in prose | PASS | Neither file matches `modules/[a-z-]+\.md` any more; both call `sdle.sh resume`. (The only `.claude/commands/` file still naming module paths is `sdle-approve.md` — see NB-2) |
| A11 every N13 battery payload denied, from each agent's own frontmatter string | PASS | I extracted the `command:` line from each of the four agent frontmatters (all four are the identical `python .claude/hooks/hooks.py product-agent-fence`) and ran my own 13-payload battery × 4 agents as real subprocesses: **52/52 `permissionDecision == "deny"`, exit 0**. Battery included `Write` to `.sdle/state.json`, `Edit` to `.sdle/audit.md`, `Write` to `.sdle/execution.json`, `Write` to `workitems/index.md`, an ordinary source file, a Windows absolute path, a `..`-traversal path, `Bash` running `gate approve`, `Bash` running `advance`, `Bash` running `artifact review`, plain `echo`, `MultiEdit`, `NotebookEdit`. Reason names invariant 6, invariant 8 and the one door |
| A12 the fence never fails open | PASS | Nine degenerate payloads — `{}`, no `tool_input`, empty `tool_input`, empty command, unknown tool, `None` tool name, `file_path: null`, malformed JSON on stdin, empty stdin — **all nine deny**. `product_agent_fence(payload)` ignores its argument entirely, so there is no payload shape to slip through |
| A13 all four agents grant only `Read, Grep, Glob` | PASS | Read from the four frontmatters: exactly `Read, Grep, Glob`. No `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Agent`, `Task` |
| A14 each agent lint check proved to fire | PASS | On a mutated tree copy, each in isolation: widen grant with `Bash` → `['product_agents_are_read_only']` only; widen with `Agent` → same, only; strip the fence hook block → `['product_agents_declare_the_fence']` only; narrow the matcher to drop `Bash` → same, only; remove the invariant-8 clause → `['product_agents_declare_the_non_approval_clause']` only. Five mutations, five single-check failures |
| A15 checks go **absent**, not passing, with `.claude/agents/` gone; repo has exactly 4 + 4 | PASS | Removing `.claude/agents/` → exit 0, `failed: []`, and the three agent checks are **absent** from the emitted check list. `test_lint_skill.py`'s `repo` fixture now copies `.claude/agents/`, so the checks are non-vacuous there; the repository-level test enumerates all eight agent files by exact equality |
| A16 the engine invokes nothing | PASS | `Task(` and `launch_agent` still banned; my own AST scan finds spawn calls in exactly two functions (`git`, `run_tests`) and no string literal in either names `claude`, `agent` or `Task`. Engine still stdlib-only |
| A17 no agent prompt or capability row on a gate-decision path | PASS | I removed the forbidding sentence from each agent file and searched the remainder for `gate approve`, `gate omit`, `gate reject`, `advance`, `sdle.sh`, `scripts/sdle`: **zero residual tokens in all four**. No gate row names an agent |
| A18 findings reach the record only through `artifact review --actor-type agent`; no new mutating command, no new state field | PASS | See "The single question". Drove the door itself: recording with `--actor-type agent --actor-name sdle-design-review` succeeds and binds a `sha256`; `--actor-type subagent` is refused `review_actor_invalid`, exit 1 |
| A19 all 33 baseline checks present by name and passing; new ones added; `failed: []` | PASS | I materialised the whole `adbdc5e` tree from `git ls-tree`/`git show` and ran **that** `sdle.py` against **that** skill: **33 checks, `failed: []`, exit 0**. HEAD: **42 checks, `failed: []`, exit 0**. Baseline names missing at HEAD: **none**. Added: exactly the nine the plan names. No duplicate names |
| A20 `_skill_files` derived; the three content checks cover every capability file and every product agent prompt | PASS | Proved by firing, not by reading: adding `Get-ChildItem` to the **new** `modules/design-review.md` → `no_powershell_only_cmdlets` only; adding `3/18` to the **product agent** `sdle-code-review.md` → `no_hardcoded_progress_outside_progress_map` only. Neither file was in the baseline four-property list |
| A21 `_searchable_files()` covers `.claude/agents/` | PASS | Both copies (`test_units_governance.py`, `test_units_discovery.py`) extended identically; `sdle-transition-*` excluded by prefix with the reason recorded in the helper itself |
| A22 integration files and the nine transcripts byte-identical | PASS | 23 frozen paths compared against `adbdc5e` with line endings normalised: **zero differences** (3 integration files, 9 dry-run transcripts, `settings.json`, `templates/state.json`, `.gitignore`, the 4 `sdle-transition-*` agents, `agent_guard.py`, `validate.py`, `transition.md`) |
| A23 `settings.json` / `state.json` / `.gitignore` byte-identical; v1.16; 16 migration rows; 8 approvals; 21 phases; GREENFIELD 19; flows element-wise identical | PASS | All byte-identical (above). `CURRENT_VERSION` **1.16**; state template **27** keys, **8** approvals; `lint-skill` reports `Parsed 21 phases, 8 gates, 16 migration rows`; `GREENFIELD_V1_PHASES` **19** entries |
| A24 invariant 3 for every new file; four existing guards unchanged; legacy dual-read and `migrate-workflow` untouched | PASS | Zero case-insensitive `speckit` occurrences in the two new capability files and the four agent prompts. `write_fence`, `untrusted_read`, `dirty_tree`, `secrets_scan` byte-identical to the `e1cf341` baseline by AST source segment. Legacy `.workflow/` binding still resolves and `resume`/`header`/`state get`/`flow show`/`gate show`/`audit verify` all behave identically on it |
| A25 D12 honesty table verbatim in ADR-007, three convention rows unsoftened; CLAUDE.md names the runtime owner | PASS | All **ten** D12 rows present in ADR-007 §3 with the plan's exact "Enforced by" values. Six softening mutations each break the assertion set: promote either runtime row to SDLE, promote the `--actor-name` row, remove the "human typed approve" row, erase the `SDLE_ACTOR` rejection, weaken CLAUDE.md's runtime sentence. Overstatement needles found in **zero** shipped prompt/doc files; needle set proved non-vacuous by injection |
| A26 full suite green, `lint-skill` `failed: []`, `validate.py` exit 0 | PASS | Full suite **`1616 passed in 1581.47s`, `RAW_EXIT=0`** via `rtk proxy python -m pytest -q --junitxml=...` (pytest wrote its own report; no shell redirection — see Conduct). JUnit XML independently confirms `tests=1616 failures=0 errors=0 skipped=0`. `lint-skill` 42/42, `failed: []`. `validate.py` exit 0, `TRANSITION_VALID: complete=10/12 next=T10` |
| A27 every changed test in X1–X7 or the X-GEN shape, literals recorded | PASS | See "Test weakening / deletion check" and the X-GEN ruling |

---

## Regression evidence

Targeted, re-run in this context and driven through the real CLI in scratch installs built from the shipped layout:

- **Resume refusal parity.** With no WorkItem registered, `resume` refuses `workitem_required` exit 1 — identically to `header` and `state get`. `--workitem ghost` → `workitem_unknown` exit 1. Two registered WorkItems → `workitem_ambiguous` exit 1, identically to `header`. `resume` is not a new lenient path.
- **Ledger byte-identity across refusals.** `gate approve --gate gate_spec` (`not_at_gate`), `gate approve --gate gate_constitution` (`not_at_gate`), `skip` (`not_failed`) and a usage-error `advance`: `audit.md` **byte-identical** after every one. `audit verify` exit 0 afterwards.
- **Legacy dual-read.** A `.workflow/` runtime at `workflow_version 1.13` still binds; `resume` reports it (`flow: GREENFIELD`, `capabilities: ['modules/phase-execution.md']`, `gate: null`) and does **not** migrate it.
- **Governed review freshness.** Recording with `--actor-type agent` binds a `sha256` to the artifact's exact content; an invalid actor type is refused `review_actor_invalid`.
- **Installed-layout lint.** In a temp install with the skill, engine, hooks and agents but no `README.md`/Reference Guide, `lint-skill` emits **40** checks, `failed: []` — the two documentation checks tolerate absence and the three agent checks are present. Absence tolerance is confined to where it was already the rule.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy python -m pytest -q --junitxml=<scratch>/full_suite.xml` | **`1616 passed in 1581.47s (0:26:21)`, `RAW_EXIT=0`** | `RAW_EXIT` echoed on the next line, no pipe. JUnit XML parsed independently: `tests=1616 errors=0 failures=0 skipped=0 time=1580.897` |
| `sdle.py lint-skill` at HEAD | **42 checks, `failed: []`, exit 0** | `Parsed 21 phases, 8 gates, 16 migration rows`; `all four locations report v1.16` |
| `sdle.py lint-skill` at a materialised `adbdc5e` tree | **33 checks, `failed: []`, exit 0** | Baseline re-derived here, not inherited. 33 → 42; missing at HEAD: none; added: exactly the nine planned |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=10/12 next=T10`, exit 0 | Run before the `progress.md` update |
| `sdle.py constants` | 21 `capability_map` rows, union = the 5 `modules/*.md` on disk, sizes `{1: 15, 2: 6}` | No row equals the union |
| Fence battery (my own, 13 payloads × 4 agents) | **52/52 deny**, exit 0 | Driven from each agent's own frontmatter command string |
| Fail-open probes (9 degenerate payloads) | **9/9 deny** | Includes malformed JSON and empty stdin |
| `lint-skill` mutation battery (13 mutations) | Each fires the expected named check | Reported in full above |
| ADR-007 softening battery (6 mutations) | 6/6 break the honesty assertions | — |
| `test_n28` replacement mutation battery (9 shapes) | 6 fire, 3 do not — see NB-1 | — |
| **Python 3.11** | **NOT_RUN** | This host runs a different interpreter. No outcome predicted |
| **CI (`ubuntu-latest` / `windows-latest`)** | **UNKNOWN / NOT_RUN** | Never observed at any point in this migration. No outcome predicted |

The F1 `ENVIRONMENT_FLAKE` procedure was treated as **VOID**. No failure occurred, so none was pattern-matched to anything.

---

## Future-phase leakage check

T11 owns legacy removal, hardening and the open findings. **None was adopted.** Re-derived here:

- `".sdle" not in sdle.SDLE_OWNED_PREFIXES` — still true; `cmd_manifest_build`'s missing exclusion unchanged.
- `branch_guard` occurrences in the engine unchanged from `adbdc5e`.
- `phase-execution.md` still names the stale `.workflow/implementation-manifest.md` (T04 N-6 residual, deliberately not fixed).
- T09 NB-2's HIGH→LOW revalidation asymmetry: untouched.
- T09 NB-3's unimplemented documentation review: not adopted; ADR-007 adds no `documentation-review` capability, no gate, no policy value.
- No version bump (v1.16 stands), no state field, no `VERSION_MIGRATION` row, no new gate, no new mutating command, no change to `gate approve` / `gate omit` / `gate reject` / `advance` / `governance` / `discovery` / `flow` / `baseline`.
- `test_n31_no_t11_leakage` carries **all four** T11 assertions from the pre-split function, byte-for-byte including the message string — I extracted and compared them by AST rather than reading the diff.
- Every file in `git diff --name-only adbdc5e..11363d9` is in the plan's "Files expected to change" table. **Zero files outside it.** `tests/conftest.py` was not touched at all.

---

## Test weakening / deletion check

- `git diff --name-status adbdc5e..11363d9 -- tests/`: **six `M`, one `A`, zero `D`, zero `R`.** 1521 lines added, 25 removed.
- Test functions removed: exactly two — `test_t06_creates_no_subagent` (X2, renamed to `test_the_engine_invokes_no_agent`) and `test_n31_no_t10_or_t11_leakage` (X1, split into two). 62 added.
- **No `skip`, `skipif`, `xfail`, `assert True`, or stubbed body was added anywhere.**
- Removed `assert` lines: exactly six, each accounted for by X1 or the X-GEN item, and each replaced by an assertion of the same or stronger shape:
  - `assert present, "..."` (non-emptiness) → `assert present == sorted(HOOK_FILES)` (exact enumeration) — **stronger**.
  - `assert agents, "..."` + `assert stray == []` → exact enumeration of all eight agent filenames — **stronger** (the old pair said nothing about which control-plane files exist).
  - `assert modules == [3 names]` → `assert modules == [5 names]` — same shape, re-valued.
  - `assert here(relative) == original` for `hooks.py` → per-definition byte equality plus an ordered guard-registry pin — see NB-1.
- X2's `"subagent"` substring ban is retired and replaced by a structural AST assertion (spawn-site owner set pinned to `["git", "run_tests"]`; no spawn argument naming `claude`/`agent`/`Task`). I re-ran the structural probe myself and it holds. This is a strengthening, not a relaxation.
- X3/X4 add `.claude/agents/` to both copies of the restatement search — a widening, applied identically to both so they cannot diverge.
- X5 extends the `lint-skill` fixture; I proved the anti-vacuity concern is real by removing `.claude/agents/` and observing the three checks go absent rather than pass.

### Ruling on the judgement call — `test_n28_the_hooks_are_byte_identical`

The implementer classified this **X-GEN, TP-003 category 2**, rather than escalating a blocker. **I agree, and the classification is correct.**

Reasoning, derived independently:

1. **The plan authorised the change that broke it.** B4 explicitly requires a fifth guard in `.claude/hooks/hooks.py`; the plan's "Files expected to change" lists `hooks.py`; its "Must not change" list does **not**. Whole-file byte identity against a pre-T10 rollback point was therefore false by construction the moment the plan was approved. That is mechanically forced, not a material decision.
2. **There is exactly one defensible resolution.** F2 and N27 simultaneously require that no hook change go unnoticed. Deleting the test is out; keeping byte identity is impossible; so the only move is to decompose the pin into the parts that remain true. No architectural or contract question is open, which is what §24.5 reserves a blocker for.
3. **T09 NB-1 asked for precisely this row.** The plan carries X-GEN in direct response. Using it is following the remedy; the T09 error was that no such row existed.
4. **The baseline did not move.** `ROLLBACK = "e1cf341"` is byte-identical to `adbdc5e`, and so is `FROZEN_FILES` — I compared both literals against `git show adbdc5e:tests/test_units_gate_policy.py`. Every other consumer of `ROLLBACK` is untouched.
5. **Condition (b) is satisfied.** The handoff records the old function and the new literals verbatim.
6. **The replacement genuinely fires.** I reconstructed `_hooks_top_level` and `_registered_guards` by AST out of the test file, then drove nine mutation shapes against the real baseline and the real HEAD source. Unmutated HEAD passes. Fires on: an edited `write_fence` body; an edited `secrets_scan` body; a sixth guard registered; a stray module-level constant; the fence dropped from `GUARDS`; an extra file in `.claude/hooks/`. That is the four shapes claimed, plus two more.

**Is it stronger or merely stronger-sounding?** Genuinely stronger in two places and genuinely narrower in one, and I record both rather than accepting the handoff's unqualified "stronger":

- Stronger: the file list moved from non-emptiness to exact enumeration (a new hook file previously would have failed only via the `at_rollback` lookup; now it fails twice), and the guard registry is newly pinned **by name and order**, so a guard defined but never wired fails.
- Narrower: whole-file bytes covered the module docstring, top-level imports, comments and top-level statements that are neither a `def` nor a simple `Assign`. The AST decomposition does not. I proved this: **adding `import yaml` to `hooks.py` passes, and changing the module docstring passes.** See NB-1. This is a test-coverage reduction on a guardrail file, not a fail-open in the product, and behaviour is covered elsewhere (`test_hooks.py` drives every guard as a real subprocess through its registered command string).

Net: the re-valuation is legitimate, in-shape, and the residual narrowing is small, bounded and mitigated. It is a non-blocking finding, not a FAIL.

---

## Deterministic guardrail check

- **Gate discipline.** `gate approve`, `gate omit`, `gate reject` and `advance` are untouched — not one line in the diff. No new path past a gate.
- **Fail safe.** `resume` is read-only and cannot leave a partial state; every refusal I drove left the ledger byte-identical.
- **Single writer.** Proved above by AST: zero new call sites of the three engine write helpers, zero functions newly containing a write primitive.
- **Claude cannot lower a deterministic floor.** No policy value is read, written or restated by anything T10 adds. The capability modules carry no threshold, gate ordinal, phase number, risk level or policy identifier; both are covered by the three widened content checks and by `test_no_policy_default_value_is_restated_outside_sdle_py`.
- **The ladder never guesses.** `resume` binds through the same `bind_workitem` as its siblings and refuses identically.
- **GREENFIELD frozen.** `GREENFIELD_V1_PHASES` still 19 entries.
- **`cmd_init` stays outside `apply_advance`.** Untouched by the diff.
- **The core refuses; it does not warn.** `lint-skill` exits 1 on every mutation I applied; the fence emits `deny`, never a warning. Neither has a warn path.
- **Invariant 3.** Zero `speckit` tokens in the six new prompt files — live now that capabilities are named skills.
- **Invariant 4.** Gate presentation stays in `gate-protocol.md`, loaded in the parent. The gate-protocol edit adds a review-capability step that explicitly says loading it "does not move the decision".
- **Invariant 7.** The capability map exists in exactly one place (`SKILL.md`), parsed by the engine. `resume` composes — I proved header byte-identity and single-derivation gate disposition. The linted file set is derived, so a new capability file cannot land in an unlinted corner. Two residual prose restatements are recorded as NB-2 and NB-4.
- **Invariant 8.** Grant + fence + three lint checks + the verbatim marker clause, and no agent prompt retains a gate verb once the forbidding sentence is removed.

---

## State / audit / evidence integrity check

- No state field added; state template still **27** keys, **8** approvals; **16** migration rows; `CURRENT_VERSION` **1.16**; `templates/state.json` byte-identical to `adbdc5e`.
- `resume` writes nothing: whole-tree SHA-256 map identical before and after a cold subprocess run.
- `audit.md` byte-identical after every refusal T10 can reach; `audit verify` exit 0 afterwards.
- Evidence records: an agent-actor review writes an `evidence/review-*.json` pointer and binds `sha256` to the artifact's exact current content — the T06/TP-011 mechanism, inherited rather than parallelled. No second registry, no stored freshness flag.

---

## Cross-platform / path handling check

- New engine code is `pathlib`-only; no `os.path` string joining, no separator literals.
- `_FRONTMATTER_RE` is `\A---\r?\n(.*?)\r?\n---\r?\n` — CRLF-aware, which is the correct call on a CRLF working tree.
- `product_agent_files` and `_skill_files` both sort by `p.name`, so the linted file set is order-stable across filesystems.
- Capability values are POSIX-style relative paths consumed as `paths.skill_root / value`, which is correct on Windows; `Path(value).name` is used for the orchestrator comparison rather than string slicing.
- `paths.agents_dir` is derived (`skill_root.parent.parent / "agents"`), never configured, and its absence is treated as "no agent files" everywhere rather than as an error.
- The fence hook itself inspects no path at all, so there is no normalisation surface to get wrong. I nonetheless drove it with a Windows absolute path and a `..`-traversal path: both deny.
- All content reads pass `encoding="utf-8"` explicitly.
- I normalised line endings (`git show` is LF, the tree is CRLF) before every byte-identity comparison in this report.

---

## Artifact review/SHA freshness check

Applicable and unchanged. `artifact review --actor-type agent --actor-name <agent>` is the single door (D14). I drove it: the record binds the artifact's `sha256` at recording time, and TP-011's stale rule is the existing one — no new command, no new field, no new refusal, no stored flag. `--actor-type subagent` refuses `review_actor_invalid` exit 1. ADR-007 §3 and the two capability modules both state plainly that `--actor-name` is an attribution the engine records faithfully and **cannot verify**; that caveat is asserted positively by a test and is present in both files that instruct recording.

---

## Findings

### Blocking

**None.**

### Non-blocking

**NB-1 — the `test_n28` X-GEN re-valuation narrows non-definition coverage of `hooks.py`.** The replacement pins every T09 top-level `def` and simple `Assign` byte-for-byte, the definition-name set, the guard registry by name and order, and the hook file list. It does **not** pin the module docstring, top-level `import` statements, comments, or top-level statements that are neither (including the `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))` dispatch block). I proved the gap: `import yaml` added to `hooks.py` passes, and a changed module docstring passes; T09's whole-file byte pin caught both. Mitigation in place: `test_hooks.py` drives every guard as a real subprocess through its registered command string, so a broken entry point or a behavioural change fails there. Recommendation for T11 or a later hardening pass: extend `_hooks_top_level` to capture `ast.Import`/`ast.ImportFrom` and the module docstring, or add a separate stdlib-only import pin for `.claude/hooks/hooks.py`. Not a product defect.

**NB-2 — `.claude/commands/sdle-approve.md` still names module paths in prose.** Lines 13 and 29 name `.claude/skills/sdle/modules/phase-execution.md` and `.claude/skills/sdle/modules/gate-protocol.md`. After T10, "which capability files a phase requires" has a single engine-owned source of truth, and `/sdle-continue` and `/sdle-start` were correctly rewritten to ask for it. A10 bound only those two, so leaving `sdle-approve.md` is scope-compliant and the implementer recorded it as a known residual — I agree that leaving it was the right call for this phase. It remains a prose restatement of an engine-owned fact and should be closed with the other command-file cleanup.

**NB-3 — `docs/architecture/ADR-001-deterministic-core.md:50` still reads "Four hooks enforce guardrails regardless of model decisions."** There are now five. `CLAUDE.md` and `README.md` were both updated to five; ADR-001 was not, and it was not in the plan's file list. Unlike `README.md`'s v1.3 version-history row — which the plan explicitly protects as a dated record — this sentence is present-tense and describes the current architecture, in the file `CLAUDE.md` points readers at for historical context. The implementer recorded it as a residual it did not adopt. Judgement: leaving it was defensible under the plan's scope, but it is now inaccurate and should be corrected in T11's documentation pass. It understates rather than overstates enforcement, so it is not an honesty defect.

**NB-4 — the read-only grant literal is restated in eight unchecked places.** `Read, Grep, Glob` appears product-side in the four agent frontmatters (machine-checked against `PRODUCT_AGENT_TOOLS` by `product_agents_are_read_only`), in the four agent **bodies** ("Your grant is `Read, Grep, Glob`", unchecked), and in `CLAUDE.md`, `README.md`, the Reference Guide and ADR-007 (unchecked). A future widening of `PRODUCT_AGENT_TOOLS` or of a frontmatter would leave eight prose statements silently stale. Low impact — the enforcement path is the frontmatter, which *is* checked — but it is the invariant-7 pattern a split prompt layer invites.

**NB-5 — documentation prose paraphrases `CAPABILITY_MAP` rows.** The Reference Guide says "Loaded at design generation and its gate" / "Loaded at implementation and its gate", and `README.md` retains "loaded at Phase 17". Each site immediately points at `CAPABILITY_MAP` as the authoritative table, and the pattern predates T10, so this is acceptable as written; recorded so a later editor does not treat the prose as normative.

**NB-6 — the shipped prompt layer states the fence's effect without the local runtime caveat.** `SKILL.md` Step 6b, both new capability modules and all four agent bodies assert that "a `PreToolUse` hook denies every write and every command". That a frontmatter hook *fires* is a Claude Code runtime property, not an SDLE guarantee — ADR-007 §3 and `CLAUDE.md` say so, and A25 binds only those two. The statements are factually accurate descriptions of what is registered and are addressed to an operator rather than an architect, so no change is required; recorded because this exact "reads like enforcement" pattern was caught at T08 (NB-3) and again at T09, and the honesty split now lives one document away from the sentences that need it.

**NB-7 — environment coverage unchanged and still open.** Python 3.11 `NOT_RUN`; CI on `ubuntu-latest`/`windows-latest` `UNKNOWN`, never observed at any point in this migration. T10 introduces no dependency and no new syntax level, but no outcome is predicted.

---

## Final result rationale

T10's one real risk is that skills and subagents hand authority back to the prompt layer. I tested that directly rather than through the suite: the engine's write-primitive call sites and their owning functions are **identical** on both sides of the diff, the only new subcommand is a read-only `resume`, the eleven new definitions are all readers or lint checks, and there is no path from a subagent to `state.json`, `audit.md`, `execution.json` or the review registry other than the pre-existing `artifact review --actor-type agent` door that the parent opens. The rejected caller-set attestation (D9) did not reappear.

The subagent boundary is detectable rather than promised. Driving the exact command string out of each of the four agents' own frontmatter, my own 13-payload battery denied 52/52, and nine degenerate payloads — including malformed JSON and empty stdin — denied 9/9, because the guard ignores its argument entirely and so has no fail-open shape. Widening a grant, stripping the fence, narrowing the matcher and removing the invariant-8 clause each fail exactly one named check and nothing else.

`lint-skill` grew from a re-derived 33 to 42 with every original name still present and no name relaxed, and it grew in coverage as well as in count: adding a PowerShell-only cmdlet to the *new* capability file and a hardcoded progress fraction to a *product agent* file each fire a pre-existing content check that could not have seen those files before M1. Removing `.claude/agents/` makes the agent checks go absent, not pass.

Two test functions were removed and both are documented renames; zero test files were deleted; no skip, xfail or stubbed assertion was introduced; the six removed assertions were each replaced by one of equal or stronger shape. On the judgement call I ruled independently that X-GEN was the right instrument — the plan's own B4 authorised the change that broke the assertion, exactly one resolution is defensible, no baseline moved, and T09 NB-1 asked for this row — while recording that the replacement is narrower than whole-file bytes on imports and the module docstring, which I proved rather than assumed.

ADR-007 §3 carries all ten D12 rows unsoftened; six softening mutations each break the assertion set, and no shipped prompt or documentation file contains an overstatement needle. No T11 finding was adopted, every frozen path is byte-identical to `adbdc5e`, and every changed file is inside the plan's expected set.

The full suite is `1616 passed, RAW_EXIT=0`, confirmed independently from the JUnit report as `failures=0 errors=0 skipped=0`; `lint-skill` is 42/42 with `failed: []`; `validate.py` exits 0. All twenty-seven acceptance criteria are met on evidence I produced in this context.

**Result: PASS.** Seven non-blocking findings are recorded above; none of them is a defect in T10's product behaviour, and none warrants remediation before T11.

---

## Conduct note

My Bash is restricted by `tools/transition/agent_guard.py verifier`. It refused three of my commands. The refusal, verbatim, in each case:

```
PreToolUse:Bash hook error: [python tools/transition/agent_guard.py verifier]: SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape
```

All three trips were caused by tokens inside my **own** payloads, not by the work: the guard's documented false positives on a literal `copy` preceded by whitespace (twice, in my own `print` strings) and on a `>` inside a quoted string (`"<h>"`). I resolved each by renaming my own token, as prior verifiers did. I did not route around the guard with an alternate shell or interpreter, and I did not patch or re-sign it.

Output redirection is blocked for this role, so the full suite was captured with pytest's own `--junitxml=` report file rather than a shell redirect, and `RAW_EXIT` was echoed on the following line with no pipe. `--report-log=` was attempted first and rejected by pytest as an unrecognised argument (`pytest-reportlog` is not installed); that run exited 4 and was discarded, not counted.

I wrote only this file and `docs/transition/progress.md`. No product code, plan, handoff or checkpoint was modified; `git status` at the end of verification is clean apart from the pre-existing, out-of-scope ` M .claude/settings.local.json`.
