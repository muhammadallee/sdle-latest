# T02 Plan — WorkItem-Scoped Runtime

**Phase:** T02 — Move runtime state from repository-global to WorkItem-scoped
**Planner context:** fresh/isolated
**Status recommendation:** **PLANNED**
**Contract authority:** `docs/transition/transition.md` §8 (primary), §5, §7, §18, §19, §20, §24.2, §25
**Rollback point:** `7b9374b` (T01, verified `PASS`). T00 baseline `a12b9e2`; SDLE product baseline `f8fdaa0`.
**Observed HEAD at planning time:** `dbc1410` on `transition/workitem-v1`, working tree clean apart from the untracked transition kit.

> Everything below was reconstructed from the repository at `dbc1410`. Prior-agent
> prose is cited only where it is itself the artefact under discussion (T01's own
> deferral lines). No test was run by this planner; every suite figure is
> attributed to the evidence file it came from.

---

## 1. Objective

Make independent WorkItems mechanically possible by moving all active workflow
runtime state out of the repository-global `.workflow/` and under the active
WorkItem, without changing the 18-phase / 8-gate lifecycle, the CLI refusal
contract, the exit codes, or any surviving Wave A guardrail.

Contract §8 exit criteria, restated as the two things a verifier must be able to
demonstrate:

1. No active workflow runtime state is repository-global.
2. Existing 18-phase behaviour passes independently for at least two WorkItems.

**From** (observed at `dbc1410`, `scripts/sdle.py:112-126`):

```text
<repo>/.workflow/
+-- state.json
+-- audit.md
+-- lock
+-- implementation-manifest.md
`-- completion-summary.json
```

**To:**

```text
<repo>/workitems/<workitem-id>/.sdle/
+-- state.json
+-- execution.json
+-- audit.md                      # chained representation retained, see D4
+-- lock
+-- implementation-manifest.md
+-- completion-summary.json
`-- evidence/                     # created by migrate-workflow only, see D7
```

---

## 2. Repository evidence — fact ledger

Classification per contract §1.3. `Evidence` cells resolve without this document.

### 2.1 Current runtime path binding

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | `Paths` is a two-field dataclass (`project_root`, `skill_root`); `workflow`, `state_file`, `audit_file`, `lock_file` are derived properties. | OBSERVED | `scripts/sdle.py:102-146` |
| E2 | Every runtime read/write in the engine routes through those properties. The engine holds exactly **two** hardcoded runtime path strings that bypass them: `scripts/sdle.py:3132` (`relative = ".workflow/implementation-manifest.md"`) and `scripts/sdle.py:3153` (`startswith(".workflow/")` manifest filter). | OBSERVED | `grep -n '\.workflow' scripts/sdle.py`, 18 hits; all others are docstrings, refusal text, `paths.workflow` uses, `SDLE_OWNED_PREFIXES`, or the security-diff exclusion at `:3240` |
| E3 | `scripts/sdle.py:3240` excludes `:(exclude).workflow` from the Phase 17 security-review diff. | OBSERVED | `scripts/sdle.py:3235-3242` |
| E4 | `write_completion_summary` builds `paths.workflow / "completion-summary.json"` and returns it `relative_to(project_root)`. | OBSERVED | `scripts/sdle.py:1825-1836` |
| E5 | `cmd_reset --confirm` unlinks exactly `state_file`, `audit_file`, `lock_file`. It does **not** `rmtree` the runtime directory. | OBSERVED | `scripts/sdle.py:2738-2743` |
| E6 | `SDLE_OWNED_PREFIXES` is `(".workflow/", ".specify/", "design/", "reviews/", "clarifications/", "guidance/", "requirements/")` and gates the dirty-tree guard. | OBSERVED | `scripts/sdle.py:2991-2994`, `:3016-3021` |
| E7 | `actor()` caches the git identity per `project_root`. | OBSERVED | `scripts/sdle.py:521-529` |
| E8 | The lock is one file, `paths.workflow / "lock"`, refreshed by `touch_lock` on every `save_state`. | OBSERVED | `scripts/sdle.py:126`, `:573-577`, `:594-612` |

### 2.2 State schema, versioning and lint coupling

| # | Claim | Class | Evidence |
|---|---|---|---|
| E9 | `CURRENT_VERSION = "1.13"`; `MIGRATIONS` has 13 rows, terminal step `_mig_1_12`. | OBSERVED | `scripts/sdle.py:541`, `:963-977` |
| E10 | `templates/state.json` has 25 top-level keys and 8 `approvals` keys; there is no `workitem` key. | OBSERVED | `.claude/skills/sdle/templates/state.json` |
| E11 | `VERSION_MIGRATION` in `SKILL.md` has 13 rows ending `1.12 -> 1.13`. | OBSERVED | `.claude/skills/sdle/SKILL.md:211-225` |
| E12 | `lint-skill` check `version_string_consistent` compares the template version against **six** regex sites in **four** documents: `templates/state.json` (source of truth), `SKILL.md` frontmatter `Lifecycle Engine v(N.N)`, `SKILL.md` heading `^# SDLE.*\(vN.N\)`, `README.md` title `^# SDLE.*\(vN.N\)`, `README.md` first `**vN.N**`, `docs/SDLE-Reference-Guide.md` first `SDLE vN.N`. | OBSERVED | `scripts/sdle.py:3556-3590` |
| E13 | `lint-skill` check `migration_covers_every_state_field` requires every template key outside a fixed 9-key `base` set to appear **as a substring** of the concatenated `action` column of `VERSION_MIGRATION`. `workitem` is not in `base`, so a new row must literally contain the string `workitem`. | OBSERVED | `scripts/sdle.py:3593-3617` (base set at `:3603-3607`) |
| E14 | `_check_single_state_template` forbids a second copy of the template (SKILL.md Step 9 no longer embeds one). | OBSERVED | `scripts/sdle.py:3537-3545` |
| E15 | `lint-skill` reports 22 checks, 22 PASS at the baseline and after T01. | OBSERVED | `baseline.md` §3.1; `T01-verification-a01.md` (re-run by the verifier) |

### 2.3 T01 state that T02 builds on

| # | Claim | Class | Evidence |
|---|---|---|---|
| E16 | `workitems/index.md` is the append-only registry; `read_index` validates heading, columns and separator before anything is written, and an absent file is an empty registry. | OBSERVED | `scripts/sdle.py:1442-1481` |
| E17 | `cmd_workitem_list` projects the **index**, never the directory listing, and documents that the index is the single source of truth. | OBSERVED | `scripts/sdle.py:1610-1620` |
| E18 | `cmd_workitem_create`'s uniqueness scan additionally walks `workitems/` filtering `child.is_dir()`, so a stray *file* at `workitems/<id>` is invisible to the collision check. | OBSERVED | `scripts/sdle.py:1540-1544` |
| E19 | `workitem_dir()` refuses any id that does not resolve directly inside `workitems/`. `WORKITEM_ID_RE` already excludes separators. | OBSERVED | `scripts/sdle.py:1418-1430` |
| E20 | T01 added 320 insertions / 0 deletions to `scripts/sdle.py`; no state field, no version bump, no migration row, no hook or `.gitignore` change. | OBSERVED | `T01-verification-a01.md` (`git diff --numstat` = 320/0) |
| E21 | T01 explicitly deferred to T02: the `workitem` state field and version bump; moving `.workflow/` state/audit/manifest/completion-summary; the `Paths` context refactor; execution identity; lock rescope; `migrate-workflow`; adding `workitems/` to the hook write fence; nested `reviews/`/`clarifications/` `.gitignore` handling; `project_name` rebinding; the `write_atomic` fix decision. | OBSERVED | `T01-plan.md` lines 291-292, 523-530, 543 |
| E22 | The `isolated_git_identity` autouse fixture exists only in `tests/test_units_workitem.py`, not in `tests/conftest.py`. | OBSERVED | `tests/test_units_workitem.py:34-45`; `grep` of `tests/conftest.py` finds no such fixture |

