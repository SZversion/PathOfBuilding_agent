import json
from types import SimpleNamespace

from starlette.testclient import TestClient

from agent import http_backend


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
