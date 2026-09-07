# ADR-008 — V1 Convergence and Legacy Runtime Removal

**Status:** Accepted
**Date:** 2026-09
**Supersedes:** the transitional dual-path runtime introduced alongside ADR-001.
**Extends:** ADR-002 … ADR-007.
**Context:** transition contract §17 (primary), with §18, §19, §20, §26, §28.

---

## 1. The decision

Make the WorkItem-based model the **only** normal runtime model, remove the
transitional scaffolding that kept the pre-v1.14 runtime alive, and close or
explicitly defer every finding accumulated during the migration — without
weakening a single guardrail.

§17 says *remove* the repository-global `.workflow/`. §20 mandates a bounded
legacy migration path, and §17 itself mandates an *interrupted legacy migration*
hardening test. Those are only compatible if "remove" means one specific thing,
so this ADR fixes that meaning:

> **`.workflow/` ceases to be a *runtime*. It remains a *migration source* and a
> *project-root marker*, and nothing more.**

Everything below follows from that sentence.

---

## 2. What was removed

| # | Removed | Where |
|---|---|---|
| R1 | Resolution rung 6 — the legacy dual-read binding | `resolve_decision`, `bind_workitem` |
| R2 | The possibility that any **bound** `Paths` has `workitem is None` | consequence of R1 |
| R3 | All twelve `workitem is None` runtime carve-outs, which became unreachable | the twelve precondition and command functions that carried them |
| R4 | The repository-global runtime lock — there is no repository-global runtime left to lock | consequence of R1 |
| R5 | WorkItem-less workflow initialization | pinned refused, and the code path that let a non-`init` command tolerate no WorkItem is gone |
| R6 | `ACTIVE_CONTEXT_SETTERS` as a dead constant | it is now *enforced* rather than deleted — see §4, D9 |
| R7 | Prose asserting that a legacy runtime binds | `SKILL.md`, `sdle-start.md`, `CLAUDE.md`, `README.md`, the Reference Guide |

**The rung was deleted, not replaced by an inference.** With zero registered
WorkItems the ladder answers `none` whether or not legacy state exists. No
tie-break, no ordering, no "most recent" was added anywhere. *The ladder still
never guesses* is a stronger statement after this change than before it.

---

## 3. What was deliberately preserved, and why removing it would have been wrong

This is the half of the decision that is easy to get wrong, so it is written
out. §28 forbids removing a safety control without providing the replacement
safety property; each row below is a control whose justification **survives**
the removal.

| # | Preserved | Why |
|---|---|---|
| P1 | `PROJECT_ROOT_MARKERS` entry `(".workflow", "state.json")` | Without it a legacy-only repository cannot be *found*, so `migrate-workflow` could not be pointed at it. Removing it is exactly the bricking §17's gate forbids |
| P2 | `Paths.legacy_workflow` and the `workitem=None → .workflow/` mapping | `cmd_migrate_workflow` builds its **source view** from it. This is no longer a runtime binding; it is a reader |
| P3 | `cmd_migrate_workflow` in full, with every refusal (`target_exists`, `legacy_state_missing`, `legacy_state_invalid`, `legacy_audit_broken`) and its never-mutate property | §20; and §17's mandatory interrupted-migration test presupposes it |
| P4 | `legacy_state_present()` | Feeds `init`'s `legacy_workflow_present` refusal and `validate`'s `runtime_state_outside_workitem` finding |
| P5 | The `validate` finding `runtime_state_outside_workitem` | It is now the *only* automated way a user learns a legacy runtime is still on disk |
| P6 | `.workflow` in the write fence and in `SDLE_OWNED_PREFIXES` | A migration source that Claude could hand-edit is a source `migrate-workflow` can no longer trust. The control's justification changed; its necessity did not |
| P7 | `.workflow/` in `.gitignore` | It is archival, never versioned (§19 versions WorkItem records, not the legacy runtime) |
| P8 | `current_feature_id` inside migration steps `1.0→1.1`, `1.1→1.2`, `1.14→1.15` | It was removed *as workflow identity* earlier in the migration. The migration rows are what `lint-skill`'s "every state field has a migration row" invariant is made of |

### 3.1 The migration path, stated plainly

After this change, a repository still on the pre-v1.14 runtime recovers with
**exactly two commands**, both runtime-free and therefore never reaching the
resolution ladder:

