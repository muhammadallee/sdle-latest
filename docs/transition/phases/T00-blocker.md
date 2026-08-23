# T00 Blocker — transition control-plane guard is path-broken in both directions

> **STATUS: RESOLVED.** The user selected **Option A** and authorized the fix. Applied by the orchestrator; see §9 for the resolution record. T00 is back to `PLANNED`. This document is retained as the audit trail for a hash-locked control that was deliberately modified.

**Phase:** T00 — Baseline Freeze and Transition Safety Net
**Raised by:** transition orchestrator (parent session)
**Raised at stage:** after PLAN completed, before IMPLEMENT was launched
**Blocked artifact:** `tools/transition/agent_guard.py`
**Nature:** migration-harness defect requiring human authorization to fix — **not** an SDLE product defect, and **not** an ambiguity in the T00 plan.

---

## 1. What is NOT blocked

`docs/transition/phases/T00-plan.md` is complete, persisted, and executable. It covers all fourteen PLAN duties of `transition.md` §24.2 and its acceptance criteria match §6's exit criteria. No material architectural decision is unresolved *inside T00 itself*.

The T00 row is set to `BLOCKED` rather than `PLANNED` for one reason only: a fresh orchestrator resuming from disk must not read `PLANNED` and launch the implementer into the defective guard. The plan remains valid and is the resumption input once this blocker is cleared.

---

## 2. The defect

`tools/transition/agent_guard.py` normalizes only backslashes and a leading `./`:

```python
path = str(raw_path).replace("\\", "/")
while path.startswith("./"):
    path = path[2:]
```

It then matches that string against **repo-relative anchored** patterns (`^docs/transition/phases/T\d{2}-plan\.md$`) and `str.startswith` prefixes (`"docs/transition/transition.md"`, `"tools/transition/"`, …).

Claude Code delivers `file_path` as an **absolute** path. So the matched string is
`C:/workspace/ai/cc/sdle-git-repo/sdle-latest/docs/transition/...`, which matches nothing.

Because the planner/verifier arms are allow-lists and the implementer arm is a deny-list over the same unmatched string, the single bug fails **closed** for two roles and **open** for the third.

## 3. Evidence (observed, this session)

Driven by feeding real `PreToolUse` JSON payloads to the guard on stdin and reading its exit code (`0` = allowed, `2` = blocked):

| Role | Target | Path form | Result |
|---|---|---|---|
| planner | its own `docs/transition/phases/T00-plan.md` | absolute | **BLOCKED** (exit 2) |
| verifier | its own `docs/transition/phases/T00-verification-a01.md` | absolute | **BLOCKED** (exit 2) |
| implementer | `docs/transition/transition.md` — the contract | absolute | **ALLOWED** (exit 0) |
| implementer | `tools/transition/agent_guard.py` — the guard itself | absolute | **ALLOWED** (exit 0) |
| planner | its own `T00-plan.md` | relative | ALLOWED (exit 0) |
| implementer | `docs/transition/transition.md` | relative | BLOCKED (exit 2) |
| implementer | `scripts/sdle.py` — product code | relative | ALLOWED (exit 0) |

The relative-path rows show the intended policy is correct. Only the path form defeats it.

### Corroborating field evidence

The T00 planner could not write its own plan with the `Write` tool and completed the phase only by routing around the tool via `python -c` in Bash. The guard's planner/verifier Bash filter blocks shell redirection and the common mutation commands, but not an interpreter invocation. That workaround is disclosed in the plan's evidence ledger. The verifier will hit the identical wall.

## 4. Why this blocks the IMPLEMENT stage specifically

The implementer is the only role that edits product code, and it is the role whose control-plane protection is inert. With absolute paths, `allowed_write("implementer", p)` reaches its terminal `return True` for **every** path, so a subagent could rewrite `transition.md` (the contract it is being judged against), `agent_guard.py` (the guard constraining it), or the specialist agent definitions — silently, and with no policy stop.

`docs/transition/control-plane.sha256` plus `tools/transition/validate.py` remain a genuine **post-hoc** backstop: tampering would be detected on the next validation run. Detection after the fact is not prevention, and it does not restore the planner's and verifier's ability to write their own sanctioned evidence.

## 5. Why this needs a human decision rather than an orchestrator fix

`tools/transition/agent_guard.py` is listed in `docs/transition/control-plane.sha256`
(`aa57c5881c86ca796e895136b5a751b0331e87d3a08c813a802ee9309101aa42`). Repairing it requires editing the guard **and** re-signing its own manifest entry.

