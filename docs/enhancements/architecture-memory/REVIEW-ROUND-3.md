# Independent Review — Round 3

Produced by a separate agent instance with a fresh context, tool grant
`Read` / `Grep` / `Glob` only (the `sdle-code-review` product agent), reviewing
the committed patch `git diff d1b203a..HEAD` (two commits: the Stage 0
restoration and the CI defect fixes), with read-only reference copies of the
engine before and after each line of work. It was pointed at Part 2 of the
prompt and at the frozen contracts **by path** rather than having them pasted
into the prompt, which is a deviation from Appendix B recorded in
`PROGRESS.md`.

**The reviewer's findings below are a verbatim transcription of its report**,
reformatted only from its table layout to a list; no finding was trimmed or
reworded. The implementer's dispositions are in a separate section at the end.

---

**Summary:** 8 findings, 1 blocking (R3-001). The reviewer read files only and ran no tests.

- **R3-001 · HIGH (blocking) · `docs/dry-runs/05-untrusted-content-scan.md:140-141`** — the patch adds `<!-- SDLE_STATE phase=constitution_draft status=pending progress=2/18 -->` and `Phase 2/18 — Generate Constitution`; the engine and SKILL.md `PROGRESS_MAP` say `2/20`, and the same file already says `8/20` at line 175. `test_dry_run_contracts.py::test_every_progress_fraction_and_gate_number_is_the_engines[05-untrusted-content-scan.md]` recomputes both lines and should fail. Fix: change both to `2/20`.
- **R3-002 · MEDIUM · `tests/conftest.py` (MAINTENANCE_RECORDS, ~652-671) and `tests/test_units_capabilities.py` (~1248-1266)** — the restatement-search exemption grows from one directory to three whole directories; `requirements-refinement/` and `open-items-01-02/` hold authored prose (`PLAN.md`, `review-rounds/round1.reply.md`) as well as raw event streams. Invariant 7 is policed by this search. Fix: exempt only `.../runs/` under the two new directories, or name files; update the `len(...) == 3` assertion and docstring.
- **R3-003 · MEDIUM · `scripts/sdle.py:4540-4575` (`_lexically_safe_path`) and `:12251-12260` (`cmd_scan` comment)** — the alias loop rejects any component where `part != part.rstrip(". ")`, which rejects `.` and `..` as well as a trailing dot. So `./requirements/x.md` is refused `path_invalid` with the "different files on different platforms" message, the `traversal` branch is unreachable for a leading `..`, and the `cmd_scan` comment saying a `./` prefix keys the same acknowledgement is false. Identical to the Stage 0 reference. Fix: skip `.`/`..` in the alias check (or run `traversal` first) and correct the comment.
- **R3-004 · MEDIUM · `docs/troubleshooting/README.md`** — no entry for `governance_content_unacknowledged`, `scan_acknowledgements_invalid` (exit 3), `path_invalid`, or `content_flagged`. `scan_acknowledgements_invalid` has no documented way out: `entry_ok` re-runs `_lexically_safe_path` (which calls `resolve()`) on every stored path on every read, so a stored path later replaced by an outside-pointing symlink, or a hand-edited store, makes every `advance`, `gate approve`, `gate omit`, `skip` and `governance assess` refuse exit 3; no engine command prunes the store and the write-fence blocks the parent session from repairing it.
- **R3-005 · LOW · `scripts/sdle.py:3512-3518` (`workitem_runtime_member_names`)** — omits `scan_acknowledgements_file`; the docstring promises a new runtime member inherits the leak check for free. Same omission in the Stage 0 reference. Fix: add it and mention the store in CLAUDE.md's runtime-members sentence.
- **R3-006 · LOW · `tests/test_units_documented_commands.py:1308-1312`** — `re.search(...).start()` raises `AttributeError` if a phase block is renamed instead of a clear assertion. Fix: assert the match is not `None`.
- **R3-007 · LOW · `tests/test_units_cli.py:97-99` and `tests/test_units_infra.py:118-119`** — the literal `22` for the registry phase count is re-hardcoded in two places. Fix: derive it from `sdle.PHASE_SEQUENCE` / `consts.phase_count`.
- **R3-008 · LOW · `DELIVERY.md` and `PROGRESS.md`** — neither records that Stage 0 was reverted by the copy and restored by a three-way merge; `docs/README.md` now indexes them as the delivery record. Fix: add a short note to `PROGRESS.md`.

