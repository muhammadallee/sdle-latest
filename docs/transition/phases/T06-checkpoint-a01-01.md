# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T06
**Attempt:** 01
**Milestone completed:** **M1** — the structural seam (D1 `Paths` members, `GOVERNANCE_POLICY_BUILTIN`, fail-closed `read_governance_policy`, D2 monotonicity, `governance policy`, `RUNTIME_FREE_COMMANDS += "governance"`).

## Objective currently being worked

M1 is complete and green. Next objective is **M2**: D5 quality model + D7 record/evidence writing + `governance assess` / `governance show`. New tests N7–N9, N19, N21, N22. **No existing-test edit is authorised in M2.**

## Completed since previous checkpoint

First checkpoint of the phase.

- **D1** — three new `Paths` properties: `governance_file` (`runtime/governance.json`), `reviews_file` (`runtime/reviews.json`), `governance_policy_file` (`.sdle/policies/governance-policy.json`). Different basenames on purpose, so the runtime/configuration name sets stay disjoint.
- `workitem_runtime_member_names` gained `bound.governance_file, bound.reviews_file`, so both `collect_validation_findings` leak detectors inherited them with **zero new detector code**.
- **D2/D3** — `GOVERNANCE_LEVELS`, `WORKITEM_TYPES`, `ENGINEERING_FLOWS`, `GOVERNANCE_POLICY_BUILTIN`, `GOVERNANCE_POLICY_OVERRIDABLE`, `SUPPORTED_POLICY_VERSIONS`, `_policy_malformed`, `_policy_weakens`, `_is_int`, `_str_list`, `_floor_key`, `_validate_policy_shapes`, `_merge_policy`, `_refuse_weakening`, `read_governance_policy`, `cmd_governance_policy`. Inserted as one new section between `cmd_config_show` and the `migrate-workflow` section header.
- `import copy` added (stdlib only; `sdle.py` still imports nothing outside `sys.stdlib_module_names`).
- Parser: `governance` group with the single `policy` subcommand; `"governance"` added to `RUNTIME_FREE_COMMANDS`.

### Two design points fixed during M1 that a resuming agent must not undo

1. **`read_governance_policy` distinguishes *absent* from *unusable*.** The first draft used `if not target.is_file(): return builtin`, which silently returned the built-in when a **directory** sat at the policy path. `test_an_unreadable_policy_file_refuses` caught it. It now returns the built-in only when `not target.exists() and not target.is_symlink()`, and refuses `policy_malformed` for anything present-but-not-a-regular-file. This is the fail-closed property the phase turns on — do not "simplify" it back.
2. **N23's content search must use identifier-shaped needles.** The first draft searched for every check id, which matched the ordinary English words `scope`, `ambiguity`, `constraints`, `contradictions` in **ten pre-existing files** (`README.md`, `CLAUDE.md`, the Reference Guide, `SKILL.md`, `phase-execution.md`, `security-review.md`, `sdle-start.md`, `hooks.py`, ADR-001, ADR-002). The needle set is now every risk-signal id plus only the check ids containing `_`, guarded by `test_the_policy_identifier_needles_are_not_english_words` so it cannot go vacuous. **M8's doc edits must not name any risk-signal id or any underscored check id**, or N23 will fail.

## Remaining

M2–M8 exactly as the plan's milestone table sets them out. Design decisions already pinned by M1 that M2/M3 must follow:

- Policy merge rule, stated once in `sdle.py`: **dict-valued keys merge key-by-key; list-valued keys replace wholesale.** That is what makes every one of D2's weakening shapes both expressible and refusable.
- `quality_checks` is **not** overridable (it is absent from `GOVERNANCE_POLICY_OVERRIDABLE`); an override naming it gets `policy_malformed`.
- The would-be gate map is three flat top-level keys — `required_gates_always`, `required_gates_by_risk`, `required_gates_by_type` — rather than one nested dict, so the single merge rule covers it.
- **Declared implementation detail vs the plan:** D3 writes the signature as `read_governance_policy(paths) -> dict`. It is implemented as `read_governance_policy(paths, consts) -> dict` so gate ids in an override can be validated against the *registered* gate set (`consts.phase_to_gate_key.values()`) and a phantom gate key refuses `policy_malformed`. Behaviour is a superset of the plan's; the returned dict is `{"policy", "source", "path", "sha256"}`.

## Files changed

| File | Nature |
|---|---|
| `scripts/sdle.py` | additive; plus `import copy` and one appended tuple entry pair in `workitem_runtime_member_names` |
| `tests/test_units_governance.py` | **new** (53 collected) |
| `tests/test_units_repo_config.py` | anti-contradiction rows 1, 2, 3 |
| `tests/test_units_workitem_resolution.py` | anti-contradiction row 0 |
| `docs/transition/phases/T06-checkpoint-a01-01.md` | this file |

`git diff --numstat 4a35a1c -- scripts/sdle.py` = **510 insertions, 1 deletion** (the single deletion is the `workitem_runtime_member_names` return tuple's last line, rewritten to append the two new members).
`git diff --name-status 4a35a1c -- tests/` = `M tests/test_units_repo_config.py`, `M tests/test_units_workitem_resolution.py`; `tests/test_units_governance.py` untracked (`??`). Zero `D`, zero `R`.

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`624 passed in 613.32s (0:10:13)`**; `-rsxX` produced **no** short-summary section |
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` | **0** | **`624 tests collected in 0.62s`** — collected == passed |
| `rtk proxy "python scripts/sdle.py lint-skill"` | **0** | **22 PASS / 0 FAIL**; `Parsed 19 phases, 8 gates, 15 migration rows`; `all four locations report v1.15` |

**Suite arithmetic, re-derived here:** baseline **569** + **53** (`tests/test_units_governance.py`, new) + **2** (`tests/test_units_repo_config.py` 69 → **71**, because `test_lifecycle_state_under_the_repository_boundary_is_an_error` is parametrised over the *derived* `workitem_runtime_member_names`, which grew by `governance.json` and `reviews.json`) = **624**. Every other per-file count is unchanged from the planner's table: resolution 96, workitem 57, speckit_binding 55, workitem_runtime 45, hooks 44, integration_02_to_05 42, integration_06_to_09 38, state 37, infra 28, transitions 24, lint_skill 17, cli 9, integration_01 8.

## Current failures

**None.**

## Git status / diff summary

- HEAD `4a35a1c` (plan commit). Nothing committed this phase yet.
- Working tree also carries the pre-existing, **out-of-scope** ` M .claude/settings.local.json` — not staged, not edited.
- Rollback point remains **`475795a`**.

## Unresolved decisions

None. No blocker.

## Exact resume instruction

M1 is additive and behaviour-neutral: nothing in the lifecycle reads any of it. Verify against disk, not against this text —

```
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"   # expect 624
rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider"   # expect 53 passed
```

then continue at **M2** per `docs/transition/phases/T06-plan.md`'s milestone table. M4 is the first behaviour-changing milestone; **M3 is the declared safe resume boundary**.