```bash
sdle.sh workitem create --name "<name>"
sdle.sh migrate-workflow --workitem <id>
```

Every other command in such a repository refuses `workitem_required` (exit 1)
and **the refusal names those two steps in order**. That is proven end-to-end
through the real CLI, not asserted.

---

## 4. The other decisions this convergence carries

| # | Decision | Basis |
|---|---|---|
| D3 | The `workitem_required` refusal widens when legacy state is present: it names the two-step recovery in order and carries `legacy_state` in `data`. Same reason string, same exit code — no CLI-contract break | §17 exit criterion; §28 replacement safety property |
| D5/D6 | `.sdle/` is engine bookkeeping on **both** guard surfaces: added to `SDLE_OWNED_PREFIXES`, and excluded from the Gate 7 implementation manifest as its sibling already did | §18 — the manifest must describe *implementation*, not SDLE's own bookkeeping |
| D7 | The write fence normalises `.` and `..` before matching, so `workitems/<id>/specs/../.sdle/state.json` no longer escapes it | §17; invariant 6 |
| D8 | `cmd_workitem_use` turns an `OSError` into a refusal rather than a traceback, and the missing-`--workitem` usage error is renamed `workitem_flag_required` so one reason string stops meaning two things across two exit codes | §18 exit codes; invariant 7 |
| D9 | `ACTIVE_CONTEXT_SETTERS` became load-bearing: `write_active_context` rejects a `set_by` outside it. A dead constant becomes an enforced one, because the fact it encodes — exactly three writers — is worth keeping | invariant 7 |
| D10 | `feature resolve` applies the 0/1/>1 rule inside the chosen tier: **more than one candidate refuses `feature_ambiguous`** instead of picking the newest mtime | §9 "never silently pick one among multiple plausible"; §10 WorkItem isolation |
| D11 | A `governance assess` that records a final level **below** one already recorded emits a distinct `governance_downgraded` audit event carrying both levels and both signal sets, and it is surfaced in later omission evidence | §15 explainability; §12 floors |
| D12 | The prompt layer states that re-assessing risk is not a means of clearing a gate, and that a downgrade is recorded | §15 |
| D13 | `pending_branch_ack` closes the branch-guard fail-open: an acknowledgement names one checkout and is no longer standing permission for the next | §28 — a declared fail-open with no other owner |
| D14 | Version 1.16 → 1.17 across all five checked locations, with the matching `VERSION_MIGRATION` row and migration step | `lint-skill` `version_string_consistent`, `migration_covers_every_state_field` |
| D16 | New `lint-skill` check `documentation_set_is_present`, asserting §17's nine documentation targets exist and are non-empty | A checklist in a plan rots; a lint rule does not |

### 4.1 Why a risk downgrade is audited and not refused

This is the single most tempting place in the design to add a rule the contract
does not state.

A HIGH→LOW re-assessment is the practical route to making a required gate
omittable. Refusing it would look stricter. It is not: a genuine re-scope —
authentication removed from the WorkItem — is legitimate, and refusing it would
invent a floor §15 never states and block honest work. The floor was never
lowered in the first place; the *inputs* changed.

So the answer is **evidence, not refusal**. The downgrade is a distinct audited
event carrying both levels and both signal sets, and it is carried into the
evidence of every gate omitted after it, so an omission and the level it rests
on can only be read together. The asymmetry closes without a false floor.

---

## 5. Hardening — and three defects it found

§17 names sixteen mandatory hardening scenarios. All sixteen are implemented as
named tests. Writing them found two real gaps, and writing the documentation set
found a third. All three are product changes made **outside** the plan's
declared D-items, and all three are recorded here rather than folded into a
D-item that does not fit them.

| Change | Found | Why |
|---|---|---|
| `cmd_gate_omit` now records `governance_sha256` on the approvals entry and in the `gate omit` payload | Hardening | The omission fingerprinted the *policy* but not the *governance record the level came from*, so "which record said LOW" was unanswerable from the evidence alone. §15 requires an omitted gate to be explainable **later**, from what was written down |
| `baseline_commit(paths)`; `baseline_precondition` and `cmd_baseline_validate` carry `baseline_commit` in their refusal `data` | Hardening | A baseline finding said *what* was wrong without saying *which repository state* its claims were ever true for. It deliberately swallows to `None` on an unreadable file, so it can never turn a diagnosed `INVALID` into an integrity failure |
| `hooks.py` gains `fenced_target`; `write_fence` tests each fenced name through it instead of through `in_dir` | Documentation | See §5.3 |

