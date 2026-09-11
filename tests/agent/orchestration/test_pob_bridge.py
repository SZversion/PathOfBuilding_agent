import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.pob.bridge import PobBridgeError, PobUnavailableError, _skill_alias, decode_response, make_pob_handlers, project_snapshot, serialize_snapshot
import json
import time


snapshot_a = {
    "activeSpec": {"id": 1, "allocNodes": [90, 12, 90, None], "jewels": {9408: 1, 9409: 1}},
    "activeSkillSet": {"id": "default", "title": None}, "config": {"enemy": "AAAA", "unsupported": {"cycle": True}},
    "socketGroups": [{"order": 1, "identity": "Fireball", "enabled": True, "gems": [{"order": 1, "identity": "Fireball", "level": 20, "quality": 20, "enabled": True, "support": False}]}],
}
cycle = {}
cycle["self"] = cycle
snapshot_a["config"]["cycle"] = cycle
snapshot_b = {"socketGroups": [{"enabled": True, "identity": "Fireball", "order": 1, "gems": [{"support": False, "enabled": True, "quality": 20, "level": 20, "identity": "Fireball", "order": 1}]}], "config": {"cycle": cycle, "unsupported": {"other": True}, "enemy": "AAAA"}, "activeSkillSet": {"title": None, "id": "default"}, "activeSpec": {"jewels": {9409: 1, 9408: 1}, "allocNodes": [12, 90, 90], "id": 1}}
projected = project_snapshot(snapshot_a)
assert projected["activeSpec"]["allocatedNodeIds"] == [12, 90]
assert projected["activeSpec"]["jewelIds"] == [9408, 9409]
assert projected["socketGroups"][0]["gems"][0]["identity"] == "Fireball"
assert projected["socketGroups"][0]["gems"][0]["level"] == 20
assert projected["socketGroups"][0]["gems"][0]["support"] is False
assert "allocNodes" not in projected["activeSpec"] and "cycle" not in projected["config"]
assert project_snapshot({"activeSpec": {"id": {"bad": True}, "title": ["bad"]}, "gamePatch": {"bad": True}})["activeSpec"] == {"id": None, "title": None, "allocatedNodeIds": [], "jewelIds": []}
assert serialize_snapshot(snapshot_a) == serialize_snapshot(snapshot_b)
mixed_keys = serialize_snapshot({"config": {"a": 1, 2: "x"}})
assert mixed_keys == '{"activeBuffs":{},"activeItemSet":{},"activeSkillSet":{},"activeSpec":{"allocatedNodeIds":[],"id":null,"jewelIds":[],"title":null},"config":{"a":1},"dataRevision":null,"enemyConditions":{},"gamePatch":null,"mainSkill":{},"pobVersion":null,"socketGroups":[]}'

baseline = json.load(open("tests/fixtures/bridge/capture_baseline.json", encoding="utf-8"))
large = {"activeSpec": {"id": 1, "allocNodes": {index: {"linked": list(range(20)), "graph": {"node": index}} for index in range(1, 5001)}, "jewels": {index: index for index in range(9000, 9100)}}}
graph_size = len(json.dumps(large, separators=(",", ":")))
elapsed_values = []
for _ in range(baseline["repetitions"]):
    started = time.perf_counter()
    large_payload = serialize_snapshot(large)
    elapsed_values.append((time.perf_counter() - started) * 1000)
elapsed = sum(elapsed_values) / len(elapsed_values)
assert len(large_payload) < graph_size
assert len(large["activeSpec"]["allocNodes"]) == baseline["fixture_nodes"]
assert len(large["activeSpec"]["jewels"]) == baseline["fixture_jewels"]
assert len(large_payload) <= baseline["payload_bytes"]
assert elapsed <= baseline["capture_ms_average"] * 10


assert decode_response('{"ok":true,"result":{"value":14}}')["value"] == 14
assert decode_response('log line\n{"ok":true,"result":1}') == 1
assert _skill_alias("\ub1cc\ub3d9\uc758 \uc5f0\uc1c4 \ubc88\uac1c") == "Arc of Oscillating"
assert _skill_alias("  Arc   of Oscillating ") == "Arc of Oscillating"
assert _skill_alias("unknown skill alias") == "unknown skill alias"
assert {"get_character_stats", "get_skill_stats", "get_skill_dps", "get_highest_dps_skill", "get_duration", "get_projectile_count", "get_skill_chain", "get_curse_limit", "get_socket_order", "get_support_links", "get_item_modifiers"}.issubset(make_pob_handlers("build.xml"))
for payload in ("", "not json", '{"ok":false,"error":"missing build"}'):
    try:
        decode_response(payload)
    except RuntimeError:
        pass
    else:
        raise AssertionError("bridge failure was not raised")
try:
    decode_response('{"ok":false,"error":"TotalDPS is unavailable for all skills"}')
except PobUnavailableError:
    pass
else:
    raise AssertionError("PoB unavailable result was not classified")
try:
    decode_response('{"ok":false,"error":{"code":"USER_CONTEXT_MISSING","recovery_class":"ASK_USER","stage":"context_resolution","retryable":false,"attempt":1,"max_attempts":1,"message":"unknown skill","next_action":"ask_user","secondary_causes":[]}}')
except PobBridgeError as error:
    assert error.error["code"] == "USER_CONTEXT_MISSING" and error.error["recovery_class"] == "ASK_USER"
    assert error.error["stage"] == "context_resolution" and error.error["next_action"] == "ask_user"
else:
    raise AssertionError("structured bridge error was not preserved")
try:
    decode_response('{"ok":false,"error":{"code":"AMBIGUOUS_ALIAS","recovery_class":"ASK_USER","stage":"context_resolution","retryable":false,"attempt":1,"max_attempts":1,"message":"ambiguous","next_action":"ask_user","secondary_causes":[]}}')
except PobBridgeError as error:
    assert error.error["code"] == "AMBIGUOUS_ALIAS"
    assert error.error["side_effect"] == "none" and "operator_message" in error.error
else:
    raise AssertionError("ambiguous alias was not preserved")
print("pob bridge self-check passed")
