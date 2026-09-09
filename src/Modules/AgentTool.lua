-- Read-only Agent tools over PoB's calculated in-memory state.
local pairs = pairs
local type = type
local tostring = tostring
local itemAliasEntries
local skillAliasEntries

local function normalize_name(value)
	if type(value) ~= "string" then return "" end
	return value:match("^%s*(.-)%s*$"):gsub("%s+", " "):lower()
end

local function canonical_item_identity(value)
	if type(value) ~= "string" or value == "" then return nil, { code = "INPUT_INVALID", recovery_class = "REPAIR_INPUT", stage = "item_alias", retryable = false, next_action = "repair_input", message = "itemIdentity is required" } end
	if not itemAliasEntries then
		itemAliasEntries = {}
		for _, path in ipairs({ "agent/knowledge/aliases/ko/items-3.29.json", "../agent/knowledge/aliases/ko/items-3.29.json" }) do
			local file = io.open(path, "r")
			if file then
				local content = file:read("*a"); file:close()
				local ok, decoder = pcall(require, "dkjson")
				if ok and decoder then local parsed = decoder.decode(content); itemAliasEntries = parsed and parsed.entries or {} end
				break
			end
		end
	end
	local needle, matches = normalize_name(value), {}
	for _, entry in ipairs(itemAliasEntries) do
		if normalize_name(entry.korean) == needle or normalize_name(entry.english) == needle then matches[#matches + 1] = entry.english end
	end
	if #matches > 1 then return nil, { code = "AMBIGUOUS_ALIAS", recovery_class = "ASK_USER", stage = "item_alias", retryable = false, next_action = "ask_user", message = "itemIdentity is ambiguous" } end
	if #matches == 0 then return nil, { code = "USER_CONTEXT_MISSING", recovery_class = "ASK_USER", stage = "item_alias", retryable = false, next_action = "ask_user", message = "itemIdentity was not found in the item alias catalog" } end
	return matches[1]
end

local function load_skill_alias_entries()
	if skillAliasEntries then return skillAliasEntries end
	skillAliasEntries = {}
	for _, path in ipairs({ "agent/knowledge/aliases/ko/skills-3.29.json", "../agent/knowledge/aliases/ko/skills-3.29.json" }) do
		local file = io.open(path, "r")
		if file then
			local content = file:read("*a"); file:close()
			local ok, decoder = pcall(require, "dkjson")
			if ok and decoder then local parsed = decoder.decode(content); skillAliasEntries = parsed and parsed.entries or {} end
			break
		end
	end
	return skillAliasEntries
end

local function evidenceGraph(sources, trace)
	local nodes, stages, sourceEdges = { }, { }, { }
	for index, source in ipairs(sources or { }) do
		nodes[#nodes + 1] = { id = "source:" .. tostring(index), type = "source", value = source }
		sourceEdges[#sourceEdges + 1] = { from = "output", to = "source:" .. tostring(index), relation = "derived_from" }
	end
	for index, entry in ipairs(trace or { }) do
		stages[#stages + 1] = { order = index, operation = entry.operation or "TRACE", value = entry.value }
	end
	return { nodes = nodes, stages = stages, sourceEdges = sourceEdges }
end

local function scalarTable(source)
	local result = { }
	if type(source) ~= "table" then
		return result
	end
	for key, value in pairs(source) do
		local valueType = type(value)
		if valueType == "number" or valueType == "string" or valueType == "boolean" then
			result[key] = value
		end
	end
	return result
end

local function playerFor(build)
	local env = build and build.calcsTab and build.calcsTab.mainEnv
	local player = env and env.player
	if not player then
		return nil, "PoB calculation state is unavailable"
	end
	return player
end

local function skillFor(player, skillIndex)
	if type(skillIndex) ~= "number" or skillIndex % 1 ~= 0 then
		return nil, "skillIndex must be an integer"
	end
	if skillIndex < 1 or not player.activeSkillList or not player.activeSkillList[skillIndex] then
		return nil, "skillIndex is out of range"
	end
	return player.activeSkillList[skillIndex]
end

local function calculatedOutput(player, skill)
	local output = skill and skill.output or { }
	if next(output) == nil and player and player.mainSkill and player.mainSkill.actor then
		output = player.mainSkill.actor.output or output
	end
	return output
end

local function finalTrace(skill, stat, value)
	local result = { }
	for _, entry in ipairs((skill and skill.breakdown and skill.breakdown[stat]) or { }) do result[#result + 1] = entry end
	result[#result + 1] = { operation = "FINAL_OUTPUT", stat = stat, value = value, source = "PoB calculated output" }
	return result
end

local function snapshotRevision(build)
	local value = build and (build.snapshotRevision or build.revision or build.agentSnapshotRevision)
	return value ~= nil and tostring(value) or "unknown"
end

local function envelope(build, facts, sources, trace)
	local sourceList = sources or { }
	local traceList = trace or { }
	local status = facts and facts.status
	if status ~= "calculated" and status ~= "partial" and status ~= "unavailable" and status ~= "not_simulated" and status ~= "conflict" and status ~= "rejected" then status = "calculated" end
	local revision = snapshotRevision(build)
	local traceWithRevision = { }
	for _, entry in ipairs(traceList) do
		if type(entry) == "table" then
			local copy = { }
			for key, value in pairs(entry) do copy[key] = value end
			copy.snapshotRevision = copy.snapshotRevision or revision
			traceWithRevision[#traceWithRevision + 1] = copy
		else
			traceWithRevision[#traceWithRevision + 1] = { value = entry, snapshotRevision = revision }
		end
	end
	return {
		status = status,
		snapshotRevision = revision,
		side_effect = "none",
		operator_message = nil,
		conditions = { },
		calculationVersion = tostring(build and build.targetVersion or "unknown"),
		version = {
			gamePatch = build and (build.gamePatch or build.targetVersion) or nil,
			pobVersion = build and (build.pobVersion or build.version) or nil,
			dataRevision = build and build.dataRevision or nil,
		},
		facts = facts,
		sources = sourceList,
		trace = traceWithRevision,
		evidenceGraph = evidenceGraph(sourceList, traceWithRevision),
		uncertainty = { level = "none", reasons = { }, missingEvidence = { }, temporaryEvidence = false },
	}
end

local function get_character_stats(build)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	return envelope(build, scalarTable(player.output), { "PoB:CalcsTab.mainEnv.player.output" })
end

local function gemFacts(skill)
	local result = { }
	local function add(effect, role)
		local granted = effect and effect.grantedEffect
		if not granted then return end
		result[#result + 1] = {
			name = granted.name,
			role = role,
			level = effect.srcInstance and effect.srcInstance.level or effect.level,
			quality = effect.srcInstance and effect.srcInstance.quality or effect.quality,
		}
	end
	add(skill.activeEffect, "active")
	for _, effect in ipairs(skill.effectList or { }) do
		if effect.grantedEffect and effect.grantedEffect.support then add(effect, "support") end
	end
	return result
end

local function get_skill_stats(build, skillIndex)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then
		return nil, skillErr
	end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	local output = calculatedOutput(player, skill)
	return envelope(build, {
		skillIndex = skillIndex,
		name = effect and effect.name,
		skillPart = skill.skillPartName,
		gems = gemFacts(skill),
		trigger = skill.infoTrigger,
		output = scalarTable(output),
	}, { "PoB:CalcsTab.mainEnv.player.activeSkillList" })
end

local function skillName(skill)
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return effect and effect.name or skill.name or skill.baseName
end

local function modifierTrace(skill, stat)
	local trace = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
	return trace.collectCombined(skill, stat, "BASE"), trace.collectCombined(skill, stat, "MORE")
end

local function get_skill_dps(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local value = output.TotalDPS
	if type(value) ~= "number" then return nil, "TotalDPS is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), value = value }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output.TotalDPS" }, (skill.breakdown and skill.breakdown.TotalDPS) or { })
end

local function get_highest_dps_skill(build)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local bestIndex, bestValue
	for index, skill in ipairs(player.activeSkillList or { }) do
		local value = calculatedOutput(player, skill).TotalDPS
		if type(value) == "number" and (bestValue == nil or value > bestValue) then
			bestIndex, bestValue = index, value
		end
	end
	if not bestIndex then return nil, "TotalDPS is unavailable for all skills" end
	return envelope(build, { skillIndex = bestIndex, name = skillName(player.activeSkillList[bestIndex]), value = bestValue }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output.TotalDPS" })
end

local function breakdownValues(source)
	local result = { }
	if type(source) ~= "table" then return result end
	for key, value in pairs(source) do
		if type(value) == "number" or type(value) == "string" or type(value) == "boolean" then
			result[key] = { value }
		elseif type(value) == "table" then
			local trace = { }
			for _, entry in ipairs(value) do
				if type(entry) == "number" or type(entry) == "string" or type(entry) == "boolean" then trace[#trace + 1] = entry end
			end
			if #trace > 0 then result[key] = trace end
		end
	end
	return result
end

local function get_skill_breakdown(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local values = breakdownValues(skill.breakdown)
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, breakdown = { status = next(values) and "calculated" or "unavailable", values = values } }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.breakdown" })
end

local function get_item_modifiers(build, itemId)
	if type(itemId) ~= "number" or itemId % 1 ~= 0 then return nil, "itemId must be an integer" end
	local item = build and build.itemsTab and build.itemsTab.items and build.itemsTab.items[itemId]
	if not item then return nil, "item was not found" end
	local lines = { }
	local function addLines(source, category)
		for _, entry in ipairs(source or { }) do
			if type(entry) == "table" and type(entry.line) == "string" then lines[#lines + 1] = { line = entry.line, category = category } end
		end
	end
	addLines(item.implicitModLines, "implicit")
	addLines(item.explicitModLines, "explicit")
	addLines(item.enchantModLines, "enchant")
	addLines(item.craftedModLines, "crafted")
	return envelope(build, { itemId = itemId, name = item.name, baseName = item.baseName, raw = item.raw, modLines = lines }, { "PoB:ItemsTab.items.modLines" })
end

local function itemMetadata(item)
	return item and { id = item.id, name = item.name, baseName = item.baseName, raw = item.raw, rarity = item.rarity, slot = item.slot } or {}
end

local function scalarOutput(build)
	local player = build and build.calcsTab and build.calcsTab.mainEnv and build.calcsTab.mainEnv.player
	return scalarTable(player and player.output)
end

local function replace_item(build, args)
	if type(args) ~= "table" then return nil, "item replacement arguments are required" end
	local slot, itemIdentity, itemText = args.slot, args.itemIdentity, args.itemText
	if type(slot) ~= "string" or slot == "" then return nil, "slot is required" end
	local canonicalIdentity, identityErr = canonical_item_identity(itemIdentity)
	if not canonicalIdentity then return nil, identityErr end
	if type(itemText) ~= "string" or itemText == "" then return nil, "itemText is required" end
	local tab = build and build.itemsTab
	local set = tab and tab.activeItemSet
	if not tab or not set or not tab.slots or not tab.slots[slot] or not set[slot] then return nil, "item slot is invalid or unavailable" end
	if type(new) ~= "function" then return nil, "PoB item constructor is unavailable" end
	local candidate = new("Item", itemText)
	if not candidate or not candidate.base then return nil, "PoB item text could not be parsed" end
	local expectedType = ({ ["Weapon 1"] = "weapon", ["Weapon 2"] = "weapon", ["Weapon 1 Swap"] = "weapon", ["Weapon 2 Swap"] = "weapon", ["Helmet"] = "Helmet", ["Body Armour"] = "Body Armour", ["Gloves"] = "Gloves", ["Boots"] = "Boots", ["Amulet"] = "Amulet", ["Ring 1"] = "Ring", ["Ring 2"] = "Ring", ["Ring 3"] = "Ring", ["Belt"] = "Belt", ["Flask 1"] = "Flask", ["Flask 2"] = "Flask", ["Flask 3"] = "Flask", ["Flask 4"] = "Flask", ["Flask 5"] = "Flask" })[slot]
	local candidateType = candidate.base.weapon and "weapon" or candidate.base.type or candidate.type
	if not expectedType or (expectedType == "weapon" and candidateType ~= "weapon") or (expectedType ~= "weapon" and candidateType ~= expectedType) then
		return nil, { code = "INPUT_INVALID", recovery_class = "REPAIR_INPUT", stage = "item_slot_validation", retryable = false, attempt = 1, max_attempts = 1, message = "parsed item type does not match the requested slot", details = { slot = slot, expectedType = expectedType, candidateType = candidateType }, next_action = "repair_input", secondary_causes = {}, side_effect = "none", operator_message = nil }
	end
	local identityNeedle = normalize_name(canonicalIdentity)
	local identityText = normalize_name(candidate.name or candidate.baseName or candidate.raw or "")
	if not identityText:find(identityNeedle, 1, true) then return nil, "itemIdentity does not match parsed PoB item" end
	local oldId = set[slot].selItemId
	local oldItem = tab.items and tab.items[oldId]
	local beforeOutput = scalarOutput(build)
	local beforeMeta = itemMetadata(oldItem)
	local mutation = (LoadModule and LoadModule("Modules/AgentMutation")) or dofile("src/Modules/AgentMutation.lua")
	local request = { expectedSnapshotRevision = args.expectedSnapshotRevision, idempotencyKey = args.idempotencyKey, fingerprint = args.fingerprint }
	local transaction, transactionErr = mutation.run(build, request, function(state)
		local itemsTab = state.itemsTab
		local id = 1
		for existingId in pairs(itemsTab.items or {}) do if type(existingId) == "number" and existingId >= id then id = existingId + 1 end end
		candidate.id = id
		itemsTab.items = itemsTab.items or {}
		itemsTab.items[id] = candidate
		itemsTab.activeItemSet[slot].selItemId = id
		if type(itemsTab.PopulateSlots) == "function" then itemsTab:PopulateSlots() end
	end)
	if not transaction then return nil, transactionErr end
	local afterOutput = scalarOutput(build)
	local delta = {}
	local outputKeys = {}
	for key in pairs(beforeOutput) do outputKeys[key] = true end
	for key in pairs(afterOutput) do outputKeys[key] = true end
	for key in pairs(outputKeys) do
		local beforeValue, afterValue = beforeOutput[key], afterOutput[key]
		if type(beforeValue) == "number" and type(afterValue) == "number" then delta[key] = afterValue - beforeValue
		elseif type(beforeValue) == "number" then delta[key] = -beforeValue
		elseif type(afterValue) == "number" then delta[key] = afterValue end
	end
	local result = envelope(build, {
		status = "calculated", slot = slot, itemIdentity = canonicalIdentity, requestedItemIdentity = itemIdentity,
		before = { item = beforeMeta, output = beforeOutput },
		after = { item = itemMetadata(tab.activeItemSet and tab.activeItemSet[slot] and tab.items[tab.activeItemSet[slot].selItemId]), output = afterOutput },
		delta = delta, saved = false, idempotencyKey = request.idempotencyKey,
	}, { "PoB:ItemsTab.activeItemSet[" .. slot .. "]", "PoB:CalcsTab.mainEnv.player.output" }, {
		{ operation = "REPLACE_ITEM", slot = slot, before = beforeMeta, after = itemMetadata(tab.items[tab.activeItemSet[slot].selItemId]), value = delta, snapshotRevision = transaction.snapshotRevision },
	})
	result.side_effect, result.operator_message, result.snapshotRevision = "in_memory", transaction.operator_message, transaction.snapshotRevision
	return result
end

local function gemDisplayName(gem)
	local effect = gem and (gem.grantedEffect or (gem.gemData and gem.gemData.grantedEffect))
	return (gem and (gem.nameSpec or gem.name)) or (effect and effect.name) or (gem and gem.gemData and gem.gemData.name)
end

local function canonical_gem_identity(build, value)
	if type(value) ~= "string" or value == "" then return nil, { code = "INPUT_INVALID", recovery_class = "REPAIR_INPUT", stage = "gem_alias", retryable = false, next_action = "repair_input", message = "gemIdentity is required" } end
	local context = (LoadModule and LoadModule("Modules/AgentContext")) or dofile("src/Modules/AgentContext.lua")
	local canonical, aliasErr = context.resolve_skill_alias(value)
	if not canonical then return nil, aliasErr end
	local needle = normalize_name(canonical)
	for _, gem in pairs(build.data and build.data.gems or {}) do
		if normalize_name(gem.name) == needle or normalize_name(gem.nameSpec) == needle then return gem.name or canonical, gem end
	end
	for _, group in ipairs(build.skillsTab and build.skillsTab.socketGroupList or {}) do
		for _, gem in ipairs(group.gemList or {}) do if normalize_name(gemDisplayName(gem)) == needle then return canonical, gem.gemData end end
	end
	for _, entry in ipairs(load_skill_alias_entries()) do
		if normalize_name(entry.english) == needle or normalize_name(entry.korean) == normalize_name(value) then
			return nil, { code = "INPUT_INVALID", recovery_class = "REPAIR_INPUT", stage = "gem_validation", retryable = false, attempt = 1, max_attempts = 1, next_action = "repair_input", message = "gemIdentity does not match a parsed PoB gem", details = { gemIdentity = value }, secondary_causes = {}, side_effect = "none", operator_message = nil }
		end
	end
	return nil, { code = "USER_CONTEXT_MISSING", recovery_class = "ASK_USER", stage = "gem_alias", retryable = false, next_action = "ask_user", message = "gemIdentity was not found in the PoB gem catalog" }
end

local function gemError(code, recovery, stage, message, details)
	return { code = code, recovery_class = recovery, stage = stage, retryable = false,
		attempt = 1, max_attempts = 1, message = message, details = details or {},
		next_action = recovery == "ASK_USER" and "ask_user" or "repair_input",
		secondary_causes = {}, side_effect = "none", operator_message = nil }
end

local function replace_gem(build, args)
	if type(args) ~= "table" then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "gem replacement arguments are required") end
	if type(args.socketGroup) ~= "number" or args.socketGroup % 1 ~= 0 or args.socketGroup < 1 then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "socketGroup must be a positive integer") end
	if type(args.level) ~= "number" or args.level % 1 ~= 0 or args.level < 1 or args.level > 40 then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "gem level must be an integer from 1 to 40") end
	if type(args.quality) ~= "number" or args.quality % 1 ~= 0 or args.quality < 0 or args.quality > 30 then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "gem quality must be an integer from 0 to 30") end
	if args.alternateQuality ~= nil and type(args.alternateQuality) ~= "string" then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "alternateQuality must be a string") end
	local tab, group = build and build.skillsTab, build and build.skillsTab and build.skillsTab.socketGroupList and build.skillsTab.socketGroupList[args.socketGroup]
	if not tab or not group then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "socket group was not found", { socketGroup = args.socketGroup }) end
	local canonical, gemData = canonical_gem_identity(build, args.gemIdentity)
	if not canonical then
		if type(gemData) == "table" and (gemData.code == "AMBIGUOUS_ALIAS" or gemData.code == "USER_CONTEXT_MISSING" or gemData.code == "INPUT_INVALID") then
			if gemData.code == "INPUT_INVALID" then
				gemData.stage, gemData.next_action = "gem_validation", "repair_input"
			else
				gemData.stage, gemData.next_action = "gem_alias", "ask_user"
			end
			return nil, gemData
		end
		return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "gemIdentity does not match a parsed PoB gem", { gemIdentity = args.gemIdentity })
	end
	local targetIndex = args.gemIndex
	if targetIndex ~= nil and (type(targetIndex) ~= "number" or targetIndex % 1 ~= 0 or targetIndex < 1) then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "gemIndex must be a positive integer") end
	if not targetIndex then
		for index, gem in ipairs(group.gemList or {}) do
			if normalize_name(gemDisplayName(gem)) == normalize_name(args.currentGemIdentity or args.gemIdentity) then targetIndex = index; break end
		end
	end
	if not targetIndex or not group.gemList[targetIndex] then return nil, gemError("INPUT_INVALID", "REPAIR_INPUT", "gem_validation", "target gem was not found in socket group") end
	local current = group.gemList[targetIndex]
	if current.fromItem or current.itemGranted or group.sourceItem then return nil, gemError("ITEM_GRANTED_SKILL", "REPAIR_INPUT", "gem_resolution", "item-granted skills cannot be replaced as socketed gems") end
	local granted = gemData and gemData.grantedEffect or current.grantedEffect or (current.gemData and current.gemData.grantedEffect)
	local support = granted and granted.support == true
	if targetIndex == 1 and support then return nil, gemError("GEM_LINK_INCOMPATIBLE", "REPAIR_INPUT", "socket_compatibility", "a support gem cannot occupy the active skill position") end
	if targetIndex > 1 and not support then return nil, gemError("GEM_LINK_INCOMPATIBLE", "REPAIR_INPUT", "socket_compatibility", "a non-support gem cannot occupy a support position") end
	local beforeOutput = scalarOutput(build)
	local beforeGems = {}
	for index, gem in ipairs(group.gemList) do beforeGems[index] = { name = gemDisplayName(gem), level = gem.level, quality = gem.quality, enabled = gem.enabled ~= false, support = gem.grantedEffect and gem.grantedEffect.support or gem.gemData and gem.gemData.grantedEffect and gem.gemData.grantedEffect.support } end
	local mutation = (LoadModule and LoadModule("Modules/AgentMutation")) or dofile("src/Modules/AgentMutation.lua")
	local transaction, transactionErr = mutation.run(build, { expectedSnapshotRevision = args.expectedSnapshotRevision, idempotencyKey = args.idempotencyKey, fingerprint = args.fingerprint }, function(state)
		local target = state.skillsTab.socketGroupList[args.socketGroup].gemList[targetIndex]
		target.nameSpec, target.level, target.quality, target.enabled = canonical, args.level, args.quality, args.enabled ~= false
		if args.alternateQuality then target.qualityId, target.alternateQuality = args.alternateQuality, args.alternateQuality end
		if gemData then target.gemData, target.grantedEffect, target.gemId, target.skillId = gemData, gemData.grantedEffect, gemData.id, gemData.grantedEffectId end
	end)
	if not transaction then return nil, transactionErr end
	local afterOutput = scalarOutput(build)
	local delta, keys = {}, {}
	for key in pairs(beforeOutput) do keys[key] = true end; for key in pairs(afterOutput) do keys[key] = true end
	for key in pairs(keys) do if type(beforeOutput[key]) == "number" and type(afterOutput[key]) == "number" then delta[key] = afterOutput[key] - beforeOutput[key] elseif type(afterOutput[key]) == "number" then delta[key] = afterOutput[key] elseif type(beforeOutput[key]) == "number" then delta[key] = -beforeOutput[key] end end
	local afterGems = {}
	for index, gem in ipairs(group.gemList) do afterGems[index] = { name = gemDisplayName(gem), level = gem.level, quality = gem.quality, enabled = gem.enabled ~= false, support = gem.grantedEffect and gem.grantedEffect.support or gem.gemData and gem.gemData.grantedEffect and gem.gemData.grantedEffect.support } end
	local result = envelope(build, { socketGroup = args.socketGroup, gemIdentity = canonical, before = { gems = beforeGems, output = beforeOutput }, after = { gems = afterGems, output = afterOutput }, delta = delta, saved = false, supportLinks = afterGems }, { "PoB:SkillsTab.socketGroupList[" .. args.socketGroup .. "].gemList", "PoB:CalcsTab.mainEnv.player.output" }, { { operation = "REPLACE_GEM", socketGroup = args.socketGroup, value = delta, snapshotRevision = transaction.snapshotRevision } })
	result.side_effect, result.operator_message, result.snapshotRevision = "in_memory", transaction.operator_message, transaction.snapshotRevision
	return result
end

local function passiveError(code, recovery, stage, message, details)
	return { code = code, recovery_class = recovery, stage = stage, retryable = false,
		attempt = 1, max_attempts = 1, message = message, details = details or {},
		next_action = recovery == "ASK_USER" and "ask_user" or "repair_input",
		secondary_causes = {}, side_effect = "none", operator_message = nil }
end

local function treeSnapshot(spec)
	local nodes, jewels = {}, {}
	for nodeId, node in pairs(spec.allocNodes or {}) do nodes[#nodes + 1] = { id = nodeId, name = node.name, type = node.type } end
	for nodeId, itemId in pairs(spec.jewels or {}) do jewels[nodeId] = itemId end
	table.sort(nodes, function(a, b) return tonumber(a.id) < tonumber(b.id) end)
	local used = 0
	if type(spec.CountAllocNodes) == "function" then used = select(1, spec:CountAllocNodes()) or 0 end
	return { allocatedNodes = nodes, jewels = jewels, pointsUsed = used }
end

local function change_passive(build, args)
	if type(args) ~= "table" then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "passive mutation arguments are required") end
	local operation = args.operation
	if operation ~= "allocate" and operation ~= "deallocate" and operation ~= "replace_cluster_jewel" then
		return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "operation must be allocate, deallocate, or replace_cluster_jewel")
	end
	local spec = build and build.spec
	if not spec and build and build.treeTab and build.treeTab.specList then spec = build.treeTab.specList[build.treeTab.activeSpec or 1] end
	if not spec then return nil, passiveError("VALUE_UNAVAILABLE", "REJECT", "passive_validation", "active passive spec is unavailable") end
	local nodeId = args.nodeId or args.socketNodeId
	if operation ~= "replace_cluster_jewel" and (type(nodeId) ~= "number" or nodeId % 1 ~= 0) then
		return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "nodeId must be an integer")
	end
	local node = nodeId and spec.nodes and spec.nodes[nodeId]
	if operation ~= "replace_cluster_jewel" and not node then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "passive node was not found", { nodeId = nodeId }) end
	if operation == "allocate" then
		if node.alloc or spec.allocNodes[nodeId] then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "passive node is already allocated", { nodeId = nodeId }) end
		if not node.path and #(node.intuitiveLeapLikesAffecting or {}) == 0 then return nil, passiveError("INVALID_PASSIVE_PATH", "REPAIR_INPUT", "passive_validation", "passive node is not connected to the allocated tree", { nodeId = nodeId }) end
		local available = build.availablePassivePoints or spec.availablePoints or spec.totalPoints
		if type(available) == "number" then
			local used = type(spec.CountAllocNodes) == "function" and select(1, spec:CountAllocNodes()) or 0
			if used >= available then return nil, passiveError("INSUFFICIENT_PASSIVE_POINTS", "REPAIR_INPUT", "passive_validation", "not enough passive points", { available = available, used = used }) end
		end
	elseif operation == "deallocate" then
		if not node.alloc and not spec.allocNodes[nodeId] then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "passive node is not allocated", { nodeId = nodeId }) end
		for _, dependent in ipairs(node.depends or {}) do
			if dependent.alloc or spec.allocNodes[dependent.id] then return nil, passiveError("INVALID_PASSIVE_PATH", "REPAIR_INPUT", "passive_validation", "node has allocated dependent nodes", { nodeId = nodeId, dependentNodeId = dependent.id }) end
		end
	else
		if type(nodeId) ~= "number" or nodeId % 1 ~= 0 then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "socketNodeId must be an integer") end
		local socket = spec.nodes and spec.nodes[nodeId]
		if not socket or socket.type ~= "Socket" then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "node is not a cluster jewel socket", { nodeId = nodeId }) end
		local itemId = args.itemId or args.clusterJewelId
		local item = build.itemsTab and build.itemsTab.items and build.itemsTab.items[itemId]
		if type(itemId) ~= "number" or not item then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "cluster jewel item was not found", { itemId = itemId }) end
		local baseName = normalize_name(item.baseName or item.name or "")
		local isClusterJewel = type(item.clusterJewel) == "table" or item.clusterJewel == true or baseName:find("cluster jewel", 1, true) ~= nil
		if item.type ~= "Jewel" or not isClusterJewel then return nil, passiveError("INPUT_INVALID", "REPAIR_INPUT", "passive_validation", "item is not a cluster jewel", { itemId = itemId, baseName = item.baseName }) end
	end
	local beforeTree, beforeOutput = treeSnapshot(spec), scalarOutput(build)
	local mutation = (LoadModule and LoadModule("Modules/AgentMutation")) or dofile("src/Modules/AgentMutation.lua")
	local request = { expectedSnapshotRevision = args.expectedSnapshotRevision, idempotencyKey = args.idempotencyKey, fingerprint = args.fingerprint }
	local transaction, transactionErr = mutation.run(build, request, function(state)
		local active = state.spec or (state.treeTab and state.treeTab.specList and state.treeTab.specList[state.treeTab.activeSpec or 1])
		if operation == "allocate" then active:AllocNode(active.nodes[nodeId])
		elseif operation == "deallocate" then active:DeallocNode(active.nodes[nodeId])
		else
			active.jewels[nodeId] = args.itemId or args.clusterJewelId
			if type(active.BuildClusterJewelGraphs) == "function" then active:BuildClusterJewelGraphs() end
		end
	end)
	if not transaction then return nil, transactionErr end
	local afterTree, afterOutput = treeSnapshot(spec), scalarOutput(build)
	local delta, keys = {}, {}
	for key in pairs(beforeOutput) do keys[key] = true end
	for key in pairs(afterOutput) do keys[key] = true end
	for key in pairs(keys) do
		if type(beforeOutput[key]) == "number" and type(afterOutput[key]) == "number" then delta[key] = afterOutput[key] - beforeOutput[key]
		elseif type(afterOutput[key]) == "number" then delta[key] = afterOutput[key]
		elseif type(beforeOutput[key]) == "number" then delta[key] = -beforeOutput[key] end
	end
	local result = envelope(build, { operation = operation, nodeId = nodeId, before = { tree = beforeTree, output = beforeOutput }, after = { tree = afterTree, output = afterOutput }, delta = delta, saved = false, idempotencyKey = request.idempotencyKey }, { "PoB:TreeTab.activeSpec.allocNodes", "PoB:TreeTab.activeSpec.jewels", "PoB:CalcsTab.mainEnv.player.output" }, { { operation = "CHANGE_PASSIVE", passiveOperation = operation, nodeId = nodeId, value = delta, snapshotRevision = transaction.snapshotRevision } })
	result.side_effect, result.operator_message, result.snapshotRevision = "in_memory", transaction.operator_message, transaction.snapshotRevision
	return result
