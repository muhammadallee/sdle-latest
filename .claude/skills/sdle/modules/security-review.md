> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP) are already in context from SKILL.md. Do not duplicate them here.

## Step 8: Security Review — Assisted, Evidence-Based Format

**This is an AI-assisted review based on project artifacts and a git diff. It is NOT a substitute for automated SAST/DAST tooling, dependency scanning, or a professional security audit.**

### How to generate the review:

**Step 8a — Gather evidence:**
1. Read the following files (note which ones exist):
   - `.specify/memory/constitution.md`
   - `.specify/specs/{state.current_feature_id}/spec.md`
   - `.specify/specs/{state.current_feature_id}/plan.md`
   - `.specify/specs/{state.current_feature_id}/tasks.md`
2. Run `git diff --stat HEAD~1` (PowerShell Bash tool) and capture the output. If git is unavailable or fails, note this explicitly — do not skip the review.
3. Run `git diff HEAD~1 -- . ":(exclude).specify" ":(exclude).workflow"` to get the actual implementation diff. Capture it.
4. Extract the tech stack from `plan.md` (look for frameworks, languages, databases, auth libraries).

**Step 8b — Generate the review file:**

Create `reviews/security-review-<YYYY-MM-DD-HHMM>.md` with this structure:

```markdown
# AI-Assisted Security Review — <Project Name>
**Date:** <YYYY-MM-DD HH:MM>
**Phase:** 14/14 — Final Security Review
**Disclaimer:** This is an AI-assisted review based on artifacts and a git diff.
It is NOT a substitute for SAST/DAST tools, dependency scanners, or a professional audit.

---

## What We Reviewed
- Artifacts read: <list each .specify/ file that was read>
- Git diff range: HEAD~1..HEAD (or "git not available")
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
