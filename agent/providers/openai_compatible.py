import json
import urllib.error
import urllib.parse
import urllib.request


class ExternalModelError(RuntimeError):
    def __init__(self, message, *, code="MODEL_TRANSIENT", retryable=True, details=None):
        super().__init__(message)
        self.error = {"code": code, "recovery_class": "RETRY_LLM" if retryable else "REJECT", "stage": "model_request", "retryable": retryable, "attempt": 1, "max_attempts": 2 if retryable else 1, "message": message, "details": details or {}, "next_action": "retry_llm" if retryable else "reject_request", "secondary_causes": [], "side_effect": "none", "operator_message": None}


def _validate_endpoint(endpoint, *, allow_local=False):
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("an explicit external model endpoint is required")
    parsed = urllib.parse.urlparse(endpoint)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"https", "http"} or not host:
        raise ValueError("model endpoint must be an explicit http(s) URL")
    if not allow_local and (host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".local")):
        raise ValueError("local model endpoints are not allowed")
    return endpoint.rstrip("/")


class OpenAICompatibleClient:
    def __init__(self, endpoint=None, model=None, api_key=None, timeout=120, *, allow_local=False):
        self.endpoint = _validate_endpoint(endpoint, allow_local=allow_local)
        if not isinstance(model, str) or not model.strip():
            raise ValueError("an explicit external model name is required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.model = model.strip()
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages):
        payload = json.dumps({"model": self.model, "messages": messages, "temperature": 0}).encode("utf-8")
        request = urllib.request.Request(self.endpoint + "/chat/completions", data=payload, headers={"Content-Type": "application/json"})
        if self.api_key:
            request.add_header("Authorization", "Bearer " + self.api_key)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            raise ExternalModelError("external model HTTP request failed", code="MODEL_TRANSIENT" if retryable else "MODEL_REQUEST_FAILED", retryable=retryable, details={"http_status": error.code}) from error
        except json.JSONDecodeError:
            raise ExternalModelError("external model response is not valid JSON", code="MODEL_SCHEMA_INVALID", retryable=True) from None
        except TimeoutError:
            raise ExternalModelError("external model request timed out", code="MODEL_TRANSIENT", retryable=True, details={"timeout": True}) from None
        except urllib.error.URLError:
            raise ExternalModelError("external model request failed", code="MODEL_TRANSIENT", retryable=True) from None
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ExternalModelError("external model response has no choices[0].message.content", code="MODEL_SCHEMA_INVALID", retryable=True) from None
        if not isinstance(content, str) or not content.strip():
            raise ExternalModelError("external model response content is empty", code="MODEL_SCHEMA_INVALID", retryable=True)
        return content
