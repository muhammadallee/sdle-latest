# T06 Implementation Handoff — Attempt a02

**Phase:** T06 — Deterministic governance inputs and a governed artifact review the gate enforces (contract §12, TP-011)
**Attempt:** 02 — **remediation** under §24.5, after `T06-verification-a01.md` returned `FAIL` on one blocking finding
**Implementer context:** fresh/isolated
**Status recommendation:** IMPLEMENTED (attempt 2), NOT YET VERIFIED

Precondition HEAD: **`246f30a`** on `transition/workitem-v1` ("T06 verified FAIL; one blocking defect, phase stays IMPLEMENTED").
T06's implementation commit: **`ccb9835`**. Prior-phase rollback point: **`475795a`**. Product baseline: `f8fdaa0`.
Nothing is committed this attempt; a02's work is in the working tree.

> **This is a remediation handoff, not a re-implementation.** It fixes exactly one finding. `T06-verification-a01.md` is the verifier's artifact and was **not edited**; `T06-handoff-a01.md` and checkpoints `a01-01`…`a01-06` are retained unchanged. Every figure below was produced by a command run in **this** context; nothing is copied from a01 or from the verification.

---

## The finding, and what was wrong

`T06-verification-a01.md` finding **B1**: `cmd_gate_approve` appends its
`gate_approved` audit entry — carrying `**Gate Decision:** APPROVED` — and only
*then* calls `apply_advance`. T06 put `governance_precondition` (E1) inside
`apply_advance`, and E1 is the **first refusal ever reachable** on that path.
So an ordinary refusal wrote an approval that never happened into the
append-only ledger, `state.json` was never saved, and `audit verify` returned
exit 3 `audit_chain_broken` until the next successful state write re-linked the
chain and made the false entry permanent and undetectable.

I reconstructed the ordering from source before changing anything. In
`cmd_gate_approve` at `ccb9835` the statement order is:

```
gate_precondition_hook(...)        # E2's neighbour, refuses here
review_precondition(...)           # E2, refuses here — before any append
state["approvals"][gate] = {...}
append_audit(..., decision="APPROVED", ...)   <-- irreversible
apply_advance(...)                 # E1 refuses here — too late
save_state(...)
```

That is why the E2 refusals leave `audit.md` byte-identical and the E1 refusals
did not: **placement relative to the append**, exactly as the verifier isolated.

---

## The fix

**One added call in `scripts/sdle.py`, in `cmd_gate_approve`, immediately after
`review_precondition`:**

```python
    gate_precondition_hook(paths, state, consts, args.gate, resolved)
    review_precondition(paths, state, args.gate, resolved)
    # ... comment block ...
    governance_precondition(paths)
```

Three properties make this the smallest deterministic change:

1. **It records nothing.** `governance_precondition(paths, state=None)` already
   guards its only side effect with `if state is not None:
   record_governance_audit(...)`. Omitting `state` therefore makes the early
   call purely a reader — `read_governance_record` plus `governance_freshness`.
   No new parameter, no new function, no forked logic.
2. **The rule stays written once.** `apply_advance` remains the enforcement
   site and is **byte-identical to `ccb9835`**; all three movers still funnel
   through it. Invariant 7 is preserved: E1 exists in exactly one function.
3. **Refusal precedence is unchanged.** The call sits *after*
   `review_precondition`, so E2 still fires before E1 from this command, and
   `forward_jump` / `gate_not_approved` were already unreachable here (the
   verifier proved this; the target is always `NEXT_PHASE[gate_phase]` and the
   approval is written `"approved"` before `apply_advance` runs). Nothing that
   refused before now refuses differently.

A side benefit, declared rather than hidden: the one *accepted* exit-3 path,
`governance_record_invalid` from `read_governance_record`, now also fires
before the append instead of after it, so a corrupt record no longer orphans an
entry either.

Two documentation-level corrections came with it, because the fix made two
existing sentences untrue:

- `governance_precondition`'s docstring gained a paragraph explaining the second,
  earlier, state-less call and why the ordering is load-bearing.
- `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md`: the
  sentence "There is exactly one enforcement site, so there is exactly one place
  to audit" became "The rule is written in exactly one function, so there is
  exactly one place to audit", plus the ordering rationale. Nothing else in
  ADR-003 changed; it contains no policy default value, so the N23 invariant-7
  content search is unaffected (verified: the added text contains none of the
  risk-signal ids or underscored check ids that form the needle set).

### What I deliberately did **not** change

**`cmd_skip` has the same append-then-move ordering and was left byte-identical
to `475795a`.** The a01 verifier reproduced its orphaned entry *at `475795a`*,
before T06 existed, by forcing `status = failed` at a gate phase so
`gate_not_approved` fires — so it is **pre-existing**, not a T06 regression, and
fixing it here would be scope creep into a phase that does not own it. It is
carried below as **NB-6** so it is not lost a second time; checkpoint `a01-04`
spotted it and it never reached the a01 handoff.

