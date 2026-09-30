---
description: Start or resume the SDLE workflow.
argument-hint: "[--verbose]"
---

1. `scripts/sdle.sh preflight`. It resolves a WorkItem first, like every
   runtime command. On exit 1 `workitem_required` in a repository that has
   no WorkItem and no legacy `.workflow/`, this is a brand-new workflow: go
   to step 3, which creates the identity and runs preflight then. On any
   other exit 1, print `message` and stop — the prerequisite is missing and
   nothing should be initialised.
   On exit 1 `requirements_unbound` a WorkItem *did* resolve and simply has
   nothing bound yet: go to step 2b, not step 3 — the identity already exists
   and must not be created again.
2. If a workflow already exists for the resolved WorkItem
   (`workitems/<id>/.sdle/state.json`), this is a resume: run
   `sdle.sh header`, then `sdle.sh resume` — which
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
   If a repository-global `.workflow/state.json` exists, it is a workflow from a retired runtime and it
   does **not** run: every runtime command refuses exit 1 `workitem_required`, and the refusal says SDLE
   does not run or migrate it and leaves it untouched. SDLE never moves or deletes it for the user: they remove it or
   move it aside themselves, then start a current WorkItem with `sdle.sh workitem create --name "<name>"`.
   `init` refuses `legacy_workflow_present` for as long as it is there.
   A WorkItem whose `state.json` uses another state schema is refused `unsupported_state_version`; show the
   message and stop.
2b. A WorkItem resolved but has no `workitems/<id>/.sdle/state.json`: it was
   registered and never initialised, or was `reset`. This is **not** a new
   workflow and step 3 must not run — `workitem create` would refuse
   `workitem_exists`. Say which WorkItem resolved, run
   `sdle.sh --workitem <id> requirements show` to report what it has bound.
   It **exits 0 either way**: branch on `data.bound`, which is `false` with an
   empty `sources` when nothing is bound. It does not refuse. Then pick up at
   the binding paragraph in step 3 and continue through steps 4 and 5 with that
   id.
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
   Then bind the documents this WorkItem is about. **Which documents those are
   is the user's decision, not yours** — list what is under `requirements/`,
   ask which of them this WorkItem is about, and offer both `all of them` and
   *another path in this repository* as answers. A bound source may be **any**
   file in the repository; `requirements/` is only where `--all-current` looks,
   so do not present that directory as the limit of what can be bound. Never bind a set the user did not choose: an unbound document
   governs nothing, so binding the wrong set silently drops constraints or
   silently imports someone else's. Then run
   `sdle.sh --workitem <id> requirements bind --source <path>` (repeatable),
   or `--all-current` if they said all of them, which takes every document
   under `requirements/` exactly as it stands now — a snapshot, not a pattern.
   Binding more than one document requires `--primary <path>`; ask which one
   names the project rather than guessing, because the engine refuses
   `requirements_primary_required` and the primary's first `#` heading becomes
   the project name. Report what was bound.
   Then run `sdle.sh --workitem <id> preflight`, naming the id just
   returned — the global `--workitem` goes before the subcommand. On exit 1
   print `message` and stop: SpecKit, its skills are missing, nothing was
   bound (`requirements_unbound`), or a bound document is not there
   (`requirements_source_missing`), and nothing has been initialised.
4. Then assess governance for that WorkItem: write the structured
   proposal the skill describes and run
   `sdle.sh --workitem <id> governance assess --input <path>`.
   `sdle.sh governance policy` reports the check ids, signals and levels it
   is scored against; it needs no WorkItem. This is required before the first
   `advance`, not before `init` — on exit 1 print `message` and stop.
5. Then run
   `sdle.sh --workitem <id> --session <8-hex token for this conversation> init`,
   naming the id step 3 returned. The WorkItem is the durable identity *and*
   the runtime scope: `init` writes `workitems/<id>/.sdle/state.json`, records
   the branch and starting SHA in `execution.json`, and refuses
   `workitem_required` if no WorkItem exists.
6. If `$ARGUMENTS` contains `--verbose`, the skill sets verbose mode.
7. Print the header, summarise the requirements found, and propose the next
   phase.

Read `.claude/skills/sdle/SKILL.md` and follow it to execute the phase.
