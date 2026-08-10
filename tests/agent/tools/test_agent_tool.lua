local tools = dofile("src/Modules/AgentTool.lua")
local build = {
	targetVersion = "3_29",
	calcsTab = {
		mainEnv = {
			player = {
				output = { Life = 5000, EnemyCurseLimit = 2 },
				breakdown = { Life = { "5000 (base)", "= 5000" } },
				activeSkillList = {
					{ activeEffect = { grantedEffect = { name = "Fireball" } }, skillPartName = "main", infoTrigger = "Manual", triggered = false, output = { ProjectileCount = 3, Chain = 2, TotalDPS = 1000, IgniteChance = 25, ElementalPenetration = { Fire = 14, Cold = 8 } }, breakdown = { TotalDPS = { "1000" }, Fire = { "base", "= 1000" } } },
					{ activeEffect = { grantedEffect = { name = "Spark" } }, skillPartName = "main", output = { TotalDPS = 900 }, breakdown = { TotalDPS = { "900" } } },
				},
			},
		},
	},
	itemsTab = { items = { [1] = { name = "Test Wand", baseName = "Wand", raw = "Test Wand", implicitModLines = { { line = "+10% to Fire Resistance" } }, explicitModLines = { { line = "+20 to Life" } } } } },
}

local character = assert(tools.get_character_stats(build))
assert(character.calculationVersion == "3_29")
assert(character.facts.Life == 5000)
assert(#character.trace == 0)

local skill = assert(tools.get_skill_stats(build, 1))
assert(skill.facts.skillIndex == 1)
assert(skill.facts.name == "Fireball")
assert(skill.facts.output.TotalDPS == 1000)

local projectile = assert(tools.get_projectile_count(build, 1))
assert(projectile.facts.value == 3)
assert(#projectile.trace == 0)

local penetration = assert(tools.get_elemental_penetration(build, 1))
assert(penetration.facts.name == "Fireball")
assert(penetration.facts.values.Fire == 14 and penetration.facts.values.Cold == 8 and penetration.facts.values.Lightning == nil)
assert(tools.get_skill_dps(build, 1).facts.value == 1000)
assert(tools.get_highest_dps_skill(build).facts.skillIndex == 1)
assert(tools.get_skill_breakdown(build, 1).facts.breakdown.status == "calculated")
assert(tools.get_projectile_behavior(build, 1).facts.values.Chain == 2)
assert(tools.get_trigger_sequence(build, 1).facts.infoTrigger == "Manual")
assert(tools.get_ailment_effect(build, 1).facts.values.IgniteChance == 25)
local item = assert(tools.get_item_modifiers(build, 1))
assert(#item.facts.modLines == 2 and item.facts.modLines[1].category == "implicit")

local curse = assert(tools.get_curse_limit(build))
assert(curse.facts.value == 2)

local explanation = assert(tools.explain_stat(build, "Life"))
assert(explanation.facts.value == 5000)
assert(explanation.trace[1] == "5000 (base)")

local function assertError(call)
	local result, err = call()
	assert(result == nil)
	assert(type(err) == "string" and err ~= "")
end

assertError(function() return tools.get_character_stats({}) end)
assertError(function() return tools.get_skill_stats(build, 0) end)
assertError(function() return tools.get_skill_stats(build, 1.5) end)
assertError(function() return tools.get_skill_stats(build, 3) end)
assertError(function() return tools.explain_stat(build, "MissingStat") end)
assertError(function() return tools.get_projectile_count(build, 2) end)
assertError(function() return tools.get_elemental_penetration(build, 2) end)
assertError(function() return tools.get_item_modifiers(build, 2) end)

print("agent tool contract self-check passed")