end

local function get_projectile_behavior(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local values = { }
	for _, key in ipairs({ "ProjectileCount", "PierceCount", "Chain", "ChainMax", "ChainRemaining", "ForkCount", "SplitCount" }) do
		if type(output[key]) == "number" then values[key] = output[key] end
	end
	if next(values) == nil then return nil, "projectile behavior is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output" }, finalTrace(skill, "ProjectileBehavior", values))
end

local function get_trigger_sequence(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local infoTrigger = type(skill.infoTrigger) == "string" and skill.infoTrigger or nil
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), trigger = infoTrigger, infoTrigger = infoTrigger, triggered = skill.triggered == true }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.infoTrigger" })
end

local function get_curse_application_order(build, skillSetSelector, skillNameValue)
	local mechanism = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	local order, err = mechanism.get_socket_order(build, skillSetSelector, skillNameValue)
	if not order then return nil, err end
	return envelope(build, { status = "not_simulated", basis = "socket order only", gems = order.facts.gems }, order.sources, { "Curse application timing is not simulated" })
end

local function get_ailment_effect(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local values = { }
	for key, value in pairs(calculatedOutput(player, skill)) do
		if type(key) == "string" and type(value) == "number" and (key:lower():find("chance", 1, true) or key:lower():find("ailment", 1, true)) then values[key] = value end
	end
	if next(values) == nil then return nil, "ailment effect is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output" }, finalTrace(skill, "Ailment", values))
