# T11 checkpoint a01-07 — M7 and M8 complete except one blocked item

**Phase:** T11 · **Attempt:** 01 · **Milestones:** M7 (documentation) and M8 (D15/X10)
**Status at this boundary:** BLOCKED on a permission decision, not on a defect.
Everything M7 and M8 own is implemented **except** `docs/workitems/`, which the
shipped write fence denies and which I am not permitted to unblock myself.

---

## 1. What this checkpoint is for

A fresh context resuming here must know three things:

1. **All of M7's and M8's work is on disk and green**, apart from one directory
   and the twelve test outcomes that depend on it.
2. **The blocker is a two-part permission decision**, written up in
   `T11-blocker.md`. It is not an ordinary coding defect and it is not
   something a fresh context can grind past — the same denial will occur.
3. **Do not route around the write fence.** The fence denied a write; the
   correct response is to correct the fence or to have the file created by
   someone who may, never to write it with a different tool.

---

## 2. The blocker, in one paragraph

Contract §17 mandates a documentation directory at **`docs/workitems/`**, and
D16's `DOCUMENTATION_TARGETS` encodes it. The shipped write-fence hook matches
its fenced names as an **unanchored path segment** (`in_dir(path, name)` →
`"/workitems/" in path`), so it denies `docs/workitems/README.md` — a
documentation path the engine does not own and has no refusal for. I prepared
the minimal correction (anchor the fence at the repository root inside this
repository, where that is what `SDLE_OWNED_PREFIXES` already means, and keep the
loose segment match for paths outside it as defence in depth). **The edit to
`.claude/hooks/hooks.py` was denied by the auto-mode permission classifier**, as
was reading `.claude/settings.local.json`. Both denials are the permission
system's, not the product's, and neither may be worked around.

---

## 3. M7 — what landed

### 3.1 Five of six new documentation directories

