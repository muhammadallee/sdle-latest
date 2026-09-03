---
description: Start or resume the SDLE workflow.
argument-hint: "[--verbose]"
---

1. `scripts/sdle.sh preflight`. On exit 1, print `message` and stop — the
   prerequisite is missing and nothing should be initialised.
2. If a workflow already exists for the resolved WorkItem
   (`workitems/<id>/.sdle/state.json`), this is a resume: run
   `sdle.sh migrate`, then `sdle.sh header`, then `sdle.sh resume` — which
   reports position, pending work and the `capabilities` this phase requires,
   from disk alone. Load exactly those capability files and follow them. A
   resume never asks for a WorkItem name. Resolution handles the
   common cases on its own — the directory Claude was launched from, a single
   registered WorkItem, a persisted active context, or a unique branch match.
   On exit 1 `workitem_ambiguous`, run `sdle.sh workitem resolve` (it always
   exits 0), show `data.candidates` with their evidence and ask which one.
   Ranking the candidates is a presentation aid, never a decision: never pick
   one, and never hand this question to a subagent. Re-run with the user's
   answer as `--workitem <id>`, and offer
   `sdle.sh workitem use --workitem <id>` to remember it for this working
   directory. On exit 1 `workitem_unregistered`, the current directory is
   inside an unindexed `workitems/<x>/` — register it or move.
   If the registry itself looks wrong, `sdle.sh validate` diagnoses it and
   still runs when resolution cannot.
   If a repository-global `.workflow/state.json` exists, it is a pre-v1.14
   workflow: run `sdle.sh migrate-workflow --workitem <id>` once, after the
   WorkItem in step 3 exists. `init` refuses while it is there.
3. Otherwise this is a new workflow, and identity comes before initialisation.
   Ask `WorkItem name?` and run
   `sdle.sh workitem create --name "<what the user typed>"`.
   - Only if the user explicitly says `auto generate`, infer a concise name
     yourself and pass `--auto-generate` as well.
   - On exit 1 `workitem_exists`, show the existing id and ask
     `Resume existing WorkItem? or Provide another name?`. Never invent a
     suffix — `foo-2`, `foo-copy` and `foo-final` are forbidden.
   - On exit 1 `workitem_name_invalid`, print `message` and ask again.
   - On exit 3 `index_malformed`, print `message` and stop. The registry is
     repaired by hand; SDLE never rewrites it.
4. Then assess governance for that WorkItem: write the structured
   proposal the skill describes and run
   `sdle.sh --workitem <id> governance assess --input <path>`.
   `sdle.sh governance policy` reports the check ids, signals and levels it
   is scored against; it needs no WorkItem. This is required before the first
   `advance`, not before `init` — on exit 1 print `message` and stop.
5. Then run
   `sdle.sh --workitem <id> init --session <8-hex token for this conversation>`,
   naming the id step 3 returned. The WorkItem is the durable identity *and*
   the runtime scope: `init` writes `workitems/<id>/.sdle/state.json`, records
   the branch and starting SHA in `execution.json`, and refuses
   `workitem_required` if no WorkItem exists.
6. If `$ARGUMENTS` contains `--verbose`, the skill sets verbose mode.
7. Print the header, summarise the requirements found, and propose the next
   phase.

Read `.claude/skills/sdle/SKILL.md` and follow it to execute the phase.
