local buildPath = assert(arg[1], "XML build path is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
dofile("HeadlessWrapper.lua")
local json = require "dkjson"
local context = LoadModule("Modules/AgentContext")
local tools = LoadModule("Modules/AgentTool")
local build, loadErr = context.load_xml_file(buildPath, "Agent XML build")
local function failure(code, recovery, stage, retryable, nextAction, message)
	return { code = code, recovery_class = recovery, stage = stage, retryable = retryable, attempt = 1, max_attempts = 1, message = message, details = {}, next_action = nextAction, secondary_causes = {} }
end
local function emitFailure(failureValue)
	io.write(json.encode({ ok = false, error = failureValue }))
end
if not build then emitFailure(failure("BUILD_LOAD_FAILED", "REJECT", "build_load", false, "reject_request", loadErr or "XML build load failed")); return end
runCallback("OnFrame")
if build.calcsTab and type(build.calcsTab.BuildOutput) == "function" then
	if wipeGlobalCache then wipeGlobalCache() end
	local calculated, calculationErr = pcall(build.calcsTab.BuildOutput, build.calcsTab)
	if not calculated then emitFailure(failure("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "pob_calculation", false, "report_error", tostring(calculationErr))); return end
end
local request = json.decode(io.read("*a") or "")
local function respond(value)
	io.write(json.encode(value))
end
if type(request) ~= "table" or type(request.tool) ~= "string" or type(request.arguments) ~= "table" then
	respond({ ok = false, error = failure("INPUT_INVALID", "REPAIR_INPUT", "input_validation", false, "repair_input", "request must contain tool and arguments") })
	return
end
local args = request.arguments
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
else
	result, err = tool(build, args.skillIndex)
end
if not result then
	local message = tostring(err or "PoB tool failed")
	local code, recovery, stage, nextAction = "POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", "report_error"
	if message:lower():find("unavailable", 1, true) then code, recovery, nextAction = "VALUE_UNAVAILABLE", "REJECT", "reject_request" end
	if message:lower():find("ambiguous", 1, true) then code, recovery = "AMBIGUOUS_ALIAS", "ASK_USER" end
	respond({ ok = false, error = failure(code, recovery, stage, false, nextAction, message) }); return
end
respond({ ok = true, result = result })
