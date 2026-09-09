package.path = "runtime/lua/?.lua;" .. package.path

local snapshot = dofile("src/Modules/AgentSnapshot.lua")
local build = {
	targetVersion = "3.29",
	characterLevel = 95,
	mainSocketGroup = 2,
	calcsTab = {
		mainEnv = {
			player = {
				output = { Life = 5000, FullDPS = 100000, ignoredTable = {} },
				activeSkillList = {
					{ activeEffect = { grantedEffect = { name = "Fireball" } }, output = { ProjectileCount = 3 } },
				},
			},
		},
	},
}

local result = snapshot.capture(build)
assert(result.calculationVersion == "3.29")
assert(result.snapshotRevision == "unknown")
assert(result.outputs.Life == 5000)
assert(result.outputs.ignoredTable == nil)
assert(result.skills[1].name == "Fireball")
assert(result.skills[1].output.ProjectileCount == 3)
local ok, conflict = snapshot.assertRevision({ snapshotRevision = "new" }, "old")
assert(ok == nil and conflict.code == "SNAPSHOT_REVISION_CONFLICT" and conflict.recovery_class == "REFRESH_CONTEXT")
assert(conflict.attempt == 1 and conflict.max_attempts == 1 and conflict.side_effect == "none" and conflict.details.expected == "old")
build.calcsTab.mainEnv.player.breakdown = { Life = { "5000 (base)", "= 5000" } }
local explanation = snapshot.explain(build, "Life")
assert(explanation.value == 5000)
assert(explanation.trace[1] == "5000 (base)")
print("agent snapshot self-check passed")
