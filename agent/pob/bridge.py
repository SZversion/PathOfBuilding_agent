import json
import os
import subprocess
from pathlib import Path


def decode_response(stdout):
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("PoB bridge returned no JSON")
    try:
        response = json.loads(lines[-1])
    except json.JSONDecodeError as error:
        raise RuntimeError("PoB bridge returned invalid JSON") from error
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(response.get("error", "PoB bridge request failed") if isinstance(response, dict) else "PoB bridge response is invalid")
    return response["result"]


class PobBridge:
    def __init__(self, luajit="luajit", script_path=None, timeout=120):
        self.luajit = luajit
        self.script_path = Path(script_path or Path(__file__).parents[2] / "tools" / "agent_pob_bridge.lua")
        self.cwd = self.script_path.parents[1] / "src"
        self.timeout = timeout

    def call(self, build_path, tool, arguments):
        payload = json.dumps({"tool": tool, "arguments": arguments}, ensure_ascii=False)
        try:
            process = subprocess.run(
                [self.luajit, str(self.script_path), str(build_path)],
                input=payload,
                text=True,
                capture_output=True,
                cwd=self.cwd,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("PoB bridge timed out") from error
        if process.returncode != 0:
            detail = process.stderr.strip() or process.stdout.strip() or "unknown process error"
            raise RuntimeError("PoB bridge exited with code %d: %s" % (process.returncode, detail))
        return decode_response(process.stdout)


def make_pob_handlers(build_path, luajit=None, timeout=120):
    bridge = PobBridge(luajit or os.getenv("LUAJIT", "luajit"), timeout=timeout)
    return {name: (lambda arguments, name=name: bridge.call(build_path, name, arguments)) for name in (
        "get_projectile_count", "get_curse_limit", "get_elemental_penetration",
    )}
