> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP, PHASE_LABEL_MAP) are already in context from SKILL.md. Do not duplicate them here.
>
> **Filename:** Phase 17 in `modules/phase-execution.md` pre-computes `review_filename` and writes it to `state.json → security_review_artifact` before loading this module. **Use that exact path as the output file — do NOT generate a new timestamped filename in Step 8b.** The pre-computed filename is available in context from Phase 17's instructions.

## Step 8: Security Review — Assisted, Evidence-Based Format

**This is an AI-assisted review based on project artifacts and a git diff. It is NOT a substitute for automated SAST/DAST tooling, dependency scanning, or a professional security audit.**

### How to generate the review:

**Step 8a — Gather evidence:**
1. Read the following files (note which ones exist):
   - `.specify/memory/constitution.md`
   - `{state.specKit.featureDirectory}/spec.md`
   - `{state.specKit.featureDirectory}/plan.md`
   - `{state.specKit.featureDirectory}/tasks.md`
2. Run `sdle.sh security-review evidence`. It diffs against `implementation_base_ref` — the HEAD recorded when Phase 15 started — rather than `HEAD~1`, which is only correct when the implementation happened to be exactly one commit. The response carries `stat`, `diff`, the resolved `base_ref`, and whether it was `pinned`. If git is unavailable it says so; note that explicitly rather than skipping the review.
4. Extract the tech stack from `plan.md` (look for frameworks, languages, databases, auth libraries).

**Step 8b — Generate the review file:**

Create the review file at `<review_filename>` (the pre-computed path from Phase 17 — do NOT generate a new timestamp; use the exact path stored in `state.json → security_review_artifact`) with this structure:

```markdown
# AI-Assisted Security Review — <Project Name>
**Date:** <YYYY-MM-DD HH:MM>
**Phase:** <progress> — Security Review
**Disclaimer:** This is an AI-assisted review based on artifacts and a git diff.
It is NOT a substitute for SAST/DAST tools, dependency scanners, or a professional audit.

---

## What We Reviewed
- Artifacts read: <list each .specify/ file that was read>
- Git diff range: <base_ref>..HEAD (or "git not available")
- Diff summary:
  <paste output of git diff --stat, or "git unavailable">

---

## Tech Stack (from plan.md)
<Extracted stack: language, framework, database, auth, external APIs>

---

## OWASP Top 10 — Relevance to This Stack
<For each OWASP category, one line: relevant/not relevant for this stack and why>
Example:
- A01 Broken Access Control — RELEVANT (REST API with user-scoped data)
- A02 Cryptographic Failures — RELEVANT (stores user credentials)
- A03 Injection — RELEVANT (SQL via ORM, review parameterization)
- A04 Insecure Design — review spec for threat modelling gaps
...

---

## Patterns Flagged in Diff
<List ONLY patterns actually observed in the git diff — with file:line references>
- If no suspicious patterns: state "No high-risk patterns observed in diff."
- Categories to look for (only flag if present):
  • Hardcoded secrets, API keys, passwords in source
  • Raw string SQL concatenation (not parameterized)
  • Missing input validation on user-controlled data
  • eval() / exec() / dynamic code execution
  • Disabled TLS verification
  • World-readable file permissions set in code
  • Logging of sensitive data (passwords, tokens, PII)

---

## Tools You Should Run
<Concrete commands tailored to the detected tech stack>
Examples (adjust to actual stack):
- JavaScript/Node: `npm audit`, `npx snyk test`
- Python: `pip-audit`, `bandit -r .`, `safety check`
- General: `semgrep --config=auto .`, `trivy fs .`
- Secrets: `trufflehog git file://. --since-commit HEAD~1`

---

## What This Review Does NOT Cover
- Runtime behavior and logic flaws not visible in static analysis
- Dependency CVEs (use the tool commands above)
- Infrastructure and deployment configuration
- Secrets already committed to git history (use trufflehog for that)
- Authentication/authorization flow testing
- Business logic security issues
```

**If git is unavailable:** Skip the diff sections, state "Git not available — diff analysis skipped." Still produce the OWASP relevance mapping, tool recommendations, and artifact-derived observations.
