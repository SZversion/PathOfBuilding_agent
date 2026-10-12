"""Authenticated local transport for commands handled by a live PoB Lua process."""

from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from typing import Any


MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
PROTOCOL_VERSION = 1


class LivePobTransportError(RuntimeError):
    """A local PoB endpoint could not be discovered or did not speak the protocol."""


def _default_endpoint_dir() -> Path:
    configured = os.environ.get("POB_AGENT_ENDPOINT_DIR")
    if configured:
        return Path(configured).expanduser()
    profile = os.environ.get("USERPROFILE")
    if profile:
        return Path(profile) / "Documents" / "Path of Building"
    return Path.home() / "Documents" / "Path of Building"


class LivePobTransport:
    """Send one bounded JSON-line request to a running PoB process on loopback."""

    def __init__(
        self,
        endpoint_dir: str | os.PathLike[str] | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.endpoint_dir = Path(endpoint_dir) if endpoint_dir else _default_endpoint_dir()
        self.timeout = timeout

    def _endpoints(self) -> list[dict[str, Any]]:
        endpoint_files = sorted(
            self.endpoint_dir.glob("AgentBridge-*.json"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        if not endpoint_files:
            raise LivePobTransportError(
                f"No running PoB Agent endpoint found in {self.endpoint_dir}"
            )
        endpoints = []
        for endpoint_file in endpoint_files:
            try:
                endpoint = json.loads(endpoint_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if self._valid_endpoint(endpoint):
                endpoints.append(endpoint)
        if not endpoints:
            raise LivePobTransportError("PoB endpoint metadata is invalid or unsupported")
        return endpoints

    @staticmethod
    def _valid_endpoint(endpoint: Any) -> bool:
        return (
            isinstance(endpoint, dict)
            and endpoint.get("host") == "127.0.0.1"
            and type(endpoint.get("port")) is int
            and 1 <= endpoint["port"] <= 65535
            and isinstance(endpoint.get("token"), str)
            and len(endpoint["token"]) == 64
            and endpoint.get("protocolVersion") == PROTOCOL_VERSION
        )

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")
        endpoints = self._endpoints()
        response = None
        connect_errors = []
        for endpoint in endpoints:
            request = dict(payload)
            request["token"] = endpoint["token"]
            try:
                encoded = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
            except (TypeError, ValueError) as error:
                raise LivePobTransportError("Request is not JSON serializable") from error
            if len(encoded) > MAX_REQUEST_BYTES:
                raise LivePobTransportError("Request exceeds the maximum frame size")
            try:
                host = os.environ.get("POB_AGENT_HOST_OVERRIDE", endpoint["host"])
                if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
                    raise LivePobTransportError("Configured PoB host override is invalid")
                with socket.create_connection((host, endpoint["port"]), timeout=self.timeout) as client:
                    client.settimeout(self.timeout)
                    client.sendall(encoded)
                    response = bytearray()
                    while len(response) <= MAX_RESPONSE_BYTES:
                        chunk = client.recv(min(8192, MAX_RESPONSE_BYTES + 1 - len(response)))
                        if not chunk:
                            break
                        response.extend(chunk)
                        newline = response.find(b"\n")
                        if newline >= 0:
                            response = response[:newline]
                            break
                    break
            except OSError as error:
                connect_errors.append(str(error))
        if response is None:
            raise LivePobTransportError(
                "Unable to reach a running PoB endpoint: " + "; ".join(connect_errors)
            )

        if not response:
            raise LivePobTransportError("PoB closed the connection without a response")
        if len(response) > MAX_RESPONSE_BYTES:
            raise LivePobTransportError("PoB response exceeds the maximum frame size")
        try:
            decoded = json.loads(response.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise LivePobTransportError("PoB returned malformed JSON") from error
        if not isinstance(decoded, dict) or not isinstance(decoded.get("ok"), bool):
            raise LivePobTransportError("PoB returned an invalid response envelope")
        return decoded