### 2.4 Hooks, ignore rules and tests

| # | Claim | Class | Evidence |
|---|---|---|---|
| E23 | The write fence is `FENCED = (".workflow", "requirements", "guidance")` with a reason string per entry; matching is `in_dir(path, name)` = `/{name}/` in path or `startswith("{name}/")` after backslash normalisation. | OBSERVED | `.claude/hooks/hooks.py:47-66`, `:118-136` |
| E24 | The `dirty-tree` hook resolves `engine.resolve_paths(str(PROJECT_DIR), None)` and reads `paths.state_file`; every failure path returns silently. | OBSERVED | `.claude/hooks/hooks.py:173-193` |
| E25 | `.gitignore` line 1 is `.workflow/`; the file's last line `.pytest_cache/` has **no trailing newline**. | OBSERVED | `cat .gitignore` — output ran directly into the next shell token |
| E26 | `workitems/index.md` and `workitems/<id>/workitem.json` are already unignored; no `.gitignore` change was needed at T01. | OBSERVED | `T01-plan.md` E23/E24; `T01-verification-a01.md` |
| E27 | The literal `.workflow` appears on exactly **22** lines across **7** `tests/*.py` files: `conftest.py` 3, `test_hooks.py` 5, `test_integration_01_happy_path.py` 2, `test_integration_06_to_09.py` 4, `test_units_state.py` 4, `test_units_transitions.py` 2, `test_units_workitem.py` 2. (`grep -rn ... tests/` reports 30 because 8 further hits are `__pycache__` binaries.) | OBSERVED | `grep -rn '\.workflow' tests/*.py`, full listing, not truncated |
| E28 | There is no `pyproject.toml`, `pytest.ini`, `setup.cfg` or `tox.ini` in the repository, so pytest runs with no `addopts`, no plugins beyond defaults, and **no xdist**: the suite is single-process and sequential. | OBSERVED | `ls -a` at repo root; all four config reads produced no output |
| E29 | Suite size after T01: 287 collected (230 baseline + 57 new). | OBSERVED | `T01-verification-a01.md` |

### 2.5 Environment

| # | Claim | Class | Evidence |
|---|---|---|---|
| E30 | Local interpreter is CPython 3.14.6 / pytest 9.1.1 on Windows 11. CI pins Python **3.11** on `ubuntu-latest` + `windows-latest`. | OBSERVED | `baseline.md` §2 |
| E31 | Behaviour of this branch on Python 3.11 or in CI. | **UNKNOWN** | The branch is unpushed; no 3.11 interpreter on this host (`baseline.md` §2, §3.4, §3.5). No CI outcome is predicted anywhere in this plan. |
| E32 | The `write_atomic` `PermissionError: [WinError 5]` flake at `scripts/sdle.py:463` is still present, with a victim set that moves between runs and has grown from 2 to 3 to 4 occurrences per full run, now including a fixture-setup `ERROR`. | OBSERVED | `baseline.md` §6.1; `progress.md` T00 and T01 rows |
| E33 | Root cause of E32. | **UNKNOWN** — bounded diagnosis in §12.1 | See §12.1 |

---

## 3. Design decisions

Each decision names the contract clause it satisfies. An implementer that
follows these does not have to guess.

### D1 — `Paths` gains a WorkItem binding; no new context classes

Contract §8 asks for "explicit concepts **similar to** `RepositoryContext` /
`WorkItemContext`". `Paths` already *is* the repository context. T02 adds one
optional field and reroutes the runtime properties through a single seam:

```text
Paths(project_root, skill_root, workitem=None)

  runtime          -> workitems/<workitem>/.sdle   when workitem is bound
                   -> .workflow                    otherwise (legacy, transitional)
  legacy_workflow  -> .workflow                    always, for migration only
  workitem_root    -> workitems/<workitem>
  state_file / audit_file / lock_file / execution_file
                   -> runtime / <name>
  manifest_file    -> runtime / implementation-manifest.md   (new property, kills E2)
  completion_file  -> runtime / completion-summary.json      (new property)
  evidence_dir     -> runtime / evidence
```

