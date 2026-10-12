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
