"""The CLI boundary itself.

The rest of the suite invokes ``main()`` in-process for speed. These tests go
through a real subprocess, because what they check — argv parsing, the process
exit code, and tracebacks never escaping — only exists at that boundary.
"""

from __future__ import annotations

import json
import subprocess
import sys

from conftest import SDLE_PY

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


def test_help_exits_zero():
    completed = subprocess.run(
        [sys.executable, str(SDLE_PY), "--help"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == EXIT_OK
    assert "sdle" in completed.stdout


def test_unknown_subcommand_is_usage_error_not_traceback():
    completed = subprocess.run(
        [sys.executable, str(SDLE_PY), "no-such-thing"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == EXIT_USAGE
    assert "Traceback" not in completed.stderr


def test_missing_required_argument_is_usage_error(project):
    result = project.run_cli("advance")
    assert result.exit_code == EXIT_USAGE
    assert "Traceback" not in result.stderr


def test_refusal_exit_code_survives_the_process_boundary(project):
    for path in (project.root / "requirements").iterdir():
        path.unlink()
    result = project.run_cli("init")
    assert result.exit_code == EXIT_REFUSED
    assert result.envelope["reason"] == "requirements_missing"


def test_integrity_exit_code_survives_the_process_boundary(project):
    result = project.run_cli("state", "get")
    assert result.exit_code == EXIT_INTEGRITY


def test_stdout_is_pure_json_and_prose_goes_to_stderr(started):
    """Callers parse stdout. Anything human-readable belongs on stderr."""
    result = started.run_cli("header")
    payload = json.loads(result.stdout)  # must not raise
    assert payload["ok"] is True
    assert "SDLE Status" in result.stderr


def test_success_and_refusal_share_one_envelope_shape(started):
    ok = json.loads(started.run_cli("header").stdout)
    refused = json.loads(started.run_cli("advance", "--to", "implement").stdout)
    assert set(ok) >= {"ok", "command", "reason", "data"}
    assert set(refused) >= {"ok", "command", "reason", "data", "message"}
    assert refused["ok"] is False
    assert refused["reason"] == "forward_jump"


def test_output_is_utf8_regardless_of_platform_encoding(started):
    """The header carries an emoji and an em dash. On Windows the default
    stream encoding is the ANSI code page, so without pinning UTF-8 a caller
    decoding UTF-8 gets mojibake — or, as CI showed, a decode error that
    surfaces as an empty stream and a confusing TypeError."""
    import os
    import subprocess

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    completed = subprocess.run(
        [sys.executable, str(SDLE_PY), "--project-root", str(started.root),
         "--skill-root", str(started.skill_root), "header"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert completed.returncode == EXIT_OK
    assert completed.stderr is not None, "stderr failed to decode as UTF-8"
    assert "SDLE Status" in completed.stderr
    assert "📋" in completed.stderr
    json.loads(completed.stdout)


def test_skill_root_can_be_pointed_elsewhere(project):
    """Tests and installed layouts both rely on this override."""
    result = project.run_cli("constants")
    assert result.exit_code == EXIT_OK
    # The registry's non-terminal count, not GREENFIELD's: the registry is the
    # catalogue of phases that exist (21 as of T08, one of them terminal), and
    # a flow is an ordered subset of it.
    assert result.data["phase_count"] == 20
