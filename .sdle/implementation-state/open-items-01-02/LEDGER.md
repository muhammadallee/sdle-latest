# OPEN-01 / OPEN-02 — ledger

## Origin

Both items were raised by Codex during the documentation alignment pass and left open **on purpose**:
each needs a change the alignment brief did not authorise. The owner has now asked for both.

| Item | Raised | Why it was deferred |
|---|---|---|
| OPEN-01 | Round 2, R2-D01 | An engine change. "This is a documentation alignment task, not authorization to redesign SDLE or change runtime behavior." |
| OPEN-02 | Round 1 R1-D03, restated in round 2's closing paragraph | A test-design change, declined twice as scope creep |

## OPEN-01 — what was actually wrong

Not the mechanism; the **message**.

* `cmd_scan` records `pending_confirm_action` only when `state.json` exists. That `if` is deliberate —
  there is nowhere else to record it, and the stale-confirmation guard assumes state.
* `cmd_accept_content` calls `read_state` unconditionally, so without state it exits **3
  `state_unreadable`**.
* The refusal message nevertheless read as an invitation to acknowledge. That is how the shipped
  dry run came to publish a sequence that cannot run.

### Why it matters more than it first looked

I initially called this low-frequency. That was wrong, and testing the patterns showed why:

| Sentence | Fires |
|---|---|
| The operator can **set status** to Shipped once the carrier confirms pickup. | `set_status` |
| A supervisor may **mark approved** any request under $500. | `mark_approved` |
| The system must not allow users to **skip approval** for high-value orders. | `skip_gate` |
| Each order can **advance phase** only when the prior phase is complete. | `advance_phase` |
| The dashboard shows total revenue by region. | clean |

Four of five ordinary business sentences trip it. On a brownfield business application a false
positive at bootstrap should be expected, not treated as rare.

### The fix

`scan` reports **`data.acknowledgeable`** — on the clean path too, so a caller branches without a
KeyError — and the message names the two routes that work: edit the flagged line and re-scan, **or**
continue to `init` and scan again, when acknowledgement becomes available.

Nothing about *when* an acknowledgement may be recorded changed. The second route already worked; it
was simply undocumented and unhinted. That is why this is a message fix and not a new pending-store:
inventing a second confirmation location to solve a wording problem would be the larger error.

Evidence: `runs/bootstrap-scan-routes.txt` drives both routes end to end.

## OPEN-02 — the blind spot, and what closes it

`tests/conftest.py`'s `project` fixture binds during setup. Every other test therefore begins from an
already-bound WorkItem, so a documented sequence that omits `requirements bind` still passes, and a
documented position nothing can reach is never contradicted.

Three classes of defect survived a full review round because of it: tutorials and dry runs showing
`create -> preflight -> assess`; seven documents showing `Phase 1/N - Requirements Check`, which no
state holds; every tutorial showing bare filenames where the engine emits repository-relative paths.

`tests/test_units_startup_contract.py` starts from `bare_project` and types the sequence out — 14 tests.

**Two of its assertions were written the wrong way round, and the engine disproved them before they
could become documentation.** `governance assess` refuses `requirements_unbound`, so `init` is not even
reachable that way; and an empty proposal refuses `governance_input_malformed` first, because input
validation precedes the binding check. Both are now pinned as observed rather than as assumed. That is
the module doing its job on its first run.

## Verification

| Check | Result |
|---|---|
| `lint-skill` | PASS |
| `tests/test_units_startup_contract.py` | PASS — 14 |
| `tests/test_integration_02_to_05.py` (the scan's existing tests) | PASS |
| `tests/test_dry_run_contracts.py` | PASS — 118 |
| Both bootstrap routes through the real CLI | PASS — `runs/bootstrap-scan-routes.txt` |
| Full suite | on CI at push |
