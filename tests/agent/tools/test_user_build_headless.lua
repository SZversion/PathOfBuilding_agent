local buildPath = assert(os.getenv("POB_AGENT_TEST_BUILD"), "POB_AGENT_TEST_BUILD is required")
local file = assert(io.open(buildPath, "r"))
local xml = file:read("*a")
file:close()

dofile("src/HeadlessWrapper.lua")
loadBuildFromXML(xml, "Agent external build test")
runCallback("OnFrame")

assert(build.agentSnapshot, "agent snapshot was not created")
assert(build.agentSnapshot.outputs, "snapshot outputs are missing")
assert(#build.agentSnapshot.skills > 0, "snapshot skills are missing")

local explanation = assert(build.explainAgentStat("Life"))
assert(explanation.value ~= nil, "Life explanation has no value")
print("user build snapshot test passed: skills=" .. #build.agentSnapshot.skills .. ", life=" .. tostring(explanation.value))