An agent that patches a tamper-evidence control and then regenerates that control's hash has defeated the control, whatever the intent of the patch. `transition.md` §24.1 also forbids the orchestrator from implementing changes itself. The authorization is therefore the user's to give.

---

## 6. Options

### Option A — authorize the path fix, re-sign the manifest *(recommended)*

Normalize an absolute path down to repo-relative before matching, leaving the policy tables untouched:

```python
ROOT = Path(__file__).resolve().parents[2].as_posix()
path = str(raw_path).replace("\\", "/")
if path.lower().startswith(ROOT.lower() + "/"):
    path = path[len(ROOT) + 1:]
while path.startswith("./"):
    path = path[2:]
```

Then recompute the `tools/transition/agent_guard.py` line in `docs/transition/control-plane.sha256` and confirm `python tools/transition/validate.py` still exits 0.

Roughly six lines. No policy change: every allow/deny decision in the table above becomes the relative-path row, which is the behaviour the guard was written for. Verifiable by re-running the payload matrix in §3 and requiring every row to match its relative-path counterpart.

*Consider also:* the planner/verifier Bash filter does not stop `python -c` writes. Tightening that is a separate, larger change and is **not** recommended as part of clearing this blocker — the fix above restores the primary control, and the manifest check still backstops the interpreter path.

### Option B — proceed unfixed

Accept a fail-open implementer, and let planner/verifier keep bypassing the `Write` tool via an interpreter. Rejected: it removes the protection precisely where product code is edited, and it normalizes tool-bypass as routine agent behaviour.

### Option C — remove the guard hooks entirely

Delete the `PreToolUse` wiring from the three agent definitions and rely solely on `control-plane.sha256` + `validate.py` for post-hoc detection. Honest about what is actually being enforced, but discards all write-scoping and still requires re-signing the manifest for the agent-definition files.

## 7. What resumes after the decision

On **Option A**, in order:

1. **Apply the §6 Option A patch to `tools/transition/agent_guard.py`.** The **orchestrator (parent session)** applies it, not a specialist agent — delegating a guard repair to a guard-constrained and currently fail-open implementer is circular. `transition.md` §24.1 forbids the orchestrator from implementing *product* changes; `agent_guard.py` is migration harness, not product. The same reasoning covers the parent having authored this blocker file and the `progress.md` row: no specialist could safely be launched to do it.

2. **Re-sign the manifest using `validate.py`'s own canonicalization.** `validate.py::sha256()` normalizes `\r\n` → `\n` before hashing. A raw `Get-FileHash` or `sha256sum` over a CRLF-saved file yields a different digest and `validate.py` will exit 3. Compute the replacement line by calling that same function, e.g.:

   ```
   python -c "import sys; sys.path.insert(0,'tools/transition'); import validate, pathlib; print(validate.sha256(pathlib.Path('tools/transition/agent_guard.py')))"
   ```

   Replace only the `tools/transition/agent_guard.py` line in `docs/transition/control-plane.sha256`.

3. **Re-run the §3 payload matrix.** Every absolute-path row must now equal its relative-path counterpart.

4. **Run the positive acceptance cases, which §3 does not cover.** These are the sanctioned writes that must become `ALLOWED`, and they are where an off-by-one in the prefix strip (trailing-slash handling, case folding) would fail silently. All with **absolute** paths:

   | Role | Target | Required |
   |---|---|---|
   | implementer | `docs/transition/phases/T00-handoff-a01.md` | ALLOWED |
   | planner | `docs/transition/progress.md` | ALLOWED |
   | verifier | `docs/transition/progress.md` | ALLOWED |
   | planner | `docs/transition/phases/T00-blocker.md` | ALLOWED |

   `progress.md` is matched by exact string compare (`p == PROGRESS`), so it passes only if normalization is exact.

5. **Run `python tools/transition/validate.py`** and require exit 0.

6. **Set T00 back to `PLANNED`** and launch a fresh implementer against the existing, unmodified `T00-plan.md`. No T00 planning work is lost or redone.

---

## 8. Carried-forward T00 findings (not blocking)

Recorded here so they survive a context loss; each is handled inside the existing plan.

