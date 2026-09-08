# Transition Phase Evidence

This directory is the durable handoff boundary between isolated transition agents.

Expected files per phase:

```text
TNN-plan.md
TNN-handoff-a01.md
TNN-verification-a01.md
TNN-handoff-a02.md        # remediation only
TNN-verification-a02.md   # remediation only
TNN-checkpoint-aNN-XX.md  # optional
TNN-blocker.md            # material decision only
```

Never overwrite an earlier attempt. A phase is COMPLETE only when `progress.md` points to a verification file whose top-level result is `PASS`.
