"""Request-scoped tracing of the major Python agent pipeline stages."""

from contextlib import contextmanager
import contextvars
import dis
import functools
from dataclasses import fields, is_dataclass
import hashlib
import inspect
from datetime import datetime, timezone
import time
import os
from pathlib import Path
import sys
import threading
import uuid

from .langfuse_exporter import LangfuseExporter, ExportResult, _bounded_call

_ACTIVE = contextvars.ContextVar("pob_function_trace", default=None)
_LOCAL = threading.local()
_EXCLUDED = {__name__, "agent.orchestration.trace", "agent.orchestration.langfuse_exporter"}
_STAGES = {
    "agent.mcp.client.McpToolClient.start": "mcp.connect",
    "agent.mcp.client.McpToolClient.list_tools": "mcp.tools",
    "agent.mcp.client.McpToolClient.read_resource": "snapshot.capture",
    "agent.orchestration.agent_loop.normalize_query": "input",
    "agent.cli._emit": "output",
    "agent.orchestration.runtime.SnapshotSync.prepare": "snapshot.prepare",
    "agent.orchestration.agent_loop.validate_plan": "plan.validate",
    "agent.orchestration.runtime.execute_plan": "tools.execute",
    "agent.mcp.client.McpToolClient.call_tool": "tool.execute",
}


def _errors(value):
    if not isinstance(value, dict):
        return []
    errors = [value["error"]] if value.get("error") else []
    for key in ("response", "execution"):
        errors.extend(_errors(value.get(key)))
    for step in value.get("steps", []) if isinstance(value.get("steps"), list) else []:
        errors.extend(_errors(step))
    return errors


class _ContextSpan:
    """Propagate the client span through MCP without duplicating its observation."""
    def __init__(self, session):
        self.session = session
        self.id = session.parent_id or uuid.uuid4().hex[:16]
    def get_trace_id(self): return self.session.trace_id
    def get_observation_id(self): return self.id


class _QueuedSpan:
    def __init__(self, session, name, arguments, parent, as_type="span", model=None):
        self.session = session
        self.id = uuid.uuid4().hex[:16]
        self.started = time.monotonic()
        self.event = {"event_id": self.id, "run_id": session.run_id, "event": name,
                      "stage": as_type, "status": "started", "input_payload": _value(arguments),
                      "provider": {"model": model},
                      "parent_event_id": parent}

    def get_trace_id(self): return self.session.trace_id
    def get_observation_id(self): return self.id

    def update(self, **values):
        if "output" in values:
            self.event["output_payload"] = values["output"]
        if values.get("level") == "ERROR":
            self.event["status"] = "failed"
        if "metadata" in values:
            self.event["error_details"] = {key: values["metadata"][key] for key in ("errors", "exceptions") if key in values["metadata"]}

    def end(self):
        self.event["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        self.event["duration_ms"] = round((time.monotonic() - self.started) * 1000)
        self.session.queue_records.append(self.event)


def current_trace():
    session = _ACTIVE.get()
    return session if session is not None and not session.closed else None


def _value(value, seen=None):
    seen = set() if seen is None else seen
    if value is None or isinstance(value, (str, int, float, bool)):
        return LangfuseExporter._payload(value)
    if isinstance(value, bytes):
        return LangfuseExporter._payload(value.decode("utf-8", errors="replace"))
    if isinstance(value, Path):
        return str(value)
    if type(value).__module__ in _EXCLUDED:
        return {"type": type(value).__name__}
    if id(value) in seen:
        return {"type": type(value).__name__, "reference": "cyclic"}
    if isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[0], (str, bytes)):
        header = value[0].decode("latin1") if isinstance(value[0], bytes) else value[0]
        if header.lower() in {"authorization", "cookie", "set-cookie"}:
            return [header, "[REDACTED]"]
    seen.add(id(value))
    try:
        if isinstance(value, dict):
            return LangfuseExporter._payload({str(k): _value(v, seen) for k, v in value.items()})
        if isinstance(value, (list, tuple, set, frozenset)):
            return [_value(v, seen) for v in value]
        if isinstance(value, type):
            return {"type": value.__module__ + "." + value.__qualname__}
        if is_dataclass(value):
            return _value({field.name: getattr(value, field.name, {"state": "uninitialized"}) for field in fields(value)}, seen)
        if hasattr(value, "model_dump"):
            return _value(value.model_dump(mode="python"), seen)
        if isinstance(value, BaseException):
            return {"type": type(value).__name__, "message": _value(str(value)),
                    "arguments": _value(value.args, seen), "details": _value(vars(value), seen),
                    "cause": _value(value.__cause__, seen)}
        if type(value).__module__.startswith(("agent.", "argparse", "types", "starlette")):
            attributes = (vars(value) if hasattr(value, "__dict__") else
                          {slot: getattr(value, slot) for slot in getattr(type(value), "__slots__", ())
                           if hasattr(value, slot)})
            return {"type": type(value).__name__, "attributes": _value(attributes, seen)}
        if callable(value):
            return {"callable": getattr(value, "__qualname__", type(value).__name__)}
        if hasattr(value, "__dict__"):
            return {"type": type(value).__name__, "attributes": _value(vars(value), seen)}
        return {"type": type(value).__module__ + "." + type(value).__name__}
    finally:
        seen.remove(id(value))


