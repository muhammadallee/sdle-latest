# Plan review, round 2 — requirements package, SA handoff, traceability, bounded implementation loop

You are an independent, adversarial reviewer. You have not seen the conversation that produced this plan; do not assume any decision in it is correct. You are in a **read-only sandbox**: do not edit, create or delete files. Reading files and read-only commands are fine.

The repository is SDLE (Spec Driven Lifecycle Engine): a deterministic gated SDLC orchestrator for Claude Code. `scripts/sdle.py` is the single-file, standard-library-only engine; it refuses rather than warns. Read `CLAUDE.md` first: its eight invariants must survive any change. Report the checked-out commit as `reviewed_commit`.

## What you are reviewing
A **plan**, not code. No production code exists for it. Everything is under `.sdle/implementation-state/requirements-package-loop/`:
- `BRIEF.md` — the owner's brief: mission, grounding table G01–G17, settled owner decisions D01–D11, release scopes, acceptance scenarios AS-01..AS-30.
- `PLAN.md` — **the artifact under review** (cross-cutting design §1, R1 §2, R2 §3, R3 §4, AS-30 §5, risks §8).
- `LEDGER.md` — decisions L1–L4 (note **L2 overrides D09**: the loop limit lives in the pinned governance policy, not `.sdle/config.json`; do not re-litigate it, but check the plan carries it through consistently), reproductions of G04/G06/G08, baseline results.

Read the **current source**; do not trust PLAN.md's description of it. Line numbers in PLAN.md are approximate. Verify cited symbols exist and behave as stated: `review_precondition`, `review_status`, `cmd_gate_approve`, `_approve_drift`, `gate_precondition_hook`, `cmd_gate_omit`, `revalidate_recorded_omissions`, `cmd_skip`, `cmd_drift_rebaseline`, `compute_drift`, `_cmd_init_locked`, `_cmd_requirements_bind_locked`, `validated_binding`, `implementation_evidence_precondition`, `_implementation_evidence_shape`, `cmd_manifest_build`, `GOVERNANCE_POLICY_BUILTIN`, `_refuse_weakening`, `exclusive_file_lock`, `workitem_runtime_member_names`, `SDLE_OWNED_PREFIXES`, `RUNTIME_FREE_COMMANDS`, `load_constants`, `run_sync_checks`, and the tests the plan says it will change (`tests/test_units_invariants.py`, `tests/test_units_repo_config.py`, `tests/test_units_flow_model.py`, `tests/test_hooks.py`).

## Round 2 context
Round 1 (nine findings, PR-R1-001..009) was applied; `PLAN.md` §10 maps each to its fix and `LEDGER.md` records the dispositions. Do **not** re-report a round-1 item unless the fix is wrong, incomplete, or creates a new defect: say which. Hunt especially for defects **introduced by the fixes**: the digest projection (§3.6), the package pin / `package adopt` / `package reseal` / immutable revisions (§2.1–2.3), the removal of the post-analyze rebaseline and the `rebaseline_not_permitted` rule (§3.5), the reconcile snapshot rules (§4.4), the loop guarantee wording (§4.1), and the pinned-policy default rule (§1.5). Also re-check items you could not reach in round 1 (see its stated coverage gaps) where static reading suffices. Use finding ids `PR-R2-001`...

## Attack list
1. **Legacy compatibility.** Is the claim true that every new refusal is inert unless the WorkItem binds a file under `requirements/packages/`? Find any new check applied to *every* WorkItem (the review-type table, `treeDigest` evidence) and judge whether it breaks existing tests, dry runs or users. Enumerate affected call sites by searching the tests.
2. **Every approval or bypass path** (§1.6): `gate approve`, drift re-approval, `gate omit`, `skip`, `restart`, `retry`, `drift rebaseline`. Is a path missing? Can `gate_tasks` omission or a flow without `gate_tasks`/`gate_design` let an uncovered criterion reach `gate_implement`?
3. **Package digest and the approval ledger** (§2.3). Is "approved iff current digest equals the latest record" sound? Can the ledger be bypassed (fence, `SDLE_OWNED_PREFIXES`, `hooks.py`)? Is the hash chain meaningful or decorative?
4. **`tasks reconcile` and the drift model** (§4.4, §3.5). The plan claims reconcile must rebaseline `artifact_shas` directly because re-approval is refused `review_stale` after a tick. Check against `_approve_drift` and `review_precondition`. Does `--expect-sha` actually close the G04 gap, given drift detection is prompt-driven?
5. **The engine never invokes Spec Kit or an agent** (pinned by tests). Does the loop design (recorder and referee) honour that, and is "step order enforced by the engine" real or only a record the orchestrator can ignore? What can the engine actually guarantee?
6. **Tree-bound evidence** (§3.6). Is the temp-index `git write-tree` approach correct (untracked included, ignored excluded; `.sdle` runtime files, the manifest and evidence files changing during the run)? Could `treeDigest` change merely because SDLE writes its own files, giving false `invalid_changed_during_run`?
7. **Pinned policy keys** (§1.5). Does adding keys to `GOVERNANCE_POLICY_BUILTIN` and `_refuse_weakening` interact badly with the pinned policy hash (ADR-011) for in-flight WorkItems, with policy validation (closed key set), or with tests comparing the built-in?
8. **Command and test surface.** Are the pins and counts the plan says it will move complete? Recount `WRITE_PRIMITIVE_COUNTS`, `COMMANDS` and others from the source. Is something missing (`RUNTIME_FREE_COMMANDS`, hook fence tests, `lint-skill` documentation checks, CLAUDE.md table rules)?
9. **Package contract** (§2.1): internal consistency, ID grammar declared once, `supersedes`, the generated `traceability.md` agreement check, and anything invented beyond BRIEF D01–D11.
10. **Brief conformance.** Anything in BRIEF §§3–5 and the AS list that the plan silently drops, weakens or contradicts. Check each of AS-01..AS-30 has a concrete test and a release.
11. **Staging directory** (§2.5, risk 3): read `hooks.py` FENCED/SCANNED and `.gitignore` and judge the proposed location.
12. **Anything in PLAN.md that is false against the current source.**

## Output
Return **only** a JSON object matching the supplied schema.
- `reviewed_commit`: the checked-out commit.
- `coverage.areas_reviewed` / `coverage.areas_not_reviewed`: be specific. Naming what you did **not** reach matters as much as findings. An empty `findings` array with non-empty `areas_not_reviewed` is rejected as incomplete.
- Each finding: unique `id` like `PR-R2-001`; `severity` (`critical|high|medium|low`); `category` = `defect/<area>` for something wrong that must be corrected, or `improvement/<area>` for something better but not wrong, never mixed; `path` and `line` (`0` if none); `claim`; `evidence` (quote the file and line); `evidence_type` `executed` or `static`; a concrete `suggested_fix`; `ac_ids` listing plan sections or AS ids touched; `confidence`.
- Do not pad. A finding without repository evidence is not a finding. Do not report wording. Do not rewrite the plan.
