# T11 checkpoint a01-06 — M6 complete

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M6 (the 16 mandatory hardening tests)
**Status at this boundary:** M6 GREEN. Safe resume point.
**Written before:** M7 begins.

---

## 1. What M6 added

A new file, `tests/test_units_hardening.py` — **38 tests**, covering §17's
sixteen mandatory bullets. **N12** is not in it: it landed in M4 beside the
governance regime it guards (`test_n12_*` in `test_units_governance.py`), which
is where it belongs.

| § | Existing coverage | What M6 adds |
|---|---|---|
| **N1** | `test_two_worktrees_drive_two_workitems_with_no_flag` (resolution only) | Both worktrees driven **to `complete`**, with the other live and unfinished throughout; each ledger verifies independently; neither ledger names the other WorkItem or its runtime path |
| **N2** | `state.json` + `audit.md` comparison | WI-B's **whole `.sdle/` tree** compared byte for byte across a full WI-A run, so `execution.json`, `governance.json`, `reviews.json` and `evidence/` are covered — and any future runtime file automatically |
| **N3** | none | Merge-conflict markers in `workitems/index.md` → `index_malformed`, exit 3, file byte-identical; `workitem create` refuses rather than repairs; a badly-resolved merge → `duplicate_workitem_id` ERROR; **plus TR19's ordering pinned** |
| **N4** | reason only | Ledger byte-identical, no `.tmp` sibling, and `doctor`/`resume` still answer usefully (name the file and the way out) |
| **N5** | `audit verify` reports a break | The break is **located** (`broken_at_entry == 2`), detection writes nothing at all, the tamper cannot be laundered by continuing to work, and `audit rebaseline` is the only way past and is itself audited |
| **N6** | `write_atomic` primitive tests | A stray partial temp is inert through `state get`, `resume` and `audit verify`; and a crash between temp and rename **during a real lifecycle command** leaves state, ledger and directory untouched |
| **N7** | 4 write points | **All 9**, asserted as a named sequence so a new write point fails loudly; the manifest and completion-summary copies are now exercised (closes **T02 NB-5**); post-commit interruptions pinned separately (**TR23**); and §3.3 proven end-to-end through `run_cli` (**A4**) |
| **N8** | rung tests | Every non-RUNTIME_FREE command names both migration steps **in order**; and >1 candidate refuses with **no pick**, asserted on disk |
| **N9** | reason on `feature bind` | Whole runtime byte-identical; `feature resolve` fails closed on its own ground; `feature capabilities` still answers |
| **N10** | `state.json` unchanged | The **whole** `.sdle/` unchanged, and no feature directory created |
| **N11** | T08 baseline tests | See §3 — declared divergence |
| **N13** | T09 omission tests | The omission's evidence is **sufficient on its own** (policy source + policy sha + governance record sha + level), and at the terminal gate the recorded fingerprint corroborates the refusal |
| **N14** | `test_n9_a_fresh_process_reconstructs...` | Mid-flow reconstruction of the **whole** operating context through a real `run_cli` subprocess, with `audit.md` and `state.json` byte-identical across it |
| **N15** | none | Same, with `workitems/.active-context.json` deleted and a **new** session token; the reconstruction must be identical, and the WorkItem-local lock must not falsely block |
| **N16** | scattered | POSIX separators in every repository-relative emitted path (on Windows, where it would actually break); every `os.sep` use is a normalisation into `/`; `write_atomic` is the only text writer and pins LF; both launchers agree on the interpreter contract; `no_powershell_only_cmdlets` passes |

## 2. Two product changes, both TP-003 category 3 (a hardening test found a gap)

M6's scope explicitly permits this: *"If a hardening test finds a defect, fix
the implementation inside M6 and record it."*

| Change | Anchor | Why |
|---|---|---|
| `cmd_gate_omit` records `governance_sha256` on the approvals entry and in the `gate omit` payload | `cmd_gate_omit`, comment `# T11 N13` | The omission fingerprinted the *policy* but not the *governance record* the level came from, so "which record said LOW" was unanswerable from the evidence alone. §15 requires an omitted gate to be explainable **later**, from what was written down |
| `baseline_commit(paths)`; `baseline_precondition` and `cmd_baseline_validate` now carry `baseline_commit` in their refusal `data` | `baseline_commit` | A baseline finding said *what* was wrong without saying *which repository state* the baseline's claims were ever true for. Deliberately swallows to `None` on an unreadable file so it can never turn a diagnosed `INVALID` into an exit 3 |

Neither adds a writer, a command, a state field or a gate.

## 3. Three declared divergences — recorded, not dropped

Each is a §17 bullet that could not be implemented exactly as worded. **None is
silently narrowed**; each is stated in the test's own docstring as well as here,
and each must appear in ADR-008.

### N5 — "refuses at the choke point"