None of the three adds a writer, a command, a state field or a gate.

### 5.1 Four scenarios implemented differently from their wording — declared

None of these was silently narrowed. Each is stated in its test's own docstring.

**"A corrupt audit refuses at the choke point."** SDLE's choke point for
*integrity* is `audit verify` (and `migrate-workflow`, which refuses
`legacy_audit_broken`). Lifecycle commands do not re-verify the whole ledger per
invocation, by design: the chain is tamper-**evident**, prevention is the write
fence plus the single-writer rule, and `audit rebaseline` exists precisely
because a detected mismatch is acknowledged rather than fatal. Turning every
`advance` into a full-ledger verification would put a new gate on the hot path
and change what a run does. **Not done; recorded.** What is asserted instead is
the property that matters: the tamper stays visible, is *located*, and cannot be
laundered by continuing to use the tool.

**"A partial temp file does not survive the next successful write."** It does
survive. Every `write_atomic` creates a uniquely named temp and renames *that*
one; nothing sweeps a stranger's leftovers, because a sweep would let one writer
delete a concurrent writer's in-flight temp — a real new failure mode for a
cosmetic benefit. **Not done; recorded.** `write_atomic` already removes its own
temp on every handled failure, so a stray temp requires a hard process kill, and
what is asserted is that such a temp is **inert**.

**"A stale baseline blocks an ITERATIVE WorkItem."** It does not, deliberately.
A merely *changed* reference is a warning, because `design_generation` runs in
ITERATIVE and rewrites the design document — treating change as invalidation
would force the third WorkItem in any repository back into full rediscovery,
which §26 forbids. Implemented instead as the two true statements the scenario
decomposes into: a **materially invalid** baseline blocks ITERATIVE outright
(`baseline_required`), and a **stale** one can never be relied on silently
(`baseline validate` refuses `baseline_not_valid`). Both refusals now name the
establishing commit.

**"Neither ledger contains the other's execution id."** Execution ids are not
globally unique, and asserting that they are would have been asserting against
the contract. §"Execution identity" *specifies* the format —
`<3-letter-git-user-prefix>-<UTC-datetime>`, example `muh-20260816T171501Z` —
at second resolution, and calls it **lightweight** identity belonging to
"execution/audit metadata". Two WorkItems started by the same user in the same
second therefore share a label by design.

This surfaced late and is worth recording as a process point as much as a
technical one: the two-worktree test carried both the id-inequality assertion
*and*, twenty lines below, a comment explaining why the WorkItem — not the
execution id — is the isolation boundary. The two disagreed, and because the
inequality held whenever the two `init` calls happened to straddle a second
boundary, the contradiction stayed invisible until a full run landed them
inside one. **A hardening test whose outcome turns on the clock is worse than
no hardening test**, because it launders a false property as a proven one.

The engine was not changed; `execution_identity` is byte-identical to its form
at the product baseline, and widening the format to force uniqueness would have
meant violating the contract to satisfy a test. **Not done; recorded.** What is
asserted instead is stronger than string inequality: each execution *record* is
a separate file that names its own WorkItem and its own worktree, so a shared
timestamp label cannot make either record ambiguous — the record itself says
which WorkItem it belongs to. The ledger half of the claim is asserted against
the WorkItem id, which *is* unique, and the id format is now pinned to the
contract's own pattern so a silent widening would fail.

---

### 5.2 The branch guard audits before it refuses — declared

Everywhere else in the engine a new precondition is a **pure reader** placed
ahead of the first audit write, so that a refusal leaves `audit.md`
byte-identical. D13's stale-acknowledgement path deliberately does not follow
that shape: it appends `branch_ack_stale`, re-arms `pending_branch_ack` against
the current checkout, saves state, **and then** refuses.

That is the branch guard's pre-existing shape, not a new one — it already
appended `branch_mismatch_guard` before refusing, and a baseline test pins it.
The branch guard is the engine's one *auditing* guard, because §9 asks a branch
mismatch to produce an explicit warning or refusal and an unrecorded
"acknowledgement rejected" would be exactly the invisibility the finding was
about. The byte-identity guarantee therefore reads, precisely: **a refusal
writes nothing except where the refusal itself is the auditable event.** The
branch guard is the only such place, and it is stated here so the narrower
guarantee is not mistaken for the general one.

