-- Real PoB XML regression: a temporary Config calculation must not leave
-- calculation output or UI/config state changed after restore.
local buildPath = assert(os.getenv("POB_AGENT_TEST_BUILD"), "POB_AGENT_TEST_BUILD is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
dofile("HeadlessWrapper.lua")
local context = LoadModule("Modules/AgentContext")
local build = assert(context.load_xml_file(buildPath, "config restore regression"))
local function totalDps()
	return build.calcsTab and build.calcsTab.mainEnv and build.calcsTab.mainEnv.player and build.calcsTab.mainEnv.player.output and build.calcsTab.mainEnv.player.output.TotalDPS
end
local function copy(values)
	local result = {}
	for key, value in pairs(values or {}) do
		if type(value) ~= "table" and type(value) ~= "function" and type(value) ~= "userdata" then result[key] = value end
	end
	return result
end
local originalInput = copy(build.configTab.input)
local originalActiveConfig = build.configTab.activeConfigSetId
local before = totalDps()
assert(before ~= nil, "real build has no baseline TotalDPS")
local resistanceControl = build.configTab.varControls and build.configTab.varControls.resistancePenalty
print("config-debug before input=" .. tostring(build.configTab.input.resistancePenalty) .. " sel=" .. tostring(resistanceControl and resistanceControl.selIndex) .. " mainSkill=" .. tostring(build.mainSkill) .. " socket=" .. tostring(build.mainSocketGroup))
local restore, applied = assert(context.begin_config_overrides(build, { resistancePenalty = 0 }))
local during = totalDps()
print("config-debug during input=" .. tostring(build.configTab.input.resistancePenalty) .. " sel=" .. tostring(resistanceControl and resistanceControl.selIndex) .. " mainSkill=" .. tostring(build.mainSkill) .. " socket=" .. tostring(build.mainSocketGroup))
assert(during ~= nil, "Config override produced no real PoB output")
if os.getenv("POB_AGENT_EXPECT_CONFIG_CHANGE") == "1" then
	assert(during ~= before, "Config override did not change real PoB output")
end
restore()
local after = totalDps()
print("config-debug after input=" .. tostring(build.configTab.input.resistancePenalty) .. " sel=" .. tostring(resistanceControl and resistanceControl.selIndex) .. " mainSkill=" .. tostring(build.mainSkill) .. " socket=" .. tostring(build.mainSocketGroup))
assert(after == before, "temporary Config restore changed TotalDPS: before=" .. tostring(before) .. ", after=" .. tostring(after))
assert(build.configTab.activeConfigSetId == originalActiveConfig, "active config set was not restored")
for key, value in pairs(originalInput) do assert(build.configTab.input[key] == value, "config input was not restored: " .. tostring(key)) end
for key in pairs(build.configTab.input) do assert(originalInput[key] ~= nil, "temporary config key remained: " .. tostring(key)) end
local bridge = LoadModule("Modules/AgentBridge")
local thrownResult, thrownError = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { resistancePenalty = 0 } } }, nil,
	function() error("forced real dispatcher failure") end)
assert(thrownResult == nil and thrownError and thrownError.code == "POB_CALCULATION_ERROR", "dispatcher exception was not structured")
assert(totalDps() == before, "dispatcher exception changed real PoB output")
for key, value in pairs(originalInput) do assert(build.configTab.input[key] == value, "exception did not restore config input: " .. tostring(key)) end
for key in pairs(build.configTab.input) do assert(originalInput[key] ~= nil, "exception left temporary config key: " .. tostring(key)) end
print("test_agent_config_restore_real: ok before=" .. tostring(before) .. " during=" .. tostring(during) .. " after=" .. tostring(after))
