local previousBuild = build
local tools = dofile("src/Modules/AgentInProcess.lua")
build = { targetVersion = "3_29", calcsTab = { mainEnv = { player = { activeSkillList = { { activeEffect = { grantedEffect = { name = "Fireball" } }, output = { TotalDPS = 10 }, breakdown = { TotalDPS = { "base 10" } } } } } } } }
local result = assert(tools.dispatch("get_skill_dps", { skillName = "Fireball" }))
assert(result.facts.value == 10)
assert(result.sources[1] and result.trace[1] == "base 10")
local explanation = assert(tools.dispatch("explain_stat", { stat = "TotalDPS", skillName = "Fireball" }))
assert(explanation.facts.value == 10)
local missing, err = tools.dispatch("get_skill_dps", { skillName = "Missing" })
assert(missing == nil and type(err) == "string")
build = previousBuild
print("agent in-process adapter self-check passed")
