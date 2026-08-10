from .planner import plan


def execute_plan(question, planned, search=None, handlers=None):
    """Execute a planner result without raising at the orchestration boundary."""
    handlers = handlers or {}
    output = {
        "question": question,
        "intent": planned.get("intent", "unknown") if isinstance(planned, dict) else "unknown",
        "steps": [],
    }
    steps = planned.get("steps", []) if isinstance(planned, dict) else []
    if not isinstance(steps, list):
        output["steps"].append({"tool": None, "status": "error", "error": "steps must be a list"})
        return output
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("tool"), str):
            output["steps"].append({"tool": None, "status": "error", "error": "invalid step"})
            continue
        tool = step["tool"]
        if "arguments" not in step:
            output["steps"].append({"tool": tool, "status": "error", "error": "arguments are required"})
            continue
        arguments = step["arguments"]
        if not isinstance(arguments, dict):
            output["steps"].append({"tool": tool, "status": "error", "error": "arguments must be a dict"})
            continue
        if tool == "search_knowledge":
            if search is None:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": "knowledge search is not configured"})
                continue
            try:
                result = search.search(arguments.get("query", ""), limit=arguments.get("limit", 10), category=arguments.get("category"))
            except Exception as error:  # boundary: keep one failed step inspectable
                output["steps"].append({"tool": tool, "status": "error", "error": str(error)})
            else:
                output["steps"].append({"tool": tool, "status": "ok", "result": result})
            continue
        if tool == "resolve_item_alias":
            if search is None:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": "knowledge search is not configured"})
                continue
            try:
                result = search.resolve_item_alias(arguments.get("query", ""), category=arguments.get("category"))
            except Exception as error:
                output["steps"].append({"tool": tool, "status": "error", "error": str(error)})
            else:
                output["steps"].append({"tool": tool, "status": "ok" if result else "unavailable", "result": result} if result else {"tool": tool, "status": "unavailable", "error": "item alias was not found"})
            continue
        handler = handlers.get(tool)
        if not callable(handler):
            output["steps"].append({"tool": tool, "status": "unavailable", "error": "handler is not configured"})
            continue
        try:
            result = handler(arguments)
        except Exception as error:  # boundary: tool failures belong to the step
            output["steps"].append({"tool": tool, "status": "error", "error": str(error)})
        else:
            output["steps"].append({"tool": tool, "status": "ok", "result": result})
    return output


execute = execute_plan


def run_question(question, search=None, handlers=None):
    """Plan and execute one question."""
    planned = plan(question)
    return execute_plan(question, planned, search=search, handlers=handlers)
