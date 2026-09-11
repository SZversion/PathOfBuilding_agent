-- In-process, read-only dispatcher for the currently running PoB Lua context.
-- It never loads XML, mutates build state, or invokes Save/Save As.
local pairs, type, tostring = pairs, type, tostring

local readOnlyTools = {
	get_character_stats = true, get_skill_stats = true, get_skill_dps = true,
	get_highest_dps_skill = true, get_skill_breakdown = true, get_item_modifiers = true,
	get_projectile_behavior = true, get_trigger_sequence = true, get_curse_application_order = true,
	get_ailment_effect = true, get_damage_breakdown = true, get_conversion_chain = true,
	get_effective_resistance = true, get_support_links = true, resolve_skill_context = true,
	get_projectile_count = true, get_curse_limit = true, get_elemental_penetration = true,
	get_skill_chain = true, get_socket_order = true, compare_support_effect = true,
	explain_damage_change = true, get_duration = true, explain_stat = true,
}
local revisions = setmetatable({}, { __mode = "k" })

local function scalar(value)
	if type(value) == "number" or type(value) == "string" or type(value) == "boolean" then return value end
	return nil
end

local function sortedNumericIds(source, values)
	local result, seen = {}, {}
	for key, value in pairs(source or {}) do
		local candidate = values and value or key
		candidate = tonumber(candidate)
		if candidate and not seen[candidate] then seen[candidate] = true; result[#result + 1] = candidate end
	end
	table.sort(result)
	return result
end

local function primitiveMap(source)
	local result = {}
	for key, value in pairs(source or {}) do
		local simple = scalar(value)
		if simple ~= nil then result[key] = simple end
	end
	return result
end

local function resolveSkillSet(skills)
	local sets, order = skills and skills.skillSets or {}, skills and skills.skillSetOrderList or {}
	local activeId = skills and skills.activeSkillSetId
	if activeId ~= nil and sets[activeId] then return sets[activeId], activeId end
	local position = skills and skills.activeSkillSet
	if type(position) == "number" and order[position] and sets[order[position]] then return sets[order[position]], order[position] end
	if type(position) == "string" and sets[position] then return sets[position], position end
	if type(position) == "string" then
		local matches = {}
		local needle = position:match("^%s*(.-)%s*$"):lower()
		for id, candidate in pairs(sets) do
			local candidateTitle = candidate and (candidate.title or candidate.label)
			if type(candidateTitle) == "string" and candidateTitle:match("^%s*(.-)%s*$"):lower() == needle then matches[#matches + 1] = id end
		end
		if #matches > 1 then return nil, nil, { code = "AMBIGUOUS_ALIAS", recovery_class = "ASK_USER", stage = "context_resolution", retryable = false, attempt = 1, max_attempts = 1, message = "Skill Set title is ambiguous", details = { title = position }, next_action = "ask_user", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil } end
		if #matches == 1 then return sets[matches[1]], matches[1] end
	end
	for _, id in ipairs(order) do if sets[id] then return sets[id], id end end
	local ids = {}
	for id in pairs(sets) do ids[#ids + 1] = id end
	table.sort(ids, function(a, b) return tostring(a) < tostring(b) end)
	for _, id in ipairs(ids) do return sets[id], id end
	return nil, nil
end

local function canonical(value, seen)
	local valueType = type(value)
	if valueType ~= "table" then
		local simple = scalar(value)
		if simple ~= nil then return simple end
		return valueType == "nil" and "null" or nil
	end
	seen = seen or {}
	if seen[value] then return "<cycle>" end
	seen[value] = true
	local keys = {}
	for key in pairs(value) do if type(key) ~= "function" and type(key) ~= "userdata" then keys[#keys + 1] = key end end
	table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
	local parts = {}
	for _, key in ipairs(keys) do
		local child = canonical(value[key], seen)
		if child ~= nil then parts[#parts + 1] = tostring(key) .. "=" .. tostring(child) end
	end
	seen[value] = nil
	return "{" .. table.concat(parts, ";") .. "}"
end

local function title(entry)
	if type(entry) ~= "table" then return scalar(entry) end
	local value = entry.title or entry.name or entry.id
	return scalar(value)
end

local function activeContext(build)
	local tree = build and build.treeTab
	local skills = build and build.skillsTab
	local items = build and build.itemsTab
	local specId = tree and tree.activeSpec or 1
	local skillSet, skillId, skillErr = resolveSkillSet(skills)
	local itemId = items and (items.activeItemSetId or items.activeItemSet)
	local spec = tree and tree.specList and tree.specList[specId]
	local itemSet = items and items.itemSets and items.itemSets[itemId]
	local config = primitiveMap(build and build.configTab and build.configTab.input)
	local groups = {}
	for index, group in ipairs(skills and skills.socketGroupList or {}) do
		local gems = {}
		for gemIndex, gem in ipairs(group.gemList or group.displayGemList or {}) do
			local effect = gem.grantedEffect or (gem.gemData and gem.gemData.grantedEffect)
			gems[gemIndex] = {
				order = gemIndex, identity = gem.nameSpec or gem.name or (effect and effect.name),
				gemId = gem.gemId or (gem.gemData and gem.gemData.id), variantId = gem.variantId or (gem.gemData and gem.gemData.variantId),
				level = gem.level, quality = gem.quality, qualityId = gem.qualityId, enabled = gem.enabled ~= false,
				support = gem.support == true or (effect and effect.support == true) or (gem.gemData and gem.gemData.grantedEffect and gem.gemData.grantedEffect.support == true),
				itemGranted = gem.fromItem == true or gem.itemGranted == true,
			}
		end
		local sourceType = group.sourceItem ~= nil and "item_granted" or (group.sourceNode ~= nil and "tree_granted" or (group.source ~= nil and "generated" or "socketed"))
		local sourceNodeId = scalar(group.sourceNode)
		groups[index] = { index = index, enabled = group.enabled ~= false, sourceItem = group.sourceItem and title(group.sourceItem), sourceType = sourceType, sourceNodeId = sourceNodeId, synthetic = sourceType ~= "socketed", itemGrantedSkill = group.sourceItem ~= nil or (gems[1] and gems[1].itemGranted == true), gems = gems }
	end
	local player = build and build.calcsTab and build.calcsTab.mainEnv and build.calcsTab.mainEnv.player
	local mainSkill = player and player.mainSkill
	local mainEffect = mainSkill and mainSkill.activeEffect and mainSkill.activeEffect.grantedEffect
	-- PoB PassiveSpec.jewels is nodeId -> itemId; the node IDs are the stable projected IDs.
	local activeSpecState = spec and { id = specId, title = title(spec), allocatedNodeIds = sortedNumericIds(spec.allocNodes), jewelIds = sortedNumericIds(spec.jewels) } or { id = specId, allocatedNodeIds = {}, jewelIds = {} }
	local itemState = itemSet or (items and items.activeItemSet)
	local activeBuffs = primitiveMap(build and build.configTab and (build.configTab.activeBuffs or build.configTab.activeEffects))
	local enemyConditions = primitiveMap(build and build.configTab and (build.configTab.enemyConditions or build.configTab.enemy))
	return {
		activeSpec = activeSpecState,
		activeSkillSet = { id = skillId, title = title(skillSet) },
		activeItemSet = { id = itemId, title = title(itemSet) },
		mainSkill = { name = mainEffect and mainEffect.name or (mainSkill and (mainSkill.name or mainSkill.baseName)), skillPart = mainSkill and mainSkill.skillPartName },
		gems = groups, socketGroups = groups, config = config, activeBuffs = activeBuffs, enemyConditions = enemyConditions,
		gamePatch = build and build.gamePatch or build and build.targetVersion,
		pobVersion = build and build.pobVersion or build and build.version,
		dataRevision = build and build.dataRevision,
	}, skillErr
end

local function contextSignature(context)
	return canonical(context)
end

local function capture(build)
	if type(build) ~= "table" then return nil, { code = "VALUE_UNAVAILABLE", recovery_class = "REJECT", stage = "snapshot_capture", retryable = false, attempt = 1, max_attempts = 1, message = "PoB build is unavailable", details = {}, next_action = "reject_request", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil } end
	local context, contextErr = activeContext(build)
	if contextErr then return nil, contextErr end
	if build.skillsTab and not context.activeSkillSet.id then
		return nil, { code = "USER_CONTEXT_MISSING", recovery_class = "ASK_USER", stage = "context_resolution", retryable = false, attempt = 1, max_attempts = 1, message = "Skill Set was not found", details = {}, next_action = "ask_user", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil }
	end
	local state = revisions[build]
	local signature = contextSignature(context)
	if not state or state.signature ~= signature then
		state = { number = (state and state.number or 0) + 1, signature = signature }
		revisions[build] = state
	end
	local revision = tostring(build.buildId or build.id or "build") .. ":" .. tostring(state.number)
	return { snapshotRevision = revision, context = context, authoritative = true, mode = "live_read_only" }
end

local function errorEnvelope(code, recovery, stage, message, nextAction)
	return { code = code, recovery_class = recovery, stage = stage, retryable = false, attempt = 1, max_attempts = 1,
		message = message, details = {}, next_action = nextAction, secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil }
end

local function dispatch(build, request, tools)
	if type(request) ~= "table" or type(request.tool) ~= "string" or type(request.arguments) ~= "table" then
		return nil, errorEnvelope("INPUT_INVALID", "REPAIR_INPUT", "request_validation", "request must contain tool and arguments", "repair_input")
	end
	if not readOnlyTools[request.tool] then
		return nil, errorEnvelope("MUTATION_NOT_PERSISTENT", "REJECT", "bridge_capability", "live dispatcher is read-only; mutation is not enabled", "reject_request")
	end
	local snapshot, snapshotErr = capture(build)
	if not snapshot then return nil, snapshotErr end
	local handler = tools and tools[request.tool]
	if type(handler) ~= "function" then return nil, errorEnvelope("TOOL_NOT_FOUND", "REPAIR_INPUT", "tool_dispatch", "read-only tool is not registered", "repair_input") end
	local result, err
	local args = request.arguments
	if request.tool == "resolve_skill_context" or request.tool == "get_support_links" or request.tool == "get_skill_chain" or request.tool == "get_socket_order" or request.tool == "get_curse_application_order" then
		result, err = handler(build, args.skillSetSelector, args.skillName)
	elseif request.tool == "compare_support_effect" or request.tool == "explain_damage_change" then
		result, err = handler(build, args.skillSetSelector, args.skillName, args.supportName)
	elseif request.tool == "get_item_modifiers" then result, err = handler(build, args.itemId)
	elseif request.tool == "get_duration" then result, err = handler(build, args.skillIndex, args.durationType)
	elseif request.tool == "explain_stat" then result, err = handler(build, args.stat, args.skillIndex)
	else result, err = handler(build, args.skillIndex) end
	if not result then return nil, type(err) == "table" and err or errorEnvelope("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", tostring(err or "PoB tool failed"), "report_error") end
	result.snapshotRevision = snapshot.snapshotRevision
	result.conditions = result.conditions or { context = snapshot.context }
	result.liveMode = snapshot.mode
	return result
end

return { capture = capture, dispatch = dispatch, isReadOnly = function(tool) return readOnlyTools[tool] == true end, clear = function() revisions = setmetatable({}, { __mode = "k" }) end }
