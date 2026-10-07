local readonly = {
	get_character_stats = true, get_skill_stats = true, get_skill_dps = true,
	get_highest_dps_skill = true, get_skill_breakdown = true, get_item_modifiers = true,
	get_projectile_behavior = true, get_trigger_sequence = true, get_curse_application_order = true,
	get_ailment_effect = true, get_damage_breakdown = true, get_conversion_chain = true,
	get_effective_resistance = true, get_support_links = true, resolve_skill_context = true,
	get_projectile_count = true, get_curse_limit = true, get_elemental_penetration = true,
	get_skill_chain = true, get_socket_order = true, compare_support_effect = true,
	explain_damage_change = true, get_duration = true, explain_stat = true,
}
local calls = {}
local agentBridge = {
	isReadOnly = function(name) return readonly[name] == true end,
	dispatch = function(build, request, _, adapter)
		assert(build == _G.testBuild)
		return adapter(build, request.tool, request.arguments)
	end,
}
local inProcess = {
	currentBuild = function() return _G.testBuild end,
	dispatch = function(name, arguments)
		calls[#calls + 1] = { name = name, arguments = arguments }
		return { facts = { tool = name, arguments = arguments } }
	end,
}
package.preload.socket = function() return {} end
package.preload.dkjson = function() return {} end
_G.LoadModule = function(name)
	if name == "Modules/AgentErrorRegistry" then return { parent = function(code) return code end } end
	if name == "Modules/AgentBridge" then return agentBridge end
	if name == "Modules/AgentInProcess" then return inProcess end
	if name == "Modules/AgentTool" then return {} end
	error("unexpected module " .. tostring(name))
end

local control = dofile("src/Modules/AgentControl.lua")
local main = { agentControlToken = "test-capability" }
_G.testBuild = { calcsTab = { mainEnv = { player = {} } } }

for name in pairs(readonly) do
	local response = control.dispatchRequest(main, { op = name, token = "test-capability", arguments = { skillIndex = 2 } })
	assert(response.ok and response.result.facts.tool == name, "read-only tool did not dispatch: " .. name)
end
assert(#calls == 24, "expected all 24 read-only tools to dispatch")
assert(calls[1].arguments.skillIndex == 2)

local mutation = control.dispatchRequest(main, { op = "replace_item", token = "test-capability", arguments = {} })
assert(not mutation.ok and mutation.error.code == "MUTATION_NOT_PERSISTENT")
assert(#calls == 24, "mutation must not reach the in-process dispatcher")
for _, name in ipairs({ "replace_gem", "change_passive" }) do
	local response = control.dispatchRequest(main, { op = name, token = "test-capability", arguments = {} })
	assert(not response.ok and response.error.code == "MUTATION_NOT_PERSISTENT")
end
assert(#calls == 24, "mutation tools must not reach the in-process dispatcher")

local unknown = control.dispatchRequest(main, { op = "unregistered_tool", token = "test-capability", arguments = {} })
assert(not unknown.ok and unknown.error.code == "TOOL_NOT_FOUND")

local unauthorized = control.dispatchRequest(main, { op = "get_skill_dps", token = "wrong", arguments = {} })
assert(not unauthorized.ok and unauthorized.error.code == "AUTH_REQUIRED")

_G.testBuild = nil
local comparison = control.dispatchRequest(main, {
	op = "compare_build_states", token = "test-capability",
	arguments = { beforeState = { id = "a" }, afterState = { id = "b" }, skillIndex = 1 },
})
assert(comparison.ok and calls[#calls].name == "compare_build_states", "snapshot comparison must not require a live build")
print("test_agent_control_dispatch: ok")
