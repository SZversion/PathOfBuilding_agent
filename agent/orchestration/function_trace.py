"""Request-scoped function-boundary tracing for the Python agent pipeline."""

from contextlib import contextmanager, nullcontext
import contextvars
import dis
import functools
import hashlib
import inspect
import os
from pathlib import Path
import sys
import threading
import uuid

from .langfuse_exporter import LangfuseExporter, ExportResult, _bounded_call

_ACTIVE = contextvars.ContextVar("pob_function_trace", default=None)
_LOCAL = threading.local()
_EXCLUDED = {__name__, "agent.orchestration.trace", "agent.orchestration.langfuse_exporter"}


def current_trace():
    return _ACTIVE.get()


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
        if hasattr(value, "model_dump"):
            return _value(value.model_dump(mode="json"), seen)
        if isinstance(value, BaseException):
            return {"type": type(value).__name__, "message": _value(str(value)),
                    "arguments": _value(value.args, seen), "details": _value(vars(value), seen),
                    "cause": _value(value.__cause__, seen)}
        if type(value).__module__.startswith(("agent.", "argparse", "types", "starlette")):
            return {"type": type(value).__name__, "attributes": _value(vars(value), seen)}
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


def _trace(frame, event, value):
    session = current_trace()
    module = frame.f_globals.get("__name__", "")
    if session is None or session.root is None or session.closed or not module.startswith("agent.") or module in _EXCLUDED:
        return None
    try:
        session.record(frame, event, value)
    except Exception as error:
        session.warnings.append(type(error).__name__)
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
        self.output = None
        self.warnings = []
        self.closed = False

    def _start(self, name, arguments, parent=None):
        client = self.exporter.client
        trace_context = {"trace_id": self.trace_id, "parent_span_id": parent or self.parent_id}
        if hasattr(client, "_otel_tracer"):
            from opentelemetry import trace
            remote = client._create_remote_parent_span(**trace_context)
            with trace.use_span(remote):
                span = client._otel_tracer.start_span(name=name)
            return client._create_observation_from_otel_span(
                otel_span=span, as_type="span", input=_value(arguments),
                metadata={"run_id": self.run_id, "function": name})
        return client.start_observation(name=name, input=_value(arguments),
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
            payload = {name: _value(arguments.locals[name]) for name in names}
            parent = self.parent_span(frame.f_back)
            parent_id = _span_ids(parent)[1] if parent else None
            name = frame.f_globals["__name__"] + "." + frame.f_code.co_qualname
            span = self._start(name, payload, parent_id)
            self.frames[key] = {"span": span, "exceptions": [], "yields": []}
        elif key in self.frames:
            entry = self.frames[key]
            if event == "exception":
                entry["exceptions"].append(_value(value[1]))
            elif event == "return":
                opcode = dis.opname[frame.f_code.co_code[frame.f_lasti]]
                if opcode in {"YIELD_VALUE", "YIELD_FROM"}:
                    # Coroutine await suspensions are not function returns.
                    if not frame.f_code.co_flags & inspect.CO_COROUTINE:
                        entry["yields"].append(_value(value))
                    return
                output = {"return": _value(value), "exceptions": entry["exceptions"]}
                if entry["yields"]:
                    output["yields"] = entry["yields"]
                escaped = bool(entry["exceptions"]) and opcode not in {"RETURN_VALUE", "RETURN_CONST"}
                entry["span"].update(output=output, level="ERROR" if escaped else "DEFAULT")
                entry["span"].end()
                del self.frames[key]

    def __enter__(self):
        self.token = _ACTIVE.set(self)
        try:
            self.exporter = LangfuseExporter.from_env()
            if self.exporter.client is not None:
                self.root = self._start("pipeline:" + self.name, self.arguments)
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
            try:
                for entry in list(self.frames.values()):
                    entry["span"].update(output={"exceptions": entry["exceptions"], "yields": entry["yields"],
                                                 "incomplete": True})
                    entry["span"].end()
                self.root.update(output=_value(self.output), level="ERROR" if error else "DEFAULT",
                                 metadata={"run_id": self.run_id, "exception": _value(error),
                                           "tracing_warnings": self.warnings})
                if self.events:
                    from opentelemetry import trace
                    with (trace.use_span(self.root._otel_span) if hasattr(self.root, "_otel_span") else nullcontext()):
                        for event in self.events:
                            with self.exporter._record_event(self.exporter.client, event):
                                pass
                self.root.end()
                _bounded_call(self.exporter.client.flush, 2.0)
            except Exception as failure:
                self.warnings.append(type(failure).__name__)
        _ACTIVE.reset(self.token)
        return False


def trace_pipeline(function):
    name = function.__module__ + "." + function.__qualname__

    def session_for(args, kwargs):
        return FunctionTrace(name, inspect.signature(function).bind(*args, **kwargs).arguments)

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
