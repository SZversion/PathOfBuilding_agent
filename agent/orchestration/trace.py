"""Bounded, memory-only execution trace for one Agent run."""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone


EVENTS = {
    "run_started", "provider_started", "provider_completed", "provider_failed",
    "planner_started", "planner_completed", "planner_failed", "tool_started",
    "tool_completed", "tool_failed", "final_started", "final_completed",
    "final_failed", "run_completed", "trace_overflow",
}
TERMINAL_EVENTS = {"run_completed", "final_failed", "run_failed"}
MAX_EVENTS = 256
MAX_BYTES = 1024 * 1024
_SAFE_ARG_KEYS = {"skillName", "supportName", "stat", "skillSetSelector", "itemSetSelector", "buildId", "skillIndex", "socketGroup", "gemIdentity", "level", "quality", "enabled", "limit", "nodeId", "operation", "slot"}
_SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "token", "rawxml", "itemtext", "prompt", "notes", "freetext", "beforestate", "afterstate", "snapshot"}


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_args(arguments):
    if not isinstance(arguments, dict):
        return {"type": type(arguments).__name__}
    result = {}
    for key, value in arguments.items():
        normalized = str(key).casefold()
        if normalized in _SENSITIVE_KEYS or key not in _SAFE_ARG_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = {"type": type(value).__name__, "length": len(value) if isinstance(value, str) else None}
        else:
            result[key] = {"type": type(value).__name__}
    return result