- **Baseline SHA verified.** `git rev-parse HEAD` = `f8fdaa048b9a9a35d317224eddd191318ccdd7f6`, matching `transition.md` line 6 and `progress.md` exactly, and equal to the tip of `remotes/origin/wave-a-deterministic-core`. An earlier orchestrator prompt contained a one-character transcription error in this SHA; the repository, not that prompt, is authoritative.
- **`lint-skill` reports 22 PASS checks, exit 0, v1.13** in all four version locations. An earlier orchestrator note said 20; 22 is the observed count.
- **Baseline suite is not deterministically green on this machine.** `1 failed, 229 passed`. The failure is a Windows `PermissionError: [WinError 5]` from `os.replace` in `write_atomic` (`scripts/sdle.py:463`), non-deterministic across re-runs with a different victim file each time — classified `INFERRED` environmental (on-access scanner), not a product defect, and explicitly not fixed in T00. Plan failure-mode F1 defines the deterministic re-run procedure.
- **CI is `NOT_RUN`.** The branch is local-only, so no run is observable. CI pins Python 3.11 on `[ubuntu-latest, windows-latest]`; local is Python 3.14.6 / pytest 9.1.1. Non-blocking under §6 item 2 ("if available"), but local results are valid evidence for this environment only.
- **Unreconciled count discrepancy.** `lint-skill` parses "19 phases" while the progress denominators say 18. Both numbers are recorded; the plan delegates reconciliation to the implementer with instructions not to silently smooth it over.

---

## 9. Resolution record

**Decision:** the user selected **Option A** and explicitly authorized modifying the hash-locked guard and re-signing its manifest entry. Applied by the orchestrator (parent session), per the reasoning in §7 item 1.

### 9.1 Change applied

`tools/transition/agent_guard.py` — six lines added before the existing `./` strip, with a comment recording why. No policy table touched; no allow/deny rule altered.

```python
ROOT = Path(__file__).resolve().parents[2].as_posix()
path = str(raw_path).replace("\\", "/")
if path.lower().startswith(ROOT.lower() + "/"):
    path = path[len(ROOT) + 1:]
```

### 9.2 Manifest re-signed

`docs/transition/control-plane.sha256`, `tools/transition/agent_guard.py` line only:

```
aa57c5881c86ca796e895136b5a751b0331e87d3a08c813a802ee9309101aa42   (before)
93afa04914005c18b64622485e42ff36f74382c4aaf523ae48bc8f310dff7f40   (after)
```

Computed with `validate.py::sha256()` itself, so the canonical-LF normalization matches. All fourteen other manifest lines are byte-identical.

### 9.3 The lock was observed working

Before re-signing, `python tools/transition/validate.py` exited **3** with
`TRANSITION_INVALID: control-plane hash mismatch: tools/transition/agent_guard.py`.
The tamper-evidence control detected the authorized edit exactly as designed. After re-signing: `TRANSITION_VALID: complete=0/12 next=T00`, exit 0.

### 9.4 Acceptance matrix — 20 cases, all green

Each case was driven with a real `PreToolUse` payload in **both** absolute and relative path form; the pass condition is `absolute == relative == expected`.

Sanctioned writes now `ALLOWED` in both forms (the fail-closed half, and the §7 item 4 positive cases):

- planner → `T00-plan.md`; verifier → `T00-verification-a01.md`
- implementer → `T00-handoff-a01.md`, `T00-checkpoint-a01-01.md`
- planner / verifier / implementer → `progress.md` (exact-string compare — passes only if normalization is exact)
- planner → `T00-blocker.md`
- implementer → `scripts/sdle.py`, `tests/test_integration_02_to_05.py`

Control-plane and cross-role writes now `BLOCKED` in both forms (the fail-open half):

- implementer → `transition.md`, `agent_guard.py`, `validate.py`, `templates/phase-plan.md`, `.claude/agents/sdle-transition-planner.md`, `.claude/skills/apply-sdle-transition/SKILL.md`, `T00-plan.md`
- planner / verifier → `scripts/sdle.py`; planner → `T00-handoff-a01.md`

**Result: ALL 20 CASES AGREE.** No mismatches.

### 9.5 Known residual, accepted

The planner/verifier Bash filter still does not stop interpreter-mediated writes (`python -c`). Not addressed here, per §6 Option A: the primary control is restored, and `control-plane.sha256` + `validate.py` remain the backstop. Recorded so it is not mistaken for an oversight.

---

## 10. Second authorized control-plane change (post-T00, guard Bash filter)

Recorded here rather than in a new document because it modifies the same hash-locked artifact under the same authorization pattern. **T00 was already `COMPLETE` and independently verified `PASS` when this was applied**; it changes no T00 evidence and no product file.

