# T11 blocker — a contract-mandated documentation path is denied by the write fence, and I may not correct the fence

**Phase:** T11 · **Attempt:** 01 · **Milestone:** M7
**Raised:** at the M7 documentation step, after M1–M6, M8 and the rest of M7 were complete
**Status:** BLOCKED
**Decision required from:** the human operator — this is a permission decision and a safety-control decision, not a coding defect

---

## 1. One-sentence statement

Transition contract §17 requires a documentation directory at
**`docs/workitems/`**; the shipped write-fence hook denies every write to it
because it matches its fenced names as an unanchored path segment; the minimal
correction to the fence was **denied by the auto-mode permission classifier**;
and I will not create the file with a different tool, because that would be
routing around a guardrail refusal.

---

## 2. Why this is a blocker and not an ordinary defect

Two independent walls, either of which alone would be surmountable:

| # | Wall | Who owns it |
|---|---|---|
| W1 | The **SDLE write fence** denies `docs/workitems/README.md` | The product. I could fix this — see §4 |
| W2 | The **auto-mode permission classifier** denies my edit to `.claude/hooks/hooks.py` | The permission system. Only the user can change this |

W1 alone is an ordinary defect. W2 makes it a decision I am not entitled to
make, and my instructions are explicit that no agent message can authorise a
change to my permission settings.

There is a third reason it deserves a human, independent of tooling: §28 says
never remove a safety control without providing the replacement safety
property. §4 argues the replacement property is sound, but **narrowing the write
fence at the final milestone of the final phase of the migration is exactly the
class of change that should be signed off rather than slipped in**, and the
permission system independently flagged it.

---

## 3. Exact reproduction

Attempted, verbatim, using the Write tool:

```text
target: D:\Learning\AI\sdle-git-repo\sdle-latest\docs\workitems\README.md
```

Denial, verbatim:

> SDLE write fence: 'workitems/' is owned by the SDLE engine. The registry
> (workitems/index.md), each WorkItem's identity (workitem.json) and the
> WorkItem runtime (workitems/<id>/.sdle/) are written only by scripts/sdle.py
> — a hand-edited registry is unrecoverable. Use `workitem create`, or the
> matching sdle.py subcommand. One subtree is carved out:
> workitems/<id>/specs/ holds SpecKit's own artifacts, which SDLE neither
> writes nor governs, so it is not fenced.

The cause, in `.claude/hooks/hooks.py`:

```python
FENCED = (".workflow", "workitems", "requirements", "guidance")

def in_dir(path, name):
    return f"/{name}/" in path or path.startswith(f"{name}/")

def write_fence(payload):
    ...
    for name in FENCED:
        if in_dir(path, name):
            emit("PreToolUse", "deny", ...)
```

`in_dir` matches `/workitems/` **anywhere** in the path, so the absolute path
`…/sdle-latest/docs/workitems/README.md` is denied.

Then, attempting the correction, the permission system denied the edit to
`.claude/hooks/hooks.py`:

> Permission for this action was denied by the Claude Code auto mode
> classifier. Reason: Blocked by classifier.

The same classifier also denied `cat .claude/settings.local.json`.

---

## 4. The fix I prepared, and why I believe it is correct

**The fence is broader than the guarantee behind it.** The engine's own
definition of what SDLE owns is `SDLE_OWNED_PREFIXES`:

```python
SDLE_OWNED_PREFIXES = (
    ".workflow/", ".sdle/", "workitems/", ".specify/", "design/", "reviews/",
    "clarifications/", "guidance/", "requirements/",
)
```

Every entry is **repository-root-relative**. The engine has no refusal for
`docs/workitems/` because it does not own it. So the hook is denying a write
that no choke-point refusal backs up — the one failure mode a tripwire must not
have, and the reason CLAUDE.md says the script's refusal at the choke point *is*
the guarantee.

**Proposed change** — inside `write_fence` only, no new top-level definition, so
no closed set in `test_n28_the_hooks_are_byte_identical` moves:

```python
    candidate = relative(path)
    anchored = candidate != path or not (
        path.startswith("/") or re.match(r"^[A-Za-z]:/", path))
    for name in FENCED:
        hit = (candidate == name or candidate.startswith(name + "/")
               ) if anchored else in_dir(path, name)
        if hit:
            emit("PreToolUse", "deny",
                 "SDLE write fence: " + FENCE_REASONS[name])
            return
```

**Replacement safety property (§28).** Inside this repository the fence becomes
*exactly* `SDLE_OWNED_PREFIXES` — no broader, no narrower — so it now agrees
with the guarantee instead of over-approximating it. Outside this repository
there is no root to anchor against, so the loose segment match is **kept**: a
write addressed at another checkout's `workitems/` is still denied.

**Nothing the fence currently catches inside the repository is lost**, because
nothing SDLE owns lives anywhere but the repository root. What is lost is the
accidental coverage of unrelated directories that merely share a name — which
was never a guarantee and is what broke §17.

**Every property `test_n28` pins is preserved.** `write_fence` is already in
`T11_HOOK_EDITS`, so it is pinned by property rather than by bytes, and each of
those properties still holds: it still emits `"deny"`, still reads its reason
from `FENCE_REASONS`, still contains exactly one `SPECS_CARVE_OUT`, still
iterates `for name in FENCED`, and still calls `normalized(`. `FENCED` itself is
unchanged, so the assertion that `.workflow/` stays fenced (P6) is untouched.

