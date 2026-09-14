"""Small, file-backed orchestration state store.

PoB remains the build authority; this module only stores local session state and
never stores raw XML or credentials.
"""

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path


FILES = ("session", "conversation", "snapshot", "orchestration", "evidence")
SENSITIVE = {"api_key", "apikey", "authorization", "auth", "token", "secret", "rawxml", "xml", "notes", "prompt", "itemtext", "freetext", "password"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class StateStoreError(RuntimeError):
    def __init__(self, message, code="STATE_ERROR", *, details=None, next_action="report_error"):
        self.error = {"code": code, "recovery_class": "REJECT", "stage": "state_store", "retryable": False,
                      "attempt": 1, "max_attempts": 1, "message": message, "details": details or {},
                      "next_action": next_action, "secondary_causes": [], "side_effect": "none",
                      "operator_message": None}
        super().__init__(message)


def _redact(value):
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if str(key).casefold() in SENSITIVE else _redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value[:1024]]
    return value


class OrchestrationStateStore:
    def __init__(self, root, *, file_max_bytes=5 * 1024 * 1024, lock_timeout=2.0, stale_lock_seconds=30.0):
        self.root = Path(root)
        self.file_max_bytes = int(file_max_bytes)
        self.lock_timeout = float(lock_timeout)
        self.stale_lock_seconds = float(stale_lock_seconds)

    def _build_dir(self, build_id):
        if not isinstance(build_id, str) or not ID_RE.fullmatch(build_id) or build_id in {".", ".."}:
            raise StateStoreError("build_id is not path-safe", "INPUT_INVALID", details={"field": "build_id"}, next_action="repair_input")
        return self.root / build_id

    def _lock(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        lock = directory / ".lock"
        deadline = time.monotonic() + self.lock_timeout
        while True:
            try:
                handle = lock.open("x", encoding="utf-8")
                handle.write(json.dumps({"pid": os.getpid(), "created": time.time()}))
                handle.flush()
                return lock, handle
            except FileExistsError:
                try:
                    if time.time() - lock.stat().st_mtime > self.stale_lock_seconds:
                        lock.unlink()
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise StateStoreError("state lock is busy", "STATE_LOCK_TIMEOUT", next_action="retry_later")
                time.sleep(0.02)

    @staticmethod
    def _unlock(lock, handle):
        try:
            handle.close()
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass

    def _envelope(self, payload, metadata):
        metadata = metadata or {}
        return {"schema_version": str(metadata.get("schema_version", "1.0")),
                "gamePatch": metadata.get("gamePatch"), "pobVersion": metadata.get("pobVersion"),
                "dataRevision": metadata.get("dataRevision"), "payload": _redact(payload)}

    def _write(self, path, value):
        data = self._encode(path, value)
        temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            with temp.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if path.exists():
                shutil.copy2(path, backup)
            os.replace(temp, path)
        except OSError as error:
            try:
                temp.unlink()
            except OSError:
                pass
            raise StateStoreError(str(error), "STATE_WRITE_FAILED") from error

    def _encode(self, path, value):
        try:
            data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise StateStoreError("state is not JSON serializable", "INPUT_INVALID", details={"file": path.name}, next_action="repair_input") from error
        if len(data) > self.file_max_bytes:
            raise StateStoreError("state file quota exceeded", "CACHE_QUOTA_EXCEEDED", details={"file": path.name, "bytes": len(data), "limit": self.file_max_bytes}, next_action="human_review")
        return data

    def _atomic_write_set(self, directory, encoded):
        """Stage the complete set, then commit it with rollback protection."""
        stage = directory / (".state-stage-" + uuid.uuid4().hex)
        rollback = stage / ".rollback"
        stage.mkdir()
        rollback.mkdir()
        targets = [directory / (name + ".json") for name in FILES]
        replaced = []
        try:
            for target, value, data in encoded:
                staged = stage / target.name
                with staged.open("wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            for target in targets:
                if target.exists():
                    shutil.copy2(target, rollback / target.name)
            for target in targets:
                staged = stage / target.name
                if target.exists():
                    shutil.copy2(target, target.with_suffix(target.suffix + ".bak"))
                os.replace(staged, target)
                replaced.append(target)
            try:
                directory_handle = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(directory_handle)
                finally:
                    os.close(directory_handle)
            except OSError:
                pass
        except OSError as error:
            for target in replaced:
                backup = rollback / target.name
                try:
                    if backup.exists():
                        shutil.copy2(backup, target)
                    else:
                        target.unlink()
                except OSError:
                    pass
            raise StateStoreError(str(error), "STATE_WRITE_FAILED", next_action="retry_later") from error
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def save_state(self, build_id, state, *, metadata=None, expected_snapshot_revision=None):
        if not isinstance(state, dict):
            raise StateStoreError("state must be an object", "INPUT_INVALID", next_action="repair_input")
        directory = self._build_dir(build_id)
        lock, handle = self._lock(directory)
        try:
            current = self._read_one(directory / "snapshot.json", allow_backup=True)
            current_revision = ((current or {}).get("payload") or {}).get("snapshotRevision") if current else None
            if expected_snapshot_revision is not None and expected_snapshot_revision != current_revision:
                raise StateStoreError("snapshot revision is stale", "SNAPSHOT_REVISION_CONFLICT", details={"expected": expected_snapshot_revision, "actual": current_revision}, next_action="recapture_snapshot")
            # Validate every serialized payload before the first replacement so
            # quota/encoding failures cannot leave a mixed state set.
            encoded = []
            for name in FILES:
                path = directory / (name + ".json")
                envelope = self._envelope(state.get(name, {}), metadata)
                encoded.append((path, envelope, self._encode(path, envelope)))
            self._atomic_write_set(directory, encoded)
            return self.load_state(build_id, expected_metadata=metadata)
        finally:
            self._unlock(lock, handle)

    def _read_one(self, path, *, allow_backup=True):
        def read(candidate):
            with candidate.open(encoding="utf-8") as handle:
                return json.load(handle)
        try:
            return read(path)
        except (OSError, json.JSONDecodeError):
            if allow_backup and path.with_suffix(path.suffix + ".bak").exists():
                try:
                    return read(path.with_suffix(path.suffix + ".bak"))
                except (OSError, json.JSONDecodeError):
                    pass
            if path.exists() or path.with_suffix(path.suffix + ".bak").exists():
                raise StateStoreError("state file is corrupt", "STATE_CORRUPT", details={"file": path.name}, next_action="human_review")
            return None

    def load_state(self, build_id, *, expected_metadata=None):
        directory = self._build_dir(build_id)
        result = {}
        for name in FILES:
            envelope = self._read_one(directory / (name + ".json"))
            if envelope is None:
                continue
            if expected_metadata:
                for key in ("gamePatch", "pobVersion", "dataRevision"):
                    expected = expected_metadata.get(key)
                    if expected is not None and envelope.get(key) != expected:
                        raise StateStoreError("state metadata version mismatch", "VERSION_MISMATCH", details={"field": key, "expected": expected, "actual": envelope.get(key)}, next_action="refresh_context")
            result[name] = envelope.get("payload", {})
        if not result:
            raise StateStoreError("state is missing", "STATE_NOT_FOUND", next_action="refresh_context")
        return result

    def save_pending(self, build_id, pending, *, metadata=None):
        if not isinstance(pending, dict):
            raise StateStoreError("pending state must be an object", "INPUT_INVALID", next_action="repair_input")
        current = self.load_state(build_id) if self._build_dir(build_id).exists() else {}
        current["orchestration"] = {"pending": pending}
        return self.save_state(build_id, current, metadata=metadata)

    def resume_pending(self, build_id):
        return self.load_state(build_id).get("orchestration", {}).get("pending")

    def clone_build(self, source_id, target_id):
        source, target = self._build_dir(source_id), self._build_dir(target_id)
        if source == target:
            raise StateStoreError("clone target must differ from source", "INPUT_INVALID", next_action="repair_input")
        if not source.is_dir():
            raise StateStoreError("source build state is missing", "STATE_NOT_FOUND")
        temp = target.with_name(target.name + ".clone-" + uuid.uuid4().hex)
        try:
            shutil.copytree(source, temp, ignore=shutil.ignore_patterns(".lock", "*.tmp"))
            for path in temp.glob("*.json"):
                with path.open(encoding="utf-8") as handle:
                    json.load(handle)
            if target.exists():
                raise StateStoreError("clone target already exists", "STATE_EXISTS")
            os.replace(temp, target)
            return self.load_state(target_id)
        except StateStoreError:
            shutil.rmtree(temp, ignore_errors=True)
            raise
        except (OSError, json.JSONDecodeError) as error:
            shutil.rmtree(temp, ignore_errors=True)
            raise StateStoreError(str(error), "CLONE_FAILED") from error
