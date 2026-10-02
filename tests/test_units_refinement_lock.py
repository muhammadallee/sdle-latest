"""The short repository mutex every mutating refinement command holds.

It serialises one command's state-absence check and write against `init` and
`requirements bind`. Never held across a model call, never a lifecycle lock.
"""

from __future__ import annotations

import os

import pytest

from conftest import sdle


def paths_of(project):
    return sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                      workitem=project.workitem)


def test_the_mutex_is_a_repository_file_under_workitems_not_a_runtime_or_config_member(project):
    paths = paths_of(project)
    lock = paths.refinement_lock_file
    assert lock == project.root / "workitems" / ".refinement-transaction.lock"
    assert paths.runtime not in lock.parents
    assert paths.config_root not in lock.parents
    assert lock.name not in sdle.workitem_runtime_member_names(paths)


def test_the_mutex_is_gitignored_beside_the_active_context():
    ignored = (sdle.Path(__file__).resolve().parent.parent / ".gitignore").read_text(
        encoding="utf-8").splitlines()
    assert "workitems/.refinement-transaction.lock" in ignored
    assert "workitems/.active-context.json" in ignored


def test_it_is_held_inside_and_released_after(project):
    paths = paths_of(project)
    with sdle.refinement_mutex(paths):
        assert paths.refinement_lock_file.exists()
    assert not paths.refinement_lock_file.exists()


def test_it_is_released_when_the_guarded_work_raises(project):
    paths = paths_of(project)
    with pytest.raises(RuntimeError):
        with sdle.refinement_mutex(paths):
            raise RuntimeError("boom")
    assert not paths.refinement_lock_file.exists()


def test_a_held_mutex_is_a_refusal_not_a_hang_and_is_not_released_by_the_refused(
        project, monkeypatch):
    paths = paths_of(project)
    monkeypatch.setattr(sdle, "REFINEMENT_LOCK_TIMEOUT", 0.2)
    paths.refinement_lock_file.write_text("held", encoding="utf-8")
    with pytest.raises(sdle.Refused) as raised:
        with sdle.refinement_mutex(paths):
            raise AssertionError("entered a held mutex")
    assert raised.value.reason == "refinement_transaction_locked"
    assert paths.refinement_lock_file.read_text(encoding="utf-8") == "held"


def test_a_mutex_left_by_a_dead_process_is_broken_once_stale(project, monkeypatch):
    paths = paths_of(project)
    monkeypatch.setattr(sdle, "REFINEMENT_LOCK_STALE_AFTER", 5.0)
    paths.refinement_lock_file.write_text("dead", encoding="utf-8")
    old = paths.refinement_lock_file.stat().st_mtime - 3600
    os.utime(paths.refinement_lock_file, (old, old))
    with sdle.refinement_mutex(paths):
        pass
    assert not paths.refinement_lock_file.exists()


def test_the_mutex_is_created_exclusively():
    """The exclusive-open invariant is `os.open(..., O_CREAT | O_EXCL)`, which the
    architecture lock already satisfies; the shared helper keeps it."""
    import inspect
    source = inspect.getsource(sdle.exclusive_file_lock)
    assert "os.O_CREAT | os.O_EXCL" in source
