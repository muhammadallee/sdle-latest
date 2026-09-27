# Round 1 reply — dispositions

Reviewed by Codex (`codex-cli 0.151.0`, model `gpt-5.6-sol`, `model_reasoning_effort = "high"` — the
event stream itself reports no model, same limitation the repository-cleanup ledger recorded; this is
read from `~/.codex/config.toml`, the CLI's configured default, not asserted from the run). Read-only,
`--sandbox read-only --ephemeral`, detached worktree at `0057425`. Run record:
`runs/20260927T182716-p08-codex-open-items-round1.json`; output:
`runs/20260927T182716-p08-codex-open-items-round1.a1.review.json`. The harness's own `area`/`task_ids`
label this `P08`, a leftover from the `codexrun.py` script's origin in the repository-cleanup work; it
is not a repository-cleanup task and the label is not corrected in the run record (append-only, per this
directory's own convention), only here.

Nine findings, all checked against the source before dispositioning — none taken on Codex's word alone.

## Verdict

**Codex is right. OPEN-01 and OPEN-02 are not genuinely closed.** The `data.acknowledgeable` message
fix is accurate about what the engine does today, but what the engine does today has a real gap: nothing
durably records a flagged, unacknowledged document before `init`, and nothing stops governance or `init`
from consuming it in the interim. The prior round's own prompt flagged this as "the main design
question in this diff" and asked Codex to argue the other side. It did.

## Dispositions

### R1-D01 (high) — the post-init route is not safe or resumable — **ACCEPT**

Confirmed directly: `cmd_scan` (`scripts/sdle.py:9580`) only records `pending_confirm_action` when
`acknowledgeable` (`paths.state_file.is_file()`) is true — i.e. never before `init`. Nothing in
`cmd_governance_assess` or `cmd_init` checks scan status; a `grep` for `content_flagged`,
`scan_required`, `scanned` or `unscanned` across `scripts/sdle.py` finds no consumer of the scan result
anywhere except the `scan` command's own message. So the message's "continue to `init` and scan again"
is a **prompt-layer convention** (SKILL.md's "scan each bound document... before doing anything with
it"), not an engine-enforced gate: nothing stops `governance assess` and `init` from running against a
document nobody ever rescanned, and an interruption between `init` and the promised rescan leaves no
trace that anything is still pending. The message is accurate about the mechanism; the mechanism itself
is the gap.

**Not fixed in this reply.** The remediation is a bootstrap-contract design decision (durable pre-init
acknowledgement vs. a scan precondition at `governance assess` vs. at `init`), and the owner is asked
directly — see "Design decision needed" below. Registered as `DEF-RR-001`.

### R1-D02 (high) — the untrusted-read hook gives the same impossible instruction — **ACCEPT**

Confirmed: `.claude/hooks/hooks.py:368-372` unconditionally tells the user to "acknowledge with
`accept content`", with no state-existence check anywhere in `untrusted_read` (`hooks.py:330-372`).
Pre-init, `sdle.py accept-content` calls `read_state` unconditionally and exits 3 `state_unreadable`
(confirmed at `cmd_accept_content`, `scripts/sdle.py:9631`) — the exact impossible instruction OPEN-01
diagnosed for `cmd_scan`'s message, left uncorrected in the hook. Registered as `DEF-RR-002`, fixed
alongside `DEF-RR-001` once the design decision lands (the hook's message needs to match whatever
mechanism ships).

### R1-D03 (medium) — the canonical start command still omits scanning — **ACCEPT**

Confirmed: `.claude/commands/sdle-start.md` step 3 (lines 49-79) goes from `workitem create` through
binding straight to `preflight`, then step 4 (lines 80-85) is governance assessment. No `scan` step
appears anywhere in the file, despite SKILL.md:283 documenting it as a required step. `test_units_startup_contract.py::test_the_documented_sequence_runs`
therefore pins a sequence the shipped command file does not contain — a tautology, exactly as flagged.
Registered as `DEF-RR-003`.

### R1-D04 (medium) — the registered-without-state end-to-end variant is missing — **ACCEPT**

Confirmed by reading `tests/test_units_startup_contract.py:259` onward: the two tests in that section
assert `reset` preserves identity and that `requirements show` reports `bound: false`; neither continues
that WorkItem through bind → preflight → scan → assess → init, and neither exercises a flagged false
positive on that route. Registered as `DEF-RR-004`.

### R1-D05 (medium) — live docs still teach the disproven pre-init semantics — **ACCEPT**

Confirmed: `docs/dry-runs/05-untrusted-content-scan.md:50` says "Say `accept content` to proceed" at a
point the transcript itself says (`:41`) is before `init`, and `:59` says the pre-init scan "set
`pending_confirm_action`" — which, per `cmd_scan`, it does not. `docs/SDLE-Reference-Guide.md:541`
(read directly) likewise states a flagged file "requires explicit acceptance" without the pre/post-init
distinction. Registered as `DEF-RR-005`.

### R1-D06 (low) — the STATE record is stale — **PARTIALLY ACCEPT**

The `current_sha`/"not pushed" half was already fixed in this session, before this review ran, by a
dated reconciliation note appended to `LEDGER.md` (commit `47fb86d` — the review's candidate worktree
was pinned at `0057425`, which predates that commit, so Codex correctly found the pre-existing
`STATE.json` unedited). The second half of the claim — "every other test starts bound" overstates the
gap, since `bare_project` is used in 15 test modules besides `conftest.py` — is a fair correction to the
*ledger's own narrative*, not to `STATE.json`; the genuine gap Codex names (an absent **complete**
startup-contract test) is the same thing R1-D04 already registers. No new defect id; folded into
`DEF-RR-004`'s fix, and the ledger's narrative is corrected there too.

### R1-P01 (low, preference) — the ordinary-prose test is a fair pin — **ACCEPT, no action**

Agreed: `set_status` is both a documented pattern and a phrase this diff names explicitly, so it is not
over-fitting. The frequency table's "four of five" claim is a small, honest sample, not a measured rate;
the ledger already limits its own claim to "should be expected, not treated as rare" rather than citing
a percentage. No change.

### R1-Q01 (low, question) — `data.acknowledgeable`'s precise contract — **ACCEPT**

Agreed: the field should be defined precisely (whether `accept-content` can succeed for *this* scan
result) and tested on both values, and must never be read as a substitute for durable pre-init
acknowledgement. Folded into `DEF-RR-001`'s fix and its tests.

### R1-CLOSURE (high) — neither item is closed — **ACCEPT**

Matches the R1-D01/D02/D03/D05 findings above. The single most valuable missing piece, per Codex, is a
real durable bootstrap-acknowledgement contract wired into the actual start command — agreed, and it is
what the design decision below asks the owner to shape.

## Defect register additions

| id | source | severity | status |
|---|---|---|---|
| DEF-RR-001 | R1-D01 | high | OPEN — blocked on the design decision below |
| DEF-RR-002 | R1-D02 | high | OPEN — depends on DEF-RR-001's shape |
| DEF-RR-003 | R1-D03 | medium | OPEN — depends on DEF-RR-001's shape |
| DEF-RR-004 | R1-D04, R1-D06 (narrative half) | medium | OPEN — depends on DEF-RR-001's shape |
| DEF-RR-005 | R1-D05 | medium | OPEN — depends on DEF-RR-001's shape |

All five are prior-stabilization defects found genuinely open in Stage 0 (brief §4.0 item 5, C8): fixed
under §9 before Stage 3, regardless of impact surface. They are dependent on one another (one bootstrap
contract, several consumers), so they are one serialized fix, not four parallel ones — recorded honestly
per §9's parallelisation rule.

## Design decision needed — not mine or Codex's to make

Three shapes close DEF-RR-001, each with a real cost:

- **(a) Re-check at `governance assess`.** The engine re-scans every bound source at assessment time and
  refuses a flagged one unless an acknowledgement keyed on `(path, sha256)` exists in a new, engine-written
  pre-init record. That record is carried into the audit at the first consuming `advance`, the way
  `record_governance_audit` already defers on `executionId`. Cost: `governance assess` gains a new
  precondition; the requirements-refinement brief already changes this command for §3.2, so this must be
  recorded as part of its baseline, not layered on top separately.
- **(b) Re-check at `init`.** Same mechanism, gated at `init` instead. Cost: `init` currently has
  deliberately no such precondition (SKILL.md:297, "a WorkItem must be able to bootstrap"), and `cmd_init`
  is on this repository's byte-identical pin list — a new precondition is a considered, visible change to
  an invariant, not a small one.
- **(c) Keep today's mechanism; fix only the surfaces that misdescribe it.** Fix the hook, `sdle-start.md`
  and the docs to accurately teach "route B has no durable acknowledgement — treat the interval between
  refusal and rescan as reviewer discipline, not an engine guarantee", and record the interruption gap as
  an accepted, tested limitation — the same shape this repository already used for F-103 (concurrency
  attribution). Cost: the gap itself stays open; only its documentation stops being false.

Asked in conversation, alongside this reply.
