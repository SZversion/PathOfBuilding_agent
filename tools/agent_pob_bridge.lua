local buildPath = assert(arg[1], "XML build path is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
dofile("HeadlessWrapper.lua")
local json = require "dkjson"
local context = LoadModule("Modules/AgentContext")
local tools = LoadModule("Modules/AgentTool")
local build, loadErr = context.load_xml_file(buildPath, "Agent XML build")
if not build then io.write(json.encode({ ok = false, error = loadErr or "XML build load failed" })); return end
runCallback("OnFrame")
if build.calcsTab and type(build.calcsTab.BuildOutput) == "function" then
	local calculated, calculationErr = pcall(build.calcsTab.BuildOutput, build.calcsTab)
	if not calculated then io.write(json.encode({ ok = false, error = calculationErr })); return end
end
local request = json.decode(io.read("*a") or "")
local function respond(value)
	io.write(json.encode(value))
end
if type(request) ~= "table" or type(request.tool) ~= "string" or type(request.arguments) ~= "table" then
	respond({ ok = false, error = "request must contain tool and arguments" })
	return
end
local args = request.arguments
if args.skillName then
	local resolved, resolveErr = context.find_skill(build, args.skillSetSelector, args.skillName)
	if not resolved then respond({ ok = false, error = resolveErr }); return end
	args.skillIndex = resolved.skillIndex
end
local tool = tools[request.tool]
if type(tool) ~= "function" then respond({ ok = false, error = "unknown PoB tool: " .. request.tool }); return end
local result, err
if request.tool == "resolve_skill_context" or request.tool == "get_support_links" or request.tool == "get_skill_chain" or request.tool == "get_socket_order" or request.tool == "get_curse_application_order" then
	result, err = tool(build, args.skillSetSelector, args.skillName)
elseif request.tool == "compare_support_effect" or request.tool == "explain_damage_change" then
	result, err = tool(build, args.skillSetSelector, args.skillName, args.supportName)
elseif request.tool == "get_item_modifiers" then
	result, err = tool(build, args.itemId)
elseif request.tool == "get_duration" then
	result, err = tool(build, args.skillIndex, args.durationType)
else
	result, err = tool(build, args.skillIndex)
end
if not result then respond({ ok = false, error = err or "PoB tool failed" }); return end
respond({ ok = true, result = result })
