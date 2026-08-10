local tools = dofile("src/Modules/AgentTool.lua")
local build = {
	targetVersion = "3_29",
	calcsTab = {
		mainEnv = {
			player = {
				output = { Life = 5000, EnemyCurseLimit = 2 },
				breakdown = { Life = { "5000 (base)", "= 5000" } },
				activeSkillList = {
					{ activeEffect = { grantedEffect = { name = "Fireball" } }, skillPartName = "main", output = { ProjectileCount = 3, TotalDPS = 1000 }, breakdown = { TotalDPS = { "1000" } } },
				},
			},
		},
	},
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
assertError(function() return tools.get_skill_stats(build, 2) end)
assertError(function() return tools.explain_stat(build, "MissingStat") end)
assertError(function() return tools.get_projectile_count(build, 2) end)

print("agent tool contract self-check passed")
