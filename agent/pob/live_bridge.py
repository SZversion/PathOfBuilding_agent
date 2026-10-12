"""Small Python boundary for the read-only dispatcher inside a live PoB process."""

import hashlib
import json

from .bridge import project_snapshot

MUTATION_TOOLS = frozenset({"replace_item", "replace_gem", "change_passive"})


class LivePobBridgeError(RuntimeError):
    def __init__(self, message, *, code="VALUE_UNAVAILABLE", stage="live_bridge", details=None, recovery_class="REJECT", next_action="reject_request", operator_message=None):
        self.error = {
            "code": code, "recovery_class": recovery_class, "stage": stage,
            "retryable": False, "attempt": 1, "max_attempts": 1,
            "message": message, "details": details or {},
            "next_action": next_action, "secondary_causes": [],
            "snapshotRevision": None, "side_effect": "none", "operator_message": operator_message,
        }
        super().__init__(message)


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


class LivePobBridge:
    """Adapt AgentInProcess.currentBuild/capture_snapshot to AgentLoop handlers.

    The adapter is deliberately injected: transport into the running Lua VM is
    PoB-host-specific, while this boundary keeps readiness, projection and
    structured failures identical for any transport.
    """

    def __init__(self, adapter=None, *, request=None):
        if adapter is None and request is None:
            raise TypeError("a live adapter or request transport is required")
        self.adapter = adapter
        self.request = request or (adapter if callable(adapter) else None)
        self.mode = "live_read_only"

    @staticmethod
    def _response(value, stage):
        if not isinstance(value, dict):
            raise LivePobBridgeError("live transport returned a non-object", code="BRIDGE_PROTOCOL_ERROR", stage=stage)
        if value.get("ok") is False:
            error = value.get("error") if isinstance(value.get("error"), dict) else {}
            raise LivePobBridgeError(error.get("message", "live transport failed"), code=error.get("code", "BRIDGE_PROTOCOL_ERROR"), stage=error.get("stage", stage), details=error.get("details"))
        return value.get("result", value)

    def _current_build(self):
        if self.request is not None:
            try:
                return self._response(self.request({"operation": "currentBuild"}), "current_build")
            except LivePobBridgeError:
                raise
            except Exception as error:
                raise LivePobBridgeError(str(error), code="BRIDGE_PROTOCOL_ERROR", stage="current_build") from error
        method = getattr(self.adapter, "currentBuild", None) or getattr(self.adapter, "current_build", None)
        if not callable(method):
            raise LivePobBridgeError("live adapter does not expose currentBuild", code="BRIDGE_PROTOCOL_ERROR", stage="bridge_capability")
        try:
            build = method()
        except Exception as error:
            raise LivePobBridgeError(str(error), code="BRIDGE_PROTOCOL_ERROR", stage="current_build") from error
        if build is None:
            raise LivePobBridgeError("running PoB build is unavailable")
        return build

    @staticmethod
    def _ready(build):
        calcs = _get(build, "calcsTab")
        env = _get(calcs, "mainEnv")
        player = _get(env, "player")
        return calcs is not None and env is not None and player is not None

    def readiness(self):
        try:
            build = self._current_build()
            ready = self._ready(build)
            return {"ready": ready, "mode": self.mode, "mainEnv": _get(_get(build, "calcsTab"), "mainEnv") is not None,
                    "player": _get(_get(_get(build, "calcsTab"), "mainEnv"), "player") is not None,
                    "error": None if ready else {"code": "VALUE_UNAVAILABLE", "stage": "readiness", "message": "PoB mainEnv/player is unavailable"}}
        except LivePobBridgeError as error:
            return {"ready": False, "mode": self.mode, "mainEnv": False, "player": False, "error": error.error}

    def capture(self):
        build = self._current_build()
        if not self._ready(build):
            raise LivePobBridgeError("PoB mainEnv/player is unavailable", stage="snapshot_capture")
        if self.request is not None:
            try:
                raw = self._response(self.request({"tool": "capture_snapshot", "arguments": {}}), "snapshot_capture")
            except LivePobBridgeError:
                raise
            except Exception as error:
                raise LivePobBridgeError(str(error), code="BRIDGE_PROTOCOL_ERROR", stage="snapshot_capture") from error
            capture = None
        else:
            capture = getattr(self.adapter, "capture_snapshot", None) or getattr(self.adapter, "capture", None)
            raw = None
        if not callable(capture):
            if self.request is None:
                raise LivePobBridgeError("live adapter does not expose AgentSnapshot.capture", code="BRIDGE_PROTOCOL_ERROR", stage="snapshot_capture")
        if callable(capture):
            try:
                raw = capture(build)
            except Exception as error:
                raise LivePobBridgeError(str(error), code="BRIDGE_PROTOCOL_ERROR", stage="snapshot_capture") from error
        if isinstance(raw, tuple):
            raw, error = raw
            if raw is None:
                if isinstance(error, dict):
                    raise LivePobBridgeError(error.get("message", "snapshot capture failed"), code=error.get("code", "VALUE_UNAVAILABLE"), stage=error.get("stage", "snapshot_capture"), details=error.get("details"))
                raise LivePobBridgeError(str(error or "snapshot capture failed"), stage="snapshot_capture")
        if not isinstance(raw, dict):
            raise LivePobBridgeError("AgentSnapshot.capture returned a non-object", code="BRIDGE_PROTOCOL_ERROR", stage="snapshot_capture")
        snapshot = project_snapshot(raw.get("context", raw))
        revision = raw.get("snapshotRevision")
        if not isinstance(revision, str) or not revision:
            revision = "live:" + hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]
        snapshot["snapshotRevision"] = revision
        snapshot["authoritative"] = True
        snapshot["mode"] = self.mode
        return snapshot

    def call(self, tool, arguments=None):
        if tool in MUTATION_TOOLS:
            raise LivePobBridgeError(
                "live PoB adapter is read-only; mutation is not enabled",
                code="MUTATION_NOT_PERSISTENT", stage="bridge_capability",
                operator_message="Live mutation requires a persistent in-process PoB session",
            )
        build = self._current_build()
        if not self._ready(build):
            raise LivePobBridgeError("PoB mainEnv/player is unavailable", stage="tool_dispatch")
        if self.request is not None:
            try:
                result = self._response(self.request({"tool": tool, "arguments": dict(arguments or {})}), "tool_execution")
            except LivePobBridgeError:
                raise
            except Exception as error:
                raise LivePobBridgeError(str(error), code="BRIDGE_PROTOCOL_ERROR", stage="tool_execution") from error
            if not isinstance(result, dict):
                raise LivePobBridgeError("PoB Tool returned a non-object", code="BRIDGE_PROTOCOL_ERROR", stage="tool_execution")
            return result
        dispatch = getattr(self.adapter, "dispatch", None)
        if not callable(dispatch):
            raise LivePobBridgeError("live adapter does not expose AgentInProcess.dispatch", code="BRIDGE_PROTOCOL_ERROR", stage="tool_dispatch")
        request = {"tool": tool, "arguments": dict(arguments or {})}
        try:
            result = dispatch(request)
        except TypeError:
            result = dispatch(tool, request["arguments"])
        if isinstance(result, tuple):
            result, error = result
            if result is None:
                if isinstance(error, dict):
                    raise LivePobBridgeError(error.get("message", "PoB Tool failed"), code=error.get("code", "VALUE_UNAVAILABLE"), stage=error.get("stage", "tool_execution"), details=error.get("details"))
                raise LivePobBridgeError(str(error or "PoB Tool failed"), stage="tool_execution")
        if not isinstance(result, dict):
            raise LivePobBridgeError("PoB Tool returned a non-object", code="BRIDGE_PROTOCOL_ERROR", stage="tool_execution")
        if "error" in result and result.get("ok") is False:
            error = result["error"] if isinstance(result["error"], dict) else {}
            raise LivePobBridgeError(error.get("message", "PoB Tool failed"), code=error.get("code", "VALUE_UNAVAILABLE"), stage=error.get("stage", "tool_execution"), details=error.get("details"))
        return result.get("result", result)

    def snapshot_provider(self):
        return self.capture()

    def handlers(self, tools):
        return {name: (lambda arguments, name=name: self.call(name, arguments)) for name in tools}
