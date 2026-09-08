# T01 Plan — Introduce WorkItem Identity Without Moving Runtime State

**Phase:** T01
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED
**Contract sections:** §5 (T01 row), §7 (full phase definition), §18 (capability matrix), §19 (version control), §22 (CLI evolution), §24.2 (this duty list)
**Baseline evidence base:** `docs/transition/baseline.md` (T00 deliverable, independently verified PASS)
**Repository at planning time:** branch `transition/workitem-v1`, HEAD `a12b9e238a08fb7f1837c01e2f4c672f84d4639e`, working tree clean

---

## Objective

Add the WorkItem as a **first-class, immutable identity** — a normalized id, a
metadata file, and an append-only registry — created **before** legacy workflow
initialization, while `.workflow/` remains the runtime state and every existing
phase/gate behaviour stays byte-for-byte identical.

Contract §7 exit criterion, verbatim:

> A new workflow has an immutable WorkItem identity before legacy workflow
> initialization, while all existing phase/gate behavior still passes.

T01 is the first phase that changes product code. It changes **only additive
surface**: new CLI subcommands, new files under `workitems/`, and the
orchestration text that calls them. It changes **no** state schema, no phase
table, no gate table, no lock code, and no `.workflow/` path.

### What "identity before init" means mechanically

The ordering constraint is enforced at the **orchestration layer**
(`.claude/commands/sdle-start.md` + `SKILL.md` Step 1), not inside the
deterministic core. `sdle init` is deliberately left untouched: it neither
requires nor records a WorkItem. That is exactly contract §7 *Compatibility
behavior* — "WorkItem identity is added alongside the legacy runtime" — and it
is what keeps the entire existing 230-test suite green without a single test
edit. Deterministic binding of state to a WorkItem is **T02's** job (contract §8
"Migration MUST: 1. require an explicitly resolved WorkItem").

---

## Repository evidence

All file:line references were opened in this planning context unless the class
says otherwise.