---

### 5.3 The write fence was broader than the ownership it protects — fixed

Creating §17's `docs/workitems/` documentation target was **denied by the write
fence**. That denial was the defect, not an obstacle to route around.

`in_dir(path, name)` matched `/{name}/` **anywhere** in a path. But
`SDLE_OWNED_PREFIXES` — the ownership the fence exists to protect — is entirely
repository-root-relative. The hook was therefore strictly broader than the
engine: it denied `docs/workitems/`, a documentation path SDLE does not own,
never writes, and has **no choke-point refusal for**.

That asymmetry is the one failure mode a tripwire must not have. Everywhere else
in this system a hook denial is the cheap early echo of a refusal the engine
would make anyway; here the hook refused where the engine had nothing to say. A
fence that fires on paths it does not own teaches the reader that the fence is
noise, and a fence people learn to route around has stopped being a fence.

**The fix.** A new `fenced_target(path, name)` anchors the match at the start of
the repository-relative path, mirroring `SDLE_OWNED_PREFIXES` exactly, and
`write_fence` calls it. Two path shapes count as repository-relative and both
anchor: one under the project directory, and one that is **not absolute at
all** — which is relative to the project directory by definition, and is how the
fence has always read `.workflow/state.json`. Only an absolute path *outside*
the repository falls through to `in_dir`'s loose match, as defence in depth: a
write into some other tree's `workitems/` is still a write the fence wants to
see. Absoluteness is tested after backslashes have been normalised to `/`, so a
Windows drive-letter path counts as absolute; `posixpath.isabs` would call
`C:/other/...` relative and wrongly anchor another tree's path against this root.

**What did not change.** `in_dir` keeps its loose form character for character —
it is the fallback above, and `untrusted_read` still uses it for `SCANNED`,
where a deliberately broad warn-and-acknowledge scan is the intent rather than
an ownership claim. `FENCED` still holds exactly `.workflow`, `workitems`,
`requirements`, `guidance`. Nothing the engine owns became writable: every
fenced root is still denied in both the repo-relative and the absolute form.

**Scope.** This does **not** supersede T10's NB-6, and the two should not be
confused. NB-6 is about the prompt layer stating the fence's *effect* without
ADR-007 §3's runtime caveat — that a registered hook fires at all is Claude
Code's guarantee, not SDLE's. That is TR6, fixed separately. NB-6 concerns
whether the fence runs; this concerns which paths it denies when it does.
`SKILL.md`'s write-fence sentence was re-checked against the corrected
behaviour and needed no edit: it names the four fenced roots and the carve-out
and never claimed a segment-anywhere match.

**Evidence.** Pinned three ways, because a guardrail fix without a regression
test is how a guardrail defect returns. `tests/test_hooks.py` drives the
**registered command** as a subprocess over every fenced name: a repo-root path
under it is denied in both forms, `docs/<name>/` is permitted in both forms,
absolute paths outside the repository are still denied, and `FENCED` is asserted
to be a strict subset of `SDLE_OWNED_PREFIXES`. `test_n28` pins the structure —
`fenced_target` anchors and falls back, `write_fence` no longer calls `in_dir`,
and `in_dir` is proved to differ from its baseline by nothing but a docstring.
`test_n27` declares the single substituted line as a before/after pair, so any
*other* lost line in an edited definition still fails.

---

## 6. Cross-platform: what is actually known

§17 mandates a Windows/Linux hardening test. The honest position, which must not
be softened into a claim:

> The engine is written to be cross-platform and is **mechanically checked** for
> platform-only constructs. During this migration it was executed only on
> Windows, on Python 3.14.

Checked and observed: POSIX separators in every emitted repository-relative
path; every `os.sep` use is a normalisation *into* `/`; `lint-skill`'s
`no_powershell_only_cmdlets` over every prompt file; both launchers present and
agreeing on the interpreter-resolution contract; line-ending-normalised
comparison wherever a test compares file text.

Not observed, and therefore not claimed: any run on Linux, any run on
Python 3.11, and any CI outcome on `ubuntu-latest` or `windows-latest` — CI has
never executed at any point in this migration.

---

## 7. Findings ledger

Every finding inherited from the migration, with exactly one disposition. A
finding that is not here is a defect in this ADR.