SDLE's audit choke point for *integrity* is `audit verify` (and
`migrate-workflow`, which refuses `legacy_audit_broken`). Lifecycle commands do
not re-verify the whole ledger per invocation. That is the design: the chain is
tamper-**evident**, prevention is the write fence plus the single-writer rule,
and `audit rebaseline` exists precisely because a detected mismatch is
acknowledged rather than fatal. Turning every `advance` into a full-ledger
verification would be a new gate on the hot path, would change what a GREENFIELD
run does, and would arrive at the last milestone of the last phase. **Not done;
recorded.** The property that matters — the tamper stays visible, and cannot be
laundered by continuing to use the tool — is asserted.

### N6 — "does not survive the next successful write"

It does survive. Each `write_atomic` creates a uniquely named temp and renames
*that* one; nothing sweeps a stranger's leftovers. Adding a sweep would let one
writer delete a concurrent writer's in-flight temp — a new failure mode for a
housekeeping benefit. **Not done; recorded.** Note that `write_atomic` already
removes its own temp on every *handled* failure (three `test_units_infra.py`
tests pin it), so a stray temp requires a hard process kill.

### N11 — "a stale baseline blocks an ITERATIVE WorkItem"

It does not, deliberately. T08's `baseline_findings` makes a *changed* reference
a **warning**, because `design_generation` runs in ITERATIVE and rewrites the
design document — treating change as invalidation would force the third WorkItem
in any repository back into full rediscovery, which §26 item 22 forbids.
`test_units_baseline.py` pins that decision, and plan §7.2 lists that file as one
the implementer may not change. Implemented instead as the two true statements
the bullet decomposes into: a **materially invalid** baseline blocks ITERATIVE
outright (`baseline_required`), and a **stale** one can never be relied on
silently (`baseline validate` refuses `baseline_not_valid`). Both refusals now
name the establishing commit.

## 4. X-GEN re-valuations in M6 — all M5 fallout, all exact-equality

Three assertions were failing because M5 changed the product and those files
were not re-run inside M5. All three are mechanically forced closed sets.

| File | Assertion | Old | New | Forced by |
|---|---|---|---|---|
| `test_units_capabilities.py` | `test_n9_...`'s `set(data["pending"])` | 5 keys | the same **+ `pending_branch_ack`** | D13 |
| `test_units_capabilities.py` | `T11_WRITE_DELTA` | `{"append_audit": 1}` | `{"append_audit": 2, "save_state": 1}` | D11 (+1 `append_audit`) and D13 (+1 `append_audit` for `branch_ack_stale`, +1 `save_state` for the re-arm exit) |
| `test_units_gate_policy.py` | `test_n28_...`'s `len(version_chain)` | `16` | `17` | D14 (X11) |

The write-primitive comparison was **not** re-baselined: it is still
`before + declared signed delta`, so any other movement in any primitive still
fails. `write_atomic` is unchanged at 30 — no new writer.

**No test was deleted in M6.**

## 5. Evidence at the M6 boundary — all re-derived in this context

| Check | Command | Result |
|---|---|---|
| The new file | `rtk proxy "python -m pytest tests/test_units_hardening.py -q --tb=short"` | **38 passed in 131.96s**, exit 0 |
| M6-affected units (first pass) | `capabilities baseline gate_policy governance flow_model` | 827 passed / **52 failed** — all three X-GEN items above |
| After the re-valuations | `rtk proxy "python -m pytest tests/test_units_capabilities.py tests/test_units_gate_policy.py -q --tb=short"` | **521 passed / 1 failed**, then the corrected `append_audit` delta → `test_n24_a18` **passed** |
| `lint-skill` | `python scripts/sdle.py lint-skill` | **42 checks, `failed: []`** |

## 6. Resuming from here

**Remaining:** M7 (documentation, ADR-008 with all 26 TR rows, D16/X7/N24,
TR2/3/4/6/13/14/21/26, RESUME.md) · M8 (D15, X10 — severable).

**Findings closed so far:** TR1, TR7, TR9, TR10, TR11, TR12, TR16, TR17, TR18,
TR22 (M1–M4) · TR15 FIXED and TR20 DEFERRED-with-evidence (M5) · **TR19**
(NOT-A-DEFECT, now pinned) **TR23** (DEFERRED, now pinned) and **TR24** (FIXED)
in M6.

**Carry forward for M7:**

- `lint-skill` is at **42**; A10 wants **43** once D16 lands. `test_n26`'s exact
  set must gain `T11_CHECKS = ("documentation_set_is_present",)` at the same
  time (X7), and N24 must prove the new check fails loudly **on a copied tree**.
- Six documentation directories do not exist yet (plan E22).
- ADR-008 must carry **all 26 TR rows**, plus the three N-bullet divergences in
  §3 above and the two M6 product changes in §2.
- The full suite has **not** been run end-to-end yet in this attempt. It must be
  the last thing before the handoff.