| # | Claim | Class | Evidence |
|---|---|---|---|
| E1 | Working tree is clean; HEAD is `a12b9e2` on branch `transition/workitem-v1`. | OBSERVED | `git status --porcelain` empty; `git rev-parse HEAD`; `git branch --show-current`, this context |
| E2 | Every file differing from baseline `f8fdaa0` is an **addition** of transition control-plane / evidence; **zero product files modified**. | OBSERVED | `git diff --name-status f8fdaa0 HEAD` → 26 rows, all `A`, all under `docs/transition/`, `tools/transition/`, `.claude/agents/`, `.claude/skills/apply-sdle-transition/`, or `SDLE-TRANSITION-*` |
| E2a | Baseline `f8fdaa0` **is an ancestor of** HEAD: `git rev-list --count HEAD..f8fdaa0` = **0** (nothing in the baseline is unreachable from HEAD) and `git rev-list --count f8fdaa0..HEAD` = **1** (the single control-plane commit). Contract §1 item 2's stop-condition does not fire. | OBSERVED | both counts run this context. `git merge-base --is-ancestor … && echo` was blocked by the planner Bash guard as a compound command shape; the two count commands are the equivalent single-command proof |
| E3 | The control plane is now **committed**, unlike the `UNCOMMITTED` value recorded in T00's progress row. T01's rollback point is `a12b9e2`. | OBSERVED | E1 + E2 |
| E4 | `scripts/sdle.py` is stdlib-only, `from __future__ import annotations`, declared "Python 3.11+". | OBSERVED | `scripts/sdle.py:1-30` |
| E5 | CI runs Python **3.11** on a matrix of `ubuntu-latest` and `windows-latest`. | OBSERVED | `git show HEAD:.github/workflows/ci.yml` (§6.3 of baseline: `.github/` needs `git show`, not Read) |
| E6 | The four exit codes are `EXIT_OK/REFUSED/USAGE/INTEGRITY = 0/1/2/3`; refusals carry a machine-readable `reason`. | OBSERVED | `scripts/sdle.py:37-40`, `:66-94`; baseline §4.2 |
| E7 | Every command returns one envelope shape via `emit(command, data, ok, reason, message)`; JSON to stdout, prose to stderr. | OBSERVED | `scripts/sdle.py:3042-3049` |
| E8 | `write_atomic(path, text)` = temp file in the target dir + `fsync` + `os.replace`, unlinking the temp on any exception. | OBSERVED | `scripts/sdle.py:446-469` |
| E9 | `git(paths, *args)` shells out with `cwd=project_root` and **never raises** — returns `(127, "")` when git is absent. | OBSERVED | `scripts/sdle.py:497-511` |
| E10 | `actor(paths)` returns one combined `"name <email>"` string and is cached per project root; it does not expose the two fields separately. | OBSERVED | `scripts/sdle.py:521-535` |
| E11 | `append_audit()` requires a live `state` dict (it writes `state["audit_sha"]`) and its callers get that dict from `read_state()`, which raises `IntegrityError("state_unreadable")` when `.workflow/state.json` is absent. | OBSERVED | `scripts/sdle.py:681-720`, `:554-571` |
| E12 | Therefore an audit entry **cannot** be written before `init` without either creating state early or failing open. | INFERRED | from E11 |
| E13 | `parse_md_table(path, heading)` matches headings via `^#{2,4}\s+([A-Za-z_][A-Za-z0-9_]*)\b` — it cannot address `# Work Items` (h1, two words). Its row helpers `_split_row` / `_is_separator` are reusable. | OBSERVED | `scripts/sdle.py:191-296` |
| E14 | `resolve_paths()` resolves `--project-root` (or `SDLE_PROJECT_ROOT`, or cwd) to an absolute path; `Paths` exposes `.workflow`, `state_file`, `audit_file`, `lock_file` and the skill files — there is no WorkItem concept. | OBSERVED | `scripts/sdle.py:101-189` |
| E15 | `build_parser()` registers every subcommand in one function ending at `return parser`; nested groups use `add_subparsers(dest="subcommand", required=True)`. | OBSERVED | `scripts/sdle.py:3446-3686` |
| E16 | The CLI surface is **65 `add_parser` registrations** (33 top-level, 32 nested; 16 top-level parsers are groups ⇒ 49 invocable paths). T00-plan.md's "21 top-level subcommands" is wrong and must not be inherited. | OBSERVED | baseline §4.1 (65 rows); `T00-verification-a01.md`; progress.md T00 Notes |
| E17 | No existing test enumerates the parser's command set, so adding a group cannot break one. | INFERRED | grep of `tests/` for `add_parser`/command-set assertions found none; `tests/test_units_cli.py` asserts help/usage/envelope only |
| E18 | lint-skill's 22 checks cover phase/gate tables, single state template, version string across 4 documents, migration coverage of every template field, PowerShell-only cmdlets in skill files, hardcoded `N/18`, and doc phase tables. **None inspects the CLI surface.** | OBSERVED | `scripts/sdle.py:3106-3398` |
| E19 | `_check_migration_covers_state_fields` fires if `templates/state.json` gains a field with no `VERSION_MIGRATION` row ⇒ any new state field forces a version bump across four documents. | OBSERVED | `scripts/sdle.py:3289-3320`; `tests/test_lint_skill.py::test_a_state_field_without_a_migration_row_fires`; CLAUDE.md "Cross-File Sync Rules" |
| E20 | `_check_version_consistency` takes the **first** `\*\*v([0-9]+\.[0-9]+)\*\*` match in README.md and the first `^# SDLE.*\(vX.Y\)` title match; both must equal the template's `workflow_version`. | OBSERVED | `scripts/sdle.py:3253-3287` |
| E21 | `_check_single_state_template` fails if `SKILL.md` contains `"workflow_version"\s*:\s*"` anywhere ⇒ no JSON state example may be pasted into SKILL.md. | OBSERVED | `scripts/sdle.py:3233-3251` |
| E22 | The write fence covers exactly `(".workflow", "requirements", "guidance")`. `workitems/` is not fenced. | OBSERVED | `.claude/hooks/hooks.py:48-64`, `:129-138` |
| E23 | `.gitignore` ignores `.workflow/ .specify/ design/ reviews/ clarifications/ __pycache__/ *.pyc .pytest_cache/`. `git check-ignore -v` reports **no match** for `workitems/index.md`, `workitems/x/workitem.json`, `workitems/x/.sdle/state.json`; it *does* match `workitems/x/reviews/…` and `workitems/x/clarifications/…` (unanchored directory patterns). | OBSERVED | `.gitignore`; `git check-ignore -v` run this context |
| E24 | T01 therefore needs **no `.gitignore` change**: the two artefacts it creates are already versionable. The nested `reviews/`/`clarifications/` collision is a T02+ concern, when those directories move under a WorkItem. | INFERRED | from E23 + contract §19 |
| E25 | The bootstrap turn is described in `SKILL.md` Step 1 (final two paragraphs) and executed by `.claude/commands/sdle-start.md` steps 1-5: preflight → resume-or-`init`. | OBSERVED | `.claude/skills/sdle/SKILL.md:229-246`; `.claude/commands/sdle-start.md` |
| E26 | The repo contains **no** "latest requirements" document requiring `workitem.yaml`; the only WorkItem prose is the contract itself and the transition control plane. | OBSERVED | repo-wide grep for `workitem`/`work item` in `*.md` outside `docs/` → only `.claude/agents/sdle-transition-orchestrator.md` and `.claude/skills/apply-sdle-transition/SKILL.md` |
| E27 | Baseline §5 row "Runtime artifacts excluded from version control" is `SUPERSEDE_LATER`, changing phase "**T01 first**, T11 completes", anchor `NO_ANCHOR`. | OBSERVED | baseline §5 |
| E28 | Baseline §4.3 marks state field `project_name` `ADAPT` at changing phase **T01**. | OBSERVED | baseline §4.3 |
| E29 | Baseline §5 row "Four wired Claude hooks" is `ADAPT` at **T02**, anchored by `tests/test_hooks.py::test_every_guard_is_registered` + 19 cases. | OBSERVED | baseline §5 |
| E30 | Baseline §7 preserves by decree until their named phase: 18-phase sequence (T07), 8 gates (T09), `.workflow/` location (T02), lock behaviour (T02), Spec Kit feature behaviour (T04). | OBSERVED | baseline §7 |
| E31 | A non-deterministic Windows `PermissionError: [WinError 5]` at `scripts/sdle.py:463` (`os.replace` in `write_atomic`) hits 1-2 arbitrary tests per full run. Five distinct victim nodes observed across three contexts; classified `ENVIRONMENT_FLAKE`. | OBSERVED (occurrence) / INFERRED (environmental cause) | baseline §6.1; T00 progress Notes |
| E32 | Baseline suite status: 230 collected, 228 passed / 2 failed (both WinError 5), lint-skill 22/22 PASS, on Python **3.14.6** / pytest 9.1.1, Windows only. | OBSERVED (recorded by T00, not re-run here) | baseline §3.1-§3.2 |
| E33 | Whether the baseline is green on **Python 3.11** (ubuntu-latest / windows-latest) is not established — CI has never been observed to run on this branch. | UNKNOWN | baseline §3.4-§3.5 record CI as `NOT_RUN`; progress T00 Notes "CI unobservable on a local-only branch" |
| E34 | Root cause of the `write_atomic` flake. | UNKNOWN | baseline §6.1 "Root cause `UNKNOWN`"; the fix decision is scheduled for T02 planning |
| E35 | Whether the human ultimately wants `workitem.yaml` instead of `workitem.json`. | UNKNOWN | E26 — no such requirement exists in the repository; contract §7 supplies a JSON default, so the default is contract-sanctioned, not a guess |
| E36 | The tests fixture `project` copies the skill, `scripts/`, hooks and settings into a scratch tree and invokes `main()` in-process; `git_project` additionally runs `git init` with local identity `SDLE Test <test@example.invalid>`. | OBSERVED | `tests/conftest.py` |

---

## Behavioral delta

### Deliberate changes

**D1 — New CLI group `workitem` with two subcommands.**
Contract §22 lists `create`, `resolve`, `list`, `validate`. T01 implements
**`create` and `list` only**; `resolve` and `validate` are contract §9 (T03)
work and are excluded (see Scope exclusions).

