import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.pob.bridge import PobBridgeError, PobUnavailableError, _skill_alias, decode_response, make_pob_handlers


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
else:
    raise AssertionError("ambiguous alias was not preserved")
print("pob bridge self-check passed")
