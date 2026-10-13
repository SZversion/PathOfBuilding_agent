import json
import pytest
from types import SimpleNamespace

from starlette.testclient import TestClient

from agent import http_backend


@pytest.mark.parametrize('valid_build', [True, False])
def test_http_trace_has_user_input_final_output_and_validation_errors(monkeypatch, tmp_path, valid_build):
    from tests.agent.orchestration.test_function_trace import Client
    trace_client = Client()
    monkeypatch.setattr('agent.orchestration.function_trace.LangfuseExporter.from_env',
                        lambda: SimpleNamespace(client=trace_client))
    monkeypatch.setenv('POB_BUILDS_DIR', str(tmp_path))
    monkeypatch.setenv('POB_AGENT_API_TOKEN', 'test-api-token')
    (tmp_path / 'valid.xml').write_text('<Build />', encoding='utf-8')
    monkeypatch.setattr(http_backend.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(stdout=json.dumps({'status': 'ok', 'answer': 'actual answer'}), stderr='', returncode=0))
    body = {'build_file': 'valid.xml' if valid_build else '../outside.xml', 'question': '내 빌드 DPS?'}
    response = TestClient(http_backend.app).post('/v1/run', json=body,
                                               headers={'Authorization': 'Bearer test-api-token'})
    input_span = next(s for s in trace_client.spans if s['name'] == 'input')
    output_span = next(s for s in trace_client.spans if s['name'] == 'output')
    assert input_span['input'] == body
    assert 'test-api-token' not in json.dumps(trace_client.spans)
    if valid_build:
        assert response.status_code == 200
        assert input_span['output']['return'] == body
        assert output_span['output'] == response.json()
        assert output_span['metadata']['errors'] == []
    else:
        assert response.status_code == 400
        assert input_span['level'] == output_span['level'] == 'ERROR'
        assert output_span['metadata']['errors'][0]['details']['status_code'] == 400
    assert all(s['ended'] for s in trace_client.spans)


def test_http_backend_authenticates_and_limits_build_paths(monkeypatch, tmp_path):
    build = tmp_path / "valid.xml"
    build.write_text("<Build />", encoding="utf-8")
    monkeypatch.setenv("POB_BUILDS_DIR", str(tmp_path))
    monkeypatch.setenv("POB_AGENT_API_TOKEN", "test-api-token")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        return SimpleNamespace(stdout=json.dumps({"status": "ok"}), stderr="", returncode=0)

    monkeypatch.setattr(http_backend.subprocess, "run", fake_run)
    client = TestClient(http_backend.app)
    assert client.get("/healthz").json() == {"status": "ok"}
    request = {"build_file": "valid.xml", "question": "How much DPS?"}
    assert client.post("/v1/run", json=request).status_code == 401
    response = client.post("/v1/run", json=request, headers={"Authorization": "Bearer test-api-token"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "--cache-root" in seen["command"]

    traversal = client.post("/v1/run", json={**request, "build_file": "../outside.xml"},
                            headers={"Authorization": "Bearer test-api-token"})
    assert traversal.status_code == 400
