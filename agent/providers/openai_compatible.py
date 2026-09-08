import json
import urllib.error
import urllib.request


class OpenAICompatibleClient:
    def __init__(self, endpoint="http://127.0.0.1:11434/v1", model="qwen3:8b", api_key=None, timeout=120):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
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
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError("model request failed: " + str(error)) from error
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("model response has no choices[0].message.content") from error