**Totals: 20 FIXED · 4 DEFERRED · 2 NOT-A-DEFECT · 26 rows.**

| ID | Finding | Disposition | Rationale |
|---|---|---|---|
| TR1 | The hooks AST pin missed imports and the module docstring | **FIXED** | A proven coverage narrowing on a guardrail file. The pin now covers the docstring and every import, and each byte-pinned property of an edited definition is asserted explicitly |
| TR2 | `sdle-approve.md` named capability-module paths in prose | **FIXED** | Invariant 7. The engine owns "which capability files a phase needs"; the command now points at `sdle.sh resume` |
| TR3 | ADR-001 said "four hooks"; there are five | **FIXED** | A present-tense architectural claim that had become false. It now records the decision and points at the guard registry rather than carrying a count |
| TR4 | The read-only tool grant was restated in eight unchecked places | **FIXED, partially** | The four agent *frontmatters* are machine-checked already. The four agent **bodies**, `CLAUDE.md` and ADR-007 now point at `PRODUCT_AGENT_TOOLS` as the authority instead of restating the literal. No ninth lint rule for prose: the enforcement path is already checked, and a prose rule would be cost without a guarantee |
| TR5 | Documents paraphrase `CAPABILITY_MAP` rows | **NOT-A-DEFECT** | Each site already names `CAPABILITY_MAP` as authoritative and the pattern predates the finding. Recorded here so a later editor does not read the prose as normative |
| TR6 | Prompt files stated the fence's effect without ADR-007 §3's runtime caveat | **FIXED, minimally** | One clause in `SKILL.md` and in the two review capability modules: those guarantees hold *when the runtime honours a declared `tools:` list and a registered hook*, which is Claude Code's guarantee and not SDLE's. The agent bodies address an operator and keep their plain statement |
| TR7 | A HIGH→LOW re-assessment was the practical route to omitting a required gate | **FIXED as evidence, not as refusal** | See §4.1. Refusing would be a false floor blocking legitimate re-scope |
| TR8 | §15's HIGH list names a documentation review that no gate implements | **DEFERRED beyond V1** | See §8. This is the single named V1 gap |
| TR9 | `.sdle/` was in neither `SDLE_OWNED_PREFIXES` nor the manifest exclusion | **FIXED** (D5, D6) | Replacement safety property: `.sdle/` is written only by `config` and `baseline`, both of which already produce their own audited records, so excluding it loses no evidence — while *not* excluding it breaks cross-WorkItem isolation, which §8/§9 do guarantee |
| TR10 | Spec Kit tier-2 newest-mtime cross-adoption between concurrent WorkItems | **FIXED** (D10) | A silent wrong pick out of a shared staging area. Strictly fail-closed, with an existing explicit escape hatch |
| TR11 | `cmd_manifest_build` lacked its sibling's relocation exclude | **FIXED** (D6) | Same edit as TR9's second half |
| TR12 | The write-fence carve-out matched a non-normalised path | **FIXED** (D7) | A fence bypass. Bounded — the engine's refusal is the guarantee, not the hook — but cheap to close |
| TR13 | `SKILL.md`'s write-fence sentence was inaccurate after the specs carve-out | **FIXED** | It now names all four fenced roots, the carve-out, and the tripwire-versus-guarantee distinction |
| TR14 | Stale `.workflow/` paths in the prompt modules and the dry-run transcripts | **FIXED** | The prompt modules now take the runtime path from the engine rather than naming a repository-global literal; the transcripts are converged under a declared substitution set |
| TR15 | `branch_guard` fail-open between a two-step command's confirmations | **FIXED** (D13) | A declared fail-open in a guard with no other owner |
| TR16 | `ACTIVE_CONTEXT_SETTERS` was dead in production | **FIXED** (D9) | |
| TR17 | `cmd_workitem_use` was not error-hardened | **FIXED** (D8) | |
| TR18 | `workitem_required` was reused for a usage error | **FIXED** (D8) | One reason string across two exit codes is an invariant-7 violation on the CLI contract itself |
| TR19 | `init` with both a corrupt index and legacy state reports `index_malformed`, not `legacy_workflow_present` | **NOT-A-DEFECT** | Both are refusals and both are correct. A registry that will not parse is the more fundamental problem and reporting it first is the right order — you cannot migrate into a registry you cannot read. The ordering is now pinned by test, so it stops being untested |
| TR20 | On a mismatched branch the ledger recorded `branch_mismatch_accepted` even when the command then refused | **DEFERRED, with the residual pinned by a test** | It did not fall out of D13, and this was verified rather than assumed. `branch_guard` runs ahead of the command body and cannot know whether that body will succeed, so the acceptance entry still precedes a later unrelated refusal; D13 changes *which* acknowledgement is honoured, not *when* it is written. What D13 does remove is the harm: the entry is no longer standing permission, because the next invocation on a different checkout is refused. The entry is an accurate record of what the user acknowledged, not of what then happened, and the residual is now a passing test (`test_tr20_the_acknowledgement_is_still_ledgered_before_a_later_refusal`) rather than an argument |
| TR21 | `SKILL.md`'s branch-mismatch paragraph over-generalised "re-run the same command — which proceeds" | **FIXED** | It now says the acknowledgement is consumed, names one checkout, and does not promise the re-run proceeds |
| TR22 | The `legacy_workflow_present` message never named archiving `.workflow/` | **FIXED** (D3) | Post-convergence this message is the user's only signpost |
| TR23 | The post-commit `workitem.json` write sits outside the migration commit window | **DEFERRED** | The commit marker is the target `state.json`, written last. A failure after it leaves a correct, resolvable runtime with slightly stale metadata, which the next command re-derives. Changing the commit window would risk the atomicity property the interrupted-migration test exists to protect. Now pinned by test, so the residual is bounded and visible |
| TR24 | The migration crash test never exercised the manifest and completion-summary copies | **FIXED** | All nine write points are now parameterised, as a **named sequence**, so a new write point fails loudly rather than going unexercised |
| TR25 | `design/`, `reviews/` and `clarifications/` are repository-level, and `design/app/app-design.md` is shared across WorkItems | **DEFERRED** | An explicit earlier decision, restated as the V1 position: these are repository-level **by design**. §10 warns against copying shared artifacts into every WorkItem for directory aesthetics. The follow-on question is which of them are genuinely WorkItem-scoped, not how to move all three |
| TR26 | `docs/transition/RESUME.md` was stale | **FIXED** | Updated to describe the completed state. It remains explicitly non-authoritative |

