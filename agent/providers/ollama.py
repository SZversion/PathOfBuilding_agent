"""Explicit development-only Ollama adapter.

Ollama is reached through its OpenAI-compatible endpoint.  This module is not
selected by the production default and never falls back to the remote model.
"""

from .openai_compatible import OpenAICompatibleClient


DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"


class OllamaDevelopmentProvider(OpenAICompatibleClient):
    def __init__(self, endpoint=DEFAULT_OLLAMA_ENDPOINT, model=DEFAULT_OLLAMA_MODEL, timeout=120, *, mode="development"):
        if mode != "development":
            raise ValueError("Ollama is available only in explicit development mode")
        self.mode = "development"
        super().__init__(endpoint=endpoint, model=model, timeout=timeout, allow_local=True)
