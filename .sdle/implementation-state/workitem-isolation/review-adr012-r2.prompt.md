# ADR-012 review, round 2

Ten findings. I verified the two cheapest load-bearing ones directly:

- **#7 confirmed.** `reserve_evidence` is called at `cmd_governance_assess` before `requirements_sources`,
  so `governance assess` on an unbound WorkItem creates `evidence/governance-<id>.json` and *then*
  refuses. That breaks the refusal atomicity this engine maintains everywhere else.
- **#1 confirmed.** `requirements_sources` writes `"sha256": sha256_file(t) if t.is_file() else None`,
  and `cmd_governance_assess` stores that straight into the record. So a deleted bound document is
  "healed" by re-assessing: the null becomes the baseline and freshness then matches it.

**Accepted and being fixed, no argument:** 1, 2, 3, 4, 5, 6, 7, 9, 10.

I am taking your closing recommendation as the shape: **one authoritative read-and-validate path** that
every consumer goes through, which refuses a missing source at assessment and rechecks schema and
containment on every read.

Thank you also for checking the test adaptation and the snapshot numbers independently — that 26
`write_atomic` and 74 command names are *correct* rather than merely agreeing is exactly what I could
not check about my own change.

Four things to settle, then I implement.

## Q1 — #2: is "missing `bindingDigest` is stale" right, or should the record version move?

Treating it as stale is the fail-closed reading and I prefer it. But it makes **every** record written
before this change stale, so every such WorkItem must re-assess before it can advance.

There are no users, so the cost is zero in practice and I lean to stale-and-simple. The alternative —
bump `governanceVersion` to 4 and refuse 3 — is louder but forces the same re-assessment through a
different door, and it would orphan records written by this branch's own intermediate commits.

Do you see a reason to prefer the version bump? If not I take stale.

## Q2 — #4: what should a consumer do when a bound path escapes at read time?

You want containment rechecked at every consumer read, and I agree. Two details:

1. **Refuse, or treat as missing?** A retargeted symlink is not the same fact as a deleted file. I lean
   to a distinct refusal (`requirements_source_invalid`) naming the path, because "this is not where you
   said it was" is a different problem from "it is gone", and silently degrading it to missing would let
   a retarget look like a deletion.
2. **Where exactly?** If the recheck lives inside the single read path, then `requirements show`,
   `preflight`, `governance assess`, freshness and `infer_project_name` all get it. But freshness is
   called inside `governance_precondition` on the *advance* path. Refusing there means a retargeted
   symlink blocks `advance` with an integrity-flavoured refusal rather than a staleness one. Is that the
   behaviour you want, or should freshness report it and let the caller refuse?

## Q3 — #8: I accept half and push back on half

Accepted: `infer_project_name` must inspect **only** the primary and then fall back to the WorkItem
title. Falling through to secondaries so that `# PCI DSS` names the project is a real defect.

Pushing back: *requiring* `--primary` whenever there are multiple sources. That is a usability change
beyond the defect, it makes the common `--all-current` case fail until the user picks one, and the
defect is entirely fixed by the inference change. Alphabetical choice as a **default** is arbitrary but
harmless once inference no longer wanders — and `requirements show` reports which document is primary.

Unless you can show a case where the arbitrary default produces a wrong outcome *after* the inference
fix, I am keeping the default and not requiring the flag.

## Q4 — #5: how far does the prompt-layer scoping go?

Discovery and impact analysis read every document under `requirements/`. I will point them at the
binding. But discovery's subject is *the repository*, not this change — ADR-005 treats it as
product-scoped, and you argued exactly that in our earlier debate.

So: should `discovery` read the **bound** documents (consistent with every other consumer), or is
discovery the one phase that legitimately reads the whole directory because its subject is the whole
repository? I can defend either; I would rather you name which, because the answer decides whether
"every consumer reads the binding" has an exception in it.

## Output

Answer Q1–Q4 directly, citing the repository where it decides something. Do not re-list the accepted
findings.
