local buildPath = assert(os.getenv("POB_AGENT_TEST_BUILD"), "POB_AGENT_TEST_BUILD is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
local file = assert(io.open(buildPath, "r"))
local xml = file:read("*a")
file:close()

dofile("HeadlessWrapper.lua")
loadBuildFromXML(xml, "Agent external build test")
runCallback("OnFrame")

assert(build.agentSnapshot, "agent snapshot was not created")
assert(build.agentSnapshot.outputs, "snapshot outputs are missing")
assert(#build.agentSnapshot.skills > 0, "snapshot skills are missing")

local tools = LoadModule("Modules/AgentTool")
local mechanisms = LoadModule("Modules/AgentMechanismTool")
local mechanism = assert(mechanisms.get_mechanism_snapshot(build))
assert(#mechanism.facts.skills > 0, "mechanism skills are missing")
local socketGroupCount = #mechanism.facts.socketGroups
local projectileIndex
for index, skill in ipairs(build.calcsTab.mainEnv.player.activeSkillList) do
	if skill.output and skill.output.ProjectileCount ~= nil then
		projectileIndex = index
		break
	end
end
local projectileValue = "unavailable"
if projectileIndex then
	local projectile = assert(tools.get_projectile_count(build, projectileIndex))
	assert(projectile.facts.value ~= nil, "projectile tool has no value")
	projectileValue = tostring(projectile.facts.value)
end
local curse = assert(tools.get_curse_limit(build))
assert(curse.facts.value ~= nil, "curse tool has no value")
local explanation = assert(build.explainAgentStat("Life"))
assert(explanation.value ~= nil, "Life explanation has no value")
print("user build tool smoke test passed: skills=" .. #build.agentSnapshot.skills .. ", socketGroups=" .. socketGroupCount .. ", projectile=" .. projectileValue .. ", curse=" .. tostring(curse.facts.value) .. ", life=" .. tostring(explanation.value) .. ", combatSimulation=" .. mechanism.facts.simulations.combatOutcome.status)
