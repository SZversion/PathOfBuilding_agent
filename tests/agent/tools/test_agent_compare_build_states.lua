local tools = dofile("src/Modules/AgentTool.lua")
local before = { buildId = "before", gamePatch = "3.29", pobVersion = "pob-test", dataRevision = "data-1", snapshotRevision = "rev-1", conditions = { enemy = "boss" }, skills = { [1] = { output = { TotalDPS = 100, ProjectileCount = 3 } } } }
local after = { buildId = "after", gamePatch = "3.29", pobVersion = "pob-test", dataRevision = "data-1", snapshotRevision = "rev-2", conditions = { enemy = "boss" }, skills = { [1] = { output = { TotalDPS = 125, ProjectileCount = 4 } } } }
local result = assert(tools.compare_build_states(before, after, 1, { "TotalDPS", "ProjectileCount" }))
assert(result.facts.before.TotalDPS == 100 and result.facts.after.TotalDPS == 125)
assert(result.facts.delta.TotalDPS == 25 and result.facts.changeRatePercent.TotalDPS == 25)
assert(result.facts.changedFields[1] == "ProjectileCount" and result.facts.changedFields[2] == "TotalDPS")
assert(result.conditions.changed == false and result.snapshotRevision == "rev-2")
local mismatch, err = tools.compare_build_states(before, { gamePatch = "3.28", skills = { [1] = { output = { TotalDPS = 1 } } } }, 1)
assert(mismatch == nil and err.code == "VERSION_MISMATCH")
print("agent compare build states self-check passed")
