"""Explicit development-only adapter for Ollama's native HTTP API.

The configured host (normally ``http://127.0.0.1:11434/v1``) is used only to
derive Ollama's native ``/api/chat`` endpoint.  This module is not selected by
the production default and never falls back to the remote model.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from .openai_compatible import ExternalModelError, OpenAICompatibleClient


DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"


class OllamaDevelopmentProvider(OpenAICompatibleClient):
    def __init__(self, endpoint=DEFAULT_OLLAMA_ENDPOINT, model=DEFAULT_OLLAMA_MODEL, timeout=120, *, mode="development"):
        if mode != "development":
            raise ValueError("Ollama is available only in explicit development mode")
        self.mode = "development"
        self.supports_json_schema = True
        super().__init__(endpoint=endpoint, model=model, timeout=timeout, allow_local=True)

    def _native_url(self):
        parsed = urllib.parse.urlparse(self.endpoint)
        return f"{parsed.scheme}://{parsed.netloc}/api/chat"

    def _native_request(self, messages, *, format=None, stream=False):
        body = {"model": self.model, "messages": messages, "stream": stream}
        if format is not None:
            body["format"] = format
        request = urllib.request.Request(self._native_url(), data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            raise ExternalModelError("Ollama request failed", code="MODEL_REQUEST_FAILED", retryable=False, details={"http_status": error.code, "format_rejected": format is not None and error.code == 400}) from error
        except TimeoutError:
            raise ExternalModelError("Ollama request timed out", code="TIMEOUT", retryable=False, details={"timeout": True}) from None
        except urllib.error.URLError:
            raise ExternalModelError("Ollama is unavailable", code="MODEL_TRANSIENT", retryable=True) from None

    def chat(self, messages, *, format=None):
        try:
            response = self._native_request(messages, format=format, stream=False)
        except ExternalModelError as error:
            if format is not None and error.error.get("details", {}).get("format_rejected"):
                response = self._native_request(messages, stream=False)
            else:
                raise
        try:
            raw = response.read().decode("utf-8")
        finally:
            if hasattr(response, "close"):
                response.close()
        try:
            data = json.loads(raw)
            content = data["message"]["content"]
        except (json.JSONDecodeError, KeyError, TypeError):
            try:
                content = json.loads(raw.splitlines()[-1])["message"]["content"]
            except (IndexError, json.JSONDecodeError, KeyError, TypeError):
                raise ExternalModelError("Ollama response has no message.content", code="MODEL_SCHEMA_INVALID", retryable=False) from None
        if not isinstance(content, str) or not content.strip():
            raise ExternalModelError("Ollama response content is empty", code="MODEL_SCHEMA_INVALID", retryable=False)
        return content

    def stream_chat(self, messages):
        response = self._native_request(messages, stream=True)
        buffer = ""
        try:
            for chunk in response:
                buffer += chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("done"):
                            return
                        content = data.get("message", {}).get("content", "")
                    except (json.JSONDecodeError, TypeError):
                        raise ExternalModelError("Ollama stream line is invalid", code="MODEL_SCHEMA_INVALID", retryable=False) from None
                    if content:
                        yield content
            if buffer.strip():
                data = json.loads(buffer)
                if not data.get("done") and data.get("message", {}).get("content"):
                    yield data["message"]["content"]
        except TimeoutError:
            raise ExternalModelError("Ollama stream timed out", code="TIMEOUT", retryable=False, details={"timeout": True}) from None
        finally:
            if hasattr(response, "close"):
                response.close()
