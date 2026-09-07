# Spec Kit integration

**Applies to:** SDLE v1.17
**Authority:** `scripts/sdle.py` (`feature` subcommands,
`detect_speckit_capabilities`). See also
`docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md`.

---

## 1. Opacity is a product rule, not a preference

SDLE wraps GitHub Spec Kit. The user interacts only with SDLE.

> **`speckit-*` names and `/speckit.*` commands are never shown to the user**
> (verbose mode excepted).

This is one of the engine's non-negotiable invariants. It is not about hiding a
dependency; it is about a single operating surface. A user who is shown two
command vocabularies has to know which one owns which decision, and SDLE owns
all of them.

---

## 2. Capability detection — refuse, never assume

Spec Kit is not version-pinned. SDLE therefore **detects** what the installed
copy supports rather than assuming it:

| Command | Behaviour |
|---|---|
| `feature capabilities` | Reports what is installed. A **diagnostic: it never refuses**, even when Spec Kit is absent |
| `feature bind` | Re-asserts this WorkItem's Spec Kit context. **Pure** — writes nothing |
| `feature resolve` | Identifies (and where necessary adopts) the feature directory |

Two refusals, both at `feature bind`, both exit 1:

- **`speckit_missing`** — no Spec Kit in the project. Fails closed at the first
  Spec Kit-owned phase, and writes nothing.
- **`speckit_capability_missing`** — Spec Kit is present but does not support
  something SDLE needs to scope a feature to a WorkItem. The refusal names what
  is missing and where it probed. **SDLE will not guess.**

The split matters: the *diagnostic* always answers, the *action* refuses. That
is the same shape as `workitem resolve` versus WorkItem binding — reporting and
deciding are different jobs.

---

## 3. Where a feature directory lives

Since v1.15, the active WorkItem's feature directory is
`workitems/<id>/specs/<feature-id>/`, not the repository-global
`.specify/specs/<feature-id>/`. That is what makes it impossible for two
WorkItems in one repository to be handed each other's specification.

Repository-wide Spec Kit scaffolding — `.specify/`, including
`memory/constitution.md` — stays where it is. It is genuinely repository-wide.

`workitems/<id>/specs/` is the **one carve-out in the write fence**: those
artifacts are Spec Kit's own, SDLE neither writes nor governs them, so fencing
them would block legitimate work. Nothing else under `workitems/` is exempt —
the registry, `workitem.json` and the whole `<id>/.sdle/` runtime stay denied.
Since v1.17 the carve-out is matched against a **normalised** path, so
`workitems/<id>/specs/../.sdle/state.json` no longer slips through it.

---

## 4. Resolution tiers — precedence, then fail closed

`feature resolve` collects candidates in a **fixed tier order** and uses the
first tier that yields anything:

1. `workitems/<id>/specs/*` — already contained;
2. `<project-root>/specs/*` — where Spec Kit 0.15.0 actually creates a feature,
   since it hardcodes `repo_root/specs` for creation;
3. `.specify/specs/*` — where pre-v1.15 SDLE assumed it was.

That is **precedence, not a tie-break between peers**. No tier ever reaches into
`workitems/<other-id>/`.

### Inside the chosen tier: more than one candidate refuses

Before v1.17, the newest directory by mtime won, and only an exact timestamp tie
refused. That meant two WorkItems both standing at the specification phase could
cross-adopt through the shared repository-global `specs/` staging area — a
silent wrong pick.

Since v1.17, **more than one candidate refuses `feature_ambiguous`** and lists
them. Recency is not evidence of ownership.

There is no override flag, because none is needed: tier 1 is
`workitems/<id>/specs/`, so *moving* the directory this WorkItem owns into its
own tier resolves the ambiguity by precedence — deterministically, without SDLE
guessing. The refusal names that remedy. `feature bind` remains the explicit
escape hatch once the binding is recorded.

Zero candidates refuses `feature_unresolved`, naming every tier it searched.

---

## 5. Environment handed to Spec Kit

`feature bind` emits the environment rather than exporting it globally:

```text
SPECIFY_INIT_DIR           the project root
SPECIFY_FEATURE_DIRECTORY  this WorkItem's feature directory
SPECIFY_FEATURE            this WorkItem's feature id
```

Spec Kit keeps exactly **one** repository-global feature slot, so a stale slot
could otherwise hand this WorkItem another's directory. Re-asserting the
environment before every invocation — together with the gate precondition, which
a hook cannot bypass — is what closes that. `feature` is deliberately not a
runtime-free command, so WorkItem resolution structurally precedes anything
Spec Kit-related.

---

## 6. What SDLE does not do

- It does not run Spec Kit in tests. Generation is simulated by writing an
  artifact over the size floor, so the suite never depends on an external tool.
- It does not repair, upgrade or reconfigure a Spec Kit installation.
- It does not approve a Spec Kit artifact belonging to another WorkItem — the
  gate refuses.
