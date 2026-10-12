import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.providers.factory import create_provider
from agent.providers.ollama import OllamaDevelopmentProvider
from agent.providers.openai_compatible import ExternalModelError, OpenAICompatibleClient


def config(mode="remote"):
    return {
        "defaultMode": mode,
        "remote": {"endpoint": "https://agent.example.invalid/v1", "model": "external-agent"},
        "local": {"enabled": True, "endpoint": "http://127.0.0.1:11434/v1", "model": "qwen3:8b"},
    }


def test_ollama_defaults_are_development_only():
    provider = OllamaDevelopmentProvider()
    assert provider.endpoint == "http://127.0.0.1:11434/v1"
    assert provider.model == "qwen3:8b"
    assert provider.mode == "development"
    with pytest.raises(ValueError):
        OllamaDevelopmentProvider(mode="production")


def test_factory_keeps_remote_default_and_rejects_local_in_production():
    assert isinstance(create_provider(config()), OpenAICompatibleClient)
    with pytest.raises(ValueError):
        create_provider(config("local"), environment="production")
    assert isinstance(create_provider(config("local"), environment="development"), OllamaDevelopmentProvider)


def test_local_enabled_does_not_change_remote_default():
    provider = create_provider(config(), environment="production")
    assert not isinstance(provider, OllamaDevelopmentProvider)


def test_malformed_provider_response_maps_to_registered_schema_error(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"not-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ExternalModelError) as raised:
        OpenAICompatibleClient(endpoint="https://agent.example.invalid/v1", model="external").chat([])
    assert raised.value.error["code"] == "MODEL_SCHEMA_INVALID"


def test_provider_timeout_preserves_timeout_metadata(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("deadline")))
    with pytest.raises(ExternalModelError) as raised:
        OpenAICompatibleClient(endpoint="https://agent.example.invalid/v1", model="external", timeout=1).chat([])
    assert raised.value.error["code"] == "MODEL_TRANSIENT"
    assert raised.value.error["details"]["timeout"] is True


@pytest.mark.skipif(os.environ.get("RUN_OLLAMA_SMOKE") != "1", reason="Ollama smoke test requires RUN_OLLAMA_SMOKE=1")
def test_real_ollama_qwen3_smoke():
    try:
        provider = OllamaDevelopmentProvider(timeout=int(os.environ.get("OLLAMA_SMOKE_TIMEOUT", "30")))
        response = provider.chat([{"role": "user", "content": "Reply with OK"}])
    except Exception as error:
        pytest.skip("Ollama unavailable: " + type(error).__name__)
    assert isinstance(response, str) and response
    assert provider.mode == "development" and provider.model == "qwen3:8b" and provider.endpoint.startswith("http://127.0.0.1")