end

local function get_damage_breakdown(build, skillIndex)
	return get_skill_breakdown(build, skillIndex)
end

local function get_conversion_chain(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local tableValue = skill.conversionTable
	if type(tableValue) ~= "table" then return nil, "conversionTable is unavailable for this skill" end
	local values = { }
	for damageType, entry in pairs(tableValue) do
		if type(entry) == "table" then
			local item = { conversion = { }, gain = { }, mult = entry.mult }
			for key, value in pairs(entry.conversion or { }) do if type(value) == "number" then item.conversion[key] = value end end
			for key, value in pairs(entry.gain or { }) do if type(value) == "number" then item.gain[key] = value end end
			values[damageType] = item
		end
	end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, status = "calculated", values = values }, { "PoB:Modules/CalcOffence.lua:1879-1926" })
end

local function get_effective_resistance(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local values = { }
	for _, key in ipairs({ "PhysicalEffMult", "FireEffMult", "ColdEffMult", "LightningEffMult", "ChaosEffMult" }) do
		if type(calculatedOutput(player, skill)[key]) == "number" then values[key] = calculatedOutput(player, skill)[key] end
	end
	if next(values) == nil then return nil, "effective resistance multipliers are unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:Modules/CalcOffence.lua:3515-3522" }, finalTrace(skill, "EffectiveResistance", values))