**Trigger.** The T00 verifier reported that the planner/verifier redirection filter rejects benign *observational* commands merely for containing `>` — `2>/dev/null`, `2>$null`, and an ASCII `->` arrow inside a Python comment or annotation. Every remaining planner and verifier would hit it. Left unfixed, it trains agents to route around the guard rather than read its refusals as meaningful, which is exactly how the first planner ended up bypassing the `Write` tool with `python -c` (§3).

**Decision.** The user authorized tightening the regex.

**Change.** `tools/transition/agent_guard.py`, one pattern in the planner/verifier `forbidden` list:

```python
r"(^|[^>])>>?\s*[^&]"                                                  # before
r"(^|[^>=<!-])>>?\s*(?!&|/dev/null|\$null|NUL\b|nul\b)[^\s&|;>=]"      # after
```

Scope is narrowed, never widened: every command the old pattern blocked *and that actually writes a file* is still blocked. A comment records that this is a tripwire, not a shell parser, and that a `>` inside a quoted string still trips it — an accepted false positive.

**Manifest re-signed** (`agent_guard.py` line only, via `validate.py::sha256`):

```
93afa04914005c18b64622485e42ff36f74382c4aaf523ae48bc8f310dff7f40   (before)
e8babae5977abdaa…                                                  (after)
```

`validate.py` again exited **3** with `control-plane hash mismatch` before re-signing — the lock caught this edit too — and exit **0** after.

**Evidence — 24-case command corpus, all pass.** Now `ALLOWED` (were blocked): `2>/dev/null`, `2>$null`, `2>&1`, `-> int` annotations, `4 -> 5` in a comment, `>=`, `!=`. Still `BLOCKED`: `echo … > transition.md`, `>> progress.md`, `> out.txt`, `cat a > b`, `rm -rf`, `git commit`, `git push`, `sed -i`, `tee`, `Set-Content`, `mv`.

**Write-scope matrix re-run: 20/20 still agree** in both absolute and relative path form. The §9 fix is undisturbed.

---

## 11. Third authorized control-plane change (post-T00, `git merge-base` false positive)

Same artifact, same authorization pattern as §9 and §10. Applied while T01 implementation was in flight; changes no T00 evidence, no T01 plan, and no product file.

**Trigger.** The T01 planner reported that the guard blocked `git merge-base --is-ancestor …`. Cause confirmed by driving the pattern directly: `\b` after each subcommand matches at a hyphen, so `git merge-base` — a pure read — matched the `git merge` mutation deny.

This is not cosmetic. Contract §1 item 2 requires every phase to confirm the baseline is an ancestor of the working branch, and `git merge-base --is-ancestor` is the canonical way to do it. The guard was blocking a contract-mandated check. The T01 planner substituted two `git rev-list --count` calls and recorded the method (ledger E2a) — correct behaviour under a wrong constraint.

**Decision.** The user authorized the fix and granted **standing approval for future guard false-positive fixes**, scoped strictly: only changes that stop the guard blocking provably read-only or otherwise sanctioned operations. Anything that would let the guard permit a *new mutation* still requires explicit approval. Every such fix keeps the full procedure — patch, re-sign only the `agent_guard.py` manifest line via `validate.py::sha256`, re-run all three matrices, record here — and is reported, never silent.

**Change.** One targeted exemption, deliberately narrower than relaxing the word boundary:

```python
r"…|clean|restore|merge|rebase|cherry-pick|tag|push))\b"            # before
r"…|clean|restore|merge(?!-base)|rebase|cherry-pick|tag|push))\b"   # after
```

Loosening `\b` to `(?![\w-])` globally was rejected: it would also permit `git checkout-index`, which genuinely writes files.

**Manifest re-signed** (`agent_guard.py` line only): `e8babae5977abdaa…` → `bd90f138d100491a…`. `validate.py` exit 0 after.

**Evidence — three matrices, 62 cases, zero mismatches.**

- *Git corpus, 22 cases.* Now `ALLOWED`: `git merge-base --is-ancestor`, `git merge-base HEAD origin/main`. Still `BLOCKED`: `git merge --abort`, `git merge origin/main`, `git checkout-index -a`, `git checkout`, `add`, `commit`, `push`, `reset --hard`, `clean -fd`, `restore`, `rebase`, `cherry-pick`, `tag`, `switch`. Still `ALLOWED`: `log`, `diff`, `rev-parse`, `show`, `status`, `rev-list`.
- *Redirection corpus, 20 cases* (§10 regression) — all still pass.
- *Write-scope matrix, 20 cases* (§9 regression) — all still agree in both path forms.