```
sdle workitem create --name "<raw name>" [--type <t>] [--synopsis <s>] [--auto-generate]
sdle workitem list
```

Both return the standard envelope (E7) and use the standard exit codes (E6).

**D2 — Deterministic name normalization**, exactly contract §7 rules 1-10:
trim → lowercase → whitespace to `-` → `_` to `-` → drop unsupported
punctuation → collapse repeated hyphens → strip leading/trailing hyphens →
allow only `[a-z0-9-]` → reject empty → require uniqueness.
`Customer Notification Service` → `customer-notification-service`.

**D3 — Two accepted id shapes.** This is load-bearing; do not collapse them.

| Path | Id shape | Regex |
|---|---|---|
| user-supplied name (default) | normalized kebab-case | `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` |
| `--auto-generate` | `WI-<normalized-name>-<YYYYMMDDTHHMMSSZ>` | `^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$` |

Normalization (D2) applies **only to the inferred-name segment** of the
auto-generated id. The `WI-` prefix and the `T`/`Z` of the timestamp are
uppercase by contract (§7 example `WI-payment-retry-20260816T170530Z`) and must
survive. An implementer that lowercases the whole id contradicts the contract.

The timestamp is minted by the deterministic core (contract §7: "Deterministic
core creates …"), UTC, second resolution — reuse `now_iso()`
(`scripts/sdle.py:477`) reformatted to compact form, do not introduce a second
clock.

**D4 — WorkItem metadata file** `workitems/<id>/workitem.json`, written with
`write_atomic` (E8), exactly the contract §7 shape:

```json
{
  "id": "customer-notification-service",
  "name": "customer-notification-service",
  "title": "Customer Notification Service",
  "type": "enhancement",
  "synopsis": "Add configurable customer notifications.",
  "createdAt": "2026-08-16T17:05:30Z",
  "createdBy": { "gitUserName": "SDLE Test", "gitUserEmail": "test@example.invalid" },
  "git": { "initialBranch": "feature/customer-notification-service" },
  "sdleVersion": "1.13"
}
```

- `title` is the caller's raw `--name` after trim only (the human form).
- `type` defaults to `enhancement` when `--type` is omitted; the four-value
  classification vocabulary (`enhancement|defect|hotfix|chore`) is **T06**, so
  T01 records the string without enumerating or validating it against a policy.
- `synopsis` defaults to `null`.
- `createdBy` fields come from `git config user.name` / `user.email` via the
  existing `git()` helper (E9). `actor()` is not reusable here (E10) and must
  not be changed — it is on the audit hot path and cached.
- `git.initialBranch` from `git rev-parse --abbrev-ref HEAD`; `null` when git
  is absent, the tree is not a repo, or HEAD is detached. **Never refuse on
  missing git** — the metadata records what is knowable.
- `sdleVersion` = the module constant `CURRENT_VERSION` (`scripts/sdle.py:541`,
  currently `"1.13"`). No version bump in T01.

**D5 — Append-only registry** `workitems/index.md`, contract §7 shape:

```markdown
# Work Items

| Created | WorkItem | Type | Title | Synopsis |
|---|---|---|---|---|
```

Rules implemented: append only; no mutable status column; duplicate id
rejected; structure validated before append; **no hash chaining** (contract §7
says not yet). Created on first `workitem create` if absent. Appending is
read → validate → append one row → `write_atomic` of the whole file, so a crash
never leaves a torn registry. Row parsing reuses `_split_row` / `_is_separator`
(E13); `parse_md_table` itself is not reusable for this heading and must not be
loosened to make it fit.

**D6 — Refusal vocabulary** (pinned; the implementer must not invent variants):

| Reason | Exit | When |
|---|---|---|
| `workitem_name_invalid` | 1 | normalization yields empty; result violates the id regex; name exceeds 64 characters; name normalizes to a Windows reserved device name (`con`, `prn`, `aux`, `nul`, `com1`-`com9`, `lpt1`-`lpt9`) |
| `workitem_exists` | 1 | id already present in the index **or** a directory of that id already exists; `data` carries the existing id so the caller can offer resume-or-rename |
| `index_malformed` | 3 | `workitems/index.md` exists but its heading/columns do not match D5, or a row has the wrong cell count |

Exit 3 for `index_malformed` mirrors `state_unreadable` (E6, `IntegrityError`):
a corrupt registry is an integrity condition, not a policy refusal, and the
engine must not "repair" it by rewriting. Nothing is written on any refusal.

The 64-character cap and reserved-name rejection are deliberate additions
beyond contract §7's ten rules: `workitems/<id>/.sdle/…` becomes deep at T02 and
the repo is Windows-first (CI matrix E5). Both fold into
`workitem_name_invalid` with a `data.rule` discriminator so the vocabulary
stays small.

**D7 — Case-insensitive uniqueness.** Uniqueness is checked case-insensitively
against both index ids and existing directory names. Ids are lowercase by
construction on the user path, but the auto path carries `WI-`/`T`/`Z`, and
Windows/macOS filesystems are case-insensitive — a case-only collision must
refuse rather than silently target the same directory.

**D8 — Path containment.** After building the target path, resolve it and
verify it is inside `<project_root>/workitems/`; refuse otherwise. The D3 regex
already makes traversal unreachable, so this is a cheap second fence, not the
primary control.

**D9 — Bootstrap orchestration order.** `.claude/commands/sdle-start.md`
becomes: preflight → **ask for the WorkItem name → `sdle.sh workitem create`** →
`sdle.sh init`. On `workitem_exists`, Claude asks the contract §7 question —
"Resume existing WorkItem? or Provide another name?" — and never auto-suffixes
(`foo-2`, `foo-copy`, `foo-final` are explicitly forbidden). `auto generate` is
honoured **only** when the user says it: Claude infers a concise name and passes
`--auto-generate`.

**D10 — SKILL.md Step 1** gains the same ordering statement for the new-workflow
path, and Step 4's routing table is left alone (`start workflow` still routes to
`/sdle-start`).