end

local function get_support_links(build, skillSetSelector, skillNameValue)
	local mechanism = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	local result, err = mechanism.get_socket_order(build, skillSetSelector, skillNameValue)
	if not result then return nil, err end
	return envelope(build, result.facts, result.sources, result.trace)
end

local function resolve_skill_context(build, skillSetSelector, skillNameValue)
	local context = (LoadModule and LoadModule("Modules/AgentContext")) or dofile("src/Modules/AgentContext.lua")
	local result, err = context.find_skill(build, skillSetSelector, skillNameValue)
	if not result then return nil, err end
	return envelope(build, result, { "PoB:Modules/AgentContext.lua:find_skill" })
end

local function comparisonOutput(state, skillIndex)
	if type(state) ~= "table" then return nil, "comparison state is required" end
	if state.skills then
		local skill = state.skills[skillIndex]
		return skill and (skill.output or skill.actorOutput), skill and skill.outputPath
	end
	local player, err = playerFor(state)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	return calculatedOutput(player, skill), "PoB:CalcsTab.mainEnv.player.activeSkillList[" .. tostring(skillIndex) .. "].output"
end

local function compare_build_states(beforeState, afterState, skillIndex, comparisonFields)
	if type(skillIndex) ~= "number" or skillIndex % 1 ~= 0 or skillIndex < 1 then return nil, "skillIndex must be an integer" end
	local beforeOutput, beforePath = comparisonOutput(beforeState, skillIndex)
	if not beforeOutput then return nil, beforePath end
	local afterOutput, afterPath = comparisonOutput(afterState, skillIndex)
	if not afterOutput then return nil, afterPath end
	local function meta(state, key)
		return state and (state[key] or (key == "gamePatch" and state.targetVersion) or (key == "pobVersion" and state.version))
	end
	for _, key in ipairs({ "gamePatch", "pobVersion", "dataRevision" }) do
		local left, right = meta(beforeState, key), meta(afterState, key)
		if left ~= nil and right ~= nil and tostring(left) ~= tostring(right) then
			return nil, { code = "VERSION_MISMATCH", recovery_class = "REJECT", stage = "comparison_validation", retryable = false, next_action = "reject_request", message = key .. " differs between comparison states" }
		end
	end
	local before, after, delta, percent, changed = scalarTable(beforeOutput), scalarTable(afterOutput), {}, {}, {}
	local fields = {}
	if type(comparisonFields) == "table" and #comparisonFields > 0 then
		for _, key in ipairs(comparisonFields) do fields[key] = true end
	else
		for key in pairs(before) do fields[key] = true end
		for key in pairs(after) do fields[key] = true end
	end
	for key in pairs(fields) do
		if type(before[key]) == "number" and type(after[key]) == "number" then
			delta[key] = after[key] - before[key]
			percent[key] = before[key] ~= 0 and (delta[key] / before[key]) * 100 or nil
			if delta[key] ~= 0 then changed[#changed + 1] = key end
		end
	end
	table.sort(changed)
	local result = envelope(afterState, {
		before = before, after = after, delta = delta, changeRatePercent = percent,
		changedFields = changed, skillIndex = skillIndex,
		buildId = { before = meta(beforeState, "buildId"), after = meta(afterState, "buildId") },
		outputPaths = { before = beforePath, after = afterPath },
	}, { beforePath or "PoB output (before)", afterPath or "PoB output (after)" }, {
		{ operation = "COMPARE_OUTPUTS", inputs = { before = before, after = after }, value = delta,
			formula = "after - before", snapshotRevision = snapshotRevision(afterState) },
	})
	local beforeConditions, afterConditions = beforeState.conditions or {}, afterState.conditions or {}
	local conditionsChanged = false
	for key, value in pairs(beforeConditions) do if afterConditions[key] ~= value then conditionsChanged = true end end
	for key, value in pairs(afterConditions) do if beforeConditions[key] ~= value then conditionsChanged = true end end
	result.conditions = { before = beforeConditions, after = afterConditions, changed = conditionsChanged }
	if result.conditions.changed then
		result.uncertainty.level = "medium"
		result.uncertainty.reasons = { "comparison conditions differ" }
	end
	return result
end

local function get_projectile_count(build, skillIndex)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then
		return nil, skillErr
	end
	local output = calculatedOutput(player, skill)
	local value = output.ProjectileCount
	if value == nil then
		return nil, "ProjectileCount is unavailable for this skill"
	end
	local baseTerms, moreTerms = modifierTrace(skill, "ProjectileCount")
	return envelope(build, { skillIndex = skillIndex, value = value }, { "PoB:Modules/CalcOffence.lua:1054-1062" }, {
		{ operation = "PROJECTILE_COUNT", value = value, inputs = { base = baseTerms, more = moreTerms }, formula = "floor(SUM_BASE(ProjectileCount) * PRODUCT_MORE(ProjectileCount))" },
	})
end

local function get_elemental_penetration(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill).ElementalPenetration or { }
	local values = { }
	for _, damageType in ipairs({ "Fire", "Cold", "Lightning" }) do
		if output[damageType] ~= nil then values[damageType] = output[damageType] end
	end
	if next(values) == nil then return nil, "ElementalPenetration is unavailable for this skill" end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, values = values }, { "PoB:Modules/CalcOffence.lua:3466-3475" }, finalTrace(skill, "ElementalPenetration", values))
