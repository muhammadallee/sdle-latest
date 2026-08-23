---
description: Start or resume the SDLE workflow.
argument-hint: "[--verbose]"
---

1. `scripts/sdle.sh preflight`. On exit 1, print `message` and stop — the
   prerequisite is missing and nothing should be initialised.
2. If a workflow already exists for the resolved WorkItem
   (`workitems/<id>/.sdle/state.json`), this is a resume: run
   `sdle.sh migrate`, then `sdle.sh header`, then follow the skill's resume
   path. A resume never asks for a WorkItem name. If more than one WorkItem is
   registered, pass `--workitem <id>`; on exit 1 `workitem_ambiguous`, show the
   ids from `data.workitems` and ask which one — never pick one.
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
4. Then run `sdle.sh init --session <8-hex token for this conversation>`. The
   WorkItem is the durable identity *and* the runtime scope: `init` writes
   `workitems/<id>/.sdle/state.json`, and refuses `workitem_required` if no
   WorkItem exists.
5. If `$ARGUMENTS` contains `--verbose`, the skill sets verbose mode.
6. Print the header, summarise the requirements found, and propose the next
   phase.

Read `.claude/skills/sdle/SKILL.md` and follow it to execute the phase.
