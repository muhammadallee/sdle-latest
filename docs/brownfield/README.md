# Brownfield — discovery once, then iterate

**Applies to:** SDLE v1.17
**Authority:** `scripts/sdle.py` (`discovery`, `baseline`) and
`docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`.

---

## 1. The problem

An existing repository already contains the decisions a greenfield WorkItem
would have to make: an architecture, conventions, dependencies, constraints. If
every WorkItem rediscovered them, the second WorkItem would pay the first
WorkItem's cost again, and the third would too.

SDLE's answer is: **discovery happens once per repository, and its result is a
durable artifact every later WorkItem converges onto.**

---

## 2. Which flow, and who decides

`init` decides, from the repository baseline — not from a convention and not
from the model's preference:

| Situation | Flow | If you propose otherwise |
|---|---|---|
| No baseline, existing repository | `BROWNFIELD_DISCOVERY` | — |
| No baseline, new product | `GREENFIELD` | — |
| Sound baseline present | `ITERATIVE` | `BROWNFIELD_DISCOVERY` refuses `baseline_present` |
| No sound baseline | — | `ITERATIVE` refuses `baseline_required` |

Both refusals fire **at `init`**, before anything is created, so the refusal
leaves no runtime and no audit entry. A genuine second discovery is still
possible: record `classification.rediscovery` as true, which is permitted only
alongside `BROWNFIELD_DISCOVERY`.

`DEFECT_FIX` and `HOTFIX` are never blocked by the baseline. Blocking an
emergency hotfix on a repository-level artifact is not a governance rule
anything asks for.

---

## 3. The `discovery` phase

`BROWNFIELD_DISCOVERY` adds one gateless phase, `discovery`, before the normal
lifecycle. Findings are submitted through `sdle.sh discovery assess` and are
**refused unless every one of them is classified**.

Get the vocabulary from the engine — `sdle.sh discovery schema` reports the
categories, the finding keys and the classifications. They are deliberately
stated in exactly one place in the codebase, so this document does not restate
them.

Three things are worth knowing before you write a discovery input:

- **Every declared category needs at least one finding.** Silence is not an
  answer.
- **Classification is closed and honest.** An `OBSERVED` finding must cite at
  least one evidence path, and every cited path must exist inside the
  repository. An `INFERRED` finding must name the findings it was inferred
  from, and none of those may itself be unknown. An `UNKNOWN` may not carry
  evidence — an unknown that cites a file is not an unknown.
- **The refusal cites a named rule.** Each validation rule has an id, so a
  refusal tells you which rule you broke rather than that something was wrong.

---

## 4. The baseline

`.sdle/baseline.json` is written **once**, at the final gate of a `GREENFIELD`
or `BROWNFIELD_DISCOVERY` WorkItem. There is no `baseline establish` command —
nothing you can call writes it. Letting a flow that performed no discovery
establish a "discovered" baseline would make the whole invariant decorative.

It records the establishing WorkItem, the commit it was established at, the
references it rests on (constitution, architecture, ADRs), the repository's
non-negotiables, whether discovery was performed, and what it supersedes.

Read it with `sdle.sh baseline show`, which needs no WorkItem. The status is
**derived**, never stored:

| Status | Meaning |
|---|---|
| `ABSENT` | No baseline. Most repositories. Emits no finding — it is not a defect |
| `VALID` | Present, well-formed, and its references resolve |
| `STALE` | Present and well-formed, but a referenced file has **changed** |
| `INVALID` | Materially broken — malformed, or a reference no longer exists |

### Stale is a warning; invalid is a refusal

This distinction is deliberate and is the most commonly misread part of the
design.

- A **materially invalid** baseline blocks `ITERATIVE` outright
  (`baseline_required`), and `baseline validate` refuses `baseline_not_valid`.
- A **changed reference** is reported, never refused. `design_generation` runs
  in `ITERATIVE` and rewrites the design document, so treating change as
  invalidation would force the third WorkItem in any repository back into full
  rediscovery — the exact cost discovery-once exists to avoid.

What a stale baseline can never do is be relied on *silently*: `baseline
validate` refuses it, and since v1.17 both refusals name the **commit the
baseline was established at**, so a finding says which repository state its
claims were ever true for.

---

## 5. Repository-level artifacts

`design/`, `reviews/` and `clarifications/` are repository-level, not
WorkItem-scoped, and `design/app/app-design.md` is shared across WorkItems.
That is a recorded V1 decision, not an oversight: copying a genuinely shared
architectural artifact into every WorkItem for directory symmetry would create
divergent copies of one truth. See ADR-008 for the V1 position and the follow-on
question.
