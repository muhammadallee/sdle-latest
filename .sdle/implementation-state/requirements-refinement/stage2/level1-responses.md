# Stage 2 — Claude's responses to the Level 1 review

Level 1 run: `runs/20261001T162206-stage2-codex-plan-level1-attempt2.json` (result `PASS`, first attempt, 19
findings, `reviewed_commit` `6162064`). The findings themselves are preserved unedited in
`runs/20261001T162206-stage2-codex-plan-level1-attempt2.a1.review.json`. Nothing below replaces them.

**Method.** Each finding's load-bearing claim was checked against the repository before it was
dispositioned; the evidence I relied on is cited per finding. Dispositions are `ACCEPT`,
`PARTIALLY ACCEPT`, `CHALLENGE`, `OUT OF SCOPE`, or `OWNER DECISION` (a disagreement the agents may not
resolve themselves, per brief §5 "Escalation").

**What changes and when.** `PLAN.md` is **not** edited yet. The brief's order is Level 1 → Claude responds →
Level 2 → Claude reconciles. Each response below states the *proposed* correction exactly, so Level 2 can
attack the correction and not only the diagnosis, and so the plan under review stays identical to the
baseline `6162064`. Corrections are applied at reconciliation.

**Summary.** 19 findings: 15 ACCEPT, 3 PARTIALLY ACCEPT (008, 010, 018), 1 OWNER DECISION (011, which is
also accepted as a plan defect). No finding was challenged outright, and I want that stated plainly rather
than implied: it is unusual, and Level 2 should test whether I accepted anything too readily. Where a
finding turned out to concern code that already merged rather than the plan (008), or code that predates
this work (014's inherited defects), that is said explicitly.

---

## S2-L1-001 — critical — the refused flip can persist the forbidden PASS · **ACCEPT**

**Verified.** `cmd_governance_assess` writes `governance.json` and its evidence **before** raising
`requirements_quality_blocked` ("Persisted BEFORE the blocking refusal ... a blocked assessment must be
inspectable", `sdle.py`, just above the `if quality["result"] == "BLOCKED":` branch). `governance_precondition`
authorizes progression from the **latest** record's `quality.result` only (`if quality.get("result") != "PASS":
raise governance_blocked`). The plan's §6 row for the refused hand re-run says "`governance.json` only,
refused". Read literally, that is the blocked-path ordering applied to the flip: the forbidden PASS is
written, the command exits 1, and the next `advance` reads PASS. The brief says "refuse `quality_verdict_flip`
(exit 1) **and record the attempt**" — it does not say where.

**Proposed correction.** `quality_verdict_flip` fires **before** any write to `governance.json`, which stays
byte-identical. The attempt is recorded only in append-only evidence
(`evidence/governance-flip-attempt-<execution_id>.json`, `status: "REFUSED"`, carrying the proposed record),
then the refusal is raised. Rewrite the §6 row to say so. New test: after the refusal, `governance show` and
`advance` still observe the preceding FAIL, byte-for-byte.

## S2-L1-002 — high — the flip check only looks at the adjacent record · **ACCEPT**

**Verified.** Brief §3.2: "a check was `FAIL` at content digest C and a *later* assessment at the same C
reports `PASS`" — not limited to the adjacent assessment. D11 reads only `superseded`, the single current
`governance.json`. Sequence C1/FAIL → C2 → revert to C1/PASS: at the third assessment the superseded record is
C2's, so no flip is seen.

**Proposed correction.** Derive history from the append-only per-assessment evidence files
(`evidence/governance-*.json`, which F4 already says carry iteration history), keyed by `(checkId,
contentDigest)`. Refuse a PASS if **any** earlier non-overturned assessment at that digest recorded FAIL.
`contentDigest` is added to the evidence record as well as `governance.json`. Records written before this
change carry no `contentDigest` and are treated as "unknown", not as a prior FAIL — stated in the plan, with a
test, so the limitation is visible rather than silent.

## S2-L1-003 — high — the dispute path is a dead end or an unvalidated channel · **ACCEPT**

**Verified** against the plan: §6's new row says a dispute "does not by itself empty Fₖ", while D11 still
refuses the next unchanged-content PASS; and §5.a's `evidenceRef` / `decisionRef` are opaque strings. The
brief is more specific than the plan (§3.2: evidence is "a fresh assessor run that returns `PASS` for the
check at the same C together with a written rationale"), and the plan did not carry that through.

**Proposed correction.** Settle on `disputeOutcomes[]`. `refinement dispute` validates that `evidenceRef`
names an engine-written assessor-evidence file in which that check is `PASS` at the **same**
`contentDigest`, with a non-empty rationale, and that `decisionRef` names a recorded human decision for that
check. It then defines the effective-verdict rule: the overturned `(check, digest)` pair — and only that
pair — is exempt from D11, the original FAIL stays in the record, and the refused flip history is kept. Tests:
a dispute citing a missing file, a different digest, a FAIL, and the positive case.

## S2-L1-004 — high — the transaction has no durable home and ignores the audit/state coupling · **ACCEPT**

**Verified.** §5.a's `refinement.json` has no transaction field; the transaction shape exists only in §6
(`C1 shared-document transaction record`). D1 puts intent "in its own `refinement.json`" but an *affected*
WorkItem has no local pointer to another WorkItem's pending intent, while the recovery text says it runs
"for the originating or an affected WorkItem". `append_audit` rebaselines `state["audit_sha"]` and its
callers follow it with `save_state`, so there is a crash window between the two that D1 does not mention. D1
itself flags exactly this ("is this precedent load-bearing for a multi-WorkItem transaction?"); the answer is
no, not as written.

**Proposed correction.** Add `transactions[]` to the origin `refinement.json`, and a
`pendingTransactions[]` pointer ({transactionId, originatingWorkitem}) in **each affected WorkItem's own**
record, written before the document write. State the ordering: target evidence → intents/pointers →
document → per-WorkItem audit and state → `COMMITTED`. Give each crash point an explicit recovery branch,
including audit appended / `state.json` not yet saved, which recovery must reconcile before ordinary drift
validation would refuse the WorkItem. Whether that last window is new or merely the existing
`append_audit` → `save_state` window is a question for Level 2.

## S2-L1-005 — high — locking only the discovered set does not stabilise it · **ACCEPT**

**Verified.** `cmd_requirements_bind` reads and writes `requirements.json` with no lock; D2 locks "per
affected WorkItem", chosen from the set discovered before the write. A WorkItem that binds the document in
between is a sharer the transaction never saw.

**Proposed correction.** One repository-scoped transaction lock, shared by refinement apply **and**
`requirements bind`, under which the complete binding set is recomputed before the document write. This
widens the plan's surface to one existing command, which I am flagging as a scope increase for the owner
rather than slipping in. Where the lock file lives (it must not trip the closed `.sdle/` boundary set) is
decided in the ADR; the architecture lock's `.sdle/architecture/` is the precedent, not a licence.

## S2-L1-006 — high — D2's lock semantics are mutually incompatible · **ACCEPT**

**Verified, and part of it is my own doing.** D2 says `open(path, "x")`, refuse if held, no crash cleanup;
my §0.4(3) says reuse `architecture_catalog_lock` (10 s wait, 60 s stale break). Those are two different
contracts. The brief (§3.5) wants the lock held "from apply through reassessment", but apply and
reassessment are separate invocations, and the assessor is a **model dispatch** the engine cannot run inside
one process.

**Proposed correction.** There are two different things and the plan conflated them. (1) A **short mutex**
around each read-check-write step, exactly the architecture lock's shape — milliseconds, so a 60 s stale break
is safe. (2) The **long interval** from apply to reassessment, protected not by a held lock but by the
durable `PENDING` intent from 004: any other WorkItem touching that document sees the pending transaction and
refuses. Rewrite D2 as (1), cite (2) as the protection for the long interval, and drop `open(..., "x")`
(see 015).

## S2-L1-007 — medium — the normal form erases a Markdown hard line break · **ACCEPT**

**Verified.** §3.5 strips trailing whitespace per line. In Markdown, two trailing spaces before a newline
force a hard break; removing them changes rendering, yet both forms normalise identically, so it would
auto-apply under C2, which says block structure is never normalised away.

**Proposed correction.** Treat any change to trailing whitespace on a non-blank prose line as **non-neutral**
(needs a human decision), or preserve hard-break syntax in the normal form. Add hard-break, indented-code,
inline-HTML and escaped-space fixtures to scenario 27.

## S2-L1-008 — high — a refinement edit can stale another WorkItem's placement · **PARTIALLY ACCEPT**

**Verified, and it corrects a claim I made.** `architecture-placement.json` stores catalog revision and
proposal data and no requirements digest; neither `architecture_precondition` nor
`architecture_binding_precondition` references one. My §0.4(7) said a refinement edit "cannot stale a
placement"; that is true only for a WorkItem refining *its own* documents pre-`init`. A C1 edit to a
**shared** document by WorkItem B can land after WorkItem A already has a placement.

**Why only partially.** (a) That gap is not created by refinement: a hand edit of a bound document after
placement has the same effect today (`governance_stale`, re-assess, placement untouched), and no generated
artifact is invalidated by a requirements change — drift detection covers approved artifacts, not their
inputs. (b) The fix proposed (pin requirement digests into the placement record) changes the **already-merged
architecture-memory design**, which this plan should not do on the side.

**Proposed correction.** Correct §0.4(7) to say exactly what is true. Have the C1 acknowledgement text name
the consequence for affected WorkItems (their governance goes stale and anything derived from the old bytes is
not re-derived). Record the placement-digest gap in the brief's §9 register for owner triage as a separate
architecture-memory change, with the reviewer's two-WorkItem test as its acceptance test. Add that same test
to *this* plan only as a characterisation of current behaviour.

## S2-L1-009 — high — D10 builds check definitions from a source that has none · **ACCEPT**

**Verified.** `GOVERNANCE_POLICY_BUILTIN` carries the twelve ids, the blocking list and the optional list;
no definitions. The only definitions are in `assessor-prompt-draft.md`, which D10 says must not become the
production prompt. D10's statement that dispatch takes "the actual check-id list and definitions ... from
`GOVERNANCE_POLICY_BUILTIN`" is false as written.

**Proposed correction.** One engine-owned structured table of check definitions; the policy's ids derive from
(or are asserted equal to) it; `governance policy` and the dispatch payload read it; the no-restatement test
is extended to cover it. This adds an engine constant and is therefore a Phase A item, not a Phase D one.

## S2-L1-010 — medium — D8 accepts unvalidated baseline citations · **PARTIALLY ACCEPT**

**Verified.** D8 says the engine performs no accuracy validation of a cited baseline id; the baseline holds
engine-readable references and discovery finding ids.

**Why partially.** *Existence* is deterministically checkable and I accept that; *relevance* is not, and
claiming otherwise would repeat the model-judged-as-mechanical error the brief warns against.

**Proposed correction.** Require a structured citation (`kind`, `id`), resolve it against a sound baseline and
its hash-pinned discovery record, and refuse an unknown or stale id. Reword scenario 14 to promise only what
that deterministic check can deliver, and say in the plan that relevance remains an assessor judgement.

## S2-L1-011 — high — the todo-api.md decision is unresolved · **OWNER DECISION** (and accepted as a plan defect)

**Verified by execution.** `recompute_metrics.py`: `todo-api.md` — `dependencies` — `['todo-api.md#run1',
'#run2', '#run3']` are false positives under the committed clean label (blocked 3/3, agreement `AGREE`). The
plan records this and leaves two readings open (§3.c); brief scenario 1 requires `todo-api.md` to pass
unchanged with no loop.

**This is not mine to resolve.** It is the one disagreement here between the owner's own scenario and the
measured behaviour, and either answer changes the owner's text: refine the `dependencies` definition so the
existing document passes; amend the document with explicit authorisation and update scenario 1; or amend the
scenario. **Escalated to the owner with this finding** (see the escalation block at the end). Implementation
Phase A cannot start until it is answered. I accept the defect that the plan leaves it open.

## S2-L1-012 — medium — the lint prototype is not kind-sensitive · **ACCEPT**

**Verified** by reading `lint-prototype.py`: the vague-term rule flags every occurrence regardless of
normative vs descriptive text, fenced blocks or quotations, and the section rules apply per document, not per
bound set. Advisory-only status prevents a refusal but not inaccurate evidence.

**Proposed correction.** The plan specifies each rule's applicability (normative vs descriptive, code/quote
exclusion, document roles, bound-set vs per-document) with neighbouring-kind and multi-document fixtures
**before** the prototype is ported, and says the prototype is a measurement tool, not the shipped rules.

## S2-L1-013 — medium — the corpus does not support the reliability claims · **ACCEPT**

**Verified by execution.** Agreement 10/14 (71%); `clean-baseline` blocked in 1 of 3 runs; three documents
`_undetermined`; `dependencies` recall and precision 0.00; and the script itself notes no duplicate-id
positive exists.

**Proposed correction.** Relabel every corpus-derived number in the plan as exploratory, not confirmatory;
add the two-document duplicate-id positive/negative pair the script says is missing; add independently
authored positives and cleans per requirement kind; report uncertainty. No claim in the plan may rest on a
three-observation cell.

## S2-L1-014 — high — three in-scope inherited defects have no design or tests · **ACCEPT**

**Verified.** `_lexically_safe_path` still rejects `.` (a component for which `part != part.rstrip(". ")`);
D6 only routes new paths through it. `cmd_accept_content` calls `write_content_acknowledgement` (line 12505)
before `read_state` (12507). D7 says no new mechanism is needed and `governance_precondition` still never
re-scans flagged bytes. I put RR-002/007/008 in scope in §0.5, and the owner confirmed it — so the plan owes
them design and tests, which it does not yet give.

**Proposed correction.** Add explicit tasks and regression tests: normalise a benign `./` *before* the alias
check and fix the message (RR-002); re-scan the exact freshness bytes at the advance/gate preconditions
(RR-007); validate state before the post-init acknowledgement write (RR-008). RR-003 and RR-006 stay in the
§9 register, as the reviewer also says.

## S2-L1-015 — medium — the pin list is incomplete · **ACCEPT**

**Verified by execution.** `test_exactly_one_function_creates_a_file_exclusively` accepts only
`reserve_evidence`, so D2's `open(..., "x")` would fail it; the `COMMANDS` pin collects every parser token
(`refinement`, `propose`, `decide`, `dispute`, `cancel`, ...), not only the group; the runtime-member names are
pinned exactly in `test_units_repo_config.py`. My §0.4(6) listed four pins and missed these.

**Proposed correction.** Enumerate every pin the change moves, with the reason: all new parser tokens; the
lock primitive (use `os.open(..., O_EXCL)` as the architecture lock does, or a shared helper, so the
exclusive-open invariant stays true); the runtime-member set including the record and the lock;
`PRODUCT_AGENTS`; and each primitive count.

## S2-L1-016 — high — `requirements_check` does not make the module available pre-`init` · **ACCEPT**

**Verified.** `cmd_resume` reports capabilities for the current phase via `Constants.capabilities_for`;
before `init` there is no state and no phase. Pre-init bootstrap routing lives in `sdle-start.md` and
`SKILL.md`, and the plan says `/sdle-start` changes only "if needed". The §5.c list has no refusal for a
mutating refinement command run after `init`, and `cmd_init` does not take part in any refinement lock.

**Proposed correction.** Make the routing explicit in `SKILL.md` and `sdle-start.md` so the module loads
before assessment; name the pre-init-only commands; add `refinement_post_init`, refused before any write when
`state.json` exists; make `init` refuse while a refinement transaction is `PENDING`; allow only read-only
diagnostics afterwards. My earlier note to "verify the `CAPABILITY_MAP` row in a throwaway worktree" is
superseded by this: the row alone is not enough.

## S2-L1-017 — medium — C3's lower-only policy cap is not designed · **ACCEPT**

**Verified.** `GOVERNANCE_POLICY_OVERRIDABLE` has no refinement key and unknown override keys are refused.

**Proposed correction.** One engine-owned maximum constant and one policy field accepting only integers in
`1..max`; pinned at loop start with its source recorded in `refinement.json`. Tests: malformed, higher,
changed-mid-loop, lower.

## S2-L1-018 — medium — D5's commands lack input contracts; `propose` duplicates assessment · **PARTIALLY ACCEPT**

**Verified.** The §6 table shows `propose`, `decide`, `apply`, `dispute`, `cancel` and the error path all
writing `refinement.json`, against D5's "single writer"; §5 defines stored records but no input envelopes; and
`propose` "re-assesses internally" although `governance assess` is the existing refusal-preserving door.

**Why partially.** The reviewer's principle is right and I accept it: `governance assess` stays the **only**
assessment path. But the command group itself is still needed — the loop's state machine (decisions, edits,
transaction, dispute) has no home in the existing commands — which is what attack item 3 asked, so I am
answering it rather than dropping it.

**Proposed correction.** `propose` records findings/questions from an assessment that `governance assess`
already produced, and does not assess a second time; the sole-writer claim becomes "one validated writer
*helper*", used by every command; strict input schemas are published for each mutation.

## S2-L1-019 — medium — the lint evidence says `"floors": true` · **ACCEPT**

**Verified.** `PLAN.md` §5.b's example has `"floors": true` while §3.b says no finding ever raises
`quality_verdict_below_floor`. An engine-written record would assert an enforcement property that is false.

**Proposed correction.** Replace it with `floorEligible` and `floorEnforced`, with `floorEnforced` always
`false` for every shipped rule; test the evidence against the authorised deviation.

---

## Escalation to the owner (brief §5)

**S2-L1-011 — severity high.** `todo-api.md` is measured as blocked 3/3 on `dependencies` (false positives
under the committed clean label), but acceptance scenario 1 requires it to pass unchanged with no loop. The
agents may not resolve this. Options: (1) refine the `dependencies` check definition so the existing document
passes; (2) amend the document with explicit authorisation and update scenario 1; (3) amend scenario 1. Consequence of
leaving it open: Phase A cannot start, because the check-definition table (S2-L1-009) is exactly what option
(1) would change. Decision required: which of the three.

## Things Level 2 should test hardest

1. That I accepted nothing too readily — especially 006 (my reframing of the lock) and 004's claim about the
   `append_audit` → `save_state` window.
2. That the **partial** acceptances (008, 010, 018) are the right place to stop.
3. That the proposed corrections do not themselves weaken an existing refusal (001, 005, 016).
