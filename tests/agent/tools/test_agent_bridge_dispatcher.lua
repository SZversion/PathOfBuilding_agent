package.path = "runtime/lua/?.lua;" .. package.path
_G.LoadModule = function(name)
	if name == "Modules/AgentErrorRegistry" then return { parent = function(code) return code end } end
	error("unexpected module " .. tostring(name))
end

local bridge = dofile("src/Modules/AgentBridge.lua")
local tools = dofile("src/Modules/AgentTool.lua")
local cycle, shared = {}, {}
cycle.self, shared.value = cycle, "shared"
local build = {
	buildId = "live-fixture", gamePatch = "3.29", pobVersion = "2.7.0",
	treeTab = { activeSpec = 1, specList = { { title = "Endgame", allocNodes = { [90] = {}, [12] = {} }, jewels = { [9408] = 1, [9409] = 1 } } } },
	skillsTab = { activeSkillSetId = 1, skillSets = { [1] = { title = "Default" } }, socketGroupList = { { enabled = true, source = { graph = cycle }, sourceNode = { id = 123, graph = cycle }, sourceItem = { name = "Synthetic Item", graph = cycle }, gemList = { { nameSpec = "Fireball", gemId = "SkillGemFireball", variantId = "Fireball", level = 20, quality = 20, enabled = true, grantedEffect = { name = "Fireball", support = false } }, { nameSpec = "Greater Volley", level = 20, quality = 20, enabled = true, grantedEffect = { name = "Greater Volley", support = true } } } } } },
	itemsTab = { activeItemSetId = 1, itemSets = { [1] = { title = "Default" } } },
	configTab = { input = { enemyIsBoss = "Boss", enemyName = "AAAA", usePowerCharges = true, cycle = cycle, sharedA = shared, sharedB = shared }, activeBuffs = { Onslaught = true }, enemyConditions = { isBoss = true } },
	calcsTab = { mainEnv = { player = { output = { TotalDPS = 123.45 } } } },
}
build.calcsTab.BuildOutput = function(self)
	self.mainEnv.player.output.TotalDPS = self.input and self.input.resistancePenalty or 123.45
end
build.calcsTab.input = build.configTab.input
local snap = assert(bridge.capture(build))
assert(snap.authoritative and snap.mode == "live_read_only")
assert(snap.context.activeSpec.title == "Endgame" and snap.context.config.enemyIsBoss == "Boss")
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
local dispatchedTool, dispatchedArguments
local adapted, adaptedErr = bridge.dispatch(build, { tool = "get_duration", arguments = { skillIndex = 2, durationType = "duration" } }, nil,
	function(current, name, arguments)
		assert(current == build)
		dispatchedTool, dispatchedArguments = name, arguments
		return { facts = { duration = 3 } }
	end)
assert(adapted and not adaptedErr and adapted.snapshotRevision == gemChanged.snapshotRevision)
assert(dispatchedTool == "get_duration" and dispatchedArguments.durationType == "duration")

local overrideResult, overrideErr = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { resistancePenalty = 0, conditionMoving = true } } },
	nil,
	function(current)
		assert(current.configTab.input.resistancePenalty == 0)
		assert(current.configTab.input.conditionMoving == true)
		return { facts = { TotalDPS = current.calcsTab.mainEnv.player.output.TotalDPS, resistancePenalty = current.configTab.input.resistancePenalty } }
	end)
assert(overrideResult and not overrideErr and overrideResult.facts.TotalDPS == 0)
assert(build.configTab.input.resistancePenalty == nil and build.configTab.input.conditionMoving == nil)
local unsupported, unsupportedErr = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { notAConfigKey = true } } }, nil,
	function() error("must not dispatch unsupported config") end)
assert(not unsupported and unsupportedErr.code == "UNSUPPORTED_REQUEST" and unsupportedErr.recovery_class == "ASK_USER")
local invalidTier, invalidTierErr = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { enemyIsBoss = true } } }, nil,
	function() error("must not dispatch invalid boss enum") end)
assert(not invalidTier and invalidTierErr.code == "INPUT_INVALID" and invalidTierErr.recovery_class == "ASK_USER")
build.configTab.input.usePowerCharges = false
local chargeMissing, chargeMissingErr = bridge.dispatch(build,
	-- The current PoB state does not use charges, so an override alone is invalid.
	{ tool = "get_character_stats", arguments = { configOverrides = { overridePowerCharges = 3 } } }, nil,
	function() error("must not dispatch charge override without use flag") end)
assert(not chargeMissing and chargeMissingErr.code == "INPUT_INVALID" and chargeMissingErr.recovery_class == "ASK_USER")
local chargeOverride, chargeOverrideErr = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { usePowerCharges = true, overridePowerCharges = 3 } } }, nil,
	function(current)
		assert(current.configTab.input.usePowerCharges == true and current.configTab.input.overridePowerCharges == 3)
		return { facts = { powerCharges = current.configTab.input.overridePowerCharges } }
	end)
assert(chargeOverride and not chargeOverrideErr and chargeOverride.facts.powerCharges == 3)
assert(build.configTab.input.overridePowerCharges == nil)
local baselineDps = build.calcsTab.mainEnv.player.output.TotalDPS
local baselinePenalty = build.configTab.input.resistancePenalty
local thrown, thrownErr = bridge.dispatch(build,
	{ tool = "get_character_stats", arguments = { configOverrides = { resistancePenalty = 0 } } }, nil,
	function() error("forced dispatcher failure") end)
assert(not thrown and thrownErr.code == "POB_CALCULATION_ERROR")
assert(build.configTab.input.resistancePenalty == baselinePenalty)
assert(build.calcsTab.mainEnv.player.output.TotalDPS == baselineDps)

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

local originalConfig = build.configTab.input
build.configTab.activeConfigSetId = 1
build.configTab.configSetOrderList = { 1, 9 }
build.configTab.configSets = { [1] = { title = "Mapping", input = originalConfig }, [9] = { title = "Boss", input = { enemyIsBoss = "Pinnacle" } } }
function build.configTab:SetActiveConfigSet(id)
	self.activeConfigSetId = id
	self.input = self.configSets[id].input
end
local selectedConfig = assert(bridge.capture(build))
assert(selectedConfig.context.activeConfigSet.id == 1)
assert(selectedConfig.context.availableConfigSets[2].id == 9)
local configResult = assert(bridge.dispatch(build, { tool = "get_character_stats", arguments = { contextOverrides = { activeConfigSet = 9 } } }, nil, function(current)
	assert(current.configTab.activeConfigSetId == 9)
	assert(current.configTab.input.enemyIsBoss == "Pinnacle")
	return { facts = { value = 1 } }
end))
assert(configResult.conditions.context.activeConfigSet.id == 9)
assert(build.configTab.activeConfigSetId == 1 and build.configTab.input == originalConfig)
