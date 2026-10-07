"""Small command-line runtime for the read-only AgentLoop."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .orchestration.agent_loop import AgentLoop, ALLOWED_TOOLS
from .orchestration.recovery import exhausted_response, recover_response, standardize_error
from .orchestration.state_store import OrchestrationStateStore, StateStoreError
from .pob.bridge import PobBridgeError, make_pob_handlers
from .search.external_search import ExternalSearch
from .providers.ollama import DEFAULT_OLLAMA_MODEL, OllamaDevelopmentProvider
from .providers.openai_compatible import OpenAICompatibleClient
from .mcp.client import McpClientError, McpSearchFacade, McpToolClient


def _error(code, message, *, next_action="reject_request", details=None):
    if code in {"INPUT_INVALID", "TOOL_NOT_FOUND"}:
        next_action = "ask_user"
        recovery = "ASK_USER"
        details = {**(details or {}), "confirmation_type": "repair"}
    else:
        recovery = "REJECT"
    return {"status": "error", "error": {
        "code": code, "recovery_class": recovery, "stage": "cli",
        "retryable": False, "attempt": 1, "max_attempts": 1,
        "message": message, "details": details or {}, "next_action": next_action,
        "secondary_causes": [], "side_effect": "none", "operator_message": None,
    }}


def _build_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("--build must be a non-empty XML path")
    path = Path(value).expanduser().resolve()
    if path.suffix.casefold() != ".xml" or not path.is_file():
        raise ValueError("--build must point to an existing XML file")
    return path


def _cache_id(build):
    slug = re.sub(r"[^a-z0-9]+", "-", build.stem.casefold()).strip("-") or "build"
    digest = hashlib.sha256(str(build).encode("utf-8")).hexdigest()[:12]
    return f"{slug[:48]}-{digest}"


def _provider(args):
    if args.local_ollama:
        return OllamaDevelopmentProvider(model=args.model or DEFAULT_OLLAMA_MODEL)
    if args.model:
        raise ValueError("--model requires --local-ollama")
    endpoint = os.getenv("POB_AGENT_MODEL_ENDPOINT")
    if not endpoint:
        raise RuntimeError("remote model endpoint is unavailable; use --local-ollama explicitly")
    return OpenAICompatibleClient(endpoint=endpoint, model=os.getenv("POB_AGENT_MODEL", "external-agent"), api_key=os.getenv("POB_AGENT_API_KEY"))


def run_cli(argv=None, *, bridge_factory=None, provider_factory=None):
    parser = argparse.ArgumentParser(prog="python -m agent.cli")
    parser.add_argument("--build", required=True)
    parser.add_argument("--cache-root", default=None)
    parser.add_argument("--local-ollama", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--clarification-answer", default=None)
    parser.add_argument("--expected-snapshot-revision", default=None)
    stream_group = parser.add_mutually_exclusive_group()
    stream_group.add_argument("--stream", dest="stream", action="store_true")
    stream_group.add_argument("--no-stream", dest="stream", action="store_false")
    parser.set_defaults(stream=True)
    parser.add_argument("question", nargs="?")
    args = parser.parse_args(argv)
    try:
        build = _build_path(args.build)
        build_id = _cache_id(build)
        cache = OrchestrationStateStore(args.cache_root or (build.parent / ".agent-cache"))
        try:
            previous = cache.load_state(build_id)
        except StateStoreError as error:
            if error.error["code"] != "STATE_NOT_FOUND":
                return _emit({"status": "error", "error": error.error}, args.json_output)
            previous = {}
        if args.expected_snapshot_revision is not None:
            actual = (previous.get("snapshot") or {}).get("snapshotRevision")
            if actual != args.expected_snapshot_revision:
                return _emit(_error("SNAPSHOT_REVISION_CONFLICT", "cached snapshot revision is stale", next_action="recapture_snapshot", details={"expected": args.expected_snapshot_revision, "actual": actual}), args.json_output)
        question = args.question
        if not question and not args.once:
            while True:
                try:
                    entered = input("PoE question> ").strip()
                except EOFError:
                    break
                if not entered or entered.casefold() in {"exit", "quit"}:
                    break
                child = ["--build", str(build), "--cache-root", str(cache.root), "--once", entered]
                if args.local_ollama:
                    child.append("--local-ollama")
                    if args.model:
                        child += ["--model", args.model]
                if args.json_output:
                    child.append("--json")
                child.append("--stream")
                if args.clarification_answer:
                    child += ["--clarification-answer", args.clarification_answer]
                run_cli(child, bridge_factory=bridge_factory, provider_factory=provider_factory)
            return 0
        if not question and args.once:
            raise ValueError("a question is required with --once")
        if args.clarification_answer:
            pending = (previous.get("orchestration") or {}).get("pending")
            if not isinstance(pending, dict):
                return _emit(_error("USER_CONTEXT_MISSING", "no pending clarification is available", next_action="ask_user"), args.json_output)
            pending_revision = pending.get("snapshotRevision")
            if args.expected_snapshot_revision is None and pending_revision is not None:
                actual = (previous.get("snapshot") or {}).get("snapshotRevision")
                if actual != pending_revision:
                    return _emit(_error("SNAPSHOT_REVISION_CONFLICT", "pending clarification is stale", next_action="recapture_snapshot", details={"expected": pending_revision, "actual": actual}), args.json_output)
            question = question + "\nClarification answer: " + args.clarification_answer
        provider = provider_factory(args) if provider_factory else _provider(args)
        search = None
        current_revision = None
        mcp_client = None
        discovered_tools = None
        if bridge_factory is None:
            # Production calls always cross the local MCP stdio boundary.
            mcp_client = McpToolClient(cwd=Path(__file__).resolve().parents[1]).start()
            try:
                discovered_tools = mcp_client.list_tools()  # startup enforces exact catalog parity
                snapshot = mcp_client.read_resource()
            except Exception:
                mcp_client.close()
                raise
            snapshot.setdefault("buildId", build_id)
            snapshot.setdefault("buildNameHash", hashlib.sha256(build.stem.encode("utf-8")).hexdigest()[:16])
            handlers = {name: (lambda arguments, name=name: mcp_client.call_tool(name, arguments)) for name in ALLOWED_TOOLS}
            search = McpSearchFacade(mcp_client)
            current_revision = lambda: mcp_client.read_resource().get("snapshotRevision")
        else:
            bridge = bridge_factory(build)
            handlers = {name: (lambda arguments, name=name: bridge.call(build, name, arguments)) for name in (
                "get_character_stats", "get_skill_stats", "get_skill_dps", "get_highest_dps_skill", "get_skill_breakdown",
                "get_projectile_count", "get_curse_limit", "get_elemental_penetration", "get_skill_chain", "get_duration",
                "get_damage_breakdown", "get_support_links", "resolve_skill_context", "get_socket_order", "explain_stat",
            )}
            cached_snapshot = previous.get("snapshot") or {}
            snapshot = {"buildId": build_id, "source": "test_adapter", "snapshotRevision": cached_snapshot.get("snapshotRevision", "unknown"), "buildNameHash": hashlib.sha256(build.stem.encode("utf-8")).hexdigest()[:16]}
            try:
                facts = bridge.call(build, "get_character_stats", {})
                snapshot["facts"] = facts
                if isinstance(facts, dict):
                    for key in ("snapshotRevision", "gamePatch", "pobVersion", "dataRevision"):
                        if facts.get(key) is not None:
                            snapshot[key] = facts[key]
            except PobBridgeError as error:
                return _emit(_error(error.error["code"], str(error), next_action=error.error.get("next_action", "reject_request")), args.json_output)
            external_search = ExternalSearch()
            handlers["search_external"] = lambda arguments: external_search.search(
                arguments.get("query", ""), source=arguments.get("source", "both"), limit=arguments.get("limit", 3)
            )
        on_token = (lambda token: print(token, end="", flush=True)) if args.stream and not args.json_output else None
        try:
            result = AgentLoop(provider).run(question, search=search, handlers=handlers, snapshot=snapshot,
                                           current_revision=current_revision, tool_definitions=discovered_tools,
                                           on_token=on_token)
        finally:
            if mcp_client is not None:
                mcp_client.close()
        if not args.json_output:
            result = recover_response(result, provider, on_token=on_token if args.stream else None)
        cache.save_state(build_id, {
            **previous,
            "session": {"buildId": build_id, "buildNameHash": snapshot["buildNameHash"]},
            "snapshot": {"buildId": build_id, "snapshotRevision": snapshot.get("snapshotRevision"), "gamePatch": snapshot.get("gamePatch"), "pobVersion": snapshot.get("pobVersion"), "dataRevision": snapshot.get("dataRevision")},
            "orchestration": {"status": result.get("status"), "pending": ({**result.get("error", {}), "snapshotRevision": snapshot.get("snapshotRevision")} if result.get("error", {}).get("next_action") == "ask_user" else None)},
            "conversation": {"lastStatus": result.get("status")},
            "evidence": {"available": bool(result.get("execution"))},
        }, metadata={"gamePatch": snapshot.get("gamePatch"), "pobVersion": snapshot.get("pobVersion"), "dataRevision": snapshot.get("dataRevision")})
        return _emit(result, args.json_output, streamed=bool(on_token))
    except StateStoreError as error:
        return _emit({"status": "error", "error": error.error}, args.json_output)
    except McpClientError as error:
        return _emit(_error("BRIDGE_UNAVAILABLE", str(error), next_action="restart_pob_or_bridge"), args.json_output)
    except (ValueError, RuntimeError) as error:
        return _emit(_error("INPUT_INVALID" if isinstance(error, ValueError) else "MODEL_PROVIDER_UNAVAILABLE", str(error), next_action="repair_input" if isinstance(error, ValueError) else "configure_provider"), args.json_output)


def _emit(value, json_output, streamed=False):
    value = standardize_error(value)
    value = exhausted_response(value)
    if not json_output and isinstance(value, dict) and isinstance(value.get("error"), dict) and not value.get("answer"):
        value = recover_response(value)
    if streamed and value.get("answer"):
        print()
        return 0 if value.get("status") not in {"error", "plan_error"} else 1
    if not json_output and value.get("answer"):
        print(value["answer"])
        return 0 if value.get("status") not in {"error", "plan_error"} else 1
    print(json.dumps(value, ensure_ascii=False, indent=None if json_output else 2))
    return 0 if value.get("status") not in {"error", "plan_error"} else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
