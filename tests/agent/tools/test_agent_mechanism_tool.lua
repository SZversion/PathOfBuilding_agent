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
print("agent mechanism tool contract self-check passed")
