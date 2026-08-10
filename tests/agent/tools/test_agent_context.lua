local context = dofile("src/Modules/AgentContext.lua")
local callbackCount = 0
loadBuildFromXML = function(xml, name)
	build = {
		targetVersion = "3_29",
		skillsTab = {
			activeSkillSetId = 1,
			skillSetOrderList = { 1 },
			skillSets = { [1] = { title = "Endgame" } },
		socketGroupList = { },
		},
		calcsTab = { mainEnv = { player = { activeSkillList = { } } } },
	}
	build.skillsTab.SetActiveSkillSet = function(tab, id) tab.activeSkillSetId = id end
	build.calcsTab.BuildOutput = function(calcs)
		build.skillsTab.socketGroupList = {
			{ sourceItem = { name = "Doomed Crown", baseName = "Helmet" }, slot = "Helmet", enabled = true,
				displayGemList = {
					{ nameSpec = "Kinetic Fusillade", fromItem = true },
					{ nameSpec = "Greater Volley", gemData = { grantedEffect = { support = true } } },
				},
			},
		}
		calcs.mainEnv.player.activeSkillList = { { socketGroup = build.skillsTab.socketGroupList[1], activeEffect = { grantedEffect = { name = "Kinetic Fusillade" } } } }
	end
end
runCallback = function(name) callbackCount = callbackCount + 1 end

local loaded = assert(context.load_xml_file("tests/agent/tools/test_agent_context.lua", "fake"))
assert(loaded.targetVersion == "3_29" and callbackCount == 1)
local found = assert(context.find_skill(loaded, "Endgame", "kinetic fusillade"))
assert(found.socketGroup == 1 and found.skillIndex == 1 and found.sourceType == "item_granted")
assert(found.sourceItem.name == "Doomed Crown" and found.supports[1] == "Greater Volley" and found.linkCount == 2)
local missing, missingErr = context.find_skill(loaded, "Endgame", "Missing")
assert(missing == nil and missingErr)
local invalid, invalidErr = context.load_xml_file("tests/agent/tools/missing.xml")
assert(invalid == nil and invalidErr)
print("agent context self-check passed")