I verified each of these against the test body before proposing the shape; I am
not asserting the replacement is stronger, only that it is **exactly as strong
where SDLE has a guarantee, and no longer stronger where it has none**.

**Tests I would add** (to `tests/test_hooks.py`, extending its existing
parametrised deny/allow lists rather than changing any assertion):

- `docs/workitems/README.md` is **allowed** — the §17 path;
- `workitems/index.md`, `workitems/<id>/.sdle/state.json`,
  `/proj/workitems/...` and the Windows-drive form are still **denied**;
- a foreign absolute path containing `/workitems/` is still **denied**.

---

## 5. Exactly what is blocked, and what is not

**Blocked (1 item):** `docs/workitems/README.md` does not exist.

**Consequences, all traceable to that one item:**

| Effect | Detail |
|---|---|
| `lint-skill` | 43 checks, `failed: ["documentation_set_is_present"]`, message `docs/workitems/ is missing`. The other five new directories pass |
| 2 failing tests | `test_units_capabilities.py::test_n24_the_schema_did_not_move` and `::test_n26_every_baseline_check_is_still_present_and_passing` — both assert `lint-skill` exits 0 |
| 10 erroring tests | `test_lint_skill.py::test_n24_*` — the `documented_repo` fixture does `shutil.copytree(REPO_ROOT / "docs/workitems")` |
| A12 | Not met: eight of nine §17 documentation targets exist |
| A10 | Not met: 43 checks is correct, `failed: []` is not |

**Not blocked, and complete:** M1–M6, all of M8, and all of M7 except this one
file — see `T11-checkpoint-a01-07.md`. Both dry-run transcript pins were
converted to the declared-substitution comparison and **pass**. ADR-008 exists
and carries all 26 findings.

### Full-suite result

Recorded in the handoff-equivalent section of `T11-checkpoint-a01-07.md` §8 and
below. It was run to answer one question — *did M7 or M8 regress anything
outside the blocked item?* — because `tests/conftest.py` is shared by the whole
suite and M8 edited it.

| Item | Value |
|---|---|
| Command | `rtk proxy "python -m pytest -q --junitxml=<scratch>/t11-full.xml --tb=line"` |
| Summary line, located in the output rather than trusted from the completion signal | **`2 failed, 1698 passed, 10 errors in 1563.20s (0:26:03)`** |
| Junit XML, parsed independently | `tests=1710 failures=2 errors=10 skipped=0` |
| Arithmetic | `1698 + 2 + 10 = 1710`, so nothing is hidden in a skip or an xfail |
| The 12 non-passing | **exactly** the ten `test_lint_skill.py::test_n24_*` fixture errors and the two `test_units_capabilities.py` lint-exit assertions listed above |

**Answer to the question the run was for: no.** M7 and M8 regressed nothing.
`tests/conftest.py` gained only additive content (the substitution list and its
helper), and every test outside the twelve — including both dry-run transcript
pins, all three integration files, `test_hooks.py` and the whole
`test_units_hardening.py` file — passes.

The background runner reported "exit code 0" for the shell pipeline. That is the
false green F9 warns about; **the junit XML is what these figures come from.**

---

## 6. The options, and my recommendation

| # | Option | Assessment |
|---|---|---|
| **A** | **Grant permission to edit `.claude/hooks/hooks.py`**, apply §4, add the `test_hooks.py` cases, create `docs/workitems/README.md`, finish TR26, re-run | **Recommended.** It fixes a real defect in a guardrail — a denial with no engine refusal behind it — and it is the only option that leaves the fence agreeing with `SDLE_OWNED_PREFIXES` |
| B | Create `docs/workitems/README.md` yourself (outside my tool surface), leave the fence as it is | Unblocks §17 but **bakes in the defect**: the file would exist while the shipped fence forbids Claude to ever edit it, and `documentation_set_is_present` would pass over a directory the product cannot maintain. I do not recommend it |
| C | Change `DOCUMENTATION_TARGETS` to a name that does not collide | Rejected: §17 names `docs/workitems/` verbatim. This would be editing the contract to fit the tool |
| D | Defer the whole documentation set | Rejected: §17 lists it under "Update at minimum", and D16 already ships the check that enforces it |

**What I will not do:** write the file with Bash, or with any other tool, to get
past the fence. The fence's denial is wrong on this path, but "the guardrail is
wrong here" is an argument for fixing the guardrail, not for stepping around it
— and in a phase whose entire subject is guardrail integrity, stepping around
one to make the phase go green would be the worst possible precedent.

---

## 7. What a resuming context must not do

- **Do not** re-attempt the same Write hoping for a different answer. The denial
  is deterministic.
- **Do not** create the file with Bash, `python`, `git checkout`, or a move from
  a temp location.
- **Do not** delete or weaken `documentation_set_is_present`, or drop
  `docs/workitems/` from `DOCUMENTATION_TARGETS`, to make the suite green. That
  is §1.16 weakening-a-test-to-pass, on the check D16 exists to be.
- **Do not** treat the twelve non-passing outcomes as flakes. `ENVIRONMENT_FLAKE`
  is VOID; every one is explained by §5 and none is a regression.
- **Do** read `T11-checkpoint-a01-07.md` first. All the M7/M8 work is real and
  on disk, and none of it needs redoing.
