from pathlib import Path

import pytest

from agent.pob.bridge import PobBridge


BUILD = Path(r"C:\Users\SZ\Documents\Path of Building\Builds\3.29\arc.xml")


@pytest.mark.skipif(not BUILD.exists(), reason="local Arc fixture is not installed")
def test_variant_display_name_resolves_socket_group():
    bridge = PobBridge(timeout=30)
    for tool in ("get_socket_order", "get_support_links"):
        result = bridge.call(BUILD, tool, {"skillSetSelector": 1, "skillName": "Arc of Oscillating"})
        assert result["status"] == "calculated"
        assert result["facts"]["skill"]["name"] == "Arc of Oscillating"
        assert result["facts"]["gems"][0]["name"] == "Vaal Arc of Oscillating"
