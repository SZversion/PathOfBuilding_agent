local tool = dofile("src/Modules/AgentMechanismTool.lua")

local build = {
	targetVersion = "3_29",
	calcsTab = { mainEnv = { player = {
		output = { EnemyCurseLimit = 3, Life = 5000 },
		breakdown = { Life = { "base life", "= 5000" } },
		activeSkillList = {
			{ activeEffect = { grantedEffect = { name = "Temporal Chains" } }, skillPartName = 1, infoTrigger = "Manual", output = { ProjectileCount = 2, TotalDPS = 100 }, breakdown = { ProjectileCount = { "base", "= 2" } } },
		},
	} } },
	itemsTab = { slots = { ["Body Armour"] = { selItemId = 1 } }, items = { [1] = { name = "Skin of the Loyal", baseName = "Simple Robe" } } },
	skillsTab = { socketGroupList = {
		{ slot = "Body Armour", label = "Main", enabled = true, mainActiveSkill = 1, gemList = {
			{ name = "Temporal Chains", baseName = "Temporal Chains", triggered = false },
			{ name = "Spell Cascade", baseName = "Spell Cascade Support", triggered = true },
		} },
	} },
}

local result = assert(tool.get_mechanism_snapshot(build))
assert(result.facts.socketGroups[1].gemOrder[2].name == "Spell Cascade")
assert(result.facts.socketGroups[1].item.name == "Skin of the Loyal")
assert(result.facts.skills[1].trigger == "Manual")
assert(result.facts.projectile.status == "calculated")
assert(result.facts.projectile.values[1].value == 2)
assert(result.facts.curse.status == "calculated" and result.facts.curse.value == 3)
assert(result.facts.simulations.curseApplicationOrder.status == "not_simulated")

local missing, err = tool.get_mechanism_snapshot(nil)
assert(missing == nil and err)

local skillSets = {
	[1] = { id = 1, title = "Leveling", socketGroupList = { } },
	[2] = { id = 2, title = "6) endgame setup", socketGroupList = {
		{ slot = "Body Armour", gemList = { { name = "Poisonous Concoction of Bouncing", baseName = "Poisonous Concoction of Bouncing" } } },
	} },
}
build.skillsTab.skillSets = skillSets
build.skillsTab.skillSetOrderList = { 1, 2 }
build.skillsTab.activeSkillSetId = 1
build.skillsTab.SetActiveSkillSet = function(tab, id)
	tab.activeSkillSetId = id
	tab.socketGroupList = skillSets[id].socketGroupList
	build.calcsTab.mainEnv.player.activeSkillList = id == 2 and {
		{ activeEffect = { grantedEffect = { name = "Poisonous Concoction of Bouncing" } }, output = { Chain = 2, ChainMax = 3, ChainRemaining = 1, ChainMaxString = 3 } },
	} or { }
end
build.skillsTab.socketGroupList = skillSets[1].socketGroupList
build.mainSocketGroup = 1
build.calcsTab.input = { skill_number = 1 }
build.calcsTab.BuildOutput = function() end

local setResult = assert(tool.get_skill_set(build, "6) endgame setup"))
assert(setResult.facts.title == "6) endgame setup")
local chainResult = assert(tool.get_skill_chain(build, "6) endgame setup", "Poisonous Concoction of Bouncing"))
assert(chainResult.facts.chain.Chain == 2 and chainResult.facts.chain.ChainMax == 3)
assert(build.skillsTab.activeSkillSetId == 1 and build.mainSocketGroup == 1)
local noChain, noChainErr = tool.get_skill_chain(build, "6) endgame setup", "Missing Skill")
assert(noChain == nil and noChainErr and build.skillsTab.activeSkillSetId == 1 and build.mainSocketGroup == 1)

build.skillsTab.skillSets[2].socketGroupList[1].gemList[2] = { name = "Greater Volley", nameSpec = "Greater Volley", enabled = true }
GlobalCache = { cachedData = { MAIN = { }, CALCS = { } } }
wipeGlobalCache = function() GlobalCache.cachedData.MAIN = { } end
build.calcsTab.BuildOutput = function()
	local support = build.skillsTab.skillSets[2].socketGroupList[1].gemList[2].enabled
	GlobalCache.cachedData.MAIN[1] = { Name = "Poisonous Concoction of Bouncing", Env = { player = { output = support and { ProjectileCount = 5, Chain = 4, ChainMax = 5, ChainRemaining = 1, TotalDPS = 1000 } or { ProjectileCount = 3, Chain = 2, ChainMax = 3, ChainRemaining = 1, TotalDPS = 700 } } } }
end
local comparison = assert(tool.compare_support_effect(build, "6) endgame setup", "Poisonous Concoction of Bouncing", "Greater Volley"))
assert(comparison.facts.enabled.output.Chain == 4 and comparison.facts.disabled.output.Chain == 2)
assert(comparison.facts.delta.Chain == 2 and comparison.facts.delta.ChainMax == 2 and comparison.facts.delta.TotalDPS == 300)
assert(build.skillsTab.skillSets[2].socketGroupList[1].gemList[2].enabled == true)
local order = assert(tool.get_socket_order(build, "6) endgame setup", "Poisonous Concoction of Bouncing"))
assert(order.facts.gems[1].name == "Poisonous Concoction of Bouncing" and order.facts.gems[2].name == "Greater Volley")
local invalidOrder, invalidOrderErr = tool.get_socket_order(build, "6) endgame setup", nil)
assert(invalidOrder == nil and invalidOrderErr)
local explanation = assert(tool.explain_damage_change(build, "6) endgame setup", "Poisonous Concoction of Bouncing", "Greater Volley"))
assert(explanation.facts.support.name == "Greater Volley" and explanation.facts.delta.TotalDPS == 300)
print("agent mechanism tool contract self-check passed")