`_approve_drift` does not call `apply_advance` (asserted by
`test_the_clause_has_exactly_one_enforcement_site`'s `movers` clause), so E1 is
not reachable there and no ordering problem exists on the drift path.

`write_atomic` was not touched. `read_repo_config` was not touched (T05 NB-4
stays T09's). No constant table, no version string, no migration row, no gate,
no phase.

---

## TP-003 — every deliberate test change in a02, with its category

**There is no fourth category.** Two files changed, both of them files T06 itself
added at `ccb9835`. **No test was weakened, relaxed, skipped, xfailed, renamed
or deleted.**

| # | File | Change | TP-003 |
|---|---|---|---|
| 1 | `tests/test_units_governance.py` | `frozen()` now returns `audit.md` **bytes** as a sixth tuple member, alongside `state["audit_sha"]` | **3 — defect discovered.** The defect was *in the assertion*. `audit_sha` lives in `state.json`, which the refusal path never saves, so the helper provably could not observe a ledger append; `test_gate_approve_inherits_the_same_clause` asserted `frozen(project) == before` and passed while `audit.md` grew by a false approval. Strengthening a helper so it catches more is the opposite of weakening — and it is what makes 786 green tests trustworthy rather than merely green. |
| 2 | `tests/test_units_artifact_review.py` | the twin `frozen()` gains the same sixth member | **3 — same defect, same helper shape.** E2 already refuses ahead of every audit write, so this clause holds today; carrying it in the tuple is what keeps it held. |
| 3 | `tests/test_units_governance.py` | `test_the_clause_has_exactly_one_enforcement_site`: `assert callers == ["apply_advance"]` → `assert callers == ["apply_advance", "cmd_gate_approve"]`, docstring rewritten to say why | **2 — genuinely superseded.** `cmd_gate_approve` now legitimately calls the guard. The assertion stays an **exact, closed set**, so a third caller still fails loudly; it was widened by exactly one named member and not converted to a subset or membership check. |
| 4 | `tests/test_units_governance.py` | **new** `test_a_refused_gate_approval_leaves_the_ledger_byte_identical`, parametrised over `stale` / `missing` | additive — the B1 regression |
| 5 | `tests/test_units_governance.py` | **new** `test_the_gate_approval_precheck_runs_before_the_first_audit_write` | additive — the structural pin on the ordering |

**Diff shape, re-derived here.**
`git diff --name-status -M 475795a -- tests/` → **10 M, 2 A, 0 D, 0 R**.
`git diff --numstat ccb9835 -- tests/` → `test_units_artifact_review.py 12/2`,
`test_units_governance.py 108/6`. Every one of those 8 removed lines is inside a
file T06 added; **zero lines were removed from any pre-existing test file in
a02**, and across the whole phase the only pre-existing test file with removed
lines is still `tests/test_units_repo_config.py` (4, from a01's authorised
row-4 rewrite).

`git diff -U0 ccb9835 -- tests/` shows the removed lines are: two one-line
docstrings and two `return` continuation lines (the `frozen()` rewrites), three
docstring lines and one `assert callers == ...` line (change #3). That is the
complete set — **change #3 is the only assertion touched anywhere in a02.**

**The skip / xfail greps, quoted rather than asserted empty:**

- `grep -rn "xfail" tests/ --include=*.py` → **no match, exit 1**.
- `grep -rnE "skipif|pytest.mark.skip|pytest.skip" tests/ --include=*.py` →
  exactly one line, pre-existing:
  `tests/test_units_infra.py:49:@pytest.mark.skipif(SH is None, reason="POSIX sh not available")`.

---

## The regression proved failing first

Contract discipline says a regression test must fail against the defect. It was
run in that order.

**Against `ccb9835`'s product code** (strengthened `frozen()` and the new test
present, `scripts/sdle.py` untouched):

```
rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider
           -k 'byte_identical or inherits_the_same_clause or exactly_one_enforcement' -rsxX"
RAW_EXIT=1
3 failed, 2 passed, 172 deselected in 11.40s
```

with the failure message
`AssertionError: a refused gate approval appended to the append-only ledger`
and a byte diff `b"## AUDIT [2...75eef3d780a\n" == b"## AUDIT [2...36bbe7cc86c\n"`.
Both new parametrisations failed, **and so did the pre-existing
`test_gate_approve_inherits_the_same_clause`** once its helper could see the
ledger — which is the a01 blind spot demonstrated rather than argued.

**After the fix,** the same selection and the two whole modules are green (below).

**Independently of pytest's in-process runner**, a real-subprocess probe
(temporary file, run then deleted; `git status` re-checked clean of it) drove
`gate approve` through `python scripts/sdle.py` after an ordinary
`requirements/` edit at `gate_constitution`:

```
SUBPROCESS_EXIT 1 REASON governance_stale
ENTRIES 5 -> 5
APPROVED_LINES 0
AUDIT_VERIFY_EXIT 0
```

a01's reproduction of the same scenario was `5 -> 6`, one
`**Gate Decision:** APPROVED`, `audit verify` exit 3.

---

## Acceptance evidence re-run in this context

| Check | Result | Evidence |
|---|---|---|
| Targeted — the two T06 modules | PASS | `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_artifact_review.py -q -p no:cacheprovider -rsxX"` → **`218 passed in 224.78s (0:03:44)`**, **RAW_EXIT=0**. 218 = a01's 175 + 40 + 3 new cases. |
| **A1 full suite** | PASS | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` on the final tree → **`789 passed in 842.77s (0:14:02)`**, **RAW_EXIT=0**. Output is 13 lines; `short test summary` count **0**, so zero skips, xfails and errors. |
| A2 suite arithmetic | PASS | `--collect-only -q` → **789 tests collected**, so collected == passed. 789 = a01's verified 786 + 3 (`…leaves_the_ledger_byte_identical[stale]`, `[missing]`, `…precheck_runs_before_the_first_audit_write`). No test was removed, so the 786 → 789 delta is entirely additive. |
| A3 `lint-skill` | PASS | `rtk proxy "python scripts/sdle.py lint-skill"` → **RAW_EXIT=0**, `"passed": true` **22**, `"passed": false` **0**, `"failed": []`, `[PASS] tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows.`, `[PASS] version_string_consistent: all four locations report v1.15`. Re-run after the ADR-003 edit. |
| A4 `validate.py` | PASS | `python tools/transition/validate.py` → **RAW_EXIT=0**, ``TRANSITION_VALID: complete=6/12 next=T06``. |
| A5 must-not-change set | PASS | `git diff --exit-code 475795a -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .claude/skills/sdle/modules/security-review.md .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ ADR-001 ADR-002 .sdle/ tools/` → **exit 0**. |
| A6 no constant table changed | PASS | a02 touched no prompt file at all: `git diff --stat 246f30a` names only `scripts/sdle.py`, the two test files, `docs/architecture/ADR-003-…md`, `docs/transition/…` and the out-of-scope `.claude/settings.local.json`. `lint-skill` re-confirms 19 phases / 8 gates / 15 migration rows / v1.15 in four locations. |
| A9 guardrails byte-identical | PASS | AST extract-and-compare of **36** named top-level definitions (the a01 guardrail set plus `apply_advance`, `_approve_drift`, `cmd_init`, `cmd_skip`, `append_audit`, `_entry_digest`, `RUNTIME_FREE_COMMANDS`, `compute_drift`, `cmd_drift_rebaseline`, the config four): vs `ccb9835` **35 identical / 1 differs (`cmd_gate_approve`) / 0 missing**; vs `475795a` **31 identical / 5 differ / 0 missing**, the five being exactly T06's declared deltas `append_audit`, `apply_advance`, `_approve_drift`, `cmd_gate_approve`, `RUNTIME_FREE_COMMANDS`. **`cmd_skip` and `read_repo_config` are byte-identical to `475795a`** — the pre-existing defect was not adopted and T05 NB-4 stays T09's. |
| **A11 audit integrity — the failing half** | PASS | The negative half a01 failed now holds: a refused `gate approve` leaves `audit.md` byte-identical and `audit verify` at **exit 0**, driven both in-process (parametrised over `governance_stale` and `governance_missing`) and through a real subprocess. `verify.data["matches"] is True` is asserted, not just the exit code. |
| **A13 fail safe — the failing half** | PASS | `frozen()` now carries the ledger bytes in both new test files, so *every* refusal assertion in T06's own suite — a01's fourteen reasons plus the two new cases — is now also a byte-identity assertion on `audit.md`. All 218 pass. |
| **A14 exit-code contract — the failing half** | PASS | The undeclared exit-3 path is closed: `audit verify` after a T06 refusal at `gate approve` is exit 0. The one **declared** exit-3 divergence, `governance_record_invalid` in `read_governance_record`, is unchanged and still accepted by the a01 verifier on the merits. |
| A23 TP-003 | PASS | 10 M / 2 A / **0 D / 0 R**; the table above; the two greps quoted verbatim. |
| A24 Python 3.11 / CI | NOT_RUN | Host is Python **3.13.0** (`python -V`); the branch is local-only. **Python 3.11: NOT_RUN. CI: NOT_RUN / UNKNOWN.** No outcome predicted. |

Everything else a01 verified `PASS` — the floor asymmetry against 8 weakening
and 9 malformed shapes, staleness in both the normal and drift paths, row 4's
proven-load-bearing rewrite, A9's 24/24, 175 identical `SKILL.md` table rows,
A17's four-repository differential, A18, A20, A22 — was **not disturbed**, and
the byte-identity sets were re-checked after the change (A5 exit 0; the AST
compare above; `cmd_skip` identical to `475795a`).

---

## Files changed in a02

| File | Nature |
|---|---|
| `scripts/sdle.py` | +23 / −4. One added `governance_precondition(paths)` call in `cmd_gate_approve` with its comment block; one added docstring paragraph on `governance_precondition`. No other function changed. |
| `tests/test_units_governance.py` | +108 / −6. Strengthened `frozen()`; two new tests (one parametrised ×2); one closed-set assertion widened by one named member. |
| `tests/test_units_artifact_review.py` | +12 / −2. Strengthened `frozen()`. |
| `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md` | One sentence corrected plus the ordering rationale. |
| `docs/transition/progress.md` | T06 → attempt **2**, handoff → a02, a02 evidence prepended to Tests and Notes with the a01 record retained. |
| `docs/transition/phases/T06-handoff-a02.md`, `T06-checkpoint-a02-01.md` | new (this attempt). |

**Not changed, and verified so:** `T06-verification-a01.md`, `T06-handoff-a01.md`,
`T06-plan.md`, `T06-checkpoint-a01-01..06.md`, `docs/transition/transition.md`,
every control-plane agent/skill/validator file, and everything on the A5 list.
`.claude/settings.local.json` is the user's Claude Code permission allowlist,
was already ` M` when this context started, and is **out of scope** — not
staged, not reverted, not edited.

---

## Residuals and findings for later phases

**NB-6 (new, needs an owning phase — this is the one a01 lost).** `cmd_skip`
appends its audit entry before calling `apply_advance`, exactly as
`cmd_gate_approve` did. The a01 verifier reproduced the resulting orphaned entry
and `audit_chain_broken` **at `475795a`**, via `gate_not_approved`, so it is
**pre-existing and out of T06's scope** and was deliberately left untouched
(`cmd_skip` is byte-identical to `475795a`). T06 does widen its *reachability*:
before T06 it took a contrived `status = failed` at a gate phase, and now a
`requirements/` edit under a bound WorkItem also reaches it via
`governance_stale`. **T11 hardening is the natural home.** The general fix is
the same shape applied here — refuse before the first irreversible write — and
the same test shape pins it: compare `audit.md` bytes, never `state["audit_sha"]`
alone.

**NB-1…NB-5 from `T06-verification-a01.md` are carried unchanged and unadopted:**
NB-1 `reviews_malformed` is an undeclared refusal reason with no frozen-state
assertion; NB-2 `governance_freshness` covers only the requirements digest, not
the recorded `policy.sha256` (owner T09); NB-3 the governance record has no
integrity binding beyond JSON shape (owner: whichever phase first *acts* on the
recorded risk); NB-4 `docs/dry-runs/` and a stale `docs/transition/RESUME.md`
remain documentation debt owned by T11; NB-5 was an accuracy note about a01's
handoff and is answered by this document.

**Process lesson worth carrying.** The a01 blind spot was not in the product and
not in the plan — it was in a *test helper*. A frozen-state tuple built from
`state.json` cannot see an append-only file that a refusal wrote and a refusal
never saved state for. Any future "a refusal freezes everything" assertion
should carry the ledger bytes for the same reason.

---

## Notes for the verifier

- Reproduce B1's negative half directly: stand at `gate_constitution` with a
  current `PASS` review, edit any file under `requirements/`, run
  `gate approve --gate gate_constitution`. Expect exit 1 `governance_stale`,
  `audit.md` byte-identical, and `audit verify` exit 0. Then re-run the same
  probe against `ccb9835` to see `5 -> 6` and exit 3.
- The single-caller structural test is now a **two**-member closed set. Check
  that it is still an exact-equality assertion (it is:
  `assert callers == ["apply_advance", "cmd_gate_approve"]`) and not a
  containment check.
- `test_the_gate_approval_precheck_runs_before_the_first_audit_write` has an
  explicit anti-vacuity guard (`assert appends, …`) so it cannot pass by
  matching nothing, and it asserts the call is made with exactly one positional
  argument and no keywords — i.e. without `state`, which is what makes it
  side-effect free.
- `cmd_skip` was intentionally left alone. If you believe it should have been
  fixed here, that is a scope disagreement to raise as a finding against the
  phase boundary, not a defect in this fix — the evidence that it is
  pre-existing is in `T06-verification-a01.md` finding B1's last paragraph and
  is reproducible at `475795a`.

## Checkpoints

`docs/transition/phases/T06-checkpoint-a02-01.md` (this attempt);
`T06-checkpoint-a01-01..06.md` retained from a01.
