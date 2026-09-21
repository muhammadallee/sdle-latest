# Getting started

This is the one end-to-end setup guide. It takes you from a machine with the prerequisites to the first `start workflow` in Claude Code, and says what you should see at each step. Nothing else in this repository is a second setup recipe.

**What you are setting up.** SDLE is a set of files that lives *inside your application repository* (the "target project") and runs there under Claude Code. The downloaded SDLE source and your target project are two different directories: you copy files from the first into the second. Everything below runs in the **target project root** unless a step says otherwise.

**What was verified, and where.** The Bash blocks of sections 1 to 8 were replayed, unedited apart from the two path variables, into an empty directory on Windows 10 in Git Bash (Python 3.13, Git 2.46, uv 0.9.16, Claude Code 2.1.278). They ran to completion, the resulting tree equals the inventory in section 7, and the readiness checks gave the results described. The failure and location cases named in sections 3 and 13 were each tested: missing or empty `requirements/`, missing Spec Kit skills, the engine launched from a subdirectory, and a target nested in another repository without its own `.git`. The hook smoke check in section 10 was observed in real headless Claude Code sessions. The PowerShell 7 forms of sections 1, 5 and 6 (copying the files, merging the hook registrations into an existing `.claude/settings.json` and running that merge a second time, the two `.gitignore` lines, the sample requirements) and the `sdle.ps1` commands of section 8 were run in a disposable target on the same machine. **Not run:** Windows PowerShell 5.1, the PowerShell form of the Spec Kit installer (`--script ps`), Linux, macOS, the interactive `/hooks` listing, and a full live `start workflow` conversation; section 11 is described from the prompt files and from a scripted run of the engine's start-up calls.

## 1. Choose the target project

Pick the directory where your application lives (or will live). This guide uses a disposable one called `todo-app`; substitute your own path. A directory that already holds code and Claude settings is fine: the steps below only add files, and the settings step merges instead of overwriting.

```bash
# Set once. SDLE_SRC is where you downloaded or cloned SDLE.
SDLE_SRC=~/src/sdle-latest          # your checkout of the SDLE source
TARGET=~/work/todo-app              # your application repository
mkdir -p "$TARGET" && cd "$TARGET"  # every command below runs here
```

```powershell
$SDLE_SRC = "$HOME\src\sdle-latest"
$TARGET   = "$HOME\work\todo-app"
New-Item -ItemType Directory -Force $TARGET | Out-Null; Set-Location $TARGET
```

**The target must be its own Git repository.** SDLE finds the project root by walking up from the directory Claude Code was launched in, stopping at the first directory that has a `.git` (or a `workitems/index.md`). A target with no `.git` of its own, inside some other repository, resolves to *that* repository's root.

## 2. Check the prerequisites