---

## 8. The single named V1 gap

**§15's HIGH-risk list names a documentation review that no gate implements.**
Seven of its eight items map onto existing gates; this one does not.

It is deferred beyond V1 deliberately. Adding a ninth gate is a **lifecycle**
change, not a §17 removal-and-hardening change. It would touch all four phase
tables, the phase-execution module, every progress denominator, the state
template's `approvals`, the integration suite's expected traversal and gate set,
and all nine dry-run transcripts — that is, it would change what a run *looks
like*, at the last milestone of the last phase of the migration, for something
§17 does not ask for and the definition of done does not list. §15 itself calls
the list a *default intent*.

**Proposed shape for a follow-on**, so the deferral is actionable rather than
merely recorded:

1. Add `documentation_review` as a **gateless** phase in the flows that already
   require `gate_security`, producing a governed artifact reviewed through the
   existing `artifact review` door.
2. Only if that proves insufficient, promote it to `gate_documentation` with a
   `required_gates_by_risk` entry at HIGH and above — at which point every
   derived view moves together, which is exactly why it should be its own
   change with its own transcript update.

---

## 9. Consequences

**Good.** There is one runtime model. The twelve `workitem is None` carve-outs
that every new precondition had to remember are gone, so a new precondition can
no longer forget one. The refusal a stranded repository gets now names its own
recovery. Three silent-pick paths (the legacy rung, newest-mtime feature
selection, a branch acknowledgement outliving its checkout) became refusals or
audited events.

**Costs, accepted.** A pre-v1.14 repository now requires two explicit commands
where it previously limped along read-only; that is the point, and the refusal
names them. The engine still carries `.workflow/` awareness — deliberately, as
§3 sets out — so "removed" is a narrower statement than it first appears, and
this ADR exists so nobody later reads it more broadly and deletes P1.

**What did not change.** Gate discipline. Fail-safe freezing. The single-writer
rule, including that a refusal leaves `audit.md` byte-identical. That Claude
cannot lower a deterministic floor. Atomic writes, the audit hash chain, exit
codes 0/1/2/3, JSON on stdout. The frozen GREENFIELD traversal. All eight
non-negotiable invariants. **The core refuses; it does not warn.**