**D11 — `workitem list`** projects the registry rows (`id`, `created`, `type`,
`title`) in index order. It reads the **index**, not the directory listing, so
the registry stays the single source of truth. Absent index ⇒ `ok: true` with an
empty list. Malformed index ⇒ the same exit-3 `index_malformed` as create.

### Preserved invariants

| # | Invariant | Why it survives |
|---|---|---|
| P1 | `.workflow/` remains the runtime state location (baseline §7 item 3, changeable only at T02). | No `Paths` property is added, moved or re-pointed. |
| P2 | Current lock behaviour (baseline §7 item 4, T02). | `workitem create`/`list` neither acquire nor refresh the lock; they do not call `touch_lock` and take no `--session` effect. |
| P3 | 18-phase sequence (baseline §7 item 1, T07) and 8 gates (item 2, T09). | No constant table in `SKILL.md` is touched; `PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_TO_GATE_KEY`, `GATE_PHASES`, `ARTIFACT_OWNERSHIP`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`, `VERSION_MIGRATION` are all out of scope. |
| P4 | Current Spec Kit feature behaviour (baseline §7 item 5, T04). | `current_feature_id`, `feature resolve` and `preflight` are untouched. |
| P5 | `state.json` schema, `workflow_version` `1.13`, and the 13-row migration chain. | T01 adds **no** state field (E19 — a field would force a version bump across four documents plus a migration row). |
| P6 | Exit-code and JSON-envelope contracts. | New commands use `emit()` and the existing `Refused`/`IntegrityError` classes only (E6, E7). |
| P7 | Atomic writes. | Both new writers go through `write_atomic` (E8); no direct `open(...,"w")` on a governed file. |
| P8 | Audit chain integrity. | `append_audit` and the ledger are not called or touched by T01 (see D-note below). |
| P9 | Idempotent deterministic commands. | `workitem list` is pure; `workitem create` is not idempotent by design (uniqueness) and refuses deterministically on repeat — the observable result of running it twice is stable. |
| P10 | Stdlib-only, Python 3.11-compatible, cross-platform. | No new import beyond what `sdle.py` already imports; no 3.12+ syntax (E4, E5). |
| P11 | Resume path unchanged. | When `.workflow/state.json` exists, `/sdle-start` resumes exactly as today and **never prompts for a WorkItem name**. Pre-T01 workflows keep working with no WorkItem — that is contract §7 "alongside", and it is what makes the transcript-derived integration tests still valid. |
| P12 | Four hook guardrails unchanged. | `.claude/hooks/hooks.py` and `.claude/settings.json` are not edited (E22, E29). |

**No audit entry on `workitem create` — deliberate, not an omission.** Ordering
forces it: creation precedes `init`, and `append_audit` cannot run without live
state (E11, E12). Wiring it would mean either creating `.workflow/state.json`
early (a T02 behaviour, forbidden here) or failing open. Contract §7 names
`workitems/index.md` the "creation registry"; the index row plus
`workitem.json` **are** the durable creation record, and both are versioned in
Git (E23/E24). No existing guardrail is weakened — this is a new artefact class
that has its own record. Binding WorkItem events into a WorkItem-scoped audit is
contract §8 (T02); governed-artifact registration/review of `workitem.json` is
contract §12 (T06).

**Baseline §4.3 `project_name` is annotated `ADAPT` at T01 (E28) — declared
deviation.** T01 leaves `project_name`'s observable contract completely
unchanged: `init` still infers it from the first `#` heading or `--project`
(`scripts/sdle.py:1053-1088`). The rebinding that annotation anticipates
(project name giving way to WorkItem title) requires state to reference the
WorkItem, which is a state-schema change (P5) and belongs to T02. This is a
documented deviation from a T00 *prediction*, not from the contract: contract §7
never mentions `project_name`. Recorded here so the verifier sees it declared
rather than silently skipped.

---

## Files expected to change

