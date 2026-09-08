import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.pob.bridge import decode_response


assert decode_response('{"ok":true,"result":{"value":14}}')["value"] == 14
assert decode_response('log line\n{"ok":true,"result":1}') == 1
for payload in ("", "not json", '{"ok":false,"error":"missing build"}'):
    try:
        decode_response(payload)
    except RuntimeError:
        pass
    else:
        raise AssertionError("bridge failure was not raised")
print("pob bridge self-check passed")