| Tool | Needed for | Check |
|---|---|---|
| Python 3.11 or newer (tested on 3.11 and 3.13) | the engine (`scripts/sdle.py`) | `$PY --version`, with `PY` set as below |
| Git | project root, branch and starting-commit evidence, the implementation diff | `git --version` |
| `uv` | running the pinned Spec Kit installer with `uvx` | `uv --version` (install: <https://docs.astral.sh/uv/>) |
| Claude Code, installed **and signed in** | running the workflow | `claude --version`, then start it once and sign in if asked |
| a POSIX `sh` | the guard hooks (`run-hook.sh`) | `sh -c 'echo ok'` (on Windows this comes with Git for Windows) |

Name the interpreter once. The launchers find Python themselves; this variable is only for the one Python snippet in section 5:

```bash
PY=$(command -v python3 || command -v python || echo "py -3")   # Windows Git Bash usually has `python`; the py launcher is `py -3`
$PY --version                                                     # must be 3.11 or newer
```

Git identity is not required to start a workflow. It is needed for the commits in this guide:

```bash
git config --global user.name  >/dev/null || echo "set: git config --global user.name 'Your Name'"
git config --global user.email >/dev/null || echo "set: git config --global user.email you@example.com"
```

## 3. Prepare the application repository

```bash
git init                       # skip if TARGET is already a Git repository
git rev-parse --show-toplevel  # must print TARGET itself
```

An **initial commit is not required** to start: `init` succeeds on a repository with no commit. It is what lets SDLE record the branch and the starting commit in the WorkItem's `execution.json` (a repository with no commit records both as `null`), and the implementation phase measures its diff from that pinned commit. Make it at the end of section 8, so it contains everything installed, and before you say `start workflow`.

## 4. Install the Spec Kit integration

SDLE is verified against **Spec Kit v1.0.6**. Do not use a different version or a locally installed `specify`.

```bash
# Bash
uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script sh
```

```powershell
# PowerShell
uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify init --here --force --non-interactive --integration claude --script ps
```

This adds the `.specify/` tree (scripts, templates, memory, manifests) and the `speckit-*` skills under `.claude/skills/`. It does not touch `.claude/settings.json`, `CLAUDE.md` or `.gitignore`. The exact file list is Spec Kit's and can vary with its version; confirm the parts SDLE depends on:

```bash
test -f .claude/skills/speckit-constitution/SKILL.md && echo "spec kit skills: ok"
test -d .specify/scripts/bash && echo "spec kit scripts: ok"
```

Spec Kit ends its output with a note suggesting you add `.claude/` to `.gitignore`. Do not: SDLE's skill, commands, agents and hooks live there and must be shared with everyone who runs the workflow.

You never type a Spec Kit command; SDLE drives it. If your project already has a Spec Kit installation, check its version with `specify version` before relying on it; SDLE never upgrades one.

## 5. Install the SDLE files

Copy exactly these paths from the SDLE source. `cp -a` keeps the executable bit that the launchers need on Linux and macOS.

```bash
mkdir -p scripts .claude/skills .claude/commands .claude/agents .claude/hooks
cp -a "$SDLE_SRC"/scripts/sdle.py "$SDLE_SRC"/scripts/sdle.sh "$SDLE_SRC"/scripts/sdle.ps1 scripts/
cp -a "$SDLE_SRC"/.claude/skills/sdle .claude/skills/
cp -a "$SDLE_SRC"/.claude/commands/. .claude/commands/
cp -a "$SDLE_SRC"/.claude/agents/. .claude/agents/
cp -a "$SDLE_SRC"/.claude/hooks/hooks.py "$SDLE_SRC"/.claude/hooks/run-hook.sh .claude/hooks/
chmod +x scripts/sdle.sh .claude/hooks/run-hook.sh    # harmless if already set
```

```powershell
New-Item -ItemType Directory -Force scripts, .claude\skills, .claude\commands, .claude\agents, .claude\hooks | Out-Null
Copy-Item "$SDLE_SRC\scripts\sdle.py", "$SDLE_SRC\scripts\sdle.sh", "$SDLE_SRC\scripts\sdle.ps1" scripts\
Copy-Item -Recurse "$SDLE_SRC\.claude\skills\sdle" .claude\skills\
Copy-Item "$SDLE_SRC\.claude\commands\*" .claude\commands\
Copy-Item "$SDLE_SRC\.claude\agents\*" .claude\agents\
Copy-Item "$SDLE_SRC\.claude\hooks\hooks.py", "$SDLE_SRC\.claude\hooks\run-hook.sh" .claude\hooks\
```

The hooks run through `sh` on every platform, so a Windows machine needs Git for Windows even if you use PowerShell for everything else.

**Register the hooks.** `.claude/settings.json` in the SDLE source holds the hook registrations. If your project has no `.claude/settings.json`, copy it:

```bash
test -f .claude/settings.json || cp "$SDLE_SRC"/.claude/settings.json .claude/settings.json
```

If it already exists, merge the SDLE entries into it without touching anything else:

```bash
$PY - "$SDLE_SRC" <<'EOF'
import json, sys
src = json.load(open(sys.argv[1] + "/.claude/settings.json"))
dst = json.load(open(".claude/settings.json"))
for event, entries in src["hooks"].items():
    have = dst.setdefault("hooks", {}).setdefault(event, [])
    have.extend(e for e in entries if e not in have)
json.dump(dst, open(".claude/settings.json", "w"), indent=2)
EOF
```

In PowerShell, the same two steps (the merge runs the same Python, so it needs Python 3.11 or newer as `py -3`, or `python` if you have no `py` launcher):

```powershell
if (-not (Test-Path .claude\settings.json)) {
    Copy-Item "$SDLE_SRC\.claude\settings.json" .claude\settings.json
} else {
@'
import json, sys
src = json.load(open(sys.argv[1] + "/.claude/settings.json"))
dst = json.load(open(".claude/settings.json"))
for event, entries in src["hooks"].items():
    have = dst.setdefault("hooks", {}).setdefault(event, [])
    have.extend(e for e in entries if e not in have)
json.dump(dst, open(".claude/settings.json", "w"), indent=2)
'@ | py -3 - $SDLE_SRC
}
```

Running the merge again changes nothing: an entry that is already there is not added twice.

**Never copy** `.claude/settings.local.json` (it is per-developer and is not part of the product), the SDLE `docs/`, `tests/`, `.github/`, `scripts/README.md`, or the SDLE repository's own `.sdle/` directory.

**Ignore three developer-local files.** SDLE writes a per-session lock and a per-developer "active WorkItem" file under `workitems/`; everything else it writes there is meant to be committed. The third is Claude Code's own per-developer settings file, `.claude/settings.local.json`, which is not part of SDLE and must never be shared. Add these to your `.gitignore`:

```bash
printf 'workitems/*/.sdle/lock\nworkitems/.active-context.json\n.claude/settings.local.json\n' >> .gitignore
```

```powershell
Add-Content .gitignore "workitems/*/.sdle/lock", "workitems/.active-context.json", ".claude/settings.local.json"
```

## 6. Create your requirements

`requirements/` is your input; SDLE reads it as data and never edits it. `init` and `preflight` need at least one file there; whether the requirements are *good enough* is judged later by twelve structured checks that all block (scope, acceptance criteria, constraints and so on), so write a real document, not a placeholder. This sample is complete enough to pass them:

```bash
mkdir -p requirements
cp "$SDLE_SRC"/requirements/todo-api.md requirements/
```

```powershell
New-Item -ItemType Directory -Force requirements | Out-Null
Copy-Item "$SDLE_SRC\requirements\todo-api.md" requirements\
```

The sample is a small REST API for personal todo items. This is its full text, identical to `requirements/todo-api.md` in the SDLE source (a check keeps the two equal):

<details>
<summary>The sample requirements, in full</summary>

````markdown
# Todo List REST API

A small REST API for managing personal todo items. This document is the ground
truth input for the SDLE workflow, and the sample requirements used throughout
the SDLE documentation.

## Purpose

Let a single user create, read, update, complete and delete todo items over
HTTP, with enough structure to exercise validation, filtering and persistence
without becoming a large system.

## Scope

In scope:

- CRUD over todo items
- Filtering the list by completion state
- A shortcut endpoint for marking an item complete
- Input validation with a consistent error format
- Persistence to a relational store

Out of scope:

- Authentication, authorisation and multi-user accounts
- Sharing, collaboration or assignment
- Attachments, comments and reminders
- Rate limiting and quotas

## Data Model

A **Todo** has:

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Server-assigned, immutable |
| `title` | string | Required, 1–200 characters, trimmed |
| `notes` | string | Optional, up to 2000 characters |
| `completed` | boolean | Defaults to `false` |
| `due_date` | date | Optional, ISO-8601 (`YYYY-MM-DD`) |
| `created_at` | timestamp | Server-assigned, UTC, immutable |
| `updated_at` | timestamp | Server-assigned, UTC, updated on every write |

## Endpoints

| Method | Path | Behaviour |
|---|---|---|
| `POST` | `/todos` | Create a todo. Returns `201` and the created item. |
| `GET` | `/todos` | List todos. Supports `?completed=true\|false`. |
| `GET` | `/todos/{id}` | Fetch one todo. `404` if absent. |
| `PATCH` | `/todos/{id}` | Partial update. `404` if absent. |
| `POST` | `/todos/{id}/complete` | Mark complete. Idempotent. |
| `DELETE` | `/todos/{id}` | Delete. Returns `204`. `404` if absent. |

## Behavioural Requirements

1. Completed todos are **included** in the default list view; `?completed=false`
   is opt-in filtering, not the default.
2. The list is ordered by `created_at` descending.
3. `POST /todos/{id}/complete` on an already-complete todo succeeds and changes
   nothing — completing twice is not an error.
4. `PATCH` accepts any subset of the writable fields. An empty body is a `400`.
5. `updated_at` changes only when a write actually modifies a field.

## Validation and Errors

Every failure returns the same envelope:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Human-readable summary",
    "details": [ { "field": "title", "issue": "must be 1-200 characters" } ]
  }
}
```

- `400` — malformed body or failed validation
- `404` — no such todo
- `422` — well-formed but semantically invalid (e.g. `due_date` in the past)
- `500` — unexpected failure; never leaks a stack trace to the client

Validation happens at the boundary. No unvalidated user data reaches the
persistence layer.

## Non-Functional Constraints

- Single-process deployment is acceptable; no clustering required.
- A read of the list must return within 200 ms for 10,000 stored items.
- All timestamps are stored and returned in UTC.
- No secrets in source. Configuration comes from the environment.
- Every endpoint has automated test coverage, including its failure modes.

## Acceptance

The feature is done when all six endpoints behave as described above, the error
envelope is consistent across every failure mode, the validation rules are
enforced, and the automated test suite passes.
````

</details>

Optional inputs, when you want them:

| Path | Purpose | Needed when |
|---|---|---|
| `requirements/*.md` (more files) | constraints, tech stack, limits | you have them |
| `guidance/<phase>.md` | steering for one phase (for example `guidance/plan.md`), read as data | you want to steer a phase |
| `.sdle/policies/governance-policy.json` | a repository policy that may only *tighten* the built-in one | you need stricter rules |

## 7. The layout before you launch Claude Code

Every **required** path in this table exists at this point; the optional rows exist only if you made them, and `workitems/` does not exist yet: it is created by `start workflow`, never by hand. The three install directories are copied whole. In the current SDLE source that is nine command files, four `sdle-*` agent files, and in the skill `SKILL.md`, five files under `modules/` and `templates/state.json`; `tests/test_units_install_contract.py` fails if a tracked file under `.claude/` or a launcher is not covered by this table, and pins those counts.

| Path | Purpose | Status | Created by | Check |
|---|---|---|---|---|
| `.git/` | project root and Git evidence | required | `git init` | `git rev-parse --show-toplevel` |
| `requirements/<your files>` | your ground truth; each WorkItem binds the ones it is about | required | you | `ls requirements` |
| `scripts/sdle.py`, `sdle.sh`, `sdle.ps1` | the engine and its launchers | required | section 5 | `sh scripts/sdle.sh constants` |
| `.claude/skills/sdle/` (`SKILL.md`, `modules/`, `templates/state.json`) | the orchestrator prompts | required | section 5 | file exists |
| `.claude/commands/` | the `/sdle-*` slash commands | required | section 5 | files exist |
| `.claude/agents/sdle-*.md` | the read-only review subagents | required | section 5 | files exist |
| `.claude/hooks/hooks.py`, `run-hook.sh` | the guard hooks | required | section 5 | direct hook check below |
| `.claude/settings.json` | the hook registrations (merged) | required | section 5 | `$PY -c "import json;json.load(open('.claude/settings.json'))"` |
| `.specify/`, `.claude/skills/speckit-*` | Spec Kit scaffolding and skills | required | section 4 | skills check in section 4 |
| `.gitignore` (three lines) | keep local files out of Git | recommended | section 5 | `git check-ignore workitems/.active-context.json .claude/settings.local.json` |
| `guidance/` | per-phase steering | optional | you | |
| `.sdle/config.json` and its folders | repository configuration | optional | `sdle.sh config init` | |
| `workitems/`, `workitems/<id>/.sdle/` | the WorkItem registry and its runtime | **absent** | `start workflow` | |

## 8. Readiness check (before launching Claude Code)

These run in a terminal and prove the files, the interpreter and the paths. They cannot prove that Claude Code loaded the hooks; that is section 10.

```bash
sh scripts/sdle.sh constants     # "ok": true, and the five flows are listed
sh scripts/sdle.sh validate      # "errors": 0; ONE warning, active_workitem_unresolved, is expected
sh scripts/sdle.sh preflight     # refuses "workitem_required": expected, see below
printf '{"tool_name":"Write","tool_input":{"file_path":"%s/workitems/x"}}' "$PWD" \
  | CLAUDE_PROJECT_DIR="$PWD" sh .claude/hooks/run-hook.sh write-fence
                                 # prints a JSON decision containing "permissionDecision": "deny"
```

`preflight` is different from the checks above: like every runtime command it first needs a WorkItem, and a fresh project has none, so it correctly answers `workitem_required`. `start workflow` creates the WorkItem and *then* runs `preflight`, which checks Spec Kit, its skills and your requirements. Do not create runtime files by hand to make it pass.

From PowerShell, the first three run as `.\scripts\sdle.ps1 constants`, `validate` and `preflight` with the same results. The hook check needs `sh`, which Claude Code finds on its own but a PowerShell prompt may not have on its path: run that one command from Git Bash, which Git for Windows provides.

If `constants` reports `no_interpreter`, Python 3.11 or newer is not on the path. Now make the initial commit:

```bash
git add -A && git commit -m "Add Spec Kit, SDLE and requirements"
```

## 9. Launch Claude Code from the project root

```bash
cd "$TARGET"     # the directory that contains .claude/settings.json
claude
```

**Launch from the project root, not from a subdirectory.** Claude Code loads project hooks only from the directory it was started in. Started from `workitems/` or from any subfolder, it loads *no* SDLE hooks at all and shows no error, so the guards are silently off. The engine's own checks still apply, but launch from the root.

The entry point is the phrase **`start workflow`**, typed *in the Claude Code conversation*, not in the shell. The slash command `/sdle-start` is the same entry: the skill routes `start workflow` and `begin` to that command, and both run the same steps. Use one or the other; you do not need both.

## 10. Check that the hooks fire (before `start workflow`)

In the Claude Code conversation:

1. Run `/hooks` and confirm the SDLE hooks are listed from **Project Settings**. *(Interactive; not run by this guide's replay.)*
2. Ask: **"Use the Write tool to create the file `workitems/.sdle-hook-probe`."**

Expected: the write is refused with a message beginning **`SDLE write fence:`**, and the file does not exist. Claude Code labels even a deliberate refusal `PreToolUse:Write hook error: SDLE write fence: …`, so do not read the words "hook error" as a failure: look for the SDLE text and for the absent file. Verified this way in a real Claude Code 2.1.278 session on Windows.

If the file **is** created, the hooks did not load. The usual causes are the wrong launch directory (section 9), a missing `sh` (section 2), or a missing `run-hook.sh` (section 5). See the troubleshooting table below.

## 11. The first `start workflow`

Say `start workflow` (or `/sdle-start`). This is the sequence the prompt files instruct, in this order; the engine calls in it were exercised against a fresh target with a scripted stand-in for the model's judgement:

1. SDLE checks for an existing WorkItem. A brand-new project has none.
2. **You** are asked for a WorkItem name (`WorkItem name?`). Type one, or say `auto generate` to have SDLE infer a short name. SDLE runs `workitem create`, which writes the identity and a registry row.
3. SDLE binds the WorkItem's requirement documents — the ones *this* piece of work is about — with `requirements bind`. A document you do not bind is inert: it governs nothing and can never stale this WorkItem's assessment, which is how two WorkItems share one `requirements/` directory without disturbing each other. Bind several with repeated `--source`, or take everything currently there with `--all-current`; either way the record is an exact list of files, never a live folder.
4. SDLE runs `preflight` for that WorkItem. It stops, with the exact message, if Spec Kit or its skills are missing, if nothing was bound (`requirements_unbound`), or if a bound document is not there (`requirements_source_missing`). Nothing is initialised on a refusal.
5. SDLE scans each **bound** document for text that tries to instruct it (the file is treated as data), and lists any `guidance/` files.
6. SDLE writes a structured governance proposal (twelve requirements-quality answers, a WorkItem type and flow, risk signals) and runs `governance assess`. The engine scores it deterministically; the model cannot lower a floor. A failed blocking check stops the workflow until you fix the requirements. The assessment records which documents it was made from, so editing one of them later is `governance_stale` and editing an unrelated one is not.
7. SDLE runs `init`, which binds the WorkItem's flow once and creates its runtime, then shows the header and summarises your requirements. The project's name comes from the heading of the binding's primary document.
8. It proposes the first phase. Under `GREENFIELD` that is generating the project constitution, followed by the first human gate.

**Which documents are bound is a decision, not a detail.** Leaving one out means the assessment was not made from it, so a constraint you meant to apply silently did not. `sdle.sh requirements show` reports the binding at any time, and SDLE displays it before the governance proposal for that reason.

**What SDLE does for you, and what is yours.** SDLE creates the identity, runs the checks and writes all state. The name, which documents are bound, the fixes to your requirements, and every approval are yours. At each gate SDLE shows the artifact **in the conversation**; you answer `approve`, or `reject` with feedback. Nothing is approved for you, and an assistant must not type `approve` on your behalf.

**Check where you are** at any time: say `status` (or `/sdle-status`). To pick up after an interruption, say `continue` (or `/sdle-continue`).

## 12. What exists after the first start

After section 6 (verified on a fresh target):

| Path | Purpose | Committed? |
|---|---|---|
| `workitems/index.md` | append-only WorkItem registry | yes |
| `workitems/<id>/workitem.json` | the WorkItem's identity | yes |
| `workitems/<id>/.sdle/state.json` | lifecycle state | yes |
| `workitems/<id>/.sdle/audit.md` | append-only, hash-chained ledger | yes |
| `workitems/<id>/.sdle/execution.json` | execution id, branch and starting commit | yes |
| `workitems/<id>/.sdle/governance.json` and `evidence/governance-*.json` | the assessment and its evidence | yes |
| `workitems/<id>/.sdle/lock` | per-session lock | no (ignored) |
| `workitems/.active-context.json` | which WorkItem this directory is driving | no (ignored) |

The specification, plan and task files appear only when their phases run, under `workitems/<id>/specs/<feature>/`; `design/`, `reviews/` and `clarifications/` at the repository root appear when their phases produce output (they are shared by every WorkItem in the repository). `.sdle/baseline.json` appears only when a `GREENFIELD` or `BROWNFIELD_DISCOVERY` WorkItem completes. `.sdle/config.json` exists only if you run `sdle.sh config init`.

## 13. If something goes wrong

| What you see | Cause | What to do |
|---|---|---|
| The probe write in section 10 succeeds | Hooks not loaded: launched from a subdirectory, no `sh`, or files missing | Relaunch from the project root; run the `sh -c 'echo ok'` and direct-hook checks; re-copy section 5 |
| `PreToolUse … hook error` with a Python or file message | A hook could not start | Re-run section 5; confirm `.claude/hooks/run-hook.sh` exists and `sh` resolves |
| `no_interpreter` | Python 3.11 or newer is not found | Install it, or install `uv` |
| `workitem_required` from `preflight` before `start workflow` | Normal on a fresh project | Say `start workflow`; do not create files by hand |
| `speckit_missing`, `speckit_skills_missing` | Spec Kit not installed, or a different version | Run section 4 exactly as written |
| `requirements_unbound` | The WorkItem has not declared which documents it is about | `sdle.sh requirements bind --all-current`, or name them with `--source` (section 11) |
| `requirements_source_missing` | A document the WorkItem bound is not in the repository | `sdle.sh requirements show` lists them; restore them or re-bind |
| `workitem_ambiguous` | Several WorkItems and none named | Name one: `sdle.sh --workitem <id> …`, or `sdle.sh workitem use --workitem <id>` |
| `unsupported_state_version` | A state file from another schema | Start a new WorkItem; the old one is left untouched |
| `Permission denied` running `scripts/sdle.sh` | The executable bit was lost in the copy | `chmod +x scripts/sdle.sh` |
| Commands run from the wrong place resolve the wrong project | The target is inside another repository without its own `.git` | `git init` in the target (section 3) |
| The session was interrupted | Quota, closed terminal, lost context | Relaunch from the project root and say `continue`; state is on disk |

More detail, one entry per refusal, is in [troubleshooting](troubleshooting/README.md).

## Where to go next

Pick the tutorial for the kind of work you have; each one starts from the setup above and describes only what differs.

| You have | Read |
|---|---|
| A new project | [`tutorials/greenfield.md`](tutorials/greenfield.md), or the [full tour](tutorials/greenfield-full-tour.md) |
| An existing codebase, first WorkItem | [`tutorials/brownfield-discovery.md`](tutorials/brownfield-discovery.md) |
| An existing codebase with a baseline | [`tutorials/iterative.md`](tutorials/iterative.md) |
| A bug | [`tutorials/defect-fix.md`](tutorials/defect-fix.md) |
| An urgent fix | [`tutorials/hotfix.md`](tutorials/hotfix.md) |

The exact behaviour of every command and field is in the [Reference Guide](SDLE-Reference-Guide.md).
