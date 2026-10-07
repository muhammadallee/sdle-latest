# AS-30 — what was and was not done against real Spec Kit v1.0.6

**AS-30 as written was NOT completed.** It asks for one real run in a scratch repository with Spec Kit v1.0.6: a small SRS becomes a package, the SA approves it, and one work item goes through the loop to `gate_implement`. Every model-driven phase of that run (specify, plan, tasks, analyze, implement, converge, the independent reviews) is performed by a Claude Code session invoking the Spec Kit skills with the human approving at the gates. That cannot be done from inside this unattended session, and nothing below pretends otherwise. It remains a **remaining human step**.

What was done instead, all against the real v1.0.6, and labelled as exactly that.

## 1. The real command templates were read (G02, G03, G04, G06)

Fetched from `github/spec-kit@v1.0.6` `templates/commands/` on 2026-10-06 and read; the files are not committed.

| Brief claim | Result against the real v1.0.6 text |
|---|---|
| G02: v1.0.6 ships a `converge` command SDLE never invoked | **Confirmed.** `specify init` installs `speckit-converge` among ten skills (analyze, checklist, clarify, constitution, converge, implement, plan, specify, tasks, taskstoissues). SDLE now names it in `SKILL.md`'s invocation table, for the loop only. |
| G03: converge treats spec, plan, tasks (and the constitution) as the sole source of intent, and its only write is appending `## Phase N: Convergence` to tasks.md | **Confirmed.** `converge.md`: "spec, plan and tasks as the **sole source of intent** (with the constitution as governing constraints)", "no git, no branch comparison, no history", "**APPEND-ONLY, NEVER REWRITE**: the command's **only** write is appending a new `## Phase N: Convergence` section to `tasks.md`", with appended items shaped `- [ ] T042 <description> per <source-ref> (<gap-type>)`. `_tasks_delta` accepts exactly that shape: whole convergence sections appended, nothing else. |
| G04: `analyze` is strictly read-only | **Confirmed.** `analyze.md`: "**STRICTLY READ-ONLY**: Do **not** modify any files", "**NEVER modify files**". This is what justified removing the post-analyze `drift rebaseline`. |
| G06: v1.0.6 `implement` marks tasks `[X]` | **Not found in the template.** `implement.md` contains no instruction to tick tasks in tasks.md (a search for tasks.md, checked, `[x]` and mark returned nothing). Whether a Claude session ticks them while implementing is behaviour of the session, not of the template. The loop accepts ticks either way (`tasks reconcile`), so nothing breaks, but the brief's premise is **unconfirmed**, and the dry run and ADR describe ticking as something the loop *accepts*, not something Spec Kit *does*. |

## 2. The engine was run against a real v1.0.6 installation

In a scratch repository, `uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script sh` (the command the engine documents) was run, SDLE's files were installed beside it, a WorkItem was created and bound, and:

- `sdle preflight` reported `speckit_present: true`, `skill_prefix: "speckit-"`, `problems: []`;
- `sdle feature capabilities` reported `SPECIFY_INIT_DIR` and `SPECIFY_FEATURE_DIRECTORY` supported, from `.specify/scripts/bash/common.sh`.

That is the engine's detection working against the real tree, nothing more.

## 3. What would still have to be shown by a human run

- the orchestrator invoking `speckit-specify` and `speckit-tasks` with the new "cite the source ids" argument, and Spec Kit actually honouring it (unverified);
- `speckit-converge` appending a section that `tasks reconcile` accepts, and real `speckit-implement` interacting with the task list as the loop expects;
- whether the project hooks were active in the scratch session (Claude Code loads hooks only from its launch directory; any run record must say which).

The engine-side behaviour of every step is covered by `tests/test_units_loop.py`, `test_units_trace.py` and the DR-23 to DR-25 transcripts, **with generation simulated**. Those are tests of the engine and are labelled as such.