def _span_ids(span):
    if hasattr(span, "_otel_span"):
        context = span._otel_span.get_span_context()
        return f"{context.trace_id:032x}", f"{context.span_id:016x}"
    return span.get_trace_id(), span.get_observation_id()


def trace_headers():
    session = current_trace()
    if session is None or session.root is None:
        return {}
    _, parent = _span_ids(session.parent_span())
    return {"X-PoB-Trace-Run-Id": session.run_id, "X-PoB-Trace-Parent-Id": parent}


def trace_environment():
    headers = trace_headers()
    return {**os.environ, **({"POB_AGENT_TRACE_RUN_ID": headers["X-PoB-Trace-Run-Id"],
                              "POB_AGENT_TRACE_PARENT_ID": headers["X-PoB-Trace-Parent-Id"]}
                             if headers else {})}


def _module(globals):
    name = globals.get("__name__", "")
    spec = globals.get("__spec__")
    return spec.name if name == "__main__" and spec is not None else name


def _trace(frame, event, value):
    session = current_trace()
    module = _module(frame.f_globals)
    if session is None or session.root is None or session.closed or not module.startswith("agent.") or module in _EXCLUDED:
        return None
    function = module + "." + frame.f_code.co_qualname
    generation = module.startswith("agent.providers.") and frame.f_code.co_name in {"chat", "stream_chat"}
    if event == "call":
        frame.f_trace_lines = False
    if event == "exception":
        try:
            session.record_exception(value[1], function, frame)
        except Exception as error:
            session.warnings.append("exception:" + type(error).__name__)
    if function not in _STAGES and not generation:
        return _trace
    if function in {"agent.orchestration.agent_loop.normalize_query", "agent.cli._emit"} and session.parent_id:
        return _trace
    if function == "agent.orchestration.agent_loop.normalize_query" and session.input_value is not None:
        return _trace
    try:
        session.record(frame, event, value)
    except Exception as error:
        session.warnings.append(module + "." + frame.f_code.co_qualname + ": " + type(error).__name__ + ": " + str(_value(str(error))))
    return _trace


@contextmanager
def _trace_thread():
    previous = sys.gettrace()
    if current_trace() is not None and current_trace().root is not None:
        sys.settrace(_trace)
    try:
        yield
    finally:
        sys.settrace(previous)