**Merge fidelity (focus 1, reviewer's words).** The top-level `def`/`class` inventory of `scripts/sdle.py` at HEAD is the union of the two references, nothing missing, nothing duplicated. Stage 0 pieces match the `65b75df` reference at 143 occurrences each; architecture pieces match the `d1b203a` reference at 307 each. The precondition call sequences in `apply_advance`, `cmd_gate_approve`, `cmd_gate_omit` and `cmd_skip` are identical to the architecture-only reference, with the acknowledgement validation added inside `governance_precondition`. All 23 Stage 0 startup tests are still present.

**Atomicity and ordering (focus 2).** In `cmd_gate_approve` every refusal runs before the first write; the early `governance_precondition(paths)` validates the acknowledgement store before `architecture_apply` mutates the catalog and before `gate_approved` is appended. No path appends to `audit.md` or mutates the catalog ahead of a refusal that should precede it.

**Requirements isolation and dirty-tree (focus 6).** `preflight` and `governance assess` read only bound sources. `SDLE_OWNED_PREFIXES` is still narrowed to `.sdle/baseline.json`, `.sdle/implementation-state/`, `.sdle/architecture/`. The write-fence covers the whole `workitems/<id>/.sdle/` runtime, including the acknowledgement store.

**Other pin changes (focus 4).** `write_atomic` 32 matches the reviewer's count of HEAD (raw substring counts include comments, a pre-existing weakness). `EXPECTED_SKILL_FILES` equals the 14 files on disk. `"architecture"` in `RUNTIME_FREE_COMMANDS` is justified and the engine set matches. `phase_count` 22 is consistent with the registry.

**Areas inspected:** every hunk of `round3.patch`; `cmd_gate_approve`, `apply_advance`, `cmd_advance`, `cmd_gate_omit`, `cmd_skip`, `governance_precondition`, `architecture_precondition`, `cmd_governance_assess`, the acknowledgement store, `cmd_scan`, `cmd_accept_content`, `_lexically_safe_path`, `RUNTIME_FREE_COMMANDS`, `SDLE_OWNED_PREFIXES`, `workitem_runtime_member_names`, `append_audit` and the `_already_recorded` regexes; both reference engines by function inventory and keyword counts; the startup-contract test inventory; `hooks.py` `untrusted_read`; `SKILL.md` and `sdle-start.md` wording against the engine; dry-run 05 against the `test_dry_run_contracts` regexes.

**Areas not reached:** a line-level diff of `cmd_init`, `cmd_restart`, `cmd_reset` and the architecture functions against the references (keyword counts and call sequences only); the bodies of `architecture_apply`, `architecture_realize` and `apply_architecture_delta` against the frozen contracts; the `phase-execution.md` blocks and the six guideline files; `lint-skill` itself; the `save_state` (50) and `append_audit` (56) pin counts, not recounted; D1–D15 conformance of the catalog and revision logic; `claude-review-rejections.md`; whether `test_05_accept_content_clears_and_logs` asserts an exact audit message; all test execution.

---

## Implementer disposition

| ID | Disposition | What was done / why |
|---|---|---|
| R3-001 | **ACCEPT** | Real regression, introduced by the Stage 0 merge: the restored dry-run 05 still carried the pre-architecture `/18`. Reproduced before fixing (`test_dry_run_contracts`: 1 failed, 185 passed), fixed to `2/20`. It would have failed the CI run in flight. |
| R3-002 | **REJECT** | The three-directory exemption is Stage 0's and Stage 1's own owner-approved design (`conftest.py` docstring: an enumerated, named set, widened by review each time; `e5af3a4`, `84925f2`). The merge carried it across unchanged; this enhancement added nothing to it. Narrowing it is a separate decision for the owner. See RR-001. |
| R3-003 | **REJECT** (out of scope, surfaced) | A real defect, but byte-identical in the Stage 0 reference `65b75df` (the reviewer says so), owner-verified and closed there under the defect-scoping rule. Fixing security-verified code inside this change would make the architecture diff unreviewable as such. See RR-002. |
| R3-004 | **REJECT** (out of scope, surfaced) | The refusals are Stage 0's, and Stage 0's own docs did not document them either. The recovery deadlock the reviewer describes is the part worth the owner's attention. See RR-003. |
| R3-005 | **REJECT** (out of scope, surfaced) | Identical omission in the Stage 0 reference. See RR-004. |
| R3-006 | **ACCEPT** | The spec-phase test now asserts both blocks were found before slicing. |
| R3-007 | **REJECT** | The literal is the repository's convention: the pin it replaced was `== 20` with a comment, and `CLAUDE.md` says tests pin properties "on purpose and in the same commit". The change was value-only. See RR-005. |
| R3-008 | **ACCEPT** | `PROGRESS.md` now records the regression, the restoration and the decisions. |