| Path | Document | Covers |
|---|---|---|
| `docs/lifecycle/` | `README.md` | The 21-phase registry, the five flows, the eight gates, gate discipline, two-step commands, drift and the ledger |
| `docs/risk-and-gates/` | `README.md` | The twelve quality checks, signal weights, thresholds, the twelve hard floors, level→gate derivation, omission evidence, and why a downgrade is audited rather than refused |
| `docs/brownfield/` | `README.md` | Flow selection at `init`, the `discovery` phase, the baseline and its four derived statuses, and why *stale* is a warning while *invalid* is a refusal |
| `docs/spec-kit-integration/` | `README.md` | Opacity, capability detection, the three resolution tiers, `feature_ambiguous`, the emitted environment |
| `docs/troubleshooting/` | `README.md` | Exit codes, and the recovery procedure for `workitem_required` (both variants, including §3.3's two-step migration), `workitem_ambiguous`, `feature_ambiguous`, `index_malformed`, corrupt state, a broken chain, stray temps, `branch_mismatch`, `dirty_tree`/`drift_pending`/`rate_limit_exceeded`, the lock, and a fence denial |
| **`docs/workitems/`** | — | **NOT CREATED. Blocked.** Content is fully drafted; see §6 |

Every one of them opens by naming the engine as the authority and itself as a
derived view, so a future divergence is a defect in the document rather than an
ambiguity.

`docs/brownfield/README.md` deliberately does **not** restate the discovery
category vocabulary: `DISCOVERY_CATEGORIES`' own comment says it is restated in
no prompt or documentation file, and `discovery_vocabulary_is_not_restated_in_prompt_files`
enforces the prompt half. It points at `discovery schema` instead.

### 3.2 The inherited findings M7 owned

| ID | Where it landed |
|---|---|
| **TR2** | `.claude/commands/sdle-approve.md` — both module paths replaced by "the capability files `sdle.sh resume` reports for this phase" |
| **TR3** | `ADR-001` — "Four hooks" now records the decision, names the fifth, and points at the guard registry instead of carrying a count |
| **TR4** | The four product-agent **bodies**, `CLAUDE.md` and `ADR-007` now name `PRODUCT_AGENT_TOOLS` as the authority instead of restating `Read, Grep, Glob`. The four frontmatters keep the literal — that is the machine-checked copy |
| **TR6** | The runtime caveat added to `SKILL.md` (subagent paragraph) and to `modules/code-review.md` and `modules/design-review.md`: those guarantees hold *when the runtime honours a declared `tools:` list and a registered hook* (ADR-007 §3) |
| **TR13** | `SKILL.md`'s write-fence sentence now names all four fenced roots, the `workitems/<id>/specs/` carve-out, and the tripwire-versus-choke-point distinction |
| **TR14** | The prompt modules take the runtime path from the engine rather than naming `.workflow/` — see §3.3 |
| **TR21** | `SKILL.md`'s branch-mismatch paragraph no longer promises the re-run proceeds; it states that the acknowledgement names one checkout and is consumed |
| **TR26** | `docs/transition/RESUME.md` — **see §7, still outstanding** |

### 3.3 Prompt-layer `.workflow/` residuals (TR14, first half)

Five in `phase-execution.md`, two path mentions in `gate-protocol.md`. None was
replaced with a `workitems/<id>/…` literal where the engine already reports the
answer:

- `manifest build` returns `path`, so both manifest mentions now say to take it
  from the response.
- The audit-append instruction dropped its path entirely, matching how
  `gate-protocol.md` already phrases the same instruction.
- The completion summary names `workitems/<workitem>/.sdle/`, taking
  `<workitem>` from `state.json → workitem`, because no command reports that
  directory directly. I checked `cmd_resume`'s payload before writing this
  rather than assuming.

### 3.4 Documentation convergence in the shipped docs

- `README.md` — ladder rung 6 replaced by the refusal-plus-recovery text; the
  migration section now shows **both** commands in order and says both are
  runtime-free; the `.workflow/` paragraph says *archival*, not transitional.
- `CLAUDE.md` — the transitional-`.workflow/` sentence rewritten to the
  two-roles form; "transitional legacy" → "archival legacy" in the gitignore
  sentence; **new "The Documentation Set" section** listing all nine targets and
  naming `documentation_set_is_present` as their enforcement; ADR-008 added to
  Historical Context.
- `docs/SDLE-Reference-Guide.md` — the ladder paragraph; the "sixth rung is
  transitional" section rewritten to record the removal and why nothing is
  stranded; the `workitem` state-field row; **Document version 1.1 → 1.5** (the
  header had drifted three revisions behind its own history table) with a new
  1.5 row.
- `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md` — **NEW**,
  see §4.

---

## 4. ADR-008

Carries, as A19 requires:

- **all 26 TR rows**, each with exactly one disposition;
- the **three M6 declared divergences** (audit choke point, temp-file survival,
  stale-baseline blocking), each with the property that *is* asserted instead;
- the **two M6 product changes** (`governance_sha256` on an omission,
  `baseline_commit` on a baseline refusal), recorded as what §17's hardening
  mandate is for;
- the **M5 declared deviation** from B2 — the branch guard audits before it
  refuses — stated as the narrower guarantee it makes: *a refusal writes nothing
  except where the refusal itself is the auditable event*, and the branch guard
  is the only such place;
- §3's removal/preservation boundary, including why deleting `P1`
  (`PROJECT_ROOT_MARKERS`' `.workflow` entry) would be the bricking §17 forbids;
- §8, the single named V1 gap (TR8), with a two-step proposed shape so the
  deferral is actionable;
- the honest cross-platform position: Windows / Python 3.14 only, CI never
  executed, Linux and 3.11 not claimed.

**Disposition totals, re-derived here from the plan's §9 rather than copied:**
**20 FIXED · 4 DEFERRED · 2 NOT-A-DEFECT = 26.** The plan listed 20 FIXED,
3 DEFERRED, 2 NOT-A-DEFECT and 1 verify-then-record (TR20); TR20 resolved to
DEFERRED in M5, which is the fourth. A hand-off note describing this as
"19 FIXED" is one short — count the table, not the prose.

---

## 5. M8 — the transcripts (D15, X10)

**Re-derived count: 17 stale lines carrying 20 `.workflow` occurrences** across
six transcripts at `97100e2`. The plan's E20 and the resume note both say "18
lines"; counted directly, it is 17 lines. Three of those lines carry two
occurrences each.

`DRY_RUN_SUBSTITUTIONS` — **17 pairs of exact literals**, no patterns — now
lives once in `tests/conftest.py`, with `apply_dry_run_substitutions(text, used)`
beside it. Both pins consume it, so they cannot drift apart.

Both pins were **converted, not re-baselined**:

```text
apply_dry_run_substitutions(at_baseline(f)) == here(f)     # capabilities, adbdc5e
apply_dry_run_substitutions(at_rollback(f)) == here(f)     # gate_policy,  e1cf341
```

Non-vacuity rides along in three ways: the directory's whole file list is still
compared (the README cannot drift), the nine-transcript count guard is kept, and
**every declared pair must be used at least once** — so a pair that stopped
matching fails loudly instead of decaying into a no-op that lets the comparison
pass. Both pins passed on the first run after the conversion.

One substitution is not a path rewrite: transcript 06's list of prefixes the
dirty-tree guard filters. It gained `.sdle/` and `workitems/` and now matches
`SDLE_OWNED_PREFIXES` **element for element and in the engine's order**, which I
read off the constant rather than guessing.

`.workflow/` still appears exactly once in `docs/dry-runs/`, in that prefix
list, and that mention is **correct**: `.workflow/` is still an owned prefix.

---

## 6. `docs/workitems/` — drafted, not written

The document is written and reviewed; it covers what a WorkItem is, the on-disk
layout, isolation and versioning, the strict `index.md` columns and why
`index_malformed` is never auto-repaired, the command table with the
runtime-free column, the seven-rung ladder with rung 6 gone, `.workflow/`'s two
surviving roles, and the active context. It could not be committed to disk.

**Whoever unblocks this should not re-derive it from scratch** — the content is
reproducible from `docs/troubleshooting/README.md` §1–§4 and ADR-008 §3, which
carry the same facts.

---

## 7. Still outstanding when the blocker clears

1. **Create `docs/workitems/README.md`** (after correcting the fence).
2. **TR26** — `docs/transition/RESUME.md` is still stale. It is deliberately
   last: it should describe the *completed* state, and the state is not complete.
3. Re-run `lint-skill` (expect **43 checks, `failed: []`**), the twelve
   currently-failing tests, then the full suite.
4. Write `T11-handoff-a01.md` and set `progress.md` to IMPLEMENTED.

---

## 8. Evidence at this boundary — every figure re-derived in this context

| Check | Command | Result |
|---|---|---|
| `lint-skill` | `rtk proxy "python scripts/sdle.py lint-skill"` | **43 checks**, `failed: ["documentation_set_is_present"]`, message `docs/workitems/ is missing` — the other five directories now pass |
| M7/M8 targeted | `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_capabilities.py tests/test_units_gate_policy.py -q --tb=short -p no:randomly"` | **571 passed, 2 failed, 10 errors in 248.48s** |
| Both transcript pins (X10) | in the run above | **PASSED** — the declared-substitution conversion works against both commits |
| Stale transcript lines | Python walk over `git show 97100e2:docs/dry-runs/*` | 17 lines / 20 occurrences (plan says 18 lines — corrected here) |
| **Full suite** | `rtk proxy "python -m pytest -q --junitxml=<scratch>/t11-full.xml --tb=line"` | **`2 failed, 1698 passed, 10 errors in 1563.20s (0:26:03)`** |
| Suite, from the junit XML rather than the prose | `ET.parse(...)` on the same run | `tests=1710 failures=2 errors=10 skipped=0` — so `1698 + 2 + 10 == 1710` and there are **no skips or xfails hiding anything** |
| `lint-skill` raw exit, no pipe | `python scripts/sdle.py lint-skill > /dev/null 2>&1; echo $?` | **1** (refused). Not 0 — recorded as observed |
| `validate.py` raw exit, no pipe | `python tools/transition/validate.py; echo $?` | **0**, `TRANSITION_VALID: complete=11/12 next=T11` |
| A1 (frozen files) | `git diff --stat 4b1aa71 -- <3 integration files> .claude/settings.json .gitignore` | **empty** — all five byte-identical |
| A7 (preservation) | `PROJECT_ROOT_MARKERS`, `hooks.py::FENCED`, `.gitignore` | `(".workflow", "state.json")` present; `.workflow` still fenced; `.workflow/` still ignored |
| A21 (control plane) | `git status --porcelain -- docs/transition/ tools/transition/ .claude/agents/sdle-transition-*` | Only **new** `T11-*` artifacts. No prior phase artifact modified or deleted |
| Python 3.11 | not available on this host | **NOT_RUN** |
| CI (`ubuntu-latest` / `windows-latest`) | never executed at any point in this migration | **UNKNOWN** |

**All twelve non-passing outcomes trace to the single missing directory.** Ten
are fixture errors in `documented_repo` (`shutil.copytree` of
`docs/workitems`); two are `test_n24_the_schema_did_not_move` and `test_n26_…`,
both of which assert `lint-skill` exits 0. None is a regression from M7 or M8.

`ENVIRONMENT_FLAKE` is VOID and was not invoked. No failure was re-run in the
hope of a different answer.
