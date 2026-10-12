import contextlib
import sys
import types

from agent.orchestration.function_trace import trace_pipeline, current_trace, trace_headers


class Span:
    def __init__(self, client, values):
        self.client = client
        self.values = values
        self.id = len(client.spans) + 1
        client.spans.append(values)

    def get_trace_id(self): return "a" * 32
    def get_observation_id(self): return f"{self.id:016x}"
    def update(self, **values): self.values.update(values)
    def end(self): self.values["ended"] = True


class Client:
    def __init__(self): self.spans = []
    def start_observation(self, **values): return Span(self, values)
    def flush(self): pass


def project_function(source):
    module = types.ModuleType("agent.trace_fixture")
    exec(source, module.__dict__)
    return module


def test_nested_functions_record_complete_arguments_returns_and_exceptions(monkeypatch):
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    fixture = project_function("""
def child(value, *, option=None):
    if option == 'fail': raise ValueError('bad value')
    return {'all': value, 'empty': [], 'none': None}
def parent(value):
    result = child(value)
    try: child(value, option='fail')
    except ValueError: pass
    return result
""")
    before = sys.gettrace()
    wrapped = trace_pipeline(fixture.parent)
    value = {"long": "x" * 500, "items": list(range(50)), "authorization": "Bearer private"}
    assert wrapped(value)["all"] == value
    assert sys.gettrace() is before
    children = [s for s in client.spans if s["name"].endswith(".child")]
    assert len(children) == 2
    assert children[0]["input"]["value"]["items"] == list(range(50))
    assert children[0]["input"]["value"]["authorization"] == "[REDACTED]"
    assert children[0]["output"]["return"]["all"]["long"] == "x" * 500
    assert children[1]["output"]["exceptions"][0]["type"] == "ValueError"
    assert all(s["ended"] for s in client.spans)
    assert current_trace() is None


def test_generator_yields_and_context_propagation(monkeypatch):
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    fixture = project_function("""
def chunks():
    yield 'first'
    yield 'second'
def run():
    from agent.orchestration.function_trace import trace_headers
    return {'chunks': list(chunks()), 'headers': trace_headers()}
""")
    result = trace_pipeline(fixture.run)()
    assert result["headers"]["X-PoB-Trace-Run-Id"].startswith("run-")
    chunk = next(s for s in client.spans if s["name"].endswith(".chunks"))
    assert chunk["output"]["yields"] == ["first", "second"]
    assert trace_headers() == {}


def test_tracing_failure_never_changes_function_result(monkeypatch):
    class Broken(Client):
        def start_observation(self, **values): raise RuntimeError('offline')
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=Broken()))
    fixture = project_function("def run(value): return value")
    assert trace_pipeline(fixture.run)({"answer": 42}) == {"answer": 42}


def test_response_objects_preserve_body_and_redact_cookies():
    from starlette.responses import JSONResponse
    from agent.orchestration.function_trace import _value
    response = JSONResponse({"nested": {"all": [None, {}, []]}, "answer": "complete"})
    response.set_cookie("session", "private-session")
    recorded = _value(response)
    assert recorded["attributes"]["body"] == {"nested": {"all": [None, {}, []]}, "answer": "complete"}
    assert ["set-cookie", "[REDACTED]"] in recorded["attributes"]["raw_headers"]


def test_async_calls_and_worker_threads_keep_function_returns(monkeypatch):
    import asyncio
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    fixture = project_function("""
from agent.orchestration.function_trace import trace_pipeline
@trace_pipeline
def worker(value): return {'value': value}
async def run(value):
    import asyncio
    result = await asyncio.to_thread(worker, value)
    await asyncio.sleep(0)
    return result
""")
    assert asyncio.run(trace_pipeline(fixture.run)(42)) == {"value": 42}
    worker = next(s for s in client.spans if s["name"].endswith(".worker"))
    assert worker["input"]["value"] == 42
    assert worker["output"]["return"] == {"value": 42}
    assert all(s.get("ended") for s in client.spans)


def test_offline_function_traces_keep_full_values_in_existing_queue(monkeypatch, tmp_path):
    import json
    from agent.orchestration.langfuse_exporter import LangfuseExporter
    queue = tmp_path / "queue.ndjson"
    exporter = LangfuseExporter(enabled=True, queue_path=queue)
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env", lambda: exporter)
    fixture = project_function("def run(value): return {'all': value, 'empty': []}")
    result = trace_pipeline(fixture.run)({"value": 42, "token": "private"})
    assert result["all"]["token"] == "private"
    saved = json.loads(queue.read_text())
    function = next(e for e in saved["events"] if e["event"] == "agent.trace_fixture.run")
    assert function["input"]["value"] == {"value": 42, "token": "[REDACTED]"}
    assert function["output"]["return"]["empty"] == []


def test_dataclass_runtime_handles_do_not_require_deepcopy():
    import asyncio
    from dataclasses import dataclass
    from agent.orchestration.function_trace import _value
    @dataclass
    class Value:
        future: object
        payload: dict
    loop = asyncio.new_event_loop()
    try:
        value = Value(loop.create_future(), {"all": [None, {}, []]})
        assert _value(value)["payload"] == {"all": [None, {}, []]}
    finally:
        loop.close()


def test_server_callback_restores_trace_context_from_request_headers(monkeypatch):
    import hashlib
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    fixture = project_function("def callback(value): return value")
    run_id = "run-request-context"
    wrapped = trace_pipeline(fixture.callback, context_provider=lambda: {
        "x-pob-trace-run-id": run_id, "x-pob-trace-parent-id": "1234567890abcdef"})
    assert wrapped({"all": 42}) == {"all": 42}
    context = client.spans[0]["trace_context"]
    assert context["trace_id"] == hashlib.sha256(("pob-agent:" + run_id).encode()).hexdigest()[:32]
    assert context["parent_span_id"] == "1234567890abcdef"


def test_detached_callback_does_not_reuse_a_closed_request_trace(monkeypatch):
    import contextvars
    from agent.orchestration.function_trace import FunctionTrace
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    with FunctionTrace("request"):
        detached = contextvars.copy_context()
    fixture = project_function("def callback(value): return value")
    wrapped = trace_pipeline(fixture.callback, context_provider=lambda: {"x-pob-trace-run-id": "run-detached"})
    assert detached.run(wrapped, 42) == 42
    callback = next(s for s in client.spans if s["name"] == "agent.trace_fixture.callback")
    assert callback["output"]["return"] == 42
    assert callback["ended"]


def test_python_module_entrypoints_keep_canonical_function_names(monkeypatch):
    from importlib.machinery import ModuleSpec
    client = Client()
    monkeypatch.setattr("agent.orchestration.function_trace.LangfuseExporter.from_env",
                        lambda: types.SimpleNamespace(client=client))
    module = types.ModuleType("__main__")
    module.__spec__ = ModuleSpec("agent.trace_fixture", loader=None)
    exec("def run(value): return value", module.__dict__)
    assert trace_pipeline(module.run)({"all": 42}) == {"all": 42}
    span = next(s for s in client.spans if s["name"] == "agent.trace_fixture.run")
    assert span["output"]["return"] == {"all": 42}
