local context = dofile("src/Modules/AgentContext.lua")

local calls = {}
local build = {
	treeTab = {
		specList = { { title = "Default" }, { title = "RedMaps-CorruptingFever" } },
		activeSpec = 1,
		SetActiveSpec = function(self, index) self.activeSpec = index; calls.tree = index end,
	},
	skillsTab = {
		skillSets = { [2] = { title = "Act1" }, [9] = { title = "RedMaps" } },
		skillSetOrderList = { 2, 9 },
		activeSkillSetId = 2,
		SetActiveSkillSet = function(self, id) self.activeSkillSetId = id; calls.skill = id end,
	},
	itemsTab = {
		itemSets = { [3] = { title = "Act2" }, [9] = { title = "RedMaps" } },
		itemSetOrderList = { 3, 9 },
		activeItemSetId = 3,
		SetActiveItemSet = function(self, id) self.activeItemSetId = id; calls.item = id end,
	},
}

local selected, err = context.apply_calculation_context(build, {
	activeSpec = "RedMaps-CorruptingFever",
	activeSkillSet = "RedMaps",
	activeItemSet = 9,
})
assert(selected and not err)
assert(calls.tree == 2 and calls.skill == 9 and calls.item == 9)
local active = assert(context.apply_calculation_context(build, {
	activeSkillSet = "active",
	activeItemSet = "active",
}))
assert(active.activeSkillSet.id == 9 and active.activeItemSet.id == 9)
assert(build.skillsTab.activeSkillSetId == 9 and build.itemsTab.activeItemSetId == 9)
local numeric = assert(context.apply_calculation_context(build, {
	activeSpec = "2", activeSkillSet = "9", activeItemSet = "9",
}))
assert(numeric.activeSpec.id == 2 and numeric.activeSkillSet.id == 9 and numeric.activeItemSet.id == 9)
build.configTab = {
	configSets = { [8] = { title = "Boss" } }, configSetOrderList = { 8 }, activeConfigSetId = 8,
	SetActiveConfigSet = function(self, id) self.activeConfigSetId = id end,
}
assert(context.apply_calculation_context(build, { activeConfigSet = "8" }).activeConfigSet.id == 8)
print("agent context selector self-check passed")