| File | Change | Risk |
|---|---|---|
| `scripts/sdle.py` | **New section** (place it after the `init / state / header` section, before `artifact path`, matching the file's existing section-banner style): `WORKITEM_ID_RE`, `AUTO_ID_RE`, `RESERVED_NAMES`, `normalize_workitem_name()`, `workitem_dir()`, `read_index()`, `append_index_row()`, `cmd_workitem_create()`, `cmd_workitem_list()`. **Plus** one `workitem` group registration in `build_parser()` (E15). No existing function modified. | Medium — largest new surface |
| `.claude/commands/sdle-start.md` | Insert the name prompt + `workitem create` between current steps 1 and 3; document the duplicate and `auto generate` branches (D9). Resume branch untouched (P11). | Low |
| `.claude/skills/sdle/SKILL.md` | Step 1 new-workflow paragraph gains the WorkItem step. **No constant table touched.** No `"workflow_version"` JSON (E21), no PowerShell-only cmdlet (`_check_no_powershell`), no literal `N/18` (`_check_no_hardcoded_progress`). | Medium — lint-sensitive |
| `README.md` | Add `workitem create` / `workitem list` to the Commands section context, and `workitems/` to the "In your target project" File Layout block. **Do not** introduce a `**vX.Y**` bold string or a `# SDLE … (vX.Y)` heading above the existing ones (E20). No version-history row (no version bump). | Medium — lint-sensitive |
| `docs/SDLE-Reference-Guide.md` | One short "WorkItem identity" subsection: id rules, the two id shapes, the registry, and the explicit statement that runtime state is still `.workflow/` until T02. Header version line untouched. | Low |
| `scripts/README.md` | Optional: one line noting the new group in the command overview, if that file enumerates commands at the edited point. Skip if it does not. | Low |
| `tests/test_units_workitem.py` | **New file** — see New tests required. | Low |

**Files that must NOT change** (a diff here is a verification failure):
`.claude/skills/sdle/templates/state.json`, `.claude/skills/sdle/modules/*`,
`.claude/hooks/hooks.py`, `.claude/settings.json`, `.gitignore` (E24),
`scripts/sdle.sh`, `scripts/sdle.ps1`, `.github/workflows/ci.yml`, and every
existing file under `tests/`.

---

## Baseline regression-matrix dispositions T01 touches

Every capability T01 comes near, with the `baseline.md` §5 / §4 row that governs
it. Where T01's behaviour differs from the row's prediction, the difference is
stated.

| baseline row | Disposition / changing phase | What T01 does |
|---|---|---|
| §5 "Runtime artifacts excluded from version control" | SUPERSEDE_LATER — "T01 first, T11 completes", `NO_ANCHOR` | **Satisfied with zero diff.** `git check-ignore` shows `workitems/index.md` and `workitems/<id>/workitem.json` are already unignored (E23). The reversal this row anticipates needs no `.gitignore` edit at T01; the nested `reviews/`/`clarifications/` patterns become relevant only when those directories move under a WorkItem (T02+). An acceptance criterion asserts the unignored state so the row gains the anchor it lacks. |
| §4.3 `project_name` | ADAPT — T01 | **Declared deviation**: unchanged in T01, rebinding deferred to T02. Rationale in "Preserved invariants". |
| §5 "Four wired Claude hooks" | ADAPT — T02 | Untouched (P12). `workitems/` is deliberately **not** added to the write fence in T01; that is the T02 path-adaptation pass. No guardrail is lost — a new artefact class simply is not fenced yet, and Git plus the deterministic append path are its integrity controls meanwhile. |
| §5 "`.workflow/` repo-global runtime" / "Single repository-wide session lock" | SUPERSEDE_LATER — T02 | Untouched (P1, P2); baseline §7 items 3 and 4 forbid change before T02 is verified. |
| §5 "Hard-coded 18-phase sequence" / "Hard-coded 8 approval gates" | SUPERSEDE_LATER — T07 / T09 | Untouched (P3); baseline §7 items 1 and 2. |
| §5 "`current_feature_id` as the primary workflow identity" / "Spec Kit preflight, skill discovery and feature binding" | SUPERSEDE_LATER — T04 | Untouched (P4); baseline §7 item 5. WorkItem identity is added **beside** it, not over it. |
| §5 "`state.json` schema, 25 top-level fields" / "Version migration chain, 13 rows" | ADAPT — T02 | Untouched (P5). No field, no migration row, no version bump. |
| §5 "`write_atomic` temp-file + `os.replace`" | PRESERVE | Reused verbatim for both new writers (P7). The known flake (E31) is **not** fixed here — see F1. |
| §5 "Four-value exit-code contract" / "Pure-JSON stdout envelope" | PRESERVE | New commands conform (P6); no new exit code, no new envelope shape. |
| §5 "22-check cross-file sync linter" | PRESERVE initially | Must still report 22/22 PASS after the doc edits; see F2. |
| §5 "Tests derived from recorded dry-run transcripts" | PRESERVE | Untouched — guaranteed by P11 (the resume/`init` paths are not modified). |
| §5 "Deterministic Python core" | PRESERVE | Extended additively; no existing function body modified. |

---

## Existing tests affected

**TP-003 declaration: the set of existing tests deliberately modified is
EMPTY.** T01 changes no existing behaviour, so category 2 ("deliberately
superseded") and category 3 ("defect discovered") are both empty. If the
implementer finds itself editing a file under `tests/` that already exists, the
plan is wrong and the phase should stop rather than the test bend (contract §1
item 16, TP-003).

All 230 collected tests are category 1 — unchanged behaviour, must remain green.
At-risk subsets, and why:

| Test / file | Why it is at risk | Expected result |
|---|---|---|
| `tests/test_lint_skill.py::test_the_repo_passes_every_check` | Runs all 22 checks against the **real repo**, so every edit to `SKILL.md` / `README.md` / the Reference Guide is under it (E18-E21). | PASS — no constant table, no template, no version string touched |
| `tests/test_lint_skill.py` (16 negative cases) | They mutate copies of the skill; unaffected unless a check's implementation changes, which T01 does not do. | PASS |
| `tests/test_units_cli.py` (9 cases) | Exercise the parser boundary — usage errors, envelope shape, UTF-8, `--skill-root`. A malformed new parser registration would surface here. | PASS |
| `tests/test_integration_01_happy_path.py` (incl. `::test_traversal_matches_the_transcript`) | Full 18-phase traversal; would break if `init`, `advance` or the gates moved. They do not (P3, P11). Also the most frequent WinError-5 victim (E31). | PASS, modulo F1 |
| `tests/test_units_state.py`, `test_units_transitions.py`, `test_units_infra.py`, `test_integration_02_to_05.py`, `test_integration_06_to_09.py` | Cover state, gates, drift, limits, lock, audit — all untouched surface. | PASS |
| `tests/test_hooks.py` (20 cases, incl. `::test_every_guard_is_registered`) | Would break only if `hooks.py`/`settings.json` changed; they do not (P12). | PASS |

---

## New tests required

One new file, `tests/test_units_workitem.py`, using the existing `project` /
`git_project` fixtures (E36). Contract §7's "New tests" list is the required
minimum; the mapping is explicit so a verifier can check coverage
mechanically.

| Contract §7 item | Required cases |
|---|---|
| normalization | `Customer Notification Service` → `customer-notification-service`; leading/trailing whitespace trimmed; `Payment_Retry` → `payment-retry`; `Foo!! Bar??` → `foo-bar`; `--foo--bar--` → `foo-bar`; mixed case lowered; a name of only punctuation refuses `workitem_name_invalid` |
| unsafe / path-traversal names | `../escape`, `..`, `a/b`, `a\b`, `.`, an absolute path, and a name > 64 chars each exit 1 `workitem_name_invalid`; **assert no directory is created anywhere under or outside `workitems/`**; one reserved-device-name case (`con`) refuses |
| duplicate names | second `create` with the same raw name exits 1 `workitem_exists`, `data` names the existing id; a case-variant name also refuses (D7); a pre-existing directory with no index row also refuses; **the index file and the existing `workitem.json` are byte-identical before and after the refused call** |
| auto-generation | `--auto-generate` id matches `^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$`; the `WI-` prefix and `T`/`Z` keep their case; the inferred segment is normalized. **Do not** write a test asserting two same-second auto-creates both succeed — second-resolution timestamps make that a deterministic duplicate refusal |
| index append | first create writes the `# Work Items` heading + header row + separator + one row; second create appends a second row and leaves the first row **byte-identical**; row order is creation order; no status column exists |
| index malformed | a hand-mangled `index.md` (wrong heading / missing separator / wrong cell count) makes both `create` and `list` exit 3 `index_malformed`; **nothing is written and the malformed file is not rewritten** |
| metadata creation | `workitem.json` parses as JSON and carries exactly the D4 keys; `title` preserves the human form; `type` defaults to `enhancement`; `synopsis` defaults to `null`; `createdAt` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`; `sdleVersion` equals the module's `CURRENT_VERSION` |
| Git identity capture | under `git_project`, `createdBy` equals the fixture's local identity and `git.initialBranch` equals the fixture branch; with git absent/unavailable, both `createdBy` fields and `initialBranch` are `null` and the command still exits 0 |

Additional cases the exit criterion and the envelope contract require:

- **Ordering / coexistence:** `workitem create` succeeds **before** `init`; `init`
  then still exits 0 and produces the same `current_phase` / `status` /
  `progress` as it does with no WorkItem; `header` and one `advance` behave
  identically. This is the mechanical form of the §7 exit criterion.
- **Non-interference:** after `workitem create`, `.workflow/` does not exist;
  after `init`, `state.json` contains **no** `workitem` key (P5 guard — this
  test is what stops T02 leaking into T01).
- **`workitem list`:** empty/absent index → exit 0, empty list; two creates →
  two entries in creation order with the projected fields (D11).
- **Envelope/exit conformance:** one refusal path asserted through
  `run_cli` (real subprocess) so the exit code and pure-JSON stdout are checked
  at the process boundary, matching `tests/test_units_cli.py`'s pattern.

**Test hygiene constraints (mandatory):**

1. The no-git case must isolate the developer's global Git config (e.g. set
   `GIT_CONFIG_GLOBAL` / `GIT_CONFIG_SYSTEM` to a nonexistent path, or run in a
   directory with git made unavailable). Without isolation the scratch project
   inherits the machine's real `user.name` / `user.email`, which both flakes the
   assertion and writes real personal identity into test output.
2. No test may assert a real person's name or email. Only the fixture identity
   `SDLE Test <test@example.invalid>` may appear.
3. Fixtures are generated at runtime, never read from the repo
   (`tests/conftest.py` rule 1) — no checked-in `workitems/` fixture.
4. No test may create `workitems/` **in the source repository** — every case
   runs under `tmp_path` via the `project` fixture.

---

## Failure modes

**F1 — `write_atomic` WinError 5 flake (inherited, not T01's to fix).**
Any full pytest run on this Windows host is expected to produce 1-2
`PermissionError: [WinError 5]` failures at `scripts/sdle.py:463`, on an
**arbitrary** node — five distinct victims have been observed across three
contexts, so expect one not previously recorded (E31).

Procedure, unchanged from T00:

1. Re-run **only** the failing node ids, up to 3 times.
2. Any pass ⇒ classify `ENVIRONMENT_FLAKE`, record both the failing and the
   passing output verbatim in the handoff, and report the raw suite exit code
   as observed — do not restate it as 0.
3. Three deterministic failures of the same node ⇒ **stop**, do not patch, write
   `T01-blocker.md`.

**Do not fix `write_atomic` in T01.** The retry/backoff decision is scheduled
for T02 planning, where runtime state actually moves. Touching it here would
mix an unrelated behavioural change into an identity-only phase (TP-002) and
would modify a `PRESERVE` row anchored by
`tests/test_units_infra.py::test_write_atomic_leaves_no_partial_file_on_failure`.

**F2 — lint-skill regression from the documentation edits.** The four concrete
traps, all confirmed by reading the checks (E18-E21):

| Trap | Guard |
|---|---|
| Pasting a state/metadata JSON example containing `"workflow_version":` into `SKILL.md` | `_check_single_state_template` fails. Put the `workitem.json` example in the README or the Reference Guide, never in a skill file. |
| Adding a bold `**v1.x**` string to README **above** the version-history row | `_check_version_consistency` takes the **first** match and would compare the wrong string. |
| A second `# SDLE … (vX.Y)` heading in README, or a `SDLE vX.Y` string earlier in the Reference Guide | Same check, same failure mode. |
| A PowerShell-only cmdlet or a literal `N/18` in new skill text | `_check_no_powershell`, `_check_no_hardcoded_progress`. |

Detection: `python scripts/sdle.py lint-skill` must exit 0 with 22 PASS after
every documentation edit, not only at the end.

**F3 — Registry corruption on append.** A partial write would leave an
unparseable registry. Mitigation: validate the existing structure **before**
constructing the new content, build the full new text in memory, and hand it to
`write_atomic` (E8) — the same temp-file+replace discipline the audit ledger
uses. On any validation failure, refuse `index_malformed` (exit 3) and write
nothing; never auto-repair.

**F4 — Half-created WorkItem (directory written, index row not, or vice versa).**
Order the writes: (a) all validation including uniqueness, (b) create the
directory + `workitem.json`, (c) append the index row. If (c) fails, the
metadata file is orphaned. Mitigation: on an exception after (b), remove the
freshly created directory before re-raising, so the operation is all-or-nothing
from the caller's point of view. Recovery for an orphan that survives anyway:
`workitem create` refuses `workitem_exists` on the stray directory (D7), which
is a visible, non-destructive stop rather than a silent overwrite.

**F5 — Scope leakage into T02+.** The most likely forms: adding a `workitem`
field to `state.json`; making `init` require or record a WorkItem; adding
`workitems/` to the write fence; adding a `Paths.workitem_*` property that
re-points runtime state; implementing `workitem resolve`. Every one of these is
excluded below and has a matching acceptance criterion or "must not change" file
entry.

**F6 — Cross-platform / Python 3.11 regression.** New code must be
stdlib-only, 3.11-syntax-safe (no `type` statements, no `itertools.batched`, no
`Path.walk`), and must not assume POSIX path semantics. Windows reserved names
and case-insensitive collisions are handled by D6/D7 precisely because CI runs
`windows-latest` **and** `ubuntu-latest` on 3.11 (E5).

**F7 — A later 3.11-only CI failure (E33 is UNKNOWN).** T01's design does not
depend on the baseline being green on 3.11: it adds an isolated, additive code
path whose tests are self-contained. If CI later reveals a pre-existing 3.11
failure, that is a baseline condition to be triaged on its own, and it neither
invalidates this plan nor is repaired inside T01.

---

## Rollback / recovery strategy

Rollback point is `a12b9e238a08fb7f1837c01e2f4c672f84d4639e` (E3), the commit
holding the verified-clean control plane and the untouched product tree.

1. **Partial or failed implementation:** `git checkout -- scripts/sdle.py
   README.md docs/SDLE-Reference-Guide.md .claude/commands/sdle-start.md
   .claude/skills/sdle/SKILL.md` and delete `tests/test_units_workitem.py`.
   Because T01 modifies no existing function body and adds no state field,
   file-level revert is complete — there is no schema or on-disk migration to
   undo.
2. **Runtime residue:** any `workitems/` directory created by manual
   exercising is untracked and disposable (`rm -rf workitems/`). It is not
   consumed by any other code path in T01, so deleting it cannot corrupt an
   existing workflow. Existing `.workflow/` state is unaffected either way.
3. **Verification FAIL:** contract §24.5 — a fresh implementer remediates the
   current phase only, increments the attempt, and must not rewrite the
   verifier's evidence. Max 3 automatic attempts, then BLOCKED.
4. **Recovery from an interrupted agent:** the phase is fully reconstructible
   from `git diff a12b9e2..`, this plan, and `progress.md`; no intermediate
   state lives outside the repository (contract §24.6).

---

## Acceptance criteria

Each is objectively checkable by a fresh verifier without trusting the handoff.

- [ ] **A1** `python scripts/sdle.py --project-root <scratch> workitem create --name "Customer Notification Service"` exits 0 and creates `workitems/customer-notification-service/workitem.json` plus `workitems/index.md` with the D5 heading, header row and exactly one data row.
- [ ] **A2** `workitem.json` parses as JSON and carries exactly the D4 key set; `id` == `name` == `customer-notification-service`; `title` == `Customer Notification Service`; `type` == `enhancement`; `createdAt` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`; `sdleVersion` equals `CURRENT_VERSION`.
- [ ] **A3** Re-running A1 exits **1** with `reason == "workitem_exists"`; `workitems/index.md` and the existing `workitem.json` are byte-identical (SHA-256 compared) before and after.
- [ ] **A4** Each of `../escape`, `..`, `a/b`, `a\b`, `.`, `   `, `!!!`, a 65-character name, and `con` exits **1** with `reason == "workitem_name_invalid"`, and no directory is created under `workitems/` or anywhere outside it.
- [ ] **A5** `workitem create --name "Payment Retry" --auto-generate` exits 0 and its id matches `^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$`, preserving the uppercase `WI-`, `T` and `Z`.
- [ ] **A6** A second create whose normalized id differs only by case from an existing id exits 1 `workitem_exists`.
- [ ] **A7** A structurally mangled `workitems/index.md` makes both `workitem create` and `workitem list` exit **3** with `reason == "index_malformed"`, and the file is unchanged afterwards (SHA-256 compared).
- [ ] **A8** `workitem list` with no index exits 0 with an empty list; after two creates it returns both entries in creation order with `id`, `created`, `type`, `title`.
- [ ] **A9** Under `git_project`, `createdBy.gitUserName`/`gitUserEmail` equal the fixture identity and `git.initialBranch` equals the fixture branch; with git isolated/unavailable all three are `null` and the command still exits 0.
- [ ] **A10** Exit-criterion check: in one scratch project, `workitem create` → `init` → `header` → one `advance` all succeed, and `init`'s `current_phase`, `status` and `progress` are identical to a control project that ran `init` with no WorkItem.
- [ ] **A11** After `init` in a project with a WorkItem, `state.json` contains **no** `workitem`-related key, and `.claude/skills/sdle/templates/state.json` is unchanged (`git diff --exit-code` on that path).
- [ ] **A12** `python scripts/sdle.py lint-skill` exits 0 with **22** checks PASS.
- [ ] **A13** Full suite: `python -m pytest -q` — every pre-existing test passes, except failures classified `ENVIRONMENT_FLAKE` strictly under the F1 procedure with both outputs recorded. **No pre-existing file under `tests/` is modified**: `git diff --name-only a12b9e2.. -- tests/` is **empty**, and the only addition under `tests/` is `tests/test_units_workitem.py` (visible in `git status --porcelain` if uncommitted, or in `git diff --name-status a12b9e2..` as `A` if committed).
- [ ] **A14** Product diff is exactly the planned set: `git diff --name-only a12b9e2.. -- . ":(exclude)docs/transition"` lists **only** files from "Files expected to change" (plus `tests/test_units_workitem.py` when committed). In particular `.claude/skills/sdle/templates/state.json`, `.claude/skills/sdle/modules/*`, `.claude/hooks/hooks.py`, `.claude/settings.json`, `.gitignore`, `scripts/sdle.sh`, `scripts/sdle.ps1` and `.github/workflows/ci.yml` are absent. `docs/transition/**` is excluded deliberately: transition evidence and `progress.md` writes are sanctioned control-plane output (contract §1.2) and are not product changes.
- [ ] **A15** `git check-ignore workitems/index.md` and `git check-ignore workitems/x/workitem.json` both exit non-zero (not ignored) — the contract §19 reversal holds without a `.gitignore` edit.
- [ ] **A16** `git diff a12b9e2.. -- scripts/sdle.py` shows **additions only** in the new section and one parser-registration block; no existing function body is modified. (`--stat` deletions attributable only to the insertion point, and a reviewer-visible read of the diff.)
- [ ] **A17** `python tools/transition/validate.py` exits 0.
- [ ] **A18** New code introduces no import beyond those already in `scripts/sdle.py` and contains no Python-3.12+ syntax.

---

## Unknowns / decision requirements

**No material unresolved decision exists. T01 is executable as planned.** The
open items below are either resolved by a contract-sanctioned default or are
inherited conditions that cannot change T01's design.

| # | Unknown | Class | Why it does not block T01 |
|---|---|---|---|
| U1 | Does the human ultimately want `workitem.yaml` rather than `workitem.json`? | UNKNOWN | Contract §7 supplies JSON as the "preferred initial shape" and permits YAML only if approved requirements explicitly demand it; no such document exists in the repository (E26). TP-008 keeps machine-owned state as JSON to avoid a parser dependency. The default is therefore contract-sanctioned, not a guess. If YAML is later required, the dependency decision is contract §11 (T05) and the conversion is mechanical — `id`, `name` and the registry are what carry identity. |
| U2 | Is the baseline green on Python 3.11 (ubuntu-latest / windows-latest)? | UNKNOWN | CI has never been observed on this branch (E33; baseline §3.4-§3.5 record `NOT_RUN`). Local evidence is Python 3.14.6 on Windows only. T01 adds an isolated additive path written to 3.11 syntax with no new imports (P10, F6, A18), so a 3.11-only failure surfacing later is a pre-existing baseline condition, not a T01 design defect (F7). |
| U3 | Root cause of the `write_atomic` WinError 5 flake. | UNKNOWN | Inherited baseline condition §6.1. Handled procedurally by F1; the fix decision is the human's, scheduled for T02 planning. |
| U4 | Should `workitem create` eventually emit an audit event? | INFERRED (answer: yes, but not here) | Impossible before `init` at this baseline (E11, E12). Belongs to T02's WorkItem-scoped audit (contract §8) and T06's governed-artifact registration (contract §12). |
| U5 | Exact `type` vocabulary enforcement (`enhancement|defect|hotfix|chore`). | OBSERVED as deferred | Contract §12 assigns classification to T06. T01 records the string and defaults it; it does not validate against a policy. |
| U6 | Whether `scripts/README.md` enumerates commands at a point that needs a new row. | UNKNOWN (trivial) | The implementer inspects the file and adds one line only if the edited section enumerates subcommands; skipping it changes no test and no lint check (E18). |

---

## Scope exclusions — must not leak into T01

Each item names the phase that owns it. Any of these appearing in the diff is a
verification failure (contract §24.4 item 8, TP-002).

| Excluded | Owner | Note |
|---|---|---|
| Any `state.json` field, `workflow_version` bump, or `VERSION_MIGRATION` row | **T02** (state moves) / **T04** (Spec Kit shape) | Would cascade across four documents plus lint (E19) |
| Moving `.workflow/` state, audit, manifest or completion summary under a WorkItem | **T02** | Baseline §7 item 3; contract §8 |
| `RepositoryContext` / `WorkItemContext` refactor of `Paths` | **T02** | Contract §8 "Core refactor" |
| Execution identity (`muh-20260816T171501Z`) | **T02** | Contract §8 "Execution identity" — distinct from the WorkItem name |
| Removing or rescoping the repository-global lock | **T02** | Baseline §7 item 4; TP-009 |
| `migrate-workflow --workitem` legacy migration | **T02** / contract §20 | |
| Adding `workitems/` to the hook write fence, or any hook/settings edit | **T02** | Baseline §5 hook row is ADAPT@T02 (E29) |
| Nested `reviews/` / `clarifications/` `.gitignore` handling | **T02+** | Only relevant once those directories move under a WorkItem (E23) |
| `workitem resolve`, `sdle validate`, CWD-based resolution, ambiguity prompts, branch/worktree rules, starting-SHA capture | **T03** | Contract §9 |
| `sdle start --workitem <name>` | **T03** | Contract §9 |
| Binding Spec Kit feature context to a WorkItem; demoting `current_feature_id` | **T04** | Baseline §7 item 5; contract §10 |
| `.sdle/` repository configuration boundary, policies, templates, `--skill-root` rebinding | **T05** | Contract §11 |
| WorkItem type/flow classification enforcement, requirements-quality gate, risk scoring | **T06** | Contract §12 |
| Governed-artifact registration/review of `workitem.json` (TP-011) | **T06** | Contract §12 |
| Changing the 18-phase sequence, `advance`, `skip`, `restart`, `doctor`, guidance map | **T07** | Baseline §7 item 1; contract §13 |
| Brownfield discovery / baseline descriptor | **T08** | Contract §14 |
| Making gates conditional; touching the 8-gate tables | **T09** | Baseline §7 item 2; contract §15 |
| Product skills/subagents (`sdle-*` specialists) | **T10** | Contract §16; the `sdle-transition-*` agents are control-plane scaffolding and do not count |
| Removing legacy scaffolding; `.workflow/` deletion | **T11** | Contract §17 |
| Hash-chaining `workitems/index.md` | later (unassigned) | Contract §7 says explicitly "do not implement hash chaining yet" |
| Fixing `write_atomic`'s WinError 5 | human decision at **T02** planning | Baseline §6.1 |
| Splitting `sdle.py` into modules | contract §23 | "Do not begin by splitting `sdle.py` only because it is large" — T01 adds one section to the existing file |

---

## Implementer quick-start checklist

1. Re-read from disk: `transition.md` §7, this plan, `progress.md`,
   `baseline.md` §4.1/§4.3/§5/§7 (contract §24.3 item 1).
2. Confirm `git status --porcelain` is clean and HEAD is `a12b9e2`; if not, stop
   and report — the plan's evidence base has moved.
3. Implement `scripts/sdle.py` first; run the new test file alone until green.
4. Run `python scripts/sdle.py lint-skill` **after each** documentation edit
   (F2), not once at the end.
5. Run the full suite; apply F1 verbatim to any WinError 5; record raw exit
   codes, never predictions (contract §24.3 item 9).
6. Persist `T01-handoff-a01.md`, set `IMPLEMENTED`, run
   `python tools/transition/validate.py`, stop.

---

## Planner attestation

- No product code was written or modified in this planning context.
- No test was created or edited.
- The only files written are `docs/transition/phases/T01-plan.md` and
  `docs/transition/progress.md`.
- No command in this context ran the test suite; all suite figures are cited
  from `baseline.md` §3 and labelled as such (E32).
- The erroneous "21 top-level subcommands" figure in `T00-plan.md` was **not**
  inherited; E16 records the verified 65/49 figures instead.
