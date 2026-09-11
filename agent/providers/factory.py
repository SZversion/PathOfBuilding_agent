"""Explicit provider selection; no automatic fallback is permitted."""

from .ollama import DEFAULT_OLLAMA_ENDPOINT, DEFAULT_OLLAMA_MODEL, OllamaDevelopmentProvider
from .openai_compatible import OpenAICompatibleClient


def create_provider(config, *, environment="production"):
    if not isinstance(config, dict):
        raise ValueError("provider configuration must be an object")
    mode = config.get("defaultMode", "remote")
    if mode == "remote":
        remote = config.get("remote")
        if not isinstance(remote, dict) or not remote.get("endpoint"):
            raise ValueError("remote provider endpoint is required")
        return OpenAICompatibleClient(endpoint=remote["endpoint"], model=remote.get("model", "external-agent"), timeout=remote.get("timeout", 120))
    if mode == "local":
        local = config.get("local")
        if environment != "development" or not isinstance(local, dict) or local.get("enabled") is not True:
            raise ValueError("local Ollama provider requires explicit development mode and local.enabled=true")
        return OllamaDevelopmentProvider(endpoint=local.get("endpoint", DEFAULT_OLLAMA_ENDPOINT), model=local.get("model", DEFAULT_OLLAMA_MODEL), timeout=local.get("timeout", 120), mode="development")
    raise ValueError("unknown provider mode: " + str(mode))
