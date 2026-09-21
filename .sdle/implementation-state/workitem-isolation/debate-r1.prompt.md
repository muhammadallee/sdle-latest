# Design debate, round 1 of at most 3

You are arguing with another senior engineer (me) about a design decision in the repository you are
sitting in. I have stated a position. **Your job is to find what is wrong with it**, not to agree
politely. If you think I am right, say so plainly and say what would change your mind — but look hard
first. End with a concrete recommendation you are willing to defend.

You are read-only. Inspect the repository freely (`git log`, `git show`, `rg`, reading files). Do not
edit anything.

## The defect, demonstrated

`requirements/` lives at the repository root. `requirements_sources()` (scripts/sdle.py ~4356) globs
`project_root / "requirements"` and hashes the whole set into one digest, stored in each WorkItem's
`governance.json`. `governance_freshness()` (~4890) re-globs and compares.

I ran this in the test harness:

```
WorkItem A assessed against requirements/todo-api.md   digest 8d4a75d5…
→ add requirements/second-workitem.md  (a different WorkItem's document)
→ A's next `advance`:  exit 1  governance_stale
```

So one WorkItem's requirements document freezes an unrelated WorkItem. ADR-008 has a family of
isolation tests (`test_two_workitems_complete_independent_runs`,
`test_a_lock_on_one_workitem_never_blocks_another`,
`test_manifest_build_under_one_workitem_leaves_the_other_alone`) and governance staleness is not a
member of it.

## The options

**A — move it:** `workitems/<id>/requirements/`. Engine cost is 4 path sites (1573 `infer_project_name`,
1595 `cmd_init`, 4364 `requirements_sources`, 9741 `cmd_preflight`) plus a `Paths` property. Breaks the
documented pre-launch setup order, ~18 docs/prompt files, ~8 test modules.

**B — scope the comparison:** leave the directory at the root; `governance_freshness` recomputes the SHA
of the *recorded* paths instead of re-globbing. Editing or deleting an assessed file is still
`governance_stale`; an unassessed new file is not. Report unassessed additions without refusing. No
record-version bump — `requirements.sources` is present at every `governanceVersion`.

**C — both:** per-WorkItem directory takes precedence, root remains for product-level requirements.

## The fact that changed my mind

**There are no users.** Not "few" — none. This repository has never been installed anywhere but here.
So migration cost, breaking-change cost, and "existing installs refuse `requirements_missing`" are all
exactly zero. Two of my three arguments against A evaporated when the owner told me that.

## My position: A

1. **No users** removes the migration and breaking-change objections entirely. What remains is which
   model is *correct*, and cost of the edit — not risk to anyone.
2. **Four of five flows are change-scoped.** `ITERATIVE`, `DEFECT_FIX`, `HOTFIX` and arguably
   `BROWNFIELD_DISCOVERY` each describe *a piece of work*, not the product. Only `GREENFIELD` reads as
   product-level — and a `GREENFIELD` repository has exactly one WorkItem, so scoping loses nothing
   there. Root-level `requirements/` is an artifact of SDLE having been designed GREENFIELD-first.
3. **ADR-008 TR25 cites §10** ("do not copy shared artifacts into every WorkItem for directory
   aesthetics") against relocating shared directories. I claim that objection does not reach
   `requirements/`, because the durable product truth already has homes that outlive a WorkItem:
   `.specify/memory/constitution.md` and `.sdle/baseline.json` (whose `BASELINE_REFERENCE_KINDS` are
   constitution, architecture, adrs). `requirements/` is the *input to a change*, not the product record.
4. **B is a patch over the wrong shape.** Its own known gap proves it: under B, two WorkItems that
   assessed against an overlapping set still both go stale when a shared document is edited. That
   residual coupling is the same bug, just smaller.

## Attack these specifically

- Is point 3 actually true? Read what the constitution and the baseline hold. If durable product
  requirements have **no** home outside `requirements/`, point 3 collapses and §10 bites.
- Point 2: is `BROWNFIELD_DISCOVERY` change-scoped or product-scoped? What does `discovery` actually
  consume? Does `GREENFIELD` really imply one WorkItem, or can a repo hold several?
- `infer_project_name` reads `requirements/` at `init` to name the project. Is there a chicken-and-egg
  problem, or a behaviour change, when that directory is WorkItem-scoped?
- Timing: this repository *just* merged a ten-phase stabilization to `main` (commit `cb9a183`) whose
  whole point was reducing drift. Is opening a breaking layout change immediately afterwards
  self-defeating, regardless of correctness?
- Is C actually the honest answer — because the domain genuinely has both product-level and
  change-level requirements — and am I dismissing it because it is less elegant rather than because it
  is wrong?

## Required output

Plain prose, no JSON. Be specific and cite files and line numbers. Structure:

1. **Where I am wrong** — the strongest defects in my position, ranked.
2. **Where I am right** — what survives, stated as plainly as the criticism.
3. **Your recommendation** — A, B, C, or something I have not considered. One paragraph on why, and
   name the single fact that would flip you to the runner-up.
4. **What you would verify before committing** — the checks that would settle it empirically.
