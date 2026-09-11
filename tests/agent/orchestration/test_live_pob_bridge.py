import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.pob.live_bridge import LivePobBridge, LivePobBridgeError


class Adapter:
    def __init__(self):
        self.build = {"calcsTab": {"mainEnv": {"player": {}}}}
        self.revision = "rev-7"

    def currentBuild(self):
        return self.build

    def capture_snapshot(self, build):
        return {"snapshotRevision": self.revision, "context": {"activeSpec": {"id": 1}, "config": {"enemy": "boss", "nested": {"drop": True}}}}

    def dispatch(self, request):
        return {"ok": True, "result": {"facts": {"value": 42}, "snapshotRevision": self.revision}}


def test_live_bridge_readiness_capture_and_dispatch():
    bridge = LivePobBridge(Adapter())
    assert bridge.readiness()["ready"] is True
    snapshot = bridge.capture()
    assert snapshot["snapshotRevision"] == "rev-7"
    assert snapshot["config"] == {"enemy": "boss"}
    assert bridge.call("get_skill_dps", {"skillIndex": 1})["facts"]["value"] == 42


def test_live_bridge_rejects_unready_pob_with_structured_error():
    adapter = Adapter()
    adapter.build = {"calcsTab": {"mainEnv": {}}}
    bridge = LivePobBridge(adapter)
    assert bridge.readiness()["ready"] is False
    with pytest.raises(LivePobBridgeError) as raised:
        bridge.capture()
    assert raised.value.error["code"] == "VALUE_UNAVAILABLE"
    assert raised.value.error["snapshotRevision"] is None


def test_callable_transport_uses_current_build_and_capture_snapshot():
    adapter = Adapter()

    def request(payload):
        if payload.get("operation") == "currentBuild":
            return {"ok": True, "result": adapter.build}
        if payload.get("tool") == "capture_snapshot":
            return {"ok": True, "result": adapter.capture_snapshot(adapter.build)}
        return adapter.dispatch(payload)

    bridge = LivePobBridge(request=request)
    assert bridge.capture()["snapshotRevision"] == "rev-7"
    assert bridge.call("get_skill_dps", {})["facts"]["value"] == 42


def test_live_bridge_rejects_mutation_tools_without_touching_pob():
    bridge = LivePobBridge(Adapter())
    for tool in ("replace_item", "replace_gem", "change_passive"):
        with pytest.raises(LivePobBridgeError) as raised:
            bridge.call(tool, {})
        assert raised.value.error["code"] == "MUTATION_NOT_PERSISTENT"
        assert raised.value.error["stage"] == "bridge_capability"
        assert raised.value.error["side_effect"] == "none"