`workflow` is kept as an alias of `runtime` so no call site outside the property
block changes. Two classes would force a signature change on all ~49 command
handlers for no behavioural gain, which contract §1 item 7 ("prefer
extraction/refactoring over replacement") and TP-001 both argue against. The
verifier should read this as satisfying §8's "similar to", not as a missed
refactor.

Contract §8's "No command should infer WorkItem-owned paths by concatenating
strings independently" is enforced by deleting the three literals at E2/E3 in
favour of the new properties.

### D2 — WorkItem resolution ladder (T02 subset only)

Full resolution (CWD, branch, persisted context, inference) is **T03**. T02
implements the minimum that makes the runtime addressable, and it must never
silently choose among plausible candidates (contract §9 "Mandatory ambiguity
behavior" is the shape T03 will extend).

```text
1. explicit --workitem <id>
      -> id must appear in workitems/index.md; otherwise refuse `workitem_unknown`
2. else exactly one row in workitems/index.md
      -> bind it
3. else zero rows AND <repo>/.workflow/state.json exists
      -> bind legacy (workitem = None).  TRANSITIONAL, removed at T11.
4. else zero rows
      -> refuse `workitem_required`  (message names `workitem create --name ...`)
5. else (>1 rows, none named)
      -> refuse `workitem_ambiguous`, listing candidate ids.  NEVER pick one.
```

Rung 3 is what stops T02 bricking a repository that already has a legacy
workflow: without it, `state get` and `header` would refuse before
`migrate-workflow` could ever be run. It is exactly the "support both layouts
only for migration" allowance of contract §8, and it is on T11's removal list
("transitional dual-path code").

Resolution reads the **index**, never the directory listing, consistent with E17.
That is also why E18's `is_dir()` nit stays out of scope (§14).

`init` is the one exception: it never takes rung 3, and it refuses
`legacy_workflow_present` — naming `migrate-workflow --workitem <id>` —
**whenever a legacy `.workflow/state.json` exists, regardless of how many
WorkItems are registered**. The unconditional form is deliberate. If `init` were
allowed to proceed with one WorkItem registered plus legacy state present, it
would create a second runtime while the legacy one became simultaneously
unbindable (rung 3 needs *zero* registered WorkItems) and unmigratable into that
WorkItem (`migrate-workflow` step 3 would now refuse `target_exists`) — an
orphaned workflow with a dead migration path. Refusing is the fail-safe
direction and is what contract §8's "Do not support indefinite dual-write"
requires.

### D3 — Commands that need no runtime

The ladder runs once, in `main()`, and only for commands that touch runtime
state:

```python
RUNTIME_FREE_COMMANDS = {"lint-skill", "sha", "constants", "workitem",
                         "migrate-workflow"}
```

`migrate-workflow` is listed because it performs its own explicit binding from a
mandatory `--workitem`. Everything else — including `scan` and `preflight`, both
of which persist to state — goes through the ladder. An acceptance test runs all
five against a repository with zero WorkItems and no `.workflow/` and asserts
exit 0 or a non-resolution refusal reason, and asserts a representative runtime
command refuses `workitem_required` in the same repository.

### D4 — Audit stays `audit.md`

Contract §8 permits "`audit.jsonl` **or compatible chained audit
representation**". The existing `## AUDIT` block format with the `prev_sha`
per-entry chain and the whole-file `audit_sha` is that representation, is
covered by 8 regression anchors (`baseline.md` §4.4), and converting it would
be a format rewrite with no capability gain. T02 **moves** the ledger and
changes nothing about its format, chaining or verification. Contract §18
lists audit integrity as PRESERVE; §28's final rule forbids removing a safety
control for aesthetics.

### D5 — Lock is rescoped, not removed

Contract §8 "Repository-global locking MUST end in this phase … optional
WorkItem-local session lock if needed". TP-009 requires only that a lock not
block a different WorkItem. Rebinding `lock_file` through `Paths.runtime`
achieves this with zero deleted code and keeps all seven §4.5 lock behaviours
(`baseline.md` §4.5) intact: freshness window, fresh-foreign-warns-never-halts,
stale-ignored, own-lock-not-foreign, session-mandatory, refresh-on-save.
Repository-global locking ends because the path is no longer repository-global.

### D6 — One new state field, one migration row, version `1.13 -> 1.14`

New top-level key `workitem` (string or `null`), placed immediately after
`workflow_version`. It records which WorkItem this state belongs to, so a state
file is self-describing and a misplaced file is detectable.

`_mig_1_13` binds it deterministically: when the state file's parent directory
is named `.sdle`, `workitem` is that directory's parent name; a state still at
the legacy `.workflow/` location keeps `null` until `migrate-workflow` runs.
`paths` is already in the migration signature (`scripts/sdle.py:980`), so no
signature change is needed.

The `VERSION_MIGRATION` action text must contain the literal string `workitem`
(E13).

### D7 — `execution.json` and execution identity

Contract §8 "Execution identity": `<3-letter-git-user-prefix>-<UTC-datetime>`,
e.g. `muh-20260816T171501Z`. Prefix derivation is specified there verbatim:
`git config user.name` → lowercase → strip non-alphanumeric → first 3 chars →
fall back to the email local part → final fallback `usr`.

Written to `<runtime>/execution.json` at `init` and at `migrate-workflow`:

```json
{
  "executionId": "muh-20260816T171501Z",
  "workitem": "customer-notification",
  "startedAt": "2026-08-16T17:15:01Z",
  "sdleVersion": "1.14"
}
```

Execution identity is **execution metadata, not the WorkItem name** (§8,
explicit). The audit block format is deliberately **not** changed — that would
churn every audit assertion for no required capability. Branch and starting SHA
are **T03** ("record branch and starting SHA"), not T02.

### D8 — `migrate-workflow --workitem <id>`, with a commit point

Contract §20 gives 12 steps and §8 gives 9 MUSTs. Mapped to an ordering whose
crash behaviour is testable:

| Step | Action | Contract clause |
|---:|---|---|
| 1 | Resolve repository (`Paths`). | §20.1 |
| 2 | Require `--workitem`; the id must be registered in `workitems/index.md`. Absent → refuse `workitem_unknown`, naming `workitem create`. (§20's "resolve/create" is deliberately narrowed to *resolve*, so WorkItem creation keeps exactly one entry point — T01's `workitem create`.) | §20.2, §8.1 |
| 3 | Refuse `target_exists` if `<runtime>/state.json` already exists. | §8.7, re-run safety |
| 4 | Validate legacy state: exists, parses as JSON, `workflow_version` is a known version. Otherwise `legacy_state_invalid` (exit 3, integrity). | §20.3, §8.2 |
| 5 | Verify legacy audit integrity: chain walk + `audit_sha` comparison using the existing verifier. Mismatch → refuse `legacy_audit_broken`, naming `audit rebaseline`. | §20.4, §8.3 |
| 6 | Capture source facts: legacy `state.json` SHA, `audit.md` SHA, current git HEAD. | §20.5 |
| 7 | Copy, in this order, each via `write_atomic`: `audit.md`, `implementation-manifest.md` (if present), `completion-summary.json` (if present), then `evidence/migration-<executionId>.json` holding the step-6 facts, then `execution.json`. | §20.6, §8.4, §8.8 |
| 8 | **Commit point:** migrate the state in memory (`migrate_state` to 1.14, set `workitem`), then `write_atomic` the target `state.json` **last**. | §8.4, §20.7-10 |
| 9 | Verify target: re-read `state.json`, re-verify the audit chain and `audit_sha` at the new location, confirm phase/status/progress/`approvals`/`artifact_shas`/`rate_limits`/`attempt_counts`/`implementation_base_ref` are byte-equal to the legacy values. Mismatch → refuse `migration_verify_failed`; legacy remains authoritative. | §20.11, §8.6 |
| 10 | Record a `migration` object in `workitems/<id>/workitem.json` (`{"migratedFrom": ".workflow", "at": ..., "executionId": ..., "legacyStateSha": ...}`). | §8.5 |
| 11 | Append a `workflow_migrated` audit entry **to the target ledger**. | §20.12, §8.8 |
| 12 | Leave `.workflow/` byte-for-byte untouched; emit its path as archival. | §8.7, §8.9 |

Because the target `state.json` is written last, an interruption anywhere leaves
no resolvable target workflow, legacy stays authoritative, and re-running is
safe: step 3 passes, steps 7-8 overwrite the partial files. No `--force` flag is
needed — the flag would be the fail-open option.

### D9 — Write fence covers all of `workitems/`

`FENCED = (".workflow", "requirements", "guidance", "workitems")`. At T02
nothing under `workitems/` is legitimately model-written: `index.md` and
`workitem.json` are engine-owned (T01), and `.sdle/` is the runtime. WorkItem
`clarifications/`, `reviews/` and Spec Kit artefacts do not move under
`workitems/` until T04+, at which point that phase carves out the artefact
subpaths. Fencing the whole tree now is the fail-safe direction; loosening later
is a one-line change, whereas a hand-edited registry is unrecoverable. The
reason string must say so, so the T04 implementer finds it.

`.workflow` stays fenced: legacy state still exists during migration.

### D10 — `project_name`, closing baseline §4.3's `ADAPT@T01`

Two things happen, neither of which changes an existing assertion:

1. **Scoping (the ADAPT itself):** `project_name` now lives in WorkItem-scoped
   state at `workitems/<id>/.sdle/state.json` instead of repository-global
   state. Its meaning — the name of the project under work — is unchanged.
2. **Identity fallback:** `cmd_init`'s precedence becomes
   `--project` → requirements-heading inference → **WorkItem title (new)** →
   `project_root.name`. The new rung sits *after* heading inference, so
   `test_init_infers_project_name_from_first_heading` stays green unchanged,
   and the WorkItem becomes the identity source only where there was previously
   nothing better than a directory name.

Rejected alternative: putting the WorkItem title *ahead* of heading inference.
That is a behavioural change no requirement asks for, and it would force a
category-2 rewrite of a passing regression test. Contract §28 item 5 ranks
existing behaviour above implementation convenience.

### D11 — Documentation and ignore rules

- `.gitignore`: add exactly one line, `workitems/*/.sdle/lock` (contract §19
  "May remain local/ignored … lock files if retained"). Everything else under
  `workitems/` must stay versioned (§19 "Must eventually be versioned"). The
  implementer must preserve the missing trailing newline situation at E25 —
  append a newline before the new line, and end the file with one.
- `CLAUDE.md` states the runtime location on **two** lines, both observed:
  line 11 ("Runtime artifacts from such runs (`.workflow/`, …) are gitignored")
  and line 34 ("Runtime state lives in the *target project's*
  `.workflow/state.json` plus an append-only `audit.md`"). Line 34 becomes false
  at T02, and line 11 becomes misleading because WorkItem records are now
  versioned (§19). **In scope:** update both, naming
  `workitems/<id>/.sdle/state.json` and describing `.workflow/` as transitional.
  Leaving them stale would make the repository's own instructions contradict the
  engine.
- `.claude/commands/` states the runtime path on **three** observed lines:
  `sdle-reset.md:8`, `sdle-start.md:8`, `sdle-start.md:23` (the last is T01's
  own "`.workflow/` is still the runtime state" sentence, which T02 supersedes).
  Text only; no command logic changes.

---

## 4. Behavioural delta

### 4.1 Deliberate changes

| # | Change | Contract clause |
|---|---|---|
| C1 | Runtime state, audit, lock, manifest, completion summary and evidence move from `<repo>/.workflow/` to `<repo>/workitems/<id>/.sdle/`. | §8 "From"/"To" |
| C2 | Runtime commands require a resolved WorkItem (ladder D2). New refusals: `workitem_required`, `workitem_unknown`, `workitem_ambiguous`. | §8 "Migration MUST … require an explicitly resolved WorkItem" |
| C3 | New global flag `--workitem <id>`. | §9 "Explicit CLI override" (the `--workitem` half only; `sdle start` is T03) |
| C4 | `init` refuses `legacy_workflow_present` whenever a legacy `.workflow/state.json` exists — unconditionally, whatever the registered-WorkItem count (rationale in D2). | §8 "Do not support indefinite dual-write" |
| C5 | New state field `workitem`; `workflow_version` `1.13` → `1.14`; new `VERSION_MIGRATION` row and `_mig_1_13`. | §8 "State migration strategy" |
| C6 | New `<runtime>/execution.json` with the `<prefix>-<UTC>` execution identity. | §8 "Execution identity" |
| C7 | New command `migrate-workflow --workitem <id>`. | §20 |
| C8 | The repository-global lock ends; the lock file is WorkItem-local. Behaviour of the lock itself is unchanged. | §8 "Lock behavior", TP-009 |
| C9 | Write fence extends to `workitems/`. | §18 "Hook guardrails — ADAPT to WorkItem paths" |
| C10 | `SDLE_OWNED_PREFIXES` gains `workitems/`; the Phase 17 diff exclusion gains the WorkItem runtime path. | §18 dirty-tree guard PRESERVE, §8 "adapt, not remove" |
| C11 | `project_name` gains a WorkItem-title fallback rung and becomes WorkItem-scoped. | `baseline.md` §4.3 `ADAPT` |
| C12 | `.gitignore` gains `workitems/*/.sdle/lock`. | §19 |

### 4.2 Preserved invariants

The implementer must be able to point at evidence for each of these **after** the
change. Every one has a named regression anchor in `baseline.md`.

| # | Invariant | Anchor |
|---|---|---|
| P1 | 18-phase sequence and 8 gates are untouched. No constant table in `SKILL.md` is edited except `VERSION_MIGRATION`. | lint `next_phase_chains_sequence`, `progress_denominator_matches_phase_count`, `gate_registered_*` |
| P2 | Exit-code contract 0/1/2/3 and the single JSON envelope shape. | `tests/test_units_cli.py` (4 anchors, `baseline.md` §4.2) |
| P3 | `write_atomic` semantics: temp file + `os.replace`, no partial file on failure. **Not patched in T02** (§12.1). | `tests/test_units_infra.py::test_write_atomic_leaves_no_partial_file_on_failure`, `::test_write_atomic_replaces_completely` |
| P4 | Audit format, `prev_sha` chaining, whole-file `audit_sha`, tamper halt, rebaseline logging. Only the path changes. | `baseline.md` §4.4, 8 anchors |
| P5 | Drift detection, queue ordering, one-at-a-time re-approval, git-diff evidence. | `baseline.md` §4.7, 10 anchors |
| P6 | Rate limits, counters-never-auto-reset, audited `limit set`. | `baseline.md` §4.6 |
| P7 | Checkpoint/idempotency, two-step confirmation, stale-confirmation guard. | `baseline.md` §4.1 `confirm *`, §5 rows |
| P8 | Secrets scan (6 patterns, masked), untrusted-content scan (11 patterns), test evidence, `implementation_base_ref`. | `baseline.md` §4.10-§4.13 |
| P9 | Migration discipline: unknown version refused, chain idempotent, every field covered. | `tests/test_units_state.py::test_migrate_refuses_unknown_version`, `::test_migrate_is_idempotent`, lint `migration_covers_every_state_field` |
| P10 | `workitems/index.md` remains append-only and validated; `workitem create`/`list` semantics unchanged; no auto-suffixing. | `tests/test_units_workitem.py` (57 cases) |
| P11 | Spec Kit behaviour, `current_feature_id`, `ARTIFACT_OWNERSHIP` templates and `feature resolve` are untouched (T04 owns them). | `baseline.md` §7 item 5 |
| P12 | `speckit-*` skill names stay out of user-facing output. | CLAUDE.md invariant 3 |
| P13 | Cross-platform: stdlib only, no new dependency, PowerShell-compatible embedded commands, Python 3.11-safe syntax (no `match`, no 3.12+ generics, no `Self`). | `baseline.md` §2; E31 |

---

## 5. Files expected to change

| File | Change | Risk |
|---|---|---|
| `scripts/sdle.py` | `Paths` field + properties (D1); `resolve_paths` gains `workitem`; new `bind_workitem` ladder + `RUNTIME_FREE_COMMANDS` (D2, D3); `--workitem` global flag; `execution_identity()` + `write_execution_file()` (D7); `cmd_migrate_workflow` + parser (D8); `CURRENT_VERSION = "1.14"`, `_mig_1_13`, `MIGRATIONS` row (D6); `cmd_init` legacy refusal + `project_name` rung (D10, C4); delete the three hardcoded `.workflow` literals at `:3132`, `:3153`, `:3240` in favour of properties (E2, E3); `SDLE_OWNED_PREFIXES += ("workitems/",)`. | **High** — the phase's whole surface |
| `.claude/skills/sdle/templates/state.json` | Add `"workitem": null` after `workflow_version`; bump `workflow_version` to `"1.14"`. | High — lint-coupled |
| `.claude/skills/sdle/SKILL.md` | New `VERSION_MIGRATION` row `1.13 → 1.14` (must contain `workitem`, E13); version string in frontmatter and heading; Step 1 / Step 9 text describing the runtime location and the new field. | High — 3 of the 6 lint regex sites |
| `README.md` | Title version, version-history table row (CLAUDE.md sync rule), state-schema section gains `workitem`, command table gains `migrate-workflow` and `--workitem`, file-layout section shows the WorkItem runtime. | Medium |
| `docs/SDLE-Reference-Guide.md` | Header version; runtime-location and migration sections. | Medium |
| `.claude/hooks/hooks.py` | `FENCED` + `FENCE_REASONS` gain `workitems` (D9); `dirty_tree` resolves the active WorkItem and stays silent when resolution is ambiguous or absent (E24). | Medium — guardrail |
| `.gitignore` | One line, `workitems/*/.sdle/lock` (D11, E25). | Low |
| `CLAUDE.md` | Lines 11 and 34, runtime location (D11). | Low |
| `.claude/commands/sdle-reset.md`, `.claude/commands/sdle-start.md` | Text only: `sdle-reset.md:8`, `sdle-start.md:8`, `sdle-start.md:23` (D11). Implementer re-greps rather than trusting these line numbers. | Low |
| `tests/conftest.py` | `Project.state_file` / `audit_file` rebind; add `runtime` / `workitem` helpers; **`project` fixture creates exactly one WorkItem — required at M2, not M7** (see §6); promote `isolated_git_identity` (§7.3). | Medium |
| `tests/*.py` | The 21 hardcoded `.workflow` lines at E27, per §7.2. | Medium |
| `tests/test_units_workitem_runtime.py` | **New**, §8. | — |
| `docs/transition/phases/T02-plan.md`, `docs/transition/progress.md` | This plan; status. | — |

**Must not change:** `scripts/sdle.sh`, `scripts/sdle.ps1`, `.claude/settings.json`
(no new hook is registered — the existing `write-fence` entry covers the new
`FENCED` member), `.github/workflows/ci.yml`, `.claude/skills/sdle/modules/*`
(no phase or gate table changes), `requirements/`, `docs/dry-runs/`.

---

## 6. Implementation milestones

T02 is the largest phase so far. Each milestone leaves the suite runnable, and
each is a natural `T02-checkpoint-a01-NN.md` boundary (contract §24.3).

| # | Milestone | Done when |
|---:|---|---|
| M1 | `Paths` rebinding + the three literal deletions (D1). Default `workitem=None`, so behaviour is byte-identical to `7b9374b`. | Full suite passes with **zero** test edits. This is the checkpoint that proves the seam is correct before anything user-visible moves. |
| M2 | Resolution ladder, `--workitem`, `RUNTIME_FREE_COMMANDS`, `init` legacy refusal (D2, D3, C4) — **plus** the `tests/conftest.py` `project` fixture change that creates exactly one WorkItem. | New resolution tests pass, and existing tests pass because the fixture's single registered WorkItem binds at **rung 2**, with no `--workitem` plumbing in any test. |
| M3 | Schema: `workitem` field, version `1.14`, `_mig_1_13`, `VERSION_MIGRATION` row, the six version-string sites, README version-history row (D6, E12, E13). | `lint-skill` exit 0 / 22 PASS. |
| M4 | `execution.json` + execution identity (D7); `project_name` rung (D10). | New tests pass. |
| M5 | `migrate-workflow` (D8), all 12 steps. | Migration, crash, corrupt-legacy-state, corrupt-legacy-audit, corrupt-target tests pass. |
| M6 | Guardrail adaptation: write fence, dirty-tree hook, `SDLE_OWNED_PREFIXES`, Phase 17 diff exclusion, `.gitignore` (C9, C10, C12). | `tests/test_hooks.py` green including new cases. |
| M7 | Remaining test-suite rebinding (§7.2), `isolated_git_identity` promotion (§7.3), documentation. | Full suite + `lint-skill` + `validate.py`. |

The order matters: M1 before M2 means a bisect can separate "the seam is wrong"
from "the ladder is wrong". Do not merge M1 into M2.

**Why the conftest WorkItem creation belongs to M2 and not M7.** Rung 3 rescues
only *post-`init`* commands in a repository that already holds legacy state; it
is explicitly excluded for `init` (D2) and is unreachable in a fresh scratch
project, which has neither a WorkItem nor legacy state. So the moment the ladder
lands, `project.ok("init", …)` would take rung 4 and refuse `workitem_required`,
reddening every `started` / `started_git` test. Creating one WorkItem in the
`project` fixture makes rung 2 bind it for every command with no test-level
flag. F10 is what keeps this honest: N10 and N12 build their own WorkItem-less
projects rather than using the shared fixture, so the fixture cannot mask a
resolution bug.

---

## 7. Existing tests affected

TP-003 admits exactly three categories. Every test change in T02 must be
recorded by the implementer with its category. **No test may be weakened,
skipped, xfailed or deleted** (contract §1 item 16, §24.4 item 9).

### 7.1 Category 1 — unchanged behaviour, must stay green untouched

The overwhelming majority. All of `test_units_cli.py`, `test_units_infra.py`,
`test_lint_skill.py`, `test_integration_02_to_05.py` (0 `.workflow` literals),
and every case in the other files that reaches state through
`Project.state()` / `Project.ok()` rather than a hardcoded path. After M1 these
must pass with **zero** edits — that is M1's whole acceptance condition.

Two named cases the implementer must confirm are still green *unmodified*,
because they are the ones a careless `project_name` change would break:

- `tests/test_units_state.py::test_init_infers_project_name_from_first_heading`
- `tests/test_units_workitem.py::test_*` (all 57; T01's surface is unchanged)

### 7.2 Category 2 — deliberately superseded, path rebinding only

These assert the **location** of runtime files. The behaviour they check is
unchanged; the path is not. Each becomes the `<runtime>` equivalent. The
rationale is identical for all of them and is stated once: contract §8 moves
runtime state under the WorkItem, and `baseline.md` §7 item 3 names T02 as the
phase permitted to do it.

| File:line | Current literal | Becomes |
|---|---|---|
| `conftest.py:130` | `root / ".workflow" / "state.json"` | `Project.runtime / "state.json"` (property, D1-shaped) |
| `conftest.py:134` | `root / ".workflow" / "audit.md"` | `Project.runtime / "audit.md"` |
| `conftest.py:180` | fixture `.gitignore` writes `.workflow/` | add `workitems/*/.sdle/lock` so fixtures mirror the shipped ignore file |
| `test_integration_01_happy_path.py:167` | `.workflow` glob for `completion-summary*.json` | `runtime` glob |
| `test_integration_01_happy_path.py:189` | `.workflow / "lock"` | `runtime / "lock"` |
| `test_integration_06_to_09.py:113` | `.workflow / "implementation-manifest.md"` | `runtime / "implementation-manifest.md"` |
| `test_integration_06_to_09.py:127` | asserts the emitted relative path `".workflow/implementation-manifest.md"` | `workitems/<id>/.sdle/implementation-manifest.md` |
| `test_integration_06_to_09.py:165` | manifest body read | `runtime` |
| `test_integration_06_to_09.py:406` | `not (.workflow / "lock").exists()` after release | `runtime` |
| `test_units_state.py:55` | lock content after `init --session` | `runtime` |
| `test_units_state.py:313` | writes a stale foreign lock | `runtime` |
| `test_units_state.py:330,332` | lock exists / removed | `runtime` |
| `test_units_transitions.py:225` | asserts `data["completion_summary"] == ".workflow/completion-summary.json"` | `workitems/<id>/.sdle/completion-summary.json` |
| `test_units_transitions.py:227` | summary file path | `runtime` |
| `test_hooks.py:103,104,105,108,136` | write-fence payload paths under `.workflow` | **keep** — `.workflow` stays fenced (D9). **Add** matching `workitems/...` cases rather than replacing these. |
| `test_units_workitem.py:4,348` | docstring + `assert not (root / ".workflow").exists()` | Docstring updated; the assertion still holds (`workitem create` still initialises no runtime) — verify rather than rewrite. |

The implementer should prefer adding a `Project.runtime` property to conftest
and rebinding through it, so a future phase moves one line, not fourteen.

### 7.3 Category 2 — `isolated_git_identity` promotion

Currently file-scoped (E22), so every pre-existing suite still writes the
machine's real Git identity into scratch `audit.md` files via `actor()` (E7).
T02 moves the audit path and adds new audit assertions, so this is the phase
that owns it.

**Decision:** promote it to `tests/conftest.py` as an autouse fixture, **on the
condition** that the implementer first proves no existing assertion depends on
the machine's identity (`grep -n 'Actor' tests/*.py` plus a full-suite run
before and after the move). If any assertion does depend on it, leave the
fixture file-scoped and record the finding — do not adjust the assertion.

This is fixture hygiene, not a weakening: the fixture makes tests *more*
hermetic. Category 2 with the rationale "test isolation defect, pre-existing,
surfaced by T01, owned by T02 because T02 touches the audit path".

### 7.4 Category 3 — defects

None predicted. If the implementer finds one, it is fixed in the implementation,
not worked around in the test, and recorded with its category.

---

## 8. New tests required

One new file, `tests/test_units_workitem_runtime.py`. Contract §8 "Tests" names
the mandatory set; each is mapped below.

### 8.1 Isolation — the phase's headline claim (contract §8 "Tests")

| # | Test | Assertion |
|---|---|---|
| N1 | Two WorkItems, independent state | Drive WI-A to a later phase; WI-B's `state.json` is byte-unchanged and still at its own phase. |
| N2 | Two separate audits | Each WorkItem's `audit.md` contains only its own entries; both chains verify independently. |
| N3 | Two separate manifests | `manifest build` under WI-A does not create or modify WI-B's manifest. |
| N4 | Two separate locks | `lock acquire --session s1` under WI-A leaves WI-B unlocked; a fresh foreign lock on WI-A never affects a WI-B command. **This is TP-009's acceptance test.** |
| N5 | No repository-global runtime | After a full WI-A run in a repository with no legacy state, `<repo>/.workflow` does not exist. **This is the §8 exit criterion.** |

### 8.2 Resolution ladder (D2, D3)

| # | Test | Assertion |
|---|---|---|
| N6 | Rung 1 | `--workitem wi-a` binds WI-A even when WI-B exists. |
| N7 | Rung 1 negative | `--workitem nope` refuses `workitem_unknown`, exit 1. |
| N8 | Rung 2 | Exactly one registered WorkItem is bound with no flag. |
| N9 | Rung 3 | Zero WorkItems + legacy `.workflow/state.json` → legacy binding; `state get` succeeds and reads the legacy file. |
| N10 | Rung 4 | Zero WorkItems, no legacy state → `workitem_required`, exit 1, message names `workitem create`. |
| N11 | Rung 5 | Two WorkItems, no flag → `workitem_ambiguous`, exit 1, `data` lists **both** ids. Nothing is written. |
| N12 | `RUNTIME_FREE_COMMANDS` | Each of `lint-skill`, `sha`, `constants`, `workitem list` runs in a WorkItem-less, `.workflow`-less repository without a resolution refusal; a representative runtime command (`state get`) refuses `workitem_required` in the same repository. |
| N13 | `init` never takes rung 3 | Legacy state present, zero WorkItems → `init` refuses `legacy_workflow_present` naming `migrate-workflow`. |
| N13b | `init` refusal is unconditional | Legacy state present **and one WorkItem registered** → `init` still refuses `legacy_workflow_present`. Guards the D2/C4 pin against the orphaned-workflow failure. |

### 8.3 Schema and migration chain (D6)

| # | Test | Assertion |
|---|---|---|
| N14 | Template | `templates/state.json` has `workflow_version == "1.14"` and a `workitem` key. |
| N15 | `1.13 → 1.14` | A 1.13 state under `workitems/wi-a/.sdle/` migrates to 1.14 with `workitem == "wi-a"`. |
| N16 | Legacy location | A 1.13 state at `.workflow/` migrates to 1.14 with `workitem is None`. |
| N17 | Whole chain | `test_migrate_walks_the_whole_chain_from_1_0` equivalent reaches 1.14. (Extend the existing test rather than duplicating it — record as category 2.) |
| N18 | Idempotence and unknown-version refusal still hold at 1.14. | |

### 8.4 `migrate-workflow` (D8, contract §20)

| # | Test | Assertion |
|---|---|---|
| N19 | Happy path | Phase, status, progress, all 8 `approvals`, `artifact_shas`, `rate_limits`, `attempt_counts`, `implementation_base_ref` and `phase_history` survive byte-equal; target audit chain verifies; `workitem` is set; `.workflow/` is byte-identical afterwards (compare SHAs before/after). |
| N20 | Legacy untouched on success | Explicit: legacy `state.json` and `audit.md` SHAs unchanged (contract §8.7, §8.9). |
| N21 | Crash during migration | Monkeypatch `write_atomic` to raise after the Nth call; assert no target `state.json` exists, legacy is unchanged, and a re-run succeeds. Run for N = 1..k covering each copied file. |
| N22 | Corrupt legacy state | Truncated/invalid JSON → integrity failure exit 3, nothing written to the target. |
| N23 | Corrupt legacy audit | `audit_sha` mismatch → refuse `legacy_audit_broken`, nothing written, message names `audit rebaseline`. |
| N24 | Corrupt target state | A pre-existing/garbage target `state.json` → refuse `target_exists`; legacy untouched. |
| N25 | Unregistered WorkItem | `--workitem nope` → `workitem_unknown`, naming `workitem create`. |
| N26 | Evidence + metadata | `<runtime>/evidence/migration-*.json` exists and records the legacy SHAs; `workitem.json` gains the `migration` object; a `workflow_migrated` entry is the last entry of the **target** ledger. |

### 8.5 Execution identity (D7)

| # | Test | Assertion |
|---|---|---|
| N27 | Prefix derivation | `"Muhammad Ali"` → `muh`; `"A_B"` → `ab`… (assert the §8 rule, including the ≤3-char case); email-local-part fallback; final fallback `usr` when git has no identity. Uses `isolated_git_identity`. |
| N28 | Shape | `executionId` matches `^[a-z0-9]{1,3}-\d{8}T\d{6}Z$`; `execution.json` is written at `init` and at `migrate-workflow`; the WorkItem id is **not** derived from it. |

### 8.6 Guardrails (D9, C10)

| # | Test | Assertion |
|---|---|---|
| N29 | Write fence | `workitems/wi-a/.sdle/state.json`, `workitems/index.md`, `workitems/wi-a/workitem.json` are all denied, in POSIX and Windows path forms; `.workflow/...` is still denied; a normal source file is still allowed. |
| N30 | `dirty-tree` hook | Asks under a resolved WorkItem in the implement phase with no preflight; silent when resolution is ambiguous, when zero WorkItems exist, and once `implementation_base_ref` is pinned. |
| N31 | Dirty-tree guard | A file under `workitems/` is not counted as dirt by `implement preflight`. |
| N32 | Phase 17 diff | The security-review diff excludes the WorkItem runtime directory (no `state.json` churn in the evidence). |

### 8.7 `reset` under rebinding (E5)

| # | Test | Assertion |
|---|---|---|
| N33 | `reset --confirm` deletes `state.json`, `audit.md` and `lock` under `<runtime>` and **preserves** `workitem.json`, `workitems/index.md` and the WorkItem directory. |

### 8.8 `project_name` (D10)

| # | Test | Assertion |
|---|---|---|
| N34 | With a requirements heading present, `project_name` is still the heading (guards the D10 precedence decision). |
| N35 | With no inferable heading, `project_name` is the WorkItem title, not the directory name. |

---

## 9. Failure modes

| # | Failure mode | Detection | Response |
|---|---|---|---|
| F1 | **`write_atomic` WinError 5 flake** (E32). Expected to occur, and to occur *more* under T02 because T02 multiplies state and audit writes. | `PermissionError: [WinError 5]` raised at `scripts/sdle.py:463` in `os.replace`. | Re-run **only** the failed node ids, up to 3 times. Classify `ENVIRONMENT_FLAKE` **only** if (a) the traceback terminates at `sdle.py:463`, (b) the exception is `PermissionError` WinError 5, and (c) the node passes on re-run. Any other failure, or a node that fails all 3 re-runs, is a **real regression** and blocks the phase. Report the raw suite exit code unmodified — do not restate a non-zero exit as zero. **Do not patch `write_atomic` in T02** (§12.1). |
| F2 | **Silent guardrail loss** — a runtime file lands outside the fence, or a guard stops firing because its path assumption moved. | N29-N32; `tests/test_hooks.py` (24 cases). | Every path-bearing guard gets an explicit new test before the path is moved, not after. |
| F3 | **Fail-open resolution** — a bug makes the ladder pick a WorkItem when it should ask, or silently write to the legacy path when a WorkItem exists. | N6-N13, especially N11 (ambiguity) and N5 (no repo-global runtime). | Rung 5 must refuse, never choose. Rung 3 must be reachable **only** when zero WorkItems are registered. |
| F4 | **Torn migration** leaves a half-populated target that later resolves as authoritative. | N21. | Target `state.json` is written last and is the sole commit marker (D8 step 8). |
| F5 | **Data loss** — legacy `.workflow/` deleted or mutated. | N20 (SHA comparison before/after). | `migrate-workflow` never writes to, renames or deletes anything under `.workflow/`. Contract §8.9 is absolute. |
| F6 | **Lint desync** — version string missed at one of the six sites, or the migration row omits the literal `workitem`. | `lint-skill` `version_string_consistent`, `migration_covers_every_state_field`. | Run `lint-skill` after **every** documentation edit, as T01's implementer did. |
| F7 | **Future-phase leakage** — T03 resolution (CWD/branch/inference), T04 Spec Kit binding, T05 `.sdle/` config, T07 flows, T09 gates. | §14 exclusion list; verifier inspection. | The ladder stops at rung 5. No `sdle start`, no branch reading, no `SPECIFY_*` env var, no repository-level `.sdle/`. |
| F8 | **Cross-platform regression** — a Windows-only or POSIX-only path assumption enters the new code. | `os.sep` normalisation in every emitted relative path; N29 asserts both path forms. | Emitted paths use `/`; comparisons normalise `\` to `/`, as `SDLE_OWNED_PREFIXES` filtering already does at `scripts/sdle.py:3019`. |
| F9 | **Python 3.11 incompatibility** (E31, UNKNOWN). | Not observable in this environment. | Keep the diff stdlib-only and 3.11-safe: no `match`, no PEP 695 generics, no `Self`, no `tomllib`-era assumptions. Existing code already uses `str \| None` under `from __future__ import annotations`, which is 3.11-safe. Never predict a CI outcome. |
| F10 | **Fixture-induced false green** — the new conftest WorkItem fixture accidentally hides a resolution bug. | N12 and N10 deliberately use a *WorkItem-less* project, not the shared fixture. | At least one test per ladder rung constructs its own project state. |

---

## 10. Rollback and recovery

**Rollback point: `7b9374b`** — the T01 implementation commit, independently
verified `PASS`. `git diff 7b9374b -- <path>` is the authoritative check for
"did T02 touch this".

- T02 is **not** additive; unlike T01 it cannot be verified by a `0 deletions`
  numstat. The equivalent structural proof is the **M1 checkpoint**: at M1 the
  full suite passes with zero test edits, which demonstrates the `Paths` seam is
  behaviour-preserving before any user-visible move happens.
- Because `migrate-workflow` never mutates `.workflow/` (F5), a user who has
  migrated can recover by deleting `workitems/<id>/.sdle/` — the legacy runtime
  is still intact and rung 3 will bind it again.
- If verification `FAIL`s, contract §24.5 applies: a fresh implementer
  remediates only T02, attempt increments, earlier handoff/verification files
  are retained. After 3 failed attempts → `BLOCKED`.
- Checkpoints: persist `T02-checkpoint-a01-NN.md` at each of M1-M7 so an
  interrupted fresh agent can resume from disk plus `git diff`.
- The repository stays usable after every milestone; no milestone leaves the
  engine unable to read its own state.

---

## 11. Acceptance criteria

Objective, each checkable by a named command or test.

- [ ] **A1** `python -m pytest -q` collects at least 287 + the new cases; every
      failure is either absent or satisfies F1's three-part `ENVIRONMENT_FLAKE`
      test. Raw exit code reported unmodified.
- [ ] **A2** `python scripts/sdle.py lint-skill` exits 0 with 22 checks, 22 PASS.
- [ ] **A3** `python tools/transition/validate.py` exits 0.
- [ ] **A4** After a full 18-phase run against WorkItem `wi-a` in a repository
      with no legacy state, `<repo>/.workflow` **does not exist** (N5) — the
      contract §8 exit criterion.
- [ ] **A5** Two WorkItems complete independent runs; N1-N4 pass — the second
      contract §8 exit criterion.
- [ ] **A6** `state.json`, `execution.json`, `audit.md`, `lock`,
      `implementation-manifest.md` and `completion-summary.json` all resolve
      under `workitems/<id>/.sdle/` (N5, N19, N33).
- [ ] **A7** `grep -n '\.workflow' scripts/sdle.py` finds **no** hardcoded
      runtime path outside the `Paths` property block, the legacy-migration
      source, and refusal/help text — in particular `:3132`, `:3153` and the
      `:(exclude).workflow` at `:3240` are gone (E2, E3 closed). Behavioural
      backstop: N31 and N32.
- [ ] **A8** `templates/state.json` reports `1.14`; `lint-skill`
      `version_string_consistent` reports all four locations at `1.14`;
      `migration_covers_every_state_field` passes with the new field.
- [ ] **A9** `VERSION_MIGRATION` has 14 rows and `lint-skill`
      `tables_wellformed` reports `14 migration rows`; `sdle.py constants`
      shows the `1.13 → 1.14` step as terminal.
- [ ] **A10** `migrate-workflow --workitem <id>` satisfies all 12 D8 steps;
      N19-N26 pass; the legacy `.workflow/` SHAs are identical before and after.
- [ ] **A11** The write fence denies `workitems/**` in both path forms and still
      denies `.workflow/**` (N29).
- [ ] **A12** `implement preflight` does not count `workitems/**` as dirt (N31),
      and the Phase 17 diff excludes the WorkItem runtime (N32).
- [ ] **A13** No file in the "must not change" list of §5 differs from
      `7b9374b` (`git diff --exit-code 7b9374b -- <paths>` returns 0).
- [ ] **A14** No phase/gate constant table changed: `SKILL.md` diff versus
      `7b9374b` touches only `VERSION_MIGRATION`, the two version strings, and
      prose.
- [ ] **A15** TP-003 record: every modified test is listed with its category and
      rationale; **no test is skipped, xfailed, deleted or weakened**
      (`git diff 7b9374b -- tests/ | grep -E '^\+.*(skip|xfail)'` is empty).
- [ ] **A16** Python 3.11 / CI: **`NOT_RUN`**. Recorded as such, with no
      predicted outcome (E31).

---

## 12. Unknowns and decision requirements

### 12.1 `write_atomic` WinError 5 — diagnosis and decision request

**This is a decision for the orchestrator to take to the user. It is
deliberately NOT in T02's scope, and T02 does not depend on it.**

#### What is established

| Class | Finding | Evidence |
|---|---|---|
| OBSERVED | `write_atomic` cannot leak a handle. The temp file is created with `delete=False`, written and closed inside `with handle:`, and `os.replace` runs only after that block exits. Both the success path and the `except BaseException` cleanup path are closed-form. | `scripts/sdle.py:446-469` read in full |
| OBSERVED | No reader in the engine, the hooks or the fixtures can leak a handle either. `scripts/sdle.py` contains exactly one non-`read_text` file open — `path.open("rb")` inside `sha256_file` at `:440` — and it is context-managed. `hooks.py` and `conftest.py` use `Path.read_text` exclusively. | `grep -n "read_text\|\.open(\|open(" scripts/sdle.py .claude/hooks/hooks.py tests/conftest.py` |
| OBSERVED | The suite is single-process and sequential: no `pyproject.toml`, `pytest.ini`, `setup.cfg` or `tox.ini` exists, so there is no `addopts`, no xdist, no parallel worker. Subprocesses (`git`, `run_cli`) are launched with `subprocess.run`, which waits for exit. | E28; `tests/conftest.py:113-118`, `:166-173` |
| OBSERVED | The victim moves between runs and between unrelated tests and files — `state.json` in `test_traversal_matches_the_transcript` (T00), `state.json` + `audit.md` in `test_04_unapproved_gates_are_never_drift_checked` (T00 plan), four distinct victims including a fixture-setup `ERROR` at T01. Wall-clock for the identical single test was 9.45 s / 9.77 s / 35.96 s. | `baseline.md` §6.1; `progress.md` T00/T01 rows |
| INFERRED | A **deterministic** defect is ruled out (moving victims). A leak **inside `write_atomic`** is ruled out by reading its source — there is no control path on which the temp handle survives to the `os.replace` call. A leak in an SDLE **reader** is ruled out by the grep above. On Windows, `os.replace` needs `DELETE` access on the source and must delete the destination; both files were written by this same process microseconds earlier. The remaining consistent explanation is a **transient external holder** (on-access scanner, search indexer or backup agent) briefly opening the freshly-created `.tmp` or the destination without `FILE_SHARE_DELETE`. The 4× wall-clock spread on identical work is the corroborating signature. | Above rows |
| **UNKNOWN** | **Which** holder. Naming it requires a live experiment. | See below |

#### Why the diagnosis stops at INFERRED

The discriminating experiment — a tight in-process `write_atomic` stress loop,
plus a handle query on the destination at the moment of failure — was attempted
and **refused by the transition guard**, verbatim:

```text
PreToolUse:Bash hook error: [python tools/transition/agent_guard.py planner]:
SDLE transition agent guard: planner Bash/PowerShell must be observational;
blocked command shape
```

That refusal is correct and was not routed around (contract §1 item 15, and the
T00-blocker §3 precedent of a planner bypassing the `Write` tool with
`python -c`). The root cause therefore stays `UNKNOWN`, as it was at
`baseline.md` §6.1.

#### Options, smallest first

| # | Option | Cost | Effect |
|---|---|---|---|
| **O1** | **Bounded retry around `os.replace` only.** ~6 lines: catch `PermissionError`, sleep 10/20/40/80 ms, retry up to 4 times, re-raise on exhaustion. Temp-file cleanup contract unchanged; `os.replace` remains a single atomic call. | 6 lines in the most safety-critical function in the engine. Requires one new test proving a **permanent** `PermissionError` (monkeypatched `os.replace`) still raises — so it can never fail open. | Fixes the symptom whatever the external holder is; portable; helps CI on `windows-latest`. |
| O2 | Do nothing; keep the F1 re-run procedure. | Zero code. | Raw suite exit stays reliably non-zero. Every future verifier inherits a judgement call on a red suite, and a genuine future regression at `:463` would be misclassified as the known flake. Risk rises at T02 and again at every later phase. |
| O3 | Exclude the pytest temp root from the host's on-access scanner. | Environment change, needs admin. | Helps this machine only. Does nothing for CI or for any other developer. Not a repository fix. |
| O4 | Instrument first: stress harness plus a Restart-Manager / `handle.exe` query to name the holder, then decide. | An extra investigation cycle before T02 implementation. | Converts the `UNKNOWN` to `OBSERVED`. Does not by itself fix anything. |

#### Recommendation

**O1, authorised by the user and landed as its own commit *before* T02
implementation begins**, with O4's evidence requirement folded into O1's
acceptance (the new permanent-failure test is what proves it is not fail-open).

Rationale: T02 multiplies state and audit writes, so the flake rate will rise
inside the very phase whose verification is hardest to read; landing the fix
first de-noises T02's verification. O1 is a strict superset of current
behaviour — after ~150 ms of retries it raises exactly the exception it raises
today.

**Why it is not the implementer's call:** `baseline.md` §5 marks atomic writes
`PRESERVE`, and contract §18 lists "Atomic writes — PRESERVE". Changing that
function inside T02 without authorisation would be exactly the silent-guardrail
edit the verifier is instructed to hunt for. If the user declines, T02 proceeds
unchanged under F1; nothing in this plan depends on the outcome.

### 12.2 Remaining unknowns

| # | Unknown | Class | Handling |
|---|---|---|---|
| U1 | Python 3.11 and CI behaviour of this branch (E31). | UNKNOWN | Design stays stdlib-only and 3.11-safe (F9). Recorded `NOT_RUN` (A16). Never predicted. |
| U2 | Whether any existing assertion depends on the machine's real Git identity (blocks the §7.3 promotion). | UNKNOWN | Resolved by the implementer with a grep plus a before/after full-suite run, per §7.3. Falls back to leaving the fixture file-scoped. Not material to T02's design. |
| U3 | Whether external users depend on the legacy `.workflow/` migration path (contract §20 allows reducing it "only by explicit decision"). | UNKNOWN | T02 implements the full path, which is the safe default. No decision needed to proceed. |

None of U1-U3 is material to executability, so per contract §24.2 item 14 and
§25 rule 6 this plan is **PLANNED**, not `BLOCKED`. §12.1 is returned as a
decision **request**, not a blocker: T00 and T01 both completed under the F1
procedure, and T02 can too.

---

## 13. Verification protocol for this phase

The T02 verifier inherits a suite that is reliably red at the raw exit level
(E32). To keep §24.4 meaningful, the pass condition is pinned here:

1. Run the full suite. Record the **raw** exit code and the complete failure
   list verbatim.
2. For each failure, apply F1: it is `ENVIRONMENT_FLAKE` **only** if it is a
   `PermissionError` WinError 5 whose traceback terminates at
   `scripts/sdle.py:463`, **and** the node passes within 3 targeted re-runs.
3. Anything else — a different exception, a different line, or a node that fails
   all 3 re-runs — is a regression and the phase `FAIL`s.
4. Run `lint-skill` and `tools/transition/validate.py`; both must exit 0.
5. Independently inspect `git diff 7b9374b` for: future-phase leakage (§14),
   weakened tests (A15), fail-open resolution (F3), duplicated sources of truth
   (a second state template, a second phase table, a hardcoded runtime path),
   and any mutation of `.workflow/` by `migrate-workflow` (F5).
6. Verify A4 and A5 by driving the real CLI, not by reading the handoff.

---

## 14. Scope exclusions — must not leak into T02

| Excluded | Owning phase | Why |
|---|---|---|
| CWD-based, branch-based, persisted-context or AI-assisted WorkItem resolution; `sdle start --workitem`; branch-mismatch warnings; recording branch and starting SHA; `sdle validate`'s WorkItem checks | **T03** | Contract §9. T02 implements only the D2 ladder. |
| Binding Spec Kit to the WorkItem; `SPECIFY_INIT_DIR` / `SPECIFY_FEATURE_DIRECTORY`; demoting `current_feature_id`; changing `ARTIFACT_OWNERSHIP` templates; moving `clarifications/`, `reviews/` or Spec Kit artefacts under `workitems/` | **T04** | Contract §10; `baseline.md` §7 item 5. This is why D9 fences all of `workitems/` now and T04 carves out artefact subpaths later. |
| Repository-level `.sdle/` (config, policies, templates, baseline, implementation-state); any YAML dependency decision | **T05** | Contract §11. T02 creates only the **WorkItem-level** `.sdle/`. Note: D9's fence pattern will also match a repository-root `.sdle/`; T05 must revisit it. |
| Requirements-quality gate, WorkItem type/flow classification, hybrid risk, governed-artifact review/SHA binding, `ARTIFACT_REVIEWED` audit events, structured JSONL audit events | **T06** | Contract §12, TP-011. D4 keeps `audit.md` precisely so this stays T06's. |
| Any change to PHASE_SEQUENCE, NEXT_PHASE, PHASE_LABEL_MAP, PROGRESS_MAP, `advance`, `skip`, `restart`, `doctor` semantics, `phase_history`, guidance files | **T07** | Contract §13; `baseline.md` §7 item 1. |
| Brownfield discovery, `.sdle/baseline.*` | **T08** | Contract §14. |
| Conditional/risk-adaptive gates, GATE_PHASES, PHASE_TO_GATE_KEY, the `approvals` key set, Gate 7 manifest enforcement rules | **T09** | Contract §15; `baseline.md` §7 item 2. |
| Product skills/subagents (`sdle-design-review` etc.) | **T10** | Contract §16 — and §1.4: the `sdle-transition-*` agents are not product subagents. |
| Removing `.workflow/` support, removing rung 3, removing the migration command, removing `current_feature_id` | **T11** | Contract §17. The dual-read path introduced by D2 rung 3 is explicitly on T11's removal list. |
| Patching `write_atomic` | **user decision**, §12.1 | `baseline.md` §5/§6.1; contract §18 "Atomic writes — PRESERVE". |
| Hardening `cmd_workitem_create`'s `is_dir()` uniqueness scan against a stray *file* at `workitems/<id>` (E18) | **deferred nit** | Unreachable through any SDLE path: `workitem create` is the only writer of `workitems/<id>`, and T02's resolution reads the **index**, not the directory listing (D2, E17). Fixing it here would add a code path with no test that can reach it honestly. Recorded so a later phase can pick it up when directory scanning becomes real (T03). |
| Release/build management, MCP, databases, REST/web UI, distributed locks, knowledge graph, OPA, cross-repository orchestration | **never in this transition** | Contract §27. |
