local buildPath = assert(arg[1], "XML build path is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
dofile("HeadlessWrapper.lua")
local json = require "dkjson"
local context = LoadModule("Modules/AgentContext")
local tools = LoadModule("Modules/AgentTool")
local build, loadErr = context.load_xml_file(buildPath, "Agent XML build")
local currentRevision = "unknown"
if build then
	currentRevision = tostring(build.snapshotRevision or build.revision or build.agentSnapshotRevision or "unknown")
end
local function failure(code, recovery, stage, retryable, nextAction, message)
	return { code = code, recovery_class = recovery, stage = stage, retryable = retryable, attempt = 1, max_attempts = retryable and 4 or 1, message = message, details = {}, next_action = nextAction, secondary_causes = {}, snapshotRevision = currentRevision, side_effect = "none", operator_message = nil }
end
local function emitFailure(failureValue)
	io.write(json.encode({ ok = false, error = failureValue }))
end
if not build then emitFailure(failure("BUILD_LOAD_FAILED", "REJECT", "build_load", false, "reject_request", loadErr or "XML build load failed")); return end
runCallback("OnFrame")
local request = json.decode(io.read("*a") or "")
local function respond(value)
	io.write(json.encode(value))
end
if type(request) ~= "table" or type(request.tool) ~= "string" or type(request.arguments) ~= "table" then
	respond({ ok = false, error = failure("INPUT_INVALID", "REPAIR_INPUT", "input_validation", false, "repair_input", "request must contain tool and arguments") })
	return
end
local args = request.arguments
local mutationTools = { replace_item = true, replace_gem = true, change_passive = true }
if mutationTools[request.tool] or request.mutation == true then
	local snapshot = LoadModule("Modules/AgentSnapshot")
	local revisionOk, revisionErr = snapshot.assertRevision(build, args.expectedSnapshotRevision or request.expectedSnapshotRevision)
	if not revisionOk then
		respond({ ok = false, error = failure("SNAPSHOT_REVISION_CONFLICT", "REFRESH_CONTEXT", "mutation_precondition", false, "recapture_snapshot", "PoB snapshot revision is stale") })
		return
	end
end
local selectedContext, contextErr = context.apply_calculation_context(build, args)
if not selectedContext then
	local message = tostring(contextErr or "PoB calculation context cannot be selected")
	local code, recovery, nextAction = "USER_CONTEXT_MISSING", "ASK_USER", "ask_user"
	if message:lower():find("ambiguous", 1, true) then code = "AMBIGUOUS_ALIAS" end
	if message:lower():find("unavailable", 1, true) or message:lower():find("cannot be applied", 1, true) then
		code, recovery, nextAction = "VALUE_UNAVAILABLE", "REJECT", "reject_request"
	end
	respond({ ok = false, error = failure(code, recovery, "context_resolution", false, nextAction, message) })
	return
end
if build.calcsTab and type(build.calcsTab.BuildOutput) == "function" then
	if wipeGlobalCache then wipeGlobalCache() end
	local calculated, calculationErr = pcall(build.calcsTab.BuildOutput, build.calcsTab)
	if not calculated then emitFailure(failure("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "pob_calculation", false, "report_error", tostring(calculationErr))); return end
end
if args.skillName then
	local resolved, resolveErr = context.find_skill(build, args.skillSetSelector, args.skillName)
if not resolved then
	if type(resolveErr) == "table" then
		respond({ ok = false, error = resolveErr }); return
	end
	local message = tostring(resolveErr)
	local code, recovery, nextAction = "USER_CONTEXT_MISSING", "ASK_USER", "ask_user"
	if message:lower():find("ambiguous", 1, true) then code = "AMBIGUOUS_ALIAS" end
	respond({ ok = false, error = failure(code, recovery, "context_resolution", false, nextAction, message) }); return
end
	args.skillIndex = resolved.skillIndex
end
local tool = tools[request.tool]
if type(tool) ~= "function" then respond({ ok = false, error = failure("TOOL_NOT_FOUND", "REPAIR_INPUT", "tool_dispatch", false, "repair_input", "unknown PoB tool: " .. request.tool) }); return end
local result, err
if request.tool == "resolve_skill_context" or request.tool == "get_support_links" or request.tool == "get_skill_chain" or request.tool == "get_socket_order" or request.tool == "get_curse_application_order" then
	result, err = tool(build, args.skillSetSelector, args.skillName)
elseif request.tool == "compare_support_effect" or request.tool == "explain_damage_change" then
	result, err = tool(build, args.skillSetSelector, args.skillName, args.supportName)
elseif request.tool == "get_item_modifiers" then
	result, err = tool(build, args.itemId)
elseif request.tool == "get_duration" then
	result, err = tool(build, args.skillIndex, args.durationType)
elseif request.tool == "explain_stat" then
	result, err = tool(build, args.stat, args.skillIndex)
elseif request.tool == "compare_build_states" then
	result, err = tool(args.beforeState, args.afterState, args.skillIndex, args.comparisonFields)
elseif request.tool == "replace_item" then
	result, err = tool(build, args)
elseif request.tool == "replace_gem" then
	result, err = tool(build, args)
elseif request.tool == "change_passive" then
	result, err = tool(build, args)
else
	result, err = tool(build, args.skillIndex)
end
if not result then
	if type(err) == "table" then
		if not err.side_effect then err.side_effect = "none" end
		if err.operator_message == nil then err.operator_message = nil end
		if not err.attempt then err.attempt = 1 end
		if not err.max_attempts then err.max_attempts = 1 end
		if not err.details then err.details = {} end
		if not err.secondary_causes then err.secondary_causes = {} end
		respond({ ok = false, error = err }); return
	end
	local message = tostring(err or "PoB tool failed")
	local code, recovery, stage, nextAction = "POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", "report_error"
	if message:lower():find("unavailable", 1, true) then code, recovery, nextAction = "VALUE_UNAVAILABLE", "REJECT", "reject_request" end
	if message:lower():find("ambiguous", 1, true) then code, recovery = "AMBIGUOUS_ALIAS", "ASK_USER" end
	respond({ ok = false, error = failure(code, recovery, stage, false, nextAction, message) }); return
end
respond({ ok = true, result = result })