class FunctionTrace:
    def __init__(self, name, arguments=None, *, run_id=None, parent_id=None):
        self.name = name
        self.arguments = arguments
        self.run_id = run_id or os.getenv("POB_AGENT_TRACE_RUN_ID") or "run-" + uuid.uuid4().hex
        self.parent_id = parent_id or os.getenv("POB_AGENT_TRACE_PARENT_ID")
        self.trace_id = hashlib.sha256(("pob-agent:" + self.run_id).encode()).hexdigest()[:32]
        self.exporter = None
        self.root = None
        self.frames = {}
        self.events = []
        self.queue_records = []
        self.output = None
        self.warnings = []
        self.closed = False
        self.input_span = None
        self.input_value = None
        self.output_recorded = False
        self.errors = []
        self.exceptions = []
        self.input_exceptions = []

    def record_exception(self, error, function, frame):
        if isinstance(self.root, _ContextSpan) and isinstance(error, (StopIteration, StopAsyncIteration, GeneratorExit)):
            return
        record = {**_value(error), "function": function, "file": frame.f_code.co_filename, "line": frame.f_lineno}
        target = self.input_exceptions if self.input_span is not None else self.exceptions
        while frame:
            if id(frame) in self.frames:
                target = self.frames[id(frame)]["exceptions"]
                break
            frame = frame.f_back
        for previous in target:
            if all(previous.get(key) == value for key, value in record.items()):
                previous["occurrences"] += 1
                return
        target.append({**record, "occurrences": 1})

    def record_error(self, error):
        self.errors.append(_value(error))

    def record_input(self, value):
        try:
            self.input_value = _value(value)
            self.root.update(input=self.input_value)
            self.input_span = self._start("input", self.input_value, _span_ids(self.root)[1])
        except Exception as error:
            self.warnings.append("input:" + type(error).__name__)

    def complete_input(self, value=None, error=None):
        if self.input_span is None:
            return
        try:
            errors = [_value(error)] if error else []
            self.input_span.update(output={"return": _value(value) if value is not None else self.input_value,
                                           "errors": errors, "exceptions": self.input_exceptions}, level="ERROR" if errors else "DEFAULT",
                                   metadata={"run_id": self.run_id, "errors": errors, "exceptions": self.input_exceptions})
            self.input_span.end()
        except Exception as failure:
            self.warnings.append("input:" + type(failure).__name__)
        finally:
            self.input_span = None

    def record_output(self, value):
        if self.output_recorded:
            return
        try:
            errors = _errors(value) + self.errors
            span = self._start("output", self.input_value or self.arguments, _span_ids(self.root)[1])
            span.update(output=_value(value), level="ERROR" if errors else "DEFAULT",
                        metadata={"run_id": self.run_id, "errors": _value(errors), "exceptions": self.exceptions})
            span.end()
            self.output = {**(self.output or {}), "response": value} if isinstance(self.output, dict) and "llm_outputs" in self.output else value
            self.output_recorded = True
        except Exception as failure:
            self.warnings.append("output:" + type(failure).__name__)

    def _start(self, name, arguments, parent=None, *, as_type="span", model=None):
        client = self.exporter.client
        if client is None:
            return _QueuedSpan(self, name, arguments, parent or self.parent_id, as_type, model)
        trace_context = {"trace_id": self.trace_id, "parent_span_id": parent or self.parent_id}
        generation = {"model": model} if as_type == "generation" else {}
        if hasattr(client, "_otel_tracer"):
            from opentelemetry import trace
            remote = client._create_remote_parent_span(**trace_context)
            with trace.use_span(remote):
                span = client._otel_tracer.start_span(name=name)
            return client._create_observation_from_otel_span(
                otel_span=span, as_type=as_type, input=_value(arguments),
                metadata={"run_id": self.run_id, "function": name}, **generation)
        return client.start_observation(name=name, as_type=as_type, input=_value(arguments),
                                        **generation,
                                        metadata={"run_id": self.run_id}, trace_context=trace_context)

    def parent_span(self, frame=None):
        frame = frame or sys._getframe(1)
        while frame:
            entry = self.frames.get(id(frame))
            if entry is not None:
                return entry["span"]
            frame = frame.f_back
        return self.root

    def record(self, frame, event, value):
        key = id(frame)
        if event == "call" and key not in self.frames:
            frame.f_trace_lines = False
            arguments = inspect.getargvalues(frame)
            names = arguments.args + [v for v in (arguments.varargs, arguments.keywords) if v]
            payload = {name: ({"type": type(arguments.locals[name]).__name__,
                               "object_id": f"{id(arguments.locals[name]):016x}"}
                              if name in {"self", "cls"} else _value(arguments.locals[name]))
                       for name in names}
            if _module(frame.f_globals) == "agent.cli" and frame.f_code.co_name == "<lambda>" and "token" in payload:
                # CLI callbacks name streamed text "token", which is not an auth credential.
                payload["stream_fragment"] = _value(arguments.locals["token"])
            parent = self.parent_span(frame.f_back)
            parent_id = _span_ids(parent)[1] if parent else None
            name = _module(frame.f_globals) + "." + frame.f_code.co_qualname
            generation = _module(frame.f_globals).startswith("agent.providers.") and frame.f_code.co_name in {"chat", "stream_chat"}
            stage = "generate" if generation else _STAGES[name]
            if stage == "tool.execute":
                stage = "tool." + str(frame.f_locals.get("name", "execute"))
            span = self._start(stage, payload.get("messages") if generation else payload, parent_id,
                               as_type="generation" if generation else "span",
                               model=getattr(frame.f_locals.get("self"), "model", None))
            self.frames[key] = {"span": span, "exceptions": [], "yields": [], "generation": generation, "stage": stage}
        elif key in self.frames:
            entry = self.frames[key]
            if event == "exception":
                pass  # Recorded above, including exceptions handled in helper functions.
            elif event == "return":
                opcode = dis.opname[frame.f_code.co_code[frame.f_lasti]]
                if opcode in {"YIELD_VALUE", "YIELD_FROM"}:
                    # Coroutine await suspensions are not function returns.
                    if not frame.f_code.co_flags & inspect.CO_COROUTINE:
                        entry["yields"].append(value if entry["generation"] else _value(value))
                    return
                returned = ({"type": type(value).__name__, "object_id": f"{id(value):016x}"}
                            if "self" in frame.f_locals and value is frame.f_locals["self"] else _value(value))
                if entry["stage"] == "output":
                    returned = _value(frame.f_locals.get("value", value))
                    self.output_recorded = True
                    self.output = {**(self.output or {}), "response": returned} if isinstance(self.output, dict) and "llm_outputs" in self.output else returned
                errors = _errors(returned)
                escaped = bool(entry["exceptions"]) and opcode not in {"RETURN_VALUE", "RETURN_CONST"}
                if escaped:
                    errors.append(entry["exceptions"][-1])
                output = {"return": returned, "exceptions": entry["exceptions"]}
                output["errors"] = errors
                if entry["yields"]:
                    output["yields"] = entry["yields"]
                if entry["generation"]:
                    output = _value("".join(entry["yields"])) if entry["yields"] else returned
                    if escaped:
                        output = {"error": errors[-1], "partial_output": output}
                entry["span"].update(output=output, level="ERROR" if errors else "DEFAULT",
                                     metadata={"run_id": self.run_id, "errors": errors, "exceptions": entry["exceptions"]})
                entry["span"].end()
                del self.frames[key]

    def __enter__(self):
        self.token = _ACTIVE.set(self)
        try:
            if self.name.startswith("agent.mcp.") and not self.name.startswith("agent.mcp.client."):
                self.root = _ContextSpan(self)
            else:
                self.exporter = LangfuseExporter.from_env()
                try:
                    self.root = self._start("pipeline:" + self.name, self.arguments)
                except Exception as error:
                    self.warnings.append(type(error).__name__)
                    if hasattr(self.exporter, "_queue"):
                        self.exporter.client = None
                        self.root = self._start("pipeline:" + self.name, self.arguments)
            if self.root is not None:
                if getattr(_LOCAL, "users", 0) == 0:
                    _LOCAL.previous = sys.gettrace()
                    sys.settrace(_trace)
                _LOCAL.users = getattr(_LOCAL, "users", 0) + 1
        except Exception as error:
            self.warnings.append(type(error).__name__)
        return self

    def export(self, events, *, input_payload=None, output_payload=None):
        self.events.extend(events)
        self.output = output_payload
        return ExportResult("buffered")

    def __exit__(self, error_type, error, traceback):
        self.closed = True
        if self.root is not None:
            _LOCAL.users -= 1
            if not _LOCAL.users:
                sys.settrace(_LOCAL.previous)
            if isinstance(self.root, _ContextSpan):
                if self.exceptions:
                    try:
                        self.exporter = LangfuseExporter.from_env()
                        span = self._start("error", self.arguments, self.parent_id)
                        span.update(output={"exceptions": self.exceptions}, level="ERROR",
                                    metadata={"run_id": self.run_id, "exceptions": self.exceptions})
                        span.end()
                        if self.exporter.client is None:
                            self.exporter._queue(self.queue_records, self.exporter.reason)
                        else:
                            _bounded_call(self.exporter.client.flush, 2.0)
                    except Exception as failure:
                        self.warnings.append("exception:" + type(failure).__name__)
                _ACTIVE.reset(self.token)
                return False
            try:
                self.complete_input(error=error)
                if not self.output_recorded and (error is not None or (self.output is not None and not self.parent_id)):
                    result = {"status": "error", "error": _value(error)} if error else self.output
                    self.record_output(result.get("response", result) if isinstance(result, dict) else result)
                for entry in list(self.frames.values()):
                    entry["span"].update(output={"exceptions": entry["exceptions"], "yields": entry["yields"],
                                                 "incomplete": True, "errors": [_value(error)] if error else []},
                                         level="ERROR" if error else "DEFAULT",
                                         metadata={"run_id": self.run_id, "exceptions": entry["exceptions"]})
                    entry["span"].end()
                errors = _errors(self.output) + self.errors + ([_value(error)] if error else [])
                self.root.update(output=_value(self.output), level="ERROR" if errors else "DEFAULT",
                                 metadata={"run_id": self.run_id, "exception": _value(error),
                                           "exceptions": self.exceptions,
                                           "errors": errors,
                                           "tracing_warnings": self.warnings})
                self.root.end()
                if self.exporter.client is None:
                    self.exporter._queue(self.queue_records, self.exporter.reason)
                else:
                    _bounded_call(self.exporter.client.flush, 2.0)
            except Exception as failure:
                self.warnings.append(type(failure).__name__)
        _ACTIVE.reset(self.token)
        return False


