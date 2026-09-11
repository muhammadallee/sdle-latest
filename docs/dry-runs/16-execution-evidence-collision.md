# Dry Run 16 — Two Executions in One Second Keep Two Records

| | |
|---|---|
| **Scenario ID** | DR-16 |
| **Flow** | `GREENFIELD` |
| **Purpose** | Two governance assessments inside the same clock second each keep their own evidence file and reach the ledger as two entries. A forced id collision is refused without touching existing evidence. Historical ids are still read. |
| **Defect IDs** | D04 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`. Evidence names and the refusal text are the engine's real output, with the WorkItem id adapted |
| **Starting conditions** | DR-01's repository with WorkItem `todo-api` created and nothing assessed yet. The executable form freezes the clock at `2026-09-10T12:00:00Z` |
| **Guardrails exercised** | The collision-resistant execution id (`<prefix>-<UTC second>-<8 hex>`), the exclusive-create claim of every evidence file (`reserve_evidence`), the bounded retry, `execution_id_collision` (exit 3) with nothing recorded, and ledger de-duplication by id |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> A real conversation cannot reliably land two commands in one second, which
> is exactly why the defect survived; the executable form freezes the clock
> instead of racing it. Evidence names and the refusal are the engine's real
> output. The engine behaviour is asserted by the tests under *Executable
> coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are
> recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

DR-01's repository, with the WorkItem created. In the suite,
`monkeypatch.setattr(sdle, "now_iso", …)` freezes the clock and
`monkeypatch.setattr(sdle, "execution_suffix", …)` forces a collision. There
are no sleeps and no waiting for a second boundary.

---

## Transcript

**User:** `the risk looks higher than LOW — this touches authentication. Re-assess.`

*(The first assessment and the re-assessment land in the same second.)*

**SDLE:**

```
Governance re-assessed: risk HIGH (signal authentication_or_authorization).

Evidence:
  workitems/todo-api/.sdle/evidence/governance-usr-20260910T120000Z-cc4f6421.json  (LOW)
  workitems/todo-api/.sdle/evidence/governance-usr-20260910T120000Z-d434113c.json  (HIGH)
```

*(Engine: `sdle.sh --workitem todo-api governance assess --input governance-input.json`,
twice. Before D04 both calls produced `governance-usr-20260910T120000Z.json`,
the one file held only the HIGH assessment, and the LOW one was gone.)*

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=constitution_draft status=in_progress progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Generate Constitution [IN PROGRESS]
```

*(Each record reaches the ledger at the first phase movement after it, as a
`governance_recorded` entry marked `(governance execution <id>)`. With distinct
ids there are two entries, one per assessment. Before D04 the second
assessment's marker equalled the first's, so it was treated as already logged
and never appeared.)*

---

### The forced collision

*(A broken random source, forced in the suite, yields the same suffix every
time, and a file with that name already exists:)*

```
Refused: execution_id_collision   (exit 3)

Could not allocate an unused execution id after 3 attempts
(usr-20260910T120000Z-deadbeef, usr-20260910T120000Z-deadbeef,
usr-20260910T120000Z-deadbeef): each one's evidence file already exists. Nothing was
recorded and no existing evidence was touched. This means the random source is not
random; re-run the command.
```

*(The pre-existing file is byte-identical afterwards, and no `governance.json`
was written. When only the first one or two attempts collide, the next free id
is used and the command succeeds.)*

---

### A historical id

*(A record written before D04 carries `usr-20260101T000000Z`, with no suffix.
`governance show` reads it unchanged. It reaches the ledger once, and later
movements do not duplicate it: nothing parses an id, and each id is compared
whole.)*

---

## Artifacts, state and audit

- Every evidence file — `governance-`, `review-`, `discovery-`, `migration-`
  and `implementation-` — is named by an execution id and claimed with an
  exclusive create before it is written. None is ever replaced.
- `governance.json` holds the latest record. Every assessment's evidence
  survives beside it.
- `audit.md` holds one `governance_recorded` entry per assessment consumed by
  a phase movement.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Three colliding ids in a row | Refused `execution_id_collision`, exit 3 | Existing evidence untouched, nothing recorded |
| One or two colliding ids | Retried with a fresh id | The existing file untouched, a new one written |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| The id keeps its prefix and gains a suffix | `tests/test_units_execution_identity.py::test_d04_the_identity_keeps_its_prefix_and_gains_a_suffix` |
| Two same-second assessments keep two files, contents intact | `tests/test_units_execution_identity.py::test_d04_two_assessments_in_one_second_keep_two_evidence_files` |
| …and reach the ledger separately | `tests/test_units_execution_identity.py::test_d04_two_same_second_assessments_reach_the_ledger_separately` |
| Two same-second reviews keep two files | `tests/test_units_execution_identity.py::test_d04_two_reviews_in_one_second_keep_two_evidence_files` |
| A forced collision retries and never overwrites | `tests/test_units_execution_identity.py::test_d04_a_forced_collision_retries_and_never_overwrites` |
| An unresolvable collision refuses and records nothing | `tests/test_units_execution_identity.py::test_d04_an_unresolvable_collision_refuses_and_records_nothing` |
| A historical id is read and de-duplicated | `tests/test_units_execution_identity.py::test_d04_a_historical_format_record_is_still_read_and_deduplicated` |
| Distinct ids across worktrees, without the clock | `tests/test_units_hardening.py::test_t11_n1_two_worktrees_each_complete_a_run_with_independent_ledgers` |
