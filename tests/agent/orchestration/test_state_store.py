import json
import pathlib
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.state_store import OrchestrationStateStore, StateStoreError
import agent.orchestration.state_store as state_store_module


def state(revision="rev-1"):
    return {"session": {"id": "s1"}, "conversation": {"messages": []}, "snapshot": {"snapshotRevision": revision, "facts": {"value": 1}}, "orchestration": {}, "evidence": {"nodes": []}}


def test_save_restore_metadata_redaction_and_stale_revision(tmp_path):
    store = OrchestrationStateStore(tmp_path)
    saved = store.save_state("build-1", {**state(), "session": {"api_key": "secret", "name": "ok"}}, metadata={"gamePatch": "3.29", "pobVersion": "2.7", "dataRevision": "d1"})
    assert saved["session"]["api_key"] == "[REDACTED]"
    assert store.load_state("build-1", expected_metadata={"gamePatch": "3.29"})["snapshot"]["snapshotRevision"] == "rev-1"
    with pytest.raises(StateStoreError) as stale:
        store.save_state("build-1", state("rev-2"), expected_snapshot_revision="old")
    assert stale.value.error["code"] == "SNAPSHOT_REVISION_CONFLICT"


def test_path_traversal_corruption_backup_and_version_error(tmp_path):
    store = OrchestrationStateStore(tmp_path)
    with pytest.raises(StateStoreError):
        store.save_state("../escape", state())
    store.save_state("build-1", state())
    store.save_state("build-1", state("rev-2"))
    path = tmp_path / "build-1" / "session.json"
    path.write_text("not json", encoding="utf-8")
    assert store.load_state("build-1")["session"] == state()["session"]
    with pytest.raises(StateStoreError) as mismatch:
        store.load_state("build-1", expected_metadata={"gamePatch": "3.29"})
    assert mismatch.value.error["code"] == "VERSION_MISMATCH"


def test_lock_stale_ask_user_clone_rollback_and_quota(tmp_path):
    store = OrchestrationStateStore(tmp_path, stale_lock_seconds=0.01, file_max_bytes=100000)
    store.save_state("source", state())
    pending = {"code": "AMBIGUOUS_ALIAS", "next_action": "ask_user"}
    store.save_pending("source", pending)
    assert store.resume_pending("source") == pending
    lock = tmp_path / "source" / ".lock"
    lock.write_text("stale", encoding="utf-8")
    time.sleep(0.02)
    store.save_state("source", state("rev-2"))
    assert store.clone_build("source", "copy")["snapshot"]["snapshotRevision"] == "rev-2"
    with pytest.raises(StateStoreError) as quota:
        OrchestrationStateStore(tmp_path / "small", file_max_bytes=10).save_state("b", state())
    assert quota.value.error["code"] == "CACHE_QUOTA_EXCEEDED"


def test_quota_validation_does_not_leave_partial_state(tmp_path):
    store = OrchestrationStateStore(tmp_path, file_max_bytes=120)
    with pytest.raises(StateStoreError) as error:
        store.save_state("build-1", state())
    assert error.value.error["code"] == "CACHE_QUOTA_EXCEEDED"
    assert not (tmp_path / "build-1" / "session.json").exists()


def test_commit_failure_rolls_back_the_complete_file_set(tmp_path, monkeypatch):
    store = OrchestrationStateStore(tmp_path)
    store.save_state("build-1", state("old"))
    original_replace = state_store_module.os.replace

    def fail_snapshot(source, target):
        if pathlib.Path(target).name == "snapshot.json":
            raise OSError("injected commit failure")
        return original_replace(source, target)

    monkeypatch.setattr(state_store_module.os, "replace", fail_snapshot)
    with pytest.raises(StateStoreError) as error:
        store.save_state("build-1", state("new"))
    assert error.value.error["code"] == "STATE_WRITE_FAILED"
    assert store.load_state("build-1")["snapshot"]["snapshotRevision"] == "old"
    assert store.load_state("build-1")["session"] == state("old")["session"]
    assert not list((tmp_path / "build-1").glob(".state-stage-*"))
