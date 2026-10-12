import json

from agent.pob import live_transport


class FakeSocket:
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def settimeout(self, _timeout): pass
    def sendall(self, payload):
        assert json.loads(payload)["token"] == "a" * 64
    def recv(self, _size):
        if getattr(self, "sent", False): return b""
        self.sent = True
        return b'{"ok":true,"result":{"mode":"BUILD"}}\n'


def test_container_host_override_changes_only_the_connection_address(monkeypatch, tmp_path):
    endpoint = {"host": "127.0.0.1", "port": 12345, "token": "a" * 64, "protocolVersion": 1}
    transport = live_transport.LivePobTransport(tmp_path)
    transport._endpoints = lambda: [endpoint]
    addresses = []
    monkeypatch.setenv("POB_AGENT_HOST_OVERRIDE", "host.docker.internal")
    monkeypatch.setattr(live_transport.socket, "create_connection",
                        lambda address, timeout: addresses.append((address, timeout)) or FakeSocket())

    assert transport.request({"op": "status"}) == {"ok": True, "result": {"mode": "BUILD"}}
    assert addresses == [(('host.docker.internal', 12345), transport.timeout)]
