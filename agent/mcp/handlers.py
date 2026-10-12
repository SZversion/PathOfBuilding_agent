"""Group based adapters for the canonical MCP tool catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from agent.orchestration.function_trace import trace_pipeline
from agent.mcp.registry import validate_tool_call
from agent.error_registry import parent_error_ref
from agent.pob.live_transport import LivePobTransport, LivePobTransportError
from agent.search.external_search import ExternalSearch
from agent.search.knowledge_search import KnowledgeSearch
from agent.tool_catalog import ALLOWED_TOOLS, TOOL_CATALOG

_ERROR_RECOVERY = {
    "INPUT_INVALID": ("REJECT", False, "reject_request"),
    "TOOL_NOT_FOUND": ("REJECT", False, "reject_request"),
    "MUTATION_NOT_PERSISTENT": ("REJECT", False, "reject_request"),
    "VALUE_UNAVAILABLE": ("REJECT", False, "reject_request"),
    "BRIDGE_PROTOCOL_ERROR": ("FATAL_INTERNAL", False, "report_error"),
    "TOOL_TRANSIENT": ("RETRY_TOOL", True, "retry_bounded"),
    "TIMEOUT": ("RETRY_TOOL", True, "retry_bounded"),
    "UNCLASSIFIED_FAILURE": ("FATAL_INTERNAL", False, "report_error"),
}


def _knowledge_search():
    index = Path(__file__).parents[1] / "knowledge" / "index" / "poe1-3.29.json"
    return KnowledgeSearch(index)


def _error(code: str, message: str, *, stage: str) -> dict:
    if code not in _ERROR_RECOVERY:
        code = "UNCLASSIFIED_FAILURE"
    recovery, retryable, action = _ERROR_RECOVERY[code]
    error = {"error_ref": parent_error_ref(code), "error_code": code, "code": code,
             "recovery_class": recovery, "stage": stage, "retryable": retryable,
             "attempt": 1, "max_attempts": 4 if retryable else 1, "message": message,
             "details": {}, "next_action": action, "secondary_causes": [],
             "side_effect": "none", "operator_message": None}
    return {"schema_version": "1.0", "status": "error", "snapshotRevision": None,
            "side_effect": "none", "operator_message": None, "facts": {}, "conditions": [],
            "trace": [], "sources": [], "version": {"gamePatch": None, "pobVersion": None, "dataRevision": None},
            "evidenceGraph": {"nodes": [], "stages": [], "sourceEdges": []},
            "uncertainty": {"level": "high", "reasons": [code], "missingEvidence": []}, "error": error}


def _success(name, value):
    if isinstance(value, dict) and ("status" in value or "facts" in value or "evidenceGraph" in value):
        result = dict(value)
        result.setdefault("schema_version", "1.0")
        result.setdefault("status", "ok")
        result.setdefault("side_effect", "none")
        result.setdefault("facts", {})
        result.setdefault("conditions", [])
        result.setdefault("trace", [])
        result.setdefault("sources", [])
        result.setdefault("version", {"gamePatch": None, "pobVersion": None, "dataRevision": None})
        result.setdefault("evidenceGraph", {"nodes": [], "stages": [], "sourceEdges": []})
        result.setdefault("uncertainty", {"level": "low", "reasons": [], "missingEvidence": [], "temporaryEvidence": False})
        return result
    facts = value if isinstance(value, dict) else {"results": value}
    sources = []
    rows = value if isinstance(value, list) else [value]
    for row in rows:
        if isinstance(row, dict) and (row.get("url") or row.get("source")):
            sources.append({key: row[key] for key in ("source", "url", "title") if key in row})
    return {"schema_version": "1.0", "status": "ok", "side_effect": "none",
            "facts": facts, "conditions": [], "trace": [], "sources": sources,
            "version": {"gamePatch": None, "pobVersion": None, "dataRevision": None},
            "evidenceGraph": {"nodes": [], "stages": [], "sourceEdges": []},
            "uncertainty": {"level": "low", "reasons": [], "missingEvidence": [], "temporaryEvidence": False},
            "tool": name, "snapshotRevision": None}


def _invoke(transport, name, arguments):
    response = transport.request({"op": name, "arguments": arguments})
    if response.get("ok") is False:
        raw = response.get("error") or {}
        return _error(raw.get("error_code", raw.get("code", "BRIDGE_PROTOCOL_ERROR")),
                      raw.get("message", "PoB tool failed"), stage=raw.get("stage", "mcp_dispatch"))
    return _success(name, response.get("result", response))


def create_handlers(endpoint_dir=None, knowledge_search=None, external_search=None,
                    *, transport=None) -> dict[str, Callable]:
    """Build all registered handlers, selecting providers by ToolSpec.group."""
    transport = transport or LivePobTransport(endpoint_dir)
    knowledge_search = knowledge_search or _knowledge_search()
    external_search = external_search or ExternalSearch()
    handlers = {}
    for name, spec in TOOL_CATALOG.items():
        if spec.group == "pob_live":
            handlers[name] = lambda args, _name=name: _invoke(transport, _name, args)
        elif spec.group == "knowledge":
            method = {
                "search_knowledge": lambda args: knowledge_search.search(
                    args["query"], limit=args.get("limit", 10), category=args.get("category")),
                "resolve_item_alias": lambda args: knowledge_search.resolve_item_alias(
                    args["query"], category=args.get("category")),
                "resolve_skill_alias": lambda args: knowledge_search.resolve_skill_alias(args["query"]),
            }[name]
            handlers[name] = lambda args, _method=method, _name=name: _success(_name, _method(args))
        elif spec.group == "external_search":
            handlers[name] = lambda args, _name=name: _success(_name, external_search.search(
                args["query"], source=args.get("source", "both"), limit=args.get("limit", 3)))
        elif spec.group == "snapshot_compare":
            handlers[name] = lambda args, _name=name: _invoke(transport, _name, args)
        elif spec.group == "mutation":
            handlers[name] = lambda args: _error(
                "MUTATION_NOT_PERSISTENT", "Live PoB mutation is not supported", stage="mutation_capability")
        else:
            raise RuntimeError(f"No handler provider for catalog group: {spec.group}")

    if set(handlers) != set(ALLOWED_TOOLS):
        raise RuntimeError("handler providers do not cover the canonical tool catalog")

    # Validate again at this boundary so direct Python callers receive the same contract.
    return {name: _validated_handler(name, handler) for name, handler in handlers.items()}


def _validated_handler(name, handler):
    @trace_pipeline
    def call(arguments):
        try:
            normalized = validate_tool_call(name, arguments)
            return handler(normalized)
        except ValueError as error:
            return _error("INPUT_INVALID", str(error)[:500], stage="mcp_validation")
        except LivePobTransportError:
            return _error("VALUE_UNAVAILABLE", "The live PoB endpoint is unavailable", stage="mcp_transport")
        except Exception as error:
            return _error("UNCLASSIFIED_FAILURE", str(error)[:500], stage="mcp_tool")
    return call


def current_snapshot(transport=None) -> dict:
    """Fetch fresh normalized live context for the pob://current-snapshot resource."""
    transport = transport or LivePobTransport()
    result = _invoke(transport, "capture_snapshot", {})
    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(json.dumps(result["error"], ensure_ascii=False))
    return result
