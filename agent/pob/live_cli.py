"""Small CLI for controlling a running PoB instance through AgentControl."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from .live_transport import LivePobTransport, LivePobTransportError


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-dir", help="PoB user data directory containing AgentBridge-*.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show the running PoB process status")
    commands.add_parser("list", help="List saved builds known to the running PoB")
    load = commands.add_parser("load", help="Open an exact build ID returned by list")
    load.add_argument("build_id")
    commands.add_parser("snapshot", help="Capture the current in-memory build snapshot")
    commands.add_parser("items", help="Open the Items tab in the active PoB build")
    select_skill = commands.add_parser("select-skill", help="Select a main skill by its exact PoB label and open Calcs")
    select_skill.add_argument("skill_name")
    dps = commands.add_parser("dps", help="Read PoB TotalDPS for a skill")
    dps.add_argument("--skill-index", type=int)
    dps.add_argument("--skill-name")
    commands.add_parser("highest-dps", help="Read PoB's highest-DPS skill")
    args = parser.parse_args(argv)

    operations = {
        "status": {"op": "status"},
        "list": {"op": "list_builds"},
        "snapshot": {"op": "capture_snapshot"},
        "items": {"op": "show_items"},
        "highest-dps": {"op": "get_highest_dps_skill"},
    }
    if args.command == "load":
        operations["load"] = {"op": "load_build", "id": args.build_id}
    elif args.command == "select-skill":
        operations["select-skill"] = {"op": "select_main_skill", "arguments": {"skillName": args.skill_name}}
    elif args.command == "dps":
        if args.skill_index is None and not args.skill_name:
            parser.error("dps requires --skill-index or --skill-name")
        arguments = {}
        if args.skill_index is not None:
            arguments["skillIndex"] = args.skill_index
        if args.skill_name:
            arguments["skillName"] = args.skill_name
        operations["dps"] = {"op": "get_skill_dps", "arguments": arguments}

    try:
        transport = LivePobTransport(args.endpoint_dir)
        response = transport.request(operations[args.command])
        if args.command == "load" and response.get("ok"):
            expected_name = response.get("result", {}).get("build", {}).get("name")
            deadline = time.monotonic() + 15
            while expected_name and time.monotonic() < deadline:
                status = transport.request({"op": "status"})
                current = status.get("result", {}) if status.get("ok") else {}
                if current.get("mode") == "BUILD" and not current.get("pendingMode") and current.get("activeBuildName") == expected_name:
                    response = {**response, "loaded": True, "status": current}
                    break
                if current.get("busy"):
                    response = {"ok": False, "error": "PoB requires user action before the build can finish loading", "load": response}
                    break
                time.sleep(0.1)
            else:
                response = {"ok": False, "error": "Timed out waiting for PoB to finish loading the selected build", "load": response}
    except LivePobTransportError as error:
        _print({"ok": False, "error": str(error)})
        return 2
    _print(response)
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
