# Design debate, round 2 of at most 3

Same rules. Disagree where you think I am wrong. End with a recommendation you will defend.

## What I concede, without reservation

1. **My point 3 is dead.** I checked: `BASELINE_REFERENCE_KINDS = ("constitution", "architecture",
   "adrs")` (scripts/sdle.py ~5797). No requirements reference. Durable product requirements have no
   home outside `requirements/`, so §10 does bite A. You were right and my argument was wrong.
2. **"GREENFIELD implies one WorkItem" is false.** `test_two_workitems_complete_independent_runs`
   contradicts it — a test I had already read in this session and still argued against. My error.
3. **`BROWNFIELD_DISCOVERY` is product-scoped.** Accepted.
4. **My criticism of B's overlap behaviour was wrong.** If two assessments genuinely consumed the same
   document, staling both is correct dependency tracking, not coupling. That was the weakest thing I said.
5. **Your point 4 is verified, and it is a bigger finding than you presented it as.** I printed the real
   list for a bound WorkItem:

   ```
   implementation_exclusions -> ['workitems/fixture-workitem/.sdle/', '.sdle/', '.specify/']
   ```

   Only *this* WorkItem's runtime. `workitems/` records are versioned by design, so **today**, with no
   layout change at all, WorkItem B's governed runtime writes — `state.json`, `audit.md`, its evidence —
   land inside WorkItem A's Gate 7 manifest and A's security-review diff. That is a live cross-WorkItem
   isolation defect independent of the requirements question, and neither A, B nor C fixes it. I am
   recording it as its own finding. Thank you for it.

## Where I still think you are wrong: C's cost is the ontology, and you named it yourself

Your own section 4 opens: *"settle the ontology... if reasonable engineers cannot classify them
consistently, neither A nor C is ready."* I think that is the decisive sentence in your answer, and it
argues against your own recommendation.

C-as-union makes the shared/owned classification **structural and permanent**: it is expressed as which
directory a file sits in, decided at authoring time, for every document, forever. If the classification
is genuinely hard — and your regulatory-constraint example suggests it is — then encoding it in the
filesystem is the worst place to put it, because moving a file later silently changes which WorkItems a
change stales.

## My counter-proposal: explicit source selection, layout unchanged

Let the assessment declare which documents it consumes. `governance assess --requirements <paths...>`,
recorded in `governance.json` exactly as `requirements.sources` already is. Freshness compares the
recorded paths (your B), and the recorded set is chosen rather than inferred from a glob.

Check it against every case you raised:

| Case | Behaviour |
|---|---|
| B's document added later | Not in A's declared set. A unaffected. The demonstrated defect, fixed |
| Two unrelated documents both present at assess time | Each WorkItem declares its own. Fixed — this is the gap you correctly identified in plain B |
| A regulatory constraint governing several WorkItems | Each declares it. Editing it stales all of them — correct dependency tracking, by your point 5 |
| Product-wide SLO | Same. No duplication of content, no false ownership |
| §10 | Satisfied. Nothing is copied; sharing is a declaration, not a second copy |
| `infer_project_name` | Reads the declared set, so it stops inheriting the alphabetically-first unrelated heading — the improvement you noted for A, without A |

Three properties I claim make this strictly better than C:

1. **It subsumes C without the duality.** If someone later wants requirements under
   `workitems/<id>/requirements/`, they select that path. The layout becomes a *convention*, adoptable
   with no engine change and reversible without one. C hard-codes the ontology; selection leaves it to
   the person who knows.
2. **B is its default, so it is one change, not two.** Declare nothing and the recorded set is whatever
   was present at assess time — which is exactly B. B is not a rival to this; B is the fallback path of it.
3. **Sharing becomes visible.** Under C, two WorkItems share a document because it happens to sit in
   the root. Under selection, they share it because both named it. Your own standard — *"intentional
   sharing is visible rather than inferred from directory coincidence"* — is better served by
   declaration than by a directory.

## The fact that would flip me to C

If the shared/owned split can be classified cleanly *and durably* — if the answer for a given document
never changes over its life — then structure beats declaration, because structure cannot be forgotten
and a declaration can. Make that case with examples from this repository, and I will take C.

## Attack these

- Is selection actually cheaper than C, or am I hiding cost in a new flag's failure modes — a named
  file that does not exist, an empty selection, a path outside the repository, a directory versus a
  file, a selection that goes stale because the file was renamed?
- Does selection break `preflight`, which today reports `requirements_missing` from a bare directory
  listing (~9741) with no notion of a declared set?
- Is there a case where declaration is genuinely worse than structure that I have not considered?
- Given the manifest-exclusion defect above, what is the right **order** of work? My instinct: the
  isolation defect first, because it is live and unrelated to layout; then the requirements mechanism.
  Argue if you disagree.
- If you still say C, tell me what happens on the day someone moves a document from the root to a
  WorkItem folder, or back.