def _safe_result(value):
    if isinstance(value, dict):
        return {str(key): _safe_result(item) for key, item in value.items() if str(key).casefold() not in _SENSITIVE_KEYS and str(key).casefold() not in {"message", "text", "itemtext", "prompt"}}
    if isinstance(value, list):
        return [_safe_result(item) for item in value[:32]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value if not isinstance(value, str) or len(value) <= 128 else {"type": "string", "length": len(value)}
    return {"type": type(value).__name__}


class TraceRecorder:
    def __init__(self, request_id=None, *, max_events=MAX_EVENTS, max_bytes=MAX_BYTES, exporter=None):
        self.request_id = request_id or "req-" + uuid.uuid4().hex
        self.run_id = "run-" + uuid.uuid4().hex
        self.max_events = max_events
        self.max_bytes = max_bytes
        self.events = []
        self._started = time.monotonic()
        self._overflowed = False
        self._warning = None
        self.snapshot = {"revision": None, "build_id": None}
        self.exporter = exporter
        self.export_result = None
        self.input_payload = None
        self.output_payload = None
        self._payloads = {}

    def set_snapshot(self, revision=None, build_id=None):
        self.snapshot = {"revision": revision if isinstance(revision, str) else None, "build_id": build_id if isinstance(build_id, str) else None}

    def provider_metadata(self, provider):
        endpoint = getattr(provider, "endpoint", None)
        return {"mode": getattr(provider, "mode", "remote"), "model": getattr(provider, "model", None), "endpoint_ref": "endpoint:" + _hash(endpoint) if isinstance(endpoint, str) else None}

    def _event(self, name, stage, status, *, attempt=1, max_attempts=None, provider=None, tool=None, step_index=None, tool_call_count=None, retry_of=None, plan_ref=None, query_ref=None, safe_args_ref=None, error_ref=None, result_ref=None, prompt_ref=None, input_payload=None, output_payload=None, duration_ms=None):
        if name == "run_completed":
            input_payload = self.input_payload if input_payload is None else input_payload
            output_payload = self.output_payload if output_payload is None else output_payload
            if output_payload is None:
                output_payload = {"status": status, "error_ref": error_ref}
        event = {"schema_version": "1.0", "event_id": "evt-" + uuid.uuid4().hex, "run_id": self.run_id, "request_id": self.request_id, "event": name, "stage": stage, "timestamp_utc": _utc_now(), "duration_ms": duration_ms, "status": status, "attempt": attempt, "max_attempts": max_attempts, "provider": provider or {"mode": None, "model": None, "endpoint_ref": None}, "snapshot": dict(self.snapshot), "tool": tool, "step_index": step_index, "tool_call_count": tool_call_count, "retry_of": retry_of, "plan_ref": plan_ref, "query_ref": query_ref, "safe_args_ref": safe_args_ref, "error_ref": error_ref, "result_ref": result_ref or {"facts_ref": None, "trace_ref": None, "sources_ref": None, "evidence_graph_ref": None}, "prompt_ref": prompt_ref}
        if input_payload is not None or output_payload is not None:
            self._payloads[event["event_id"]] = {"input_payload": input_payload, "output_payload": output_payload}
        return event

    def _append(self, event):
        encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        if len(self.events) < self.max_events and sum(len(json.dumps(item, ensure_ascii=False, separators=(",", ":"))) for item in self.events) + len(encoded) <= self.max_bytes:
            self.events.append(event)
            return
        self._overflowed = True
        if self._warning is None:
            self._warning = self._event("trace_overflow", "run", "partial", error_ref="TRACE_OVERFLOW")
            if len(self.events) >= self.max_events and len(self.events) > 1:
                self.events.pop(1)
            if len(self.events) < self.max_events:
                self.events.append(self._warning)
        if event["event"] in TERMINAL_EVENTS:
            keep = [item for item in self.events if item["event"] in {"run_started", "run_warning", "trace_overflow"} or item["status"] in {"failed", "rejected"}]
            keep.append(event)
            self.events = keep[-self.max_events:]

    def emit(self, event, stage, status, **kwargs):
        try:
            if event not in EVENTS:
                event = "trace_overflow"
            if kwargs.get("duration_ms") is None and status != "started":
                kwargs["duration_ms"] = round((time.monotonic() - self._started) * 1000)
            self._append(self._event(event, stage, status, **kwargs))
            if event == "run_completed" and self.exporter is not None and self.export_result is None:
                try:
                    try:
                        export_events = []
                        for event in self.events:
                            enriched = dict(event)
                            enriched.update(self._payloads.get(event.get("event_id"), {}))
                            export_events.append(enriched)
                        self.export_result = self.exporter.export(export_events, input_payload=getattr(self, "input_payload", None), output_payload=getattr(self, "output_payload", None))
                    except TypeError as error:
                        # Preserve compatibility with small injected exporters used by callers/tests.
                        if "input_payload" not in str(error) and "output_payload" not in str(error):
                            raise
                        self.export_result = self.exporter.export(list(self.events))
                except Exception as error:
                    self._warning = self._warning or "exporter_failure:" + type(error).__name__
        except Exception as error:
            # Trace must never interrupt PoB calculation or final response.
            self._warning = self._warning or "recorder_failure:" + type(error).__name__

    def safe_args_ref(self, arguments):
        safe = _safe_args(arguments)
        return "args:" + _hash(json.dumps(safe, sort_keys=True, separators=(",", ":")))

    def plan_ref(self, plan):
        return "plan:" + _hash(json.dumps({"intent": plan.get("intent"), "steps": [step.get("tool") for step in plan.get("steps", [])]} if isinstance(plan, dict) else {}, sort_keys=True, separators=(",", ":")))

    def query_ref(self, query):
        return "query:" + _hash(json.dumps(query if isinstance(query, dict) else {"text": query}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    def prompt_ref(self, messages):
        return "prompt:" + _hash(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    def set_input(self, value):
        self.input_payload = value

    def set_output(self, value):
        self.output_payload = value

    def result_refs(self, result):
        if not isinstance(result, dict):
            return {"facts_ref": None, "trace_ref": None, "sources_ref": None, "evidence_graph_ref": None}
        return {key: ("ref:" + _hash(json.dumps(_safe_result(result.get(source)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))) if source in result else None) for key, source in (("facts_ref", "facts"), ("trace_ref", "trace"), ("sources_ref", "sources"), ("evidence_graph_ref", "evidenceGraph"))}

    def snapshot_refs(self):
        return dict(self.snapshot)

    def finish(self, status="ok", *, error_ref=None, outcome=None):
        self.emit("run_completed", "run", status, error_ref=error_ref, result_ref={"facts_ref": None, "trace_ref": None, "sources_ref": None, "evidence_graph_ref": None})
        return list(self.events)
