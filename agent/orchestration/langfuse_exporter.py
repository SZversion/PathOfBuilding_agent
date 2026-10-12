"""Optional development-only exporter for the existing sanitized Agent Trace."""

import hashlib
import importlib
import json
import re
import os
import threading
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class ExportResult:
    status: str
    reason: str = ""


def _bounded_call(function, timeout):
    result = {"error": None}

    def run():
        try:
            function()
        except Exception as error:  # exporter boundary only
            result["error"] = error

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return TimeoutError("Langfuse operation timed out")
    return result["error"]


class LangfuseExporter:
    def __init__(self, client=None, *, enabled=False, reason="disabled", timeout=2.0, close_retries=1, queue_path=None, queue_max_bytes=10 * 1024 * 1024):
        self.client = client
        self.enabled = bool(enabled)
        self.reason = reason
        self.timeout = timeout
        self.close_retries = close_retries
        self._sample_rate = 1.0 if enabled else 0.0
        self._exported_run_ids = set()
        self.warnings = []
        self.queue_path = Path(queue_path or "data/traces/langfuse-queue.ndjson")
        self.queue_max_bytes = int(queue_max_bytes)
        self._queue_lock = threading.Lock()
        self._queued_run_ids = self._read_queued_ids()

    def _read_queued_ids(self):
        ids = set()
        try:
            for line in self.queue_path.read_text(encoding="utf-8").splitlines():
                try:
                    value = __import__("json").loads(line)
                    if isinstance(value, dict) and isinstance(value.get("run_id"), str):
                        ids.add(value["run_id"])
                except ValueError:
                    continue
        except OSError:
            pass
        return ids

    @classmethod
    def from_env(cls, env=None, *, sdk_module=None, timeout=2.0):
        values = dict(os.environ if env is None else env)
        root_env = Path(__file__).parents[2] / ".env"
        if root_env.is_file():
            try:
                for line in root_env.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key, value = key.strip(), value.strip().strip("\"'")
                    if key and key not in values:
                        values[key] = value
            except OSError:
                pass
        queue_path = values.get("POB_AGENT_LANGFUSE_QUEUE_PATH") or "data/traces/langfuse-queue.ndjson"
        try:
            queue_max_bytes = int(values.get("POB_AGENT_LANGFUSE_QUEUE_MAX_BYTES", 10 * 1024 * 1024))
        except (TypeError, ValueError):
            queue_max_bytes = 10 * 1024 * 1024
        try:
            sample = float(values.get("POB_AGENT_LANGFUSE_SAMPLE_RATE", "1"))
        except (TypeError, ValueError):
            return cls(enabled=True, reason="invalid sampling rate", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        if sample <= 0:
            return cls(enabled=True, reason="sampling is disabled", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        if sample > 1:
            return cls(enabled=True, reason="sampling rate must be between 0 and 1", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        required = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")
        if any(not values.get(key) for key in required):
            return cls(enabled=True, reason="queue_only: incomplete Langfuse configuration", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        host = urlparse(values["LANGFUSE_BASE_URL"]).hostname
        allowed_hosts = {"localhost", "127.0.0.1", "::1"}
        allowed_hosts.update(item.strip() for item in values.get("POB_AGENT_LANGFUSE_ALLOWED_HOSTS", "").split(",") if item.strip())
        if host not in allowed_hosts:
            return cls(enabled=True, reason="queue_only: Langfuse host must be local", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        if sdk_module is None:
            try:
                sdk_module = importlib.import_module("langfuse")
            except ImportError:
                return cls(enabled=True, reason="queue_only: Langfuse SDK is unavailable", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        version = str(getattr(sdk_module, "__version__", "4"))
        if not version.startswith("4."):
            return cls(enabled=True, reason="queue_only: Langfuse SDK 4.x is required", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        try:
            client = sdk_module.Langfuse(public_key=values["LANGFUSE_PUBLIC_KEY"], secret_key=values["LANGFUSE_SECRET_KEY"], host=values["LANGFUSE_BASE_URL"])
        except Exception:
            return cls(enabled=True, reason="queue_only: Langfuse SDK initialization failed", timeout=timeout, queue_path=queue_path, queue_max_bytes=queue_max_bytes)
        exporter = cls(client, enabled=True, reason="enabled", timeout=timeout,
                       queue_path=queue_path,
                       queue_max_bytes=queue_max_bytes)
        exporter._sample_rate = sample
        return exporter

    def _sampled(self, run_id):
        rate = getattr(self, "_sample_rate", 0)
        if rate >= 1:
            return True
        digest = int(hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12], 16) / float(16 ** 12)
        return digest < rate

    @classmethod
    def _payload(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (ValueError, TypeError):
                parsed = value
            if isinstance(parsed, (dict, list)):
                return cls._payload(parsed)
            for key, secret in os.environ.items():
                if any(part in key.upper() for part in ("KEY", "TOKEN", "PASSWORD", "SECRET")) and len(secret) >= 8:
                    value = value.replace(secret, "[REDACTED]")
            return re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]+", "Bearer [REDACTED]", value)
        if isinstance(value, dict):
            credentials = {"apikey", "authorization", "token", "accesstoken", "refreshtoken",
                           "password", "secret", "secretkey", "publickey"}
            return {key: ("[REDACTED]" if str(key).lower().replace("_", "").replace("-", "") in credentials
                          else cls._payload(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._payload(item) for item in value]
        return value

    @staticmethod
    def _timestamp(event):
        value = event.get("timestamp_utc")
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

    @contextmanager
    def _observation(self, client, *, start_time=None, end_time=None, **kwargs):
        if hasattr(client, "_otel_tracer") and start_time is not None:
            # SDK 4.x has no start_time argument; use its OpenTelemetry tracer
            # to preserve historical timestamps instead of export-time latency.
            from opentelemetry import trace
            trace_context = kwargs.pop("trace_context", None)
            parent = (trace.use_span(client._create_remote_parent_span(trace_id=trace_context["trace_id"], parent_span_id=trace_context.get("parent_span_id")))
                      if trace_context else nullcontext())
            with parent:
                span = client._otel_tracer.start_span(name=kwargs.pop("name"),
                                                     start_time=int(start_time.timestamp() * 1_000_000_000))
            if trace_context:
                from langfuse._client.attributes import LangfuseOtelSpanAttributes
                span.set_attribute(LangfuseOtelSpanAttributes.AS_ROOT, True)
            try:
                observation = client._create_observation_from_otel_span(otel_span=span, **kwargs)
                with trace.use_span(span, end_on_exit=False):
                    yield observation
            finally:
                span.end(end_time=int(end_time.timestamp() * 1_000_000_000) if end_time else None)
        else:
            with client.start_as_current_observation(**kwargs) as observation:
                yield observation

    @staticmethod
    def _safe_event(event):
        provider = event.get("provider") if isinstance(event.get("provider"), dict) else {}
        snapshot = event.get("snapshot") if isinstance(event.get("snapshot"), dict) else {}
        result = event.get("result_ref") if isinstance(event.get("result_ref"), dict) else {}
        return {
            "event_id": event.get("event_id"), "event": event.get("event"), "stage": event.get("stage"),
            "timestamp_utc": event.get("timestamp_utc"), "duration_ms": event.get("duration_ms"),
            "status": event.get("status"), "attempt": event.get("attempt"), "max_attempts": event.get("max_attempts"), "tool": event.get("tool"),
            "step_index": event.get("step_index"), "tool_call_count": event.get("tool_call_count"),
            "retry_of": event.get("retry_of"), "plan_ref": event.get("plan_ref"), "query_ref": event.get("query_ref"),
            "safe_args_ref": event.get("safe_args_ref"), "prompt_ref": event.get("prompt_ref"),
            "error_ref": event.get("error_ref"), "error_code": event.get("error_code"), "error_details": event.get("error_details", {}), "provider": {"mode": provider.get("mode"), "model": provider.get("model"), "endpoint_ref": provider.get("endpoint_ref")},
            "presentation_class": event.get("presentation_class"),
            "snapshot": {"revision": snapshot.get("revision"), "build_id": snapshot.get("build_id")},
            "result_ref": {key: result.get(key) for key in ("facts_ref", "trace_ref", "sources_ref", "evidence_graph_ref")},
            "input": LangfuseExporter._payload(event.get("input_payload")),
            "output": LangfuseExporter._payload(event.get("output_payload")),
        }

    def _record_event(self, trace, event):
        safe = self._safe_event(event)
        metadata = {key: value for key, value in safe.items() if key not in {"event_id", "event", "timestamp_utc", "duration_ms", "input", "output"}}
        # Langfuse 4.x creates child observations from the current observation.
        # Keep the fallback for injected test clients that expose a simple span.
        if hasattr(trace, "start_as_current_observation"):
            end_time = self._timestamp(event)
            duration = event.get("duration_ms") or 0
            start_time = end_time - timedelta(milliseconds=duration) if end_time else None
            return self._observation(trace, name=safe["event"] or "event", as_type="span", input=safe.get("input"), output=safe.get("output"), metadata=metadata, start_time=start_time, end_time=end_time)
        if hasattr(trace, "span"):
            trace.span(name=safe["event"], metadata=metadata)
            return nullcontext()
        if hasattr(trace, "event"):
            trace.event(name=safe["event"], metadata=metadata)
        return nullcontext()

    def _queue(self, events, reason):
        run_id = events[0].get("run_id") if events else None
        if not isinstance(run_id, str) or run_id in self._queued_run_ids:
            return ExportResult("queued", "duplicate_or_invalid_run")
        import json
        record = (json.dumps({"run_id": run_id, "request_id": events[0].get("request_id"),
                              "events": [self._safe_event(event) for event in events]}, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._queue_lock:
            try:
                self.queue_path.parent.mkdir(parents=True, exist_ok=True)
                mode = "ab"
                with self.queue_path.open(mode) as handle:
                    handle.seek(0, 2)
                    current = handle.tell()
                    if current:
                        handle.seek(0)
                        existing = handle.read()
                        tail = existing.rfind(b"\n")
                        if tail != len(existing) - 1:
                            handle.seek(tail + 1)
                            handle.truncate()
                            current = tail + 1
                        handle.seek(0, 2)
                    if current + len(record) > self.queue_max_bytes:
                        self.warnings.append("queue_cap_exceeded")
                        return ExportResult("unavailable", "queue_cap_exceeded")
                    written = handle.write(record)
                    if written != len(record):
                        handle.seek(current)
                        handle.truncate()
                        self.warnings.append("queue_partial_write")
                        return ExportResult("unavailable", "queue_partial_write")
                    handle.flush()
                self._queued_run_ids.add(run_id)
                self.warnings.append("queued:" + reason)
                return ExportResult("queued", reason)
            except OSError:
                self.warnings.append("queue_write_failed")
                return ExportResult("unavailable", "queue_write_failed")

    @staticmethod
    def _trace_context(run_id):
        # Langfuse accepts a W3C-compatible 32-hex trace id.  Import lazily so
        # the optional exporter remains importable without the SDK installed.
        try:
            from langfuse.types import TraceContext
            return TraceContext(trace_id=hashlib.sha256(("pob-agent:" + run_id).encode("utf-8")).hexdigest()[:32])
        except Exception:
            return None

    def export(self, events, *, input_payload=None, output_payload=None):
        try:
            if not self.enabled or not events:
                return ExportResult("disabled", self.reason)
            run_id = events[0].get("run_id")
            if not isinstance(run_id, str) or run_id in self._exported_run_ids or not self._sampled(run_id):
                return ExportResult("disabled", "not sampled or already exported")
            if self.client is None:
                self._exported_run_ids.add(run_id)
                return self._queue(events, self.reason)
            request_id = events[0].get("request_id")
            metadata = {"run_id": run_id, "request_id": request_id}
            if output_payload is None:
                terminal = next((event for event in reversed(events) if event.get("event") in {"run_completed", "final_failed"}), events[-1])
                output_payload = {"status": terminal.get("status"), "error_ref": terminal.get("error_ref")}
            trace_context = self._trace_context(run_id)
            root_kwargs = {
                "name": "pob-agent",
                "as_type": "chain",
                "input": self._payload(input_payload),
                "output": self._payload(output_payload),
                "metadata": metadata,
            }
            if trace_context is not None:
                root_kwargs["trace_context"] = trace_context
            start = getattr(self.client, "start_as_current_observation", None)
            if start is None:
                return self._queue(events, "observation_api_unavailable")
            try:
                root = self._observation(self.client, start_time=self._timestamp(events[0]), end_time=self._timestamp(events[-1]), **root_kwargs)
            except TypeError:
                # Test doubles or minor SDK variants may not expose trace_context.
                root_kwargs.pop("trace_context", None)
                root = self._observation(self.client, start_time=self._timestamp(events[0]), end_time=self._timestamp(events[-1]), **root_kwargs)
            with root:
                for event in events:
                    observation = self._record_event(self.client, event)
                    with observation:
                        pass
            self._exported_run_ids.add(run_id)
            flush_error = None
            for _ in range(self.close_retries + 1):
                error = _bounded_call(lambda: self.client.flush(), self.timeout) if hasattr(self.client, "flush") else None
                if error is None:
                    break
                flush_error = error
            if hasattr(self.client, "shutdown"):
                close_operation = lambda: self.client.shutdown()
            elif hasattr(self.client, "close"):
                close_operation = lambda: self.client.close()
            else:
                close_operation = None
            close_error = None
            if close_operation is not None:
                for _ in range(self.close_retries + 1):
                    close_error = _bounded_call(close_operation, self.timeout)
                    if close_error is None:
                        break
            if flush_error is not None:
                self.warnings.append(type(flush_error).__name__)
                return self._queue(events, "flush_failed")
            if close_error is not None:
                self.warnings.append(type(close_error).__name__)
                return self._queue(events, "close_failed")
            return ExportResult("sent")
        except Exception as error:
            self.warnings.append(type(error).__name__)
            return self._queue(events, type(error).__name__)
