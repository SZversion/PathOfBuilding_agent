package.path = "runtime/lua/?.lua;" .. package.path

local bridge = dofile("src/Modules/AgentBridge.lua")
local tools = dofile("src/Modules/AgentTool.lua")
local cycle, shared = {}, {}
cycle.self, shared.value = cycle, "shared"
local build = {
	buildId = "live-fixture", gamePatch = "3.29", pobVersion = "2.7.0",
	treeTab = { activeSpec = 1, specList = { { title = "Endgame", allocNodes = { [90] = {}, [12] = {} }, jewels = { [9408] = 1, [9409] = 1 } } } },
	skillsTab = { activeSkillSetId = 1, skillSets = { [1] = { title = "Default" } }, socketGroupList = { { enabled = true, source = { graph = cycle }, sourceNode = { id = 123, graph = cycle }, sourceItem = { name = "Synthetic Item", graph = cycle }, gemList = { { nameSpec = "Fireball", gemId = "SkillGemFireball", variantId = "Fireball", level = 20, quality = 20, enabled = true, grantedEffect = { name = "Fireball", support = false } }, { nameSpec = "Greater Volley", level = 20, quality = 20, enabled = true, grantedEffect = { name = "Greater Volley", support = true } } } } } },
	itemsTab = { activeItemSetId = 1, itemSets = { [1] = { title = "Default" } } },
	configTab = { input = { enemyIsBoss = true, enemyName = "AAAA", usePowerCharges = 3, cycle = cycle, sharedA = shared, sharedB = shared }, activeBuffs = { Onslaught = true }, enemyConditions = { isBoss = true } },
	calcsTab = { mainEnv = { player = { output = { TotalDPS = 123.45 } } } },
}
local snap = assert(bridge.capture(build))
assert(snap.authoritative and snap.mode == "live_read_only")
assert(snap.context.activeSpec.title == "Endgame" and snap.context.config.enemyIsBoss == true)
assert(snap.context.activeSpec.allocatedNodeIds[1] == 12 and snap.context.activeSpec.allocatedNodeIds[2] == 90)
assert(snap.context.activeSpec.jewelIds[1] == 9408 and snap.context.activeSpec.jewelIds[2] == 9409 and snap.context.socketGroups[1].gems[1].identity == "Fireball")
assert(snap.context.socketGroups[1].gems[1].level == 20 and snap.context.socketGroups[1].gems[1].quality == 20 and snap.context.socketGroups[1].gems[2].support == true)
assert(snap.context.config.cycle == nil and snap.context.config.sharedA == nil)
assert(snap.context.socketGroups[1].sourceType == "item_granted" and snap.context.socketGroups[1].sourceNodeId == nil)
local same = assert(bridge.capture(build))
assert(same.snapshotRevision == snap.snapshotRevision)
assert(build.treeTab.activeSpec == 1 and build.skillsTab.activeSkillSetId == 1 and build.itemsTab.activeItemSetId == 1)
build.skillsTab.socketGroupList[1].sourceNode.graph.changed = true
local graphStable = assert(bridge.capture(build))
assert(graphStable.snapshotRevision == same.snapshotRevision)
build.configTab.input.enemyIsBoss = false
local changed = assert(bridge.capture(build))
assert(changed.snapshotRevision ~= snap.snapshotRevision)
build.configTab.input.enemyName = "BBBB"
local enemyChanged = assert(bridge.capture(build))
assert(enemyChanged.snapshotRevision ~= changed.snapshotRevision)
build.skillsTab.socketGroupList[1].gemList[1].enabled = false
local gemChanged = assert(bridge.capture(build))
assert(gemChanged.snapshotRevision ~= enemyChanged.snapshotRevision)

local result, err = bridge.dispatch(build, { tool = "get_character_stats", arguments = {} }, tools)
assert(result and not err and result.snapshotRevision == gemChanged.snapshotRevision)
assert(result.liveMode == "live_read_only" and result.facts.TotalDPS == 123.45)

local fallback = { skillsTab = { activeSkillSet = 2, skillSetOrderList = { "missing", "fallback" }, skillSets = { fallback = { title = nil } } } }
local fallbackSnapshot = assert(bridge.capture(fallback))
assert(fallbackSnapshot.context.activeSkillSet.id == "fallback")
local missing, missingErr = bridge.capture({ skillsTab = { skillSets = {} } })
assert(not missing and missingErr.code == "USER_CONTEXT_MISSING" and missingErr.snapshotRevision == nil)
local ambiguous, ambiguousErr = bridge.capture({ skillsTab = { activeSkillSet = "Default", skillSets = { first = { title = "Default" }, second = { label = "Default" } } } })
assert(not ambiguous and ambiguousErr.code == "AMBIGUOUS_ALIAS" and ambiguousErr.recovery_class == "ASK_USER")

local mutation, mutationErr = bridge.dispatch(build, { tool = "replace_gem", arguments = {} }, tools)
assert(not mutation and mutationErr.code == "MUTATION_NOT_PERSISTENT")

local invalid, invalidErr = bridge.dispatch(build, { tool = "get_character_stats" }, tools)
assert(not invalid and invalidErr.code == "INPUT_INVALID")
print("test_agent_bridge_dispatcher: ok")
