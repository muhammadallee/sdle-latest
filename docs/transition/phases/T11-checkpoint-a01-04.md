# T11 checkpoint a01-04 — M4 complete

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M4 (governance downgrade evidence)
**Status at this boundary:** M4 GREEN. Safe resume point.
**Written before:** M5 begins.

---

## 1. What M4 changed

### D11 — a re-assessment that lowers a recorded level is evidence, not a refusal

T09's verifier recorded the asymmetry (NB-2 / TR7): *within* one assessment a
lower proposal is inert and recorded (`loweringAttempted`), but *across* two
assessments there was no record at all. Re-running `governance assess` with a
smaller signal set simply replaced the record, so a gate that had been required
could become omittable with nothing anywhere stating that a level had fallen.
That was the practical route to omitting a required gate.

| Change | Anchor |
|---|---|
| `governance_downgrade(previous, risk)` — a pure comparison returning both levels, both signal sets, and the added/removed deltas, or `None` | `governance_downgrade`, next to `evaluate_risk` |
| `cmd_governance_assess` reads the record it is about to replace **before** overwriting it, and stores `record["downgrade"]` (always present, `null` when nothing was lowered) | `cmd_governance_assess`, comment `# T11 D11: read the record this one replaces` |
| `governance show` promotes `downgrade` out of `record` | `cmd_governance_show` |
| `GOVERNANCE_DOWNGRADE_EVENT = "governance_downgraded"` plus its own de-duplication marker, `(governance downgrade <executionId>)` | `governance_downgrade_marker` |
| `_record_governance_downgrade_audit` appends the second ledger entry, de-duplicated independently of `governance_recorded` so neither can suppress the other | called from both arms of `record_governance_audit` |
| `cmd_gate_omit` carries the block into the approvals entry, the `gate omit` payload and the `gate_omitted` audit message | `cmd_gate_omit`, `"governance_downgrade": downgrade` |

**Why it audits and does not refuse.** A genuine re-scope — authentication
dropped out of the WorkItem — legitimately lowers risk. Refusing would invent a
floor no contract section states, would leave a correct user no honest way
forward, and would push them toward hand-editing the record, which the write
fence denies and the audit chain would catch: a dead end, not a guardrail. §15
requires an omitted gate to be *explainable and auditable*, and evidence is the
instrument that answers that. **B3 is intact: no policy floor value moved.**

**Where the entry lands.** `governance assess` runs before `init`, so it has no
`audit_sha` to rebaseline and appends nothing — the same constraint
`governance_recorded` already lives with. The downgrade therefore lands at the
first phase movement that consumes the record, through the same call site, with
the same `executionId` de-duplication.

### D12 — the prompt layer says so

One paragraph in `modules/gate-protocol.md` Step 6b (the capability file
`CAPABILITY_MAP` names for every `gate_*` phase) and one in `SKILL.md` beside
"Nothing else about a gate is conditional": *re-assessment is not a
gate-clearing device*; re-assess only when scope actually changed; a downgrade
is recorded and carried into the omission; it is never refused and never
invisible.

---

## 2. Tests — nine new, three re-valued

**New (`test_units_governance.py`):**

| Test | What it pins |
|---|---|
| `test_n12_a_lower_proposal_inside_one_assessment_still_has_no_effect` | The floor property, across **every** level in the lattice, not one example |
| `test_n12_a_downgrading_reassessment_is_recorded_on_the_record` | Both levels, both execution ids, both signal sets, both deltas |
| `test_n12_raising_or_holding_a_level_is_not_a_downgrade` | The detector cannot be satisfied by *any* re-assessment — same-level and upward both leave `null` |
| `test_n12_a_downgrade_is_audited_and_never_refused` | Exit 0, no reason, and `hard_floors`/`risk_thresholds` unmoved |
| `test_n12_governance_show_surfaces_the_downgrade` | A reader need not know the record schema |
| `test_n12_the_downgrade_detector_is_a_pure_reader` | B2 — `governance_downgrade` reaches no writer and names no runtime file |
| `test_n12_an_omission_that_rests_on_a_downgrade_carries_it_as_evidence` | **The substantive closure.** See below |
| `test_n12_the_downgrade_event_is_logged_once_however_often_it_is_consumed` | De-duplication by marker |

`test_n12_an_omission_that_rests_on_a_downgrade_carries_it_as_evidence` drives
**the exact route T09 NB-2 described**, not a paraphrase of it. `gate_tasks` is
in `required_gates_by_risk["HIGH"]` and absent from `["LOW"]`, so it is the
first gate whose requirement actually moves. The test drives GREENFIELD to
`gate_tasks` under a HIGH assessment, asserts `gate omit` refuses
`gate_required` at `final_risk == "HIGH"`, re-assesses with the signals
removed, and then asserts the omission is permitted **and** that the downgrade
appears in all three places: the `gate omit` payload, `approvals.gate_tasks`,
and the ledger — as a distinct `governance_downgraded` event *and* named inside
the `gate_omitted` message. It finishes with `audit verify` exit 0, so the
second event is a chained entry rather than a hand-written line.

