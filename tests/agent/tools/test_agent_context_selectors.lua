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
print("agent context selector self-check passed")