end

local function get_curse_limit(build)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	local value = player.output and player.output.EnemyCurseLimit
	if value == nil then
		return nil, "EnemyCurseLimit is unavailable"
	end
	return envelope(build, { value = value }, { "PoB:Modules/CalcPerform.lua:3156-3158" }, finalTrace(player, "EnemyCurseLimit", value))
end

local function get_duration(build, skillIndex, durationType)
	if type(durationType) ~= "string" or durationType == "" then return nil, "durationType is required" end
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local outputKey = ({ skill_effect = "Duration", secondary = "DurationSecondary", tertiary = "DurationTertiary", aura = "AuraDuration", reserve = "ReserveDuration", totem = "TotemDuration" })[durationType]
	if outputKey and type(output[outputKey]) == "number" then
		local sourceSkill = skill
		if (not sourceSkill.breakdown or not sourceSkill.breakdown.DurationMod) and player.mainSkill then sourceSkill = player.mainSkill end
		local trace = { }
		local breakdown = sourceSkill.breakdown or (sourceSkill.actor and sourceSkill.actor.breakdown) or { }
		for _, entry in ipairs(breakdown[outputKey] or breakdown.DurationMod or { }) do trace[#trace + 1] = entry end
		local traceTool = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
		local modifierTerms = traceTool.collectCombined(sourceSkill, "Duration")
		for _, term in ipairs(modifierTerms) do
			trace[#trace + 1] = {
				operation = "DURATION_MODIFIER_SOURCE",
				stat = term.stat,
				modifierType = term.operation,
				value = term.value,
				source = term.source,
				scope = term.scope,
			}
		end
		trace[#trace + 1] = { operation = "FINAL_DURATION", stat = outputKey, value = output[outputKey], modifier = output.DurationMod, source = "PoB output", gems = gemFacts(skill) }
		return envelope(build, { skillIndex = skillIndex, name = skillName(skill), durationType = durationType, value = output[outputKey], modifier = output.DurationMod, unit = "seconds", status = "calculated", gems = gemFacts(skill), modifierTerms = modifierTerms }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output." .. outputKey, "PoB:CalcsTab.mainEnv.player.activeSkillList.breakdown." .. outputKey }, trace)
	end
	if durationType ~= "trauma" then return nil, "duration is unavailable for this skill and durationType" end
	if not skill.skillModList or not skill.skillCfg then return nil, "TraumaDuration modifiers are unavailable" end
	local baseTerms = (LoadModule and LoadModule("Modules/AgentTrace") or dofile("src/Modules/AgentTrace.lua")).collectCombined(skill, "TraumaDuration", "BASE")
	local durationTerms = (LoadModule and LoadModule("Modules/AgentTrace") or dofile("src/Modules/AgentTrace.lua")).collectCombined(skill, "Duration")
	local base = 0
	for _, term in ipairs(baseTerms) do base = base + (term.value or 0) end
	local inc, red, more = 0, 0, 1
	for _, term in ipairs(durationTerms) do
		if term.operation == "INC" then inc = inc + term.value elseif term.operation == "RED" then red = red + term.value elseif term.operation == "MORE" then more = more * (1 + term.value / 100) end
	end
	local multiplier = more * (1 + inc / 100) * (1 + red / 100)
	local value = base * multiplier
	if base <= 0 then return nil, "TraumaDuration is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), durationType = durationType, value = value, unit = "seconds", status = "calculated", gems = gemFacts(skill) }, { "PoB:Modules/CalcOffence.lua:2252" }, {
		{ operation = "SUM_BASE", stat = "TraumaDuration", value = base, inputs = baseTerms },
		{ operation = "DURATION_MODIFIER", stat = "Duration", value = multiplier, inputs = durationTerms },
		{ operation = "FINAL_DURATION", value = value, formula = "SUM_BASE(TraumaDuration) * calcLib.mod(Duration)" },
	})
end

local function explain_stat(build, stat, skillIndex)
	if type(stat) ~= "string" or stat == "" then
		return nil, "stat is required"
	end
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	if skillIndex then
		local _, skillErr = skillFor(player, skillIndex)
		if skillErr then
			return nil, skillErr
		end
	end
	local snapshot = (LoadModule and LoadModule("Modules/AgentSnapshot")) or dofile("src/Modules/AgentSnapshot.lua")
	local explanation, explainErr = snapshot.explain(build, stat, skillIndex)
	if not explanation then
		return nil, explainErr
	end
	if explanation.value == nil then
		return nil, "requested stat is unavailable"
	end
	local trace = explanation.trace or { }
	for _, entry in ipairs(explanation.modifierSources or { }) do trace[#trace + 1] = entry end
	return envelope(build, { stat = stat, value = explanation.value, modifierSources = explanation.modifierSources or { } }, { explanation.source }, trace)
end

local function mechanism(name, build, skillSetSelector, skillNameValue, supportName)
	local module = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	return module[name](build, skillSetSelector, skillNameValue, supportName)
end

local function get_skill_chain(build, skillSetSelector, skillNameValue)
	local result, err = mechanism("get_skill_chain", build, skillSetSelector, skillNameValue)
	if not result then return nil, err end
	return envelope(build, result.facts, result.sources, result.trace)
end

local function get_socket_order(build, skillSetSelector, skillNameValue)
	local result, err = mechanism("get_socket_order", build, skillSetSelector, skillNameValue)
	if not result then return nil, err end
	return envelope(build, result.facts, result.sources, result.trace)
end

local function compare_support_effect(build, skillSetSelector, skillNameValue, supportName)
	return mechanism("compare_support_effect", build, skillSetSelector, skillNameValue, supportName)
end

local function explain_damage_change(build, skillSetSelector, skillNameValue, supportName)
	return mechanism("explain_damage_change", build, skillSetSelector, skillNameValue, supportName)
end

return {
	get_character_stats = get_character_stats,
	get_skill_stats = get_skill_stats,
	get_skill_dps = get_skill_dps,
	get_highest_dps_skill = get_highest_dps_skill,
	get_skill_breakdown = get_skill_breakdown,
	get_item_modifiers = get_item_modifiers,
	replace_item = replace_item,
	replace_gem = replace_gem,
	change_passive = change_passive,
	get_projectile_behavior = get_projectile_behavior,
	get_trigger_sequence = get_trigger_sequence,
	get_curse_application_order = get_curse_application_order,
	get_ailment_effect = get_ailment_effect,
	get_damage_breakdown = get_damage_breakdown,
	get_conversion_chain = get_conversion_chain,
	get_effective_resistance = get_effective_resistance,
	get_support_links = get_support_links,
	get_skill_chain = get_skill_chain,
	get_socket_order = get_socket_order,
	compare_support_effect = compare_support_effect,
	explain_damage_change = explain_damage_change,
	resolve_skill_context = resolve_skill_context,
	compare_build_states = compare_build_states,
	get_projectile_count = get_projectile_count,
	get_elemental_penetration = get_elemental_penetration,
	get_curse_limit = get_curse_limit,
	get_duration = get_duration,
	explain_stat = explain_stat,
}