**Note what is deliberately *not* asserted:** that the omission is now refused.
T11 does not take the re-scope away; it makes it visible.

### Re-valuations, all X-GEN, all exact-equality shapes kept

| # | Assertion | Old value | New value | Forced by |
|---|---|---|---|---|
| 1 | `test_only_evaluate_risk_produces_a_final_level`'s closed **reader** set | `{cmd_governance_assess, cmd_governance_gates, gate_requirements_for_state, record_governance_audit}` | the same **+ `governance_downgrade`** | D11 |
| 2 | `test_n24_a18_the_engine_gained_no_writer_and_no_state_field`'s write-primitive counts | `append_audit` 47 | 48 | D11 |

For (1), the **producer** set is unchanged at `{evaluate_risk}` — which is what
carries the guarantee — and the test now additionally asserts
`"governance_downgrade" not in producers`. `governance_downgrade` compares two
already-decided levels and returns a dict keyed `from`/`to`, never
`finalLevel`, so it structurally cannot decide one.

For (2), the count comparison was **not** re-baselined. A declared signed delta
map, `T11_WRITE_DELTA = {"append_audit": 1}`, is added and every primitive is
compared to `before + delta`. That is stronger than re-baselining: the
permitted movement is named and quantified, and any other movement in any
primitive still fails. Observed deltas across the whole of T11 so far, computed
against `adbdc5e`: `write_atomic` 30→30, `save_state` 46→46, **`append_audit`
47→48**, `record_audit` 0→0, `.write_text(` 0→0, `.write_bytes(` 0→0,
`os.replace` 3→3, `.mkdir(` 6→6. Exactly one call site, exactly where D11 put
it. The `add_parser` command set is unchanged, so no new command was added.

**A new ledger call site is not a new writer.** `append_audit` remains the only
thing that writes the ledger and `write_atomic` the only thing that writes a
file. Invariant 6 is about *who may write*, and it is untouched.

**No test was deleted in M4.**

---

## 3. Evidence at the M4 boundary

| Check | Command | Result |
|---|---|---|
| Governance + gate policy | `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_gate_policy.py -q --tb=short"` | **559 passed in 277.98s**, 0 failed |
| Capabilities | `rtk proxy "python -m pytest tests/test_units_capabilities.py -q --tb=short"` | **159 passed in 116.65s**, 0 failed |
| Review / flow / state / transitions | `rtk proxy "python -m pytest tests/test_units_artifact_review.py tests/test_units_flow_model.py tests/test_units_state.py tests/test_units_transitions.py -q"` | **208 passed in 294.29s**, 0 failed |
| Integration 01 + review + capabilities | earlier combined run | 206 passed, then the one X-GEN failure above, now green |
| `lint-skill` | `python scripts/sdle.py lint-skill` | **42 checks, `failed: []`** |
| Audit chain under the new event | asserted inside `test_n12_an_omission_that_rests_on_a_downgrade_carries_it_as_evidence` | `audit verify` exit 0 |

Two failures were seen during M4 and **both were real, attributable and fixed
by re-valuing the assertion, never by relaxing its shape**:
`test_only_evaluate_risk_produces_a_final_level` and
`test_n24_a18_the_engine_gained_no_writer_and_no_state_field`. Neither was
re-run to make it pass. `ENVIRONMENT_FLAKE` remains VOID.

A third failure was seen and was a **test defect of my own**, fixed in the
test: the de-duplication count was written against the event *name*, which the
`gate_omitted` message deliberately mentions so a reader of the omission is
pointed at it. It now counts the de-duplication **marker**, which appears only
in the entry it de-duplicates.

---

## 4. Resuming from here

**Remaining:** M5 (D13, D14, X6, X11, N22, N23) · M6 (N1–N16) · M7
(documentation, ADR-008 with all 26 TR rows, D16/X7/N24, TR2/3/4/6/13/14/21/26)
· M8 (D15, X10 — severable).

**M5 is the first milestone that edits `templates/state.json`**, so it is the
one that touches the two `FROZEN` pins (E18), and X6 re-baselines exactly that
one entry. Carry forward: `scripts/sdle.py::CURRENT_VERSION` is a **sixth**
version location that `_check_version_consistency` does not read — F6's
instruction is to add it there rather than edit it by hand. The README version
row must be inserted **above** `**v1.16**`, because the lint check reads the
first `**vX.Y**` match in the file.

**Findings closed so far:** TR1, TR9, TR10, TR11, TR12, TR16, TR17, TR18 (M2,
M3) and **TR7** (M4). TR22 was closed by M1's D3.

Recoverability unchanged: M4 is additive.
