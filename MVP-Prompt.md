You are an expert Claude Code skill engineer.

You previously created a large enterprise-grade architecture. Now discard all over-engineering.

**Task:** Build a **Minimal Viable SDLE Orchestrator (v1)** — a clean, practical, and immediately usable conversational skill for Claude Code that works reliably with SpecKit.

### Core Constraints (Strictly Follow)
- This must be a **working, runnable implementation**, not a design document.
- Keep it minimal, pragmatic, and easy to maintain.
- The orchestrator internally calls SpecKit skills. The user must never run SpecKit commands manually.

### Updated Minimal Workflow (v1)
Implement this exact sequence:

1. Check / read requirements from `./requirements/`
2. Generate Constitution (`constitution`)
3. **Approval Gate**
4. Generate Specification (`specify`)
5. **Approval Gate**
6. Generate Plan (`plan`)
7. **Approval Gate**
8. Generate Checklist (`checklist`)
9. Generate Tasks (`tasks`)
10. Analyze (`analyze`)
11. **Approval Gate** (new)
12. Implement (`implement`)
13. **Approval Gate** (new)
14. Security Review (new) → Generate a timestamped security review file

**Approval Gates (Total 5)**: Constitution, Specification, Plan, Analyze, and Implement.

### Practical Improvements (Must Include All)
- **Auto-save after every successful step**: Immediately update and save `.workflow/state.json` after each successful SpecKit execution or approval.
- Smart state detection: On every user message, read `.workflow/state.json` and clearly tell the user the current phase and status.
- Robust resume logic: Automatically resume from the last successful phase/gate after interruption.
- Simple remediation: On `reject`, ask for specific feedback, then re-run the same step after user input.
- Good command support: `approve`, `reject`, `approve with comments: ...`, `status`, `resume`, `restart phase X`, `show state`.
- Requirements validation: At start, check if `./requirements/` exists and contains files. If not, ask the user to add requirements first.
- Clear progress: Always show a short progress summary (e.g., "Phase 7/14 - Awaiting approval on Implementation").
- Defensive handling: If a SpecKit call fails, explain conversationally and offer retry or skip (with warning).
- Minimal logging: Append to `.workflow/audit.md` with timestamp + action.

### Security Review (Final Step)
- After Implement approval, run a final Security Review.
- Generate a file: `reviews/security-review-[YYYY-MM-DD-HHMM].md`
- Keep it simple but useful (findings, severity, recommendations).

### State Management (Minimal)
Use `.workflow/state.json` with this structure:
```json
{
  "current_phase": "string",
  "status": "pending | in_progress | awaiting_approval | completed | rejected",
  "last_updated": "ISO timestamp",
  "approvals": {},
  "current_artifact": "string or null",
  "progress": "X/14"
}

Output Requirements
Deliver exactly these:

SDLE-Orchestrator.md — The complete main skill file (the only file the user interacts with). Include:
Role / system instructions
State loading & auto-save logic
Phase handling logic
Approval gate logic
SpecKit internal call mapping
Resume, remediation, and auto-save logic

Example state.json (minimal template)
SpecKit skill mapping table
Short example interaction flow (6-10 turns)

Design Principle: Working minimal orchestrator > perfect architecture.
Start your response directly with the full content of SDLE-Orchestrator.md, followed by the state schema, mapping table, and example flow.
Make the skill clean, well-commented, conversational, reliable, and production-usable inside Claude Code.