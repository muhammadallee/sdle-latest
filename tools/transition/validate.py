#!/usr/bin/env python3
"""Deterministically validate SDLE transition-control state."""
from __future__ import annotations
import argparse, hashlib, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRESS = ROOT / "docs/transition/progress.md"
PHASES = ROOT / "docs/transition/phases"
MANIFEST = ROOT / "docs/transition/control-plane.sha256"
ALLOWED = {"NOT_STARTED", "PLANNED", "IMPLEMENTED", "BLOCKED", "COMPLETE"}
EXPECTED = [f"T{i:02d}" for i in range(12)]


def fail(msg):
    print(f"TRANSITION_INVALID: {msg}", file=sys.stderr)
    raise SystemExit(3)


def sha256(path: Path) -> str:
    # Control-plane files are UTF-8 text. Normalize line endings so the
    # integrity check is stable across Windows/Linux Git and ZIP extraction.
    text = path.read_text(encoding='utf-8')
    canonical = text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def validate_manifest():
    if not MANIFEST.is_file(): fail("missing docs/transition/control-plane.sha256")
    for lineno, line in enumerate(MANIFEST.read_text(encoding='utf-8').splitlines(), 1):
        line=line.strip()
        if not line or line.startswith('#'): continue
        try: expected, rel = line.split(None, 1)
        except ValueError: fail(f"bad manifest line {lineno}")
        p=ROOT/rel.strip()
        if not p.is_file(): fail(f"control-plane file missing: {rel.strip()}")
        actual=sha256(p)
        if actual != expected: fail(f"control-plane hash mismatch: {rel.strip()}")


def parse_progress():
    if not PROGRESS.is_file(): fail("missing docs/transition/progress.md")
    rows={}
    for line in PROGRESS.read_text(encoding='utf-8').splitlines():
        if not re.match(r"^\| T\d{2} \|", line): continue
        parts=[p.strip() for p in line.strip().strip('|').split('|')]
        if len(parts) != 9: fail(f"progress row must have 9 columns: {line}")
        phase,status,attempt,plan,handoff,verification,commit,tests,notes=parts
        if phase in rows: fail(f"duplicate phase row: {phase}")
        try: attempt_i=int(attempt)
        except ValueError: fail(f"invalid attempt for {phase}: {attempt}")
        rows[phase] = dict(status=status, attempt=attempt_i, plan=plan, handoff=handoff,
                           verification=verification, commit=commit, tests=tests, notes=notes)
    if list(rows) != EXPECTED:
        fail(f"progress phases must be exactly {', '.join(EXPECTED)} in order; got {', '.join(rows)}")
    return rows


def file_ref(value):
    if value in {'-', '', 'NOT_RUN'}: return None
    p=ROOT/value
    return p


def verification_result(path: Path) -> str | None:
    if not path or not path.is_file(): return None
    body=path.read_text(encoding='utf-8', errors='replace')
    m=re.search(r"(?mi)^\*\*Result:\*\*\s*(PASS|FAIL)\s*$", body)
    return m.group(1).upper() if m else None


def validate_rows(rows):
    seen_incomplete=False
    for phase in EXPECTED:
        r=rows[phase]
        if r['status'] not in ALLOWED: fail(f"{phase}: unsupported status {r['status']}")
        if r['attempt'] < 0: fail(f"{phase}: attempt cannot be negative")
        plan=file_ref(r['plan']); hand=file_ref(r['handoff']); ver=file_ref(r['verification'])
        for label,p in [('plan',plan),('handoff',hand),('verification',ver)]:
            if p is not None and not p.is_file(): fail(f"{phase}: {label} file does not exist: {p.relative_to(ROOT)}")
        st=r['status']
        if st == 'NOT_STARTED':
            if r['attempt'] != 0: fail(f"{phase}: NOT_STARTED must have attempt 0")
        elif st == 'PLANNED':
            if not plan: fail(f"{phase}: PLANNED requires plan")
        elif st == 'IMPLEMENTED':
            if not plan or not hand or r['attempt'] < 1: fail(f"{phase}: IMPLEMENTED requires plan, handoff, attempt>=1")
        elif st == 'COMPLETE':
            if not plan or not hand or not ver or r['attempt'] < 1:
                fail(f"{phase}: COMPLETE requires plan, handoff, verification, attempt>=1")
            if verification_result(ver) != 'PASS': fail(f"{phase}: COMPLETE verification must contain **Result:** PASS")
        elif st == 'BLOCKED':
            blocker=PHASES/f"{phase}-blocker.md"
            if not blocker.is_file(): fail(f"{phase}: BLOCKED requires {blocker.relative_to(ROOT)}")
        if seen_incomplete and st == 'COMPLETE':
            fail(f"{phase}: later phase COMPLETE before an earlier phase is complete")
        if st != 'COMPLETE': seen_incomplete=True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--skip-manifest', action='store_true', help='validate progress only')
    args=ap.parse_args()
    if not args.skip_manifest: validate_manifest()
    rows=parse_progress(); validate_rows(rows)
    complete=sum(1 for r in rows.values() if r['status']=='COMPLETE')
    current=next((p for p,r in rows.items() if r['status']!='COMPLETE'), 'DONE')
    print(f"TRANSITION_VALID: complete={complete}/12 next={current}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