def trace_pipeline(function=None, *, context_provider=None):
    if function is None:
        return lambda target: trace_pipeline(target, context_provider=context_provider)
    name = _module(function.__globals__) + "." + function.__qualname__

    def session_for(args, kwargs):
        headers = context_provider() if context_provider else {}
        return FunctionTrace(name, inspect.signature(function).bind(*args, **kwargs).arguments,
                             run_id=headers.get("x-pob-trace-run-id") or headers.get("X-PoB-Trace-Run-Id"),
                             parent_id=headers.get("x-pob-trace-parent-id") or headers.get("X-PoB-Trace-Parent-Id"))

    if inspect.iscoroutinefunction(function):
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            if current_trace() is not None:
                return await function(*args, **kwargs)
            with session_for(args, kwargs) as session:
                result = await function(*args, **kwargs)
                if session.output is None:
                    session.output = result
                return result
    elif inspect.isgeneratorfunction(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            parent = current_trace()
            headers = trace_headers()

            def iterate():
                if current_trace() is parent and parent is not None:
                    with _trace_thread():
                        yield from function(*args, **kwargs)
                    return
                with FunctionTrace(name, inspect.signature(function).bind(*args, **kwargs).arguments,
                                   run_id=headers.get("X-PoB-Trace-Run-Id"),
                                   parent_id=headers.get("X-PoB-Trace-Parent-Id")) as session:
                    yield from function(*args, **kwargs)
            return iterate()
    else:
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            if current_trace() is not None:
                with _trace_thread():
                    return function(*args, **kwargs)
            with session_for(args, kwargs) as session:
                result = function(*args, **kwargs)
                if session.output is None:
                    session.output = result
                return result
    return wrapped
