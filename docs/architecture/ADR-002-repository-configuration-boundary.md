# ADR-002 — A repository-level `.sdle/` configuration boundary, and JSON for policy

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-25 |
| **Scope** | Migration phase T05 (transition contract §11). No engine version change. |

## Context

As of v1.14 every runtime fact SDLE owns lives under `workitems/<id>/.sdle/` —
state, execution identity, the audit ledger, the lock, evidence and the Gate 7
manifest. That was the right move: it made independent WorkItems genuinely
independent.

It left one thing unresolved. A repository also has facts that are **not**
about any particular WorkItem: how this repository configures SDLE, what
policies it applies, what templates its teams share, what baseline describes
the code that already exists. Those have no home. Left long enough, they end up
in the only writable place available — a WorkItem's runtime — and the isolation
that motivated the WorkItem scope quietly erodes.

The later phases of the migration make this urgent rather than tidy: risk and
gate policies, a brownfield baseline and shared flow definitions are all
repository-wide by nature. Introducing them without a boundary would mean
introducing them into WorkItem runtime state.

## Decision

**Two boundaries, distinguished by derivation rather than by string matching.**

| Boundary | Derived from | Owns |
|---|---|---|
| `<repo>/.sdle/` | `project_root` alone | global configuration, policy definitions, shared templates, the future baseline, implementation-transition metadata |
| `<repo>/workitems/<id>/.sdle/` | the bound WorkItem | lifecycle state, execution identity, audit, evidence, WorkItem-specific manifests |

The two directories share a name, which is exactly why the split is expressed
as **derivation in `Paths`** and not as a path prefix test. `Paths.config_root`,
`config_file`, `policies_dir`, `shared_templates_dir`, `baseline_file` and
`implementation_state_dir` reference `project_root` and nothing else; they never
mention `workitem`, `workitem_root` or `runtime`. Rebinding the WorkItem moves
every runtime member and none of these. That property is asserted directly, both
at value level and at source level, rather than described.

**The split is enforced, not documented.** `sdle validate` carries a
bidirectional leak detector: a WorkItem runtime member appearing under the
repository boundary is `lifecycle_state_in_repository_config`, and a repository
configuration member appearing under a WorkItem is `repository_config_in_workitem`.
Both member-name sets are *derived* from `Paths`, so a later phase that adds a
member on either side inherits the check without editing it.

**Two commands, both runtime-free.** `sdle config init` creates the boundary and
never overwrites; `sdle config show` reports the effective configuration and
creates nothing. Neither binds a WorkItem — repository configuration that could
only be read once a WorkItem resolved would not be repository configuration.

**One predicate.** `repo_config_findings()` is the single implementation of "is
this repository's configuration sound". `config show` refuses on its errors and
`validate` reports them; they cannot disagree, because there is nothing to
disagree with.

**No lifecycle rule moved.** The 18-phase sequence, the gates, artifact
ownership, approval requirements, rate limits and the progress map stay exactly
where they were. Nothing in the lifecycle reads `config.json`. `configVersion` is
a separate namespace from `workflow_version`: it is not a state field, it gets no
migration row, and the engine version is unchanged by this ADR.

### Policy format: JSON

The requirements that motivate later phases describe YAML policy files. The
decision here is **JSON**, and the reason, as the maintainer gave it, is:

> preserve the zero-dependency stdlib-only core exactly as it is today, so
> `sdle.py` stays runnable anywhere Python 3.11+ exists with no install step.

`scripts/sdle.py` imports fourteen modules and every one is in the standard
library. There is no `pyproject.toml`, no `setup.py`, no `requirements.txt`. The
install story is "copy the files"; a parser dependency would end that.

The decision is made **operative rather than commemorative**: `config.json`
declares `policyFormat`, `"json"` is the only supported value, and any other
value — including `"yaml"` — is refused with a message naming the requirement
that a dependency be explicitly accepted first.

### Alternatives rejected

**YAML with a small dependency (`PyYAML`, `ruamel.yaml`).** Better for
hand-authored policy files, which is a real advantage and the reason the
requirements reach for it. Rejected here because nothing hand-authors a policy
yet — no executable policy exists at all — so the cost would be paid before the
benefit. A later phase may revisit this with actual authoring evidence and an
explicit dependency acceptance; the refusal message points at exactly that.

**A home-grown YAML subset parser.** Forbidden outright by the transition
contract, and rightly: a partial YAML parser is a source of silent
misinterpretation in the component whose entire job is not misinterpreting
machine-owned state. The same reasoning that rejected PowerShell's JSON
semantics in ADR-001 applies unchanged.

**Putting repository configuration in `state.json`.** It is the file that
already exists and is already written atomically. Rejected: it is WorkItem-scoped
by construction, so every WorkItem would carry its own copy of a repository-wide
fact — one fact, many homes, which is the invariant this project is built to
avoid. It would also drag repository configuration into the migration chain and
the audit hash.

**Extending the write fence to `<repo>/.sdle/`.** Deferred, deliberately. At this
point the boundary holds nothing machine-owned: `config.json` is human-authorable,
`policies/` is empty, no baseline exists, and nothing in the audit chain or any
drift comparison lives there. A hand-edited `config.json` is detected — `config
show` refuses and `validate` reports it — and cannot change lifecycle behaviour,
because nothing lifecycle reads it. The first phase that puts executable policy
under `policies/` is the phase that must fence it, and it inherits a known
hazard: the hook's `in_dir(path, name)` matches `/{name}/` **anywhere** in a
path, so a bare `".sdle"` entry would also match `workitems/<id>/.sdle/` and
shadow the existing WorkItem reason text. A fence for the repository boundary
must anchor to the start of the repository-relative path.

**Adding `.sdle/` to `SDLE_OWNED_PREFIXES`.** Rejected. That tuple hides paths
SDLE itself writes *during a run* from the implement-preflight dirty-tree list.
Nothing writes the repository boundary mid-run, and the boundary is versioned
engineering evidence, so an uncommitted change to it *should* trip the guard
exactly as an uncommitted source change does. That direction fails closed. The
contrast with `workitems/`, which was added to that tuple, is the intended one:
`workitems/` holds runtime state SDLE writes mid-run.

## Consequences

**Gained.** A place for repository-wide configuration that is structurally
incapable of being confused with WorkItem runtime state, with the confusion
detected in both directions by `validate` rather than avoided by convention. A
recorded, enforced answer to the policy-format question, made before any
executable policy exists rather than after.

**Paid.** A second directory named `.sdle`, which is a genuine readability cost
and a genuine hazard for any future code that reasons about paths as strings.
The mitigation is that no engine code does: the boundary is a derivation, and a
closed set of five functions is the only code allowed to reach it.

**Deliberately empty.** `policies/` and `templates/` carry only a `.gitkeep`, and
`implementation-state/` is an empty slot: the contract names it in a diagram and
defines no schema, producer or consumer for it, so inventing one would be
speculation. `baseline.json` is *named* by `Paths.baseline_file` and policed by
`validate`, but no code writes it — the phase that owns the baseline schema
creates the file.

**Versioned, with no `.gitignore` change.** Global configuration and shared
templates are team-shared engineering evidence, not ephemera. Nothing under the
boundary was ignored to begin with, so the versioning decision cost zero diff.
