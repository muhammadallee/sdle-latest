# Plan review, round 1 — SDLE UI-quality enhancement, Phase M (loop and review integrity)

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first (eight invariants: the engine refuses rather than warns; single writer; one source of truth per fact). Report the checked-out commit as `reviewed_commit`.

You are reviewing a **plan**, not code: `.sdle/implementation-state/ui-quality/phases/M-PLAN.md`, with PLAN.md §3 (F7, F8), §6 Phase M, and the Amendments sections. It changes `scripts/sdle.py` in three places. Read the current source; do not trust the plan's description. You may run read-only Python probes against in-memory data.

## Attack list
1. **M1.** Is filtering `_blocking_finding_fingerprints` on `reviewType == "code-review"` correct and sufficient? Does any other caller or other review type rely on the unfiltered behaviour? Is the "newest" record chosen correctly when several code reviews of one path exist, or when a code review exists for a stale sha?
2. **M2.** Is "no `findings` summary on the matching record" exactly the condition for "recorded without structured findings"? Is an empty list handled? Can the check be bypassed (a second review recorded afterwards, another review type, the review step run twice, a review recorded before the loop begins)? What happens to an in-flight loop run state? Does it change any currently passing behaviour that is not a defect?
3. **M3.** Which review paths record a finding disposition? Is `cmd_artifact_review` the only door for findings? Is refusing only `--actor-type agent` the right set (the plan raises `tool`, `test`, `system`)? Can the waiver be recorded another way (editing evidence files; a later review that re-lists the finding; `--findings` read from a file that changes)? Is the refusal ahead of every write (single-writer, refuse before first write)?
4. **Honesty of the wording.** The plan says the actor type is self-declared and the refusal must not be called authorization. Is the claim accurate against ADR-007 §3, and is there any place in the plan that overstates it?
5. **Mechanical fit.** Which tests, pins, counts and docs enumerate refusal reasons, command surface, write call sites or review record fields (search `tests/`, `docs/`, `scripts/`)? Which would the three changes move? Anything the plan omits?
6. **Other surfaces reaching the same behaviour** (per this repository's defect-fix rule): list every code path that reads review findings or dispositions (gate approve, review status, manifest/verification, loop) and say whether each is affected.

## Output
Return **only** a JSON object matching the supplied schema. Ids `MP-R1-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, `areas_not_reviewed` specific, no padding, no wording nits.
