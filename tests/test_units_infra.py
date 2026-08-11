"""Interpreter resolution, atomic writes, and the settable-field whitelist.

The launcher probes are exercised with fake interpreters on a synthetic PATH
so every branch is reachable regardless of what the host machine has
installed — including the branch where nothing qualifies.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, sdle

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2
LAUNCHER = REPO_ROOT / "scripts" / "sdle.sh"
SH = shutil.which("sh") or next(
    (c for c in (r"C:\Program Files\Git\bin\sh.exe",
                 r"C:\Program Files\Git\usr\bin\sh.exe") if Path(c).is_file()),
    None,
)


def fake_interpreter(directory: Path, name: str, version: tuple[int, int] | None):
    """A stub that answers the launcher's version probe.

    `version=None` models the Windows Store stub: it resolves on PATH but
    reports no version, which is exactly why the launcher gates on a
    successful version report rather than on the command being found.
    """
    path = directory / name
    if version is None:
        body = '#!/bin/sh\necho "not found" >&2\nexit 9009\n'
    else:
        ok = "0" if version >= (3, 11) else "1"
        body = f'#!/bin/sh\nif [ "$1" = "-c" ]; then exit {ok}; fi\nexit {ok}\n'
    path.write_text(body, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.mark.skipif(SH is None, reason="POSIX sh not available")
class TestLauncherResolution:
    def run_launcher(self, path_dir: Path, extra_env=None):
        env = {
            "PATH": str(path_dir),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            **(extra_env or {}),
        }
        return subprocess.run(
            [SH, str(LAUNCHER), "--help"],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def test_refuses_when_nothing_qualifies(self, tmp_path):
        """PATH is stripped to nothing, which is also the case in which the
        launcher must still be able to report its own failure — so this
        doubles as proof it depends on no external binary."""
        result = self.run_launcher(tmp_path)
        assert result.returncode == EXIT_REFUSED
        payload = json.loads(result.stdout)
        assert payload["reason"] == "no_interpreter"
        assert payload["ok"] is False
        assert "3.11" in payload["message"]

    def test_rejects_an_interpreter_below_3_11(self, tmp_path):
        fake_interpreter(tmp_path, "python3", (3, 9))
        result = self.run_launcher(tmp_path)
        assert result.returncode == EXIT_REFUSED, "3.9 must not satisfy the gate"
        assert json.loads(result.stdout)["reason"] == "no_interpreter"

    def test_rejects_a_stub_that_reports_no_version(self, tmp_path):
        """The Windows Store stub resolves on PATH but is not an interpreter."""
        fake_interpreter(tmp_path, "python", None)
        result = self.run_launcher(tmp_path)
        assert result.returncode == EXIT_REFUSED
        assert json.loads(result.stdout)["reason"] == "no_interpreter"

    def test_falls_back_to_uv_when_no_system_python_qualifies(self, tmp_path):
        fake_interpreter(tmp_path, "python3", (3, 9))
        marker = tmp_path / "uv-was-used"
        uv = tmp_path / "uv"
        # ':' redirection, not touch: PATH is deliberately stripped here, so
        # external binaries are unreachable — the same condition the launcher
        # itself has to survive.
        uv.write_text(f'#!/bin/sh\n: > "{marker}"\nexit 0\n',
                      encoding="utf-8", newline="\n")
        uv.chmod(uv.stat().st_mode | stat.S_IEXEC)

        result = self.run_launcher(tmp_path)
        assert marker.exists(), "uv fallback was not reached"
        assert result.returncode == EXIT_OK

    def test_sdle_python_override_wins(self, tmp_path):
        marker = tmp_path / "override-was-used"
        override = tmp_path / "myinterp"
        override.write_text(f'#!/bin/sh\n: > "{marker}"\nexit 0\n',
                            encoding="utf-8", newline="\n")
        override.chmod(override.stat().st_mode | stat.S_IEXEC)

        self.run_launcher(tmp_path, {"SDLE_PYTHON": str(override)})
        assert marker.exists()

    def test_a_real_launcher_run_succeeds_here(self):
        """The environment this repo is actually developed in must work."""
        result = subprocess.run(
            [SH, str(LAUNCHER), "constants"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
        assert result.returncode == EXIT_OK, result.stderr
        assert json.loads(result.stdout)["data"]["phase_count"] == 18


# -- atomic writes ----------------------------------------------------------


def test_write_atomic_leaves_no_partial_file_on_failure(tmp_path, monkeypatch):
    """A crash between temp and rename must leave the original intact."""
    target = tmp_path / "state.json"
    target.write_text('{"original": true}', encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(sdle.os, "replace", boom)
    with pytest.raises(OSError):
        sdle.write_atomic(target, '{"replacement": true}')

    assert json.loads(target.read_text(encoding="utf-8")) == {"original": True}
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".state.json.")]
    assert leftovers == [], f"temp file was not cleaned up: {leftovers}"


def test_write_atomic_replaces_completely(tmp_path):
    target = tmp_path / "state.json"
    sdle.write_atomic(target, '{"a": 1}')
    sdle.write_atomic(target, '{"b": 2}')
    assert json.loads(target.read_text(encoding="utf-8")) == {"b": 2}


def test_state_writes_survive_repeated_saves(started):
    for index in range(20):
        started.ok("state", "set", "--field", "clarification_phase",
                   "--value", f"phase-{index}")
    assert started.state()["clarification_phase"] == "phase-19"
    assert started.ok("audit", "verify").data["matches"] is True


# -- settable-field whitelist ----------------------------------------------


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("verbose", "true", True),
        ("verbose", "false", False),
        ("clarification_phase", "spec_draft", "spec_draft"),
        ("clarification_phase", "null", None),
        ("speckit_skill_prefix", "speckit.", "speckit."),
    ],
)
def test_state_set_accepts_orchestrator_fields(started, field, value, expected):
    result = started.ok("state", "set", "--field", field, "--value", value)
    assert result.data["value"] == expected
    assert started.state()[field] == expected


def test_state_set_is_audited(started):
    started.ok("state", "set", "--field", "verbose", "--value", "true")
    assert "verbose:" in started.audit_file.read_text("utf-8")
    assert started.ok("audit", "verify").data["matches"] is True


@pytest.mark.parametrize(
    "field",
    ["current_phase", "status", "approvals", "artifact_shas", "audit_sha",
     "progress", "phase_history"],
)
def test_state_set_refuses_engine_owned_fields(started, field):
    """Everything derived from a transition, verification or approval stays
    out of the model's hands — that is what the write fence protects."""
    result = started.run("state", "set", "--field", field, "--value", "x")
    assert result.exit_code in (EXIT_REFUSED, EXIT_USAGE)
    if result.exit_code == EXIT_REFUSED:
        assert result.reason == "field_not_settable"


def test_state_set_rejects_a_non_boolean_for_verbose(started):
    result = started.run("state", "set", "--field", "verbose", "--value", "maybe")
    assert result.exit_code == EXIT_USAGE
    assert result.reason == "bad_value"


def test_preflight_persists_the_discovered_prefix(started):
    assert started.state()["speckit_skill_prefix"] is None
    started.ok("preflight")
    assert started.state()["speckit_skill_prefix"] == "speckit-"


# -- retry guard ------------------------------------------------------------


def test_retry_is_allowed_when_no_drift_is_pending(started):
    assert started.ok("retry").data["phase"] == "constitution_draft"


def test_retry_refuses_while_drift_reapproval_is_pending(started):
    state = started.state()
    state["drift_queue"] = ["gate_spec"]
    state["pending_phase"] = "plan_draft"
    started.write_state(state)

    result = started.run("retry")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "drift_pending"
    assert "approve" in result.envelope["message"]
