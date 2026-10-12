-- In-process, read-only dispatcher for the currently running PoB Lua context.
-- It never loads XML, mutates build state, or invokes Save/Save As.
local pairs, type, tostring = pairs, type, tostring
local context
if LoadModule then
	local ok, loaded = pcall(LoadModule, "Modules/AgentContext")
	if ok then context = loaded end
end
context = context or dofile("src/Modules/AgentContext.lua")
local ErrorRegistry = LoadModule("Modules/AgentErrorRegistry")

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
		availableSpecs = (function()
			local result = {}
			for id, entry in ipairs(tree and tree.specList or {}) do result[#result + 1] = { id = id, title = title(entry) } end
			return result
		end)(),
		availableSkillSets = (function()
			local result = {}
			for id, entry in pairs(skills and skills.skillSets or {}) do result[#result + 1] = { id = id, title = title(entry) } end
			return result
		end)(),
		availableItemSets = (function()
			local result = {}
			for id, entry in pairs(items and items.itemSets or {}) do result[#result + 1] = { id = id, title = title(entry) } end
			return result
		end)(),
	}, skillErr
end

local function contextSignature(context)
	return canonical(context)
end

local function capture(build, provenance, preserveRevision)
	if type(build) ~= "table" then return nil, { code = "VALUE_UNAVAILABLE", recovery_class = "REJECT", stage = "snapshot_capture", retryable = false, attempt = 1, max_attempts = 1, message = "PoB build is unavailable", details = {}, next_action = "reject_request", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil } end
	-- A caller may pass raw selectors for one request. Apply only those fields,
	-- capture the resulting calculation context, then restore PoB's active state.
	local rawOverride = false
	if type(provenance) == "table" then
		for key, value in pairs(provenance) do if (key == "activeSpec" or key == "activeSkillSet" or key == "activeItemSet") and type(value) ~= "table" then rawOverride = true end end
	end
	if rawOverride then
		local previous = { activeSpec = build.treeTab and build.treeTab.activeSpec, activeSkillSet = build.skillsTab and build.skillsTab.activeSkillSetId, activeItemSet = build.itemsTab and build.itemsTab.activeItemSetId }
		local function restore()
			if build.treeTab and previous.activeSpec ~= nil and build.treeTab.SetActiveSpec then build.treeTab:SetActiveSpec(previous.activeSpec) end
			if build.skillsTab and previous.activeSkillSet ~= nil and build.skillsTab.SetActiveSkillSet then build.skillsTab:SetActiveSkillSet(previous.activeSkillSet) end
			if build.itemsTab and previous.activeItemSet ~= nil and build.itemsTab.SetActiveItemSet then build.itemsTab:SetActiveItemSet(previous.activeItemSet) end
		end
		local selected, applyErr = context.apply_calculation_context(build, provenance)
		if not selected then
			local message = tostring(applyErr)
			local code = message:lower():find("ambiguous", 1, true) and "AMBIGUOUS_ALIAS" or "USER_CONTEXT_MISSING"
			restore()
			return nil, { code = code, recovery_class = "ASK_USER", stage = "context_override", retryable = false, attempt = 1, max_attempts = 1, message = message, details = {}, next_action = "ask_user", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil }
		end
		local applied = {}
		for key in pairs(provenance) do applied[key] = { provenance = "explicit_override", requested = provenance[key], resolved = selected[key] } end
		local result, err = capture(build, applied, true)
		restore()
		return result, err
	end
	local activeState, contextErr = activeContext(build)
	if contextErr then return nil, contextErr end
	if build.skillsTab and not activeState.activeSkillSet.id then
		return nil, { code = "USER_CONTEXT_MISSING", recovery_class = "ASK_USER", stage = "context_resolution", retryable = false, attempt = 1, max_attempts = 1, message = "Skill Set was not found", details = {}, next_action = "ask_user", secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil }
	end
	local state = revisions[build]
	local signature = contextSignature(activeState)
	if not preserveRevision and (not state or state.signature ~= signature) then
		state = { number = (state and state.number or 0) + 1, signature = signature }
		revisions[build] = state
	end
	if not state then
		state = { number = 1, signature = signature }
		revisions[build] = state
	end
	local revision = tostring(build.buildId or build.id or "build") .. ":" .. tostring(state.number)
	return { snapshotRevision = revision, context = activeState, authoritative = true, mode = "live_read_only", contextProvenance = provenance or {} }
end

local function errorEnvelope(code, recovery, stage, message, nextAction)
	return { code = code, error_ref = ErrorRegistry.parent(code), recovery_class = recovery, stage = stage, retryable = false, attempt = 1, max_attempts = 1,
		message = message, details = {}, next_action = nextAction, secondary_causes = {}, side_effect = "none", operator_message = nil, snapshotRevision = nil }
end

local function dispatch(build, request, tools, dispatcher)
	if type(request) ~= "table" or type(request.tool) ~= "string" or type(request.arguments) ~= "table" then
		return nil, errorEnvelope("INPUT_INVALID", "REPAIR_INPUT", "request_validation", "request must contain tool and arguments", "repair_input")
	end
	if not readOnlyTools[request.tool] then
		return nil, errorEnvelope("MUTATION_NOT_PERSISTENT", "REJECT", "bridge_capability", "live dispatcher is read-only; mutation is not enabled", "reject_request")
	end
	local args = request.arguments
	local overrides = args.contextOverrides
	if overrides ~= nil and type(overrides) ~= "table" then return nil, errorEnvelope("INPUT_INVALID", "REPAIR_INPUT", "context_override", "contextOverrides must be an object", "repair_input") end
	overrides = overrides or {}
	local allowedOverrides = { activeSpec = true, activeSkillSet = true, activeItemSet = true }
	for key in pairs(overrides) do if not allowedOverrides[key] then return nil, errorEnvelope("INPUT_INVALID", "REPAIR_INPUT", "context_override", "unsupported context override: " .. tostring(key), "repair_input") end end
	local previous = { activeSpec = build.treeTab and build.treeTab.activeSpec, activeSkillSet = build.skillsTab and build.skillsTab.activeSkillSetId, activeItemSet = build.itemsTab and build.itemsTab.activeItemSetId }
	local configRestore, appliedConfig
	local function restore()
		if not next(overrides) and not configRestore then return end
		if build.treeTab and previous.activeSpec ~= nil and build.treeTab.SetActiveSpec then build.treeTab:SetActiveSpec(previous.activeSpec) end
		if build.skillsTab and previous.activeSkillSet ~= nil and build.skillsTab.SetActiveSkillSet then build.skillsTab:SetActiveSkillSet(previous.activeSkillSet) end
		if build.itemsTab and previous.activeItemSet ~= nil and build.itemsTab.SetActiveItemSet then build.itemsTab:SetActiveItemSet(previous.activeItemSet) end
		if configRestore then configRestore(); configRestore = nil end
	end
	local applied = {}
	if next(overrides) then
		local selected, applyErr = context and context.apply_calculation_context and context.apply_calculation_context(build, overrides)
		if not selected then
			local message = tostring(applyErr)
			local code = message:lower():find("ambiguous", 1, true) and "AMBIGUOUS_ALIAS" or "USER_CONTEXT_MISSING"
			restore()
			return nil, errorEnvelope(code, "ASK_USER", "context_override", message, "ask_user")
		end
		for key in pairs(overrides) do applied[key] = { provenance = "explicit_override", requested = overrides[key], resolved = selected[key] } end
	end
	if args.configOverrides ~= nil then
		if type(args.configOverrides) ~= "table" then restore(); return nil, errorEnvelope("INPUT_INVALID", "REPAIR_INPUT", "config_override", "configOverrides must be an object", "repair_input") end
		configRestore, appliedConfig = context.begin_config_overrides(build, args.configOverrides)
		if not configRestore then
			local message = tostring(appliedConfig)
			local code, recovery, nextAction = "INPUT_INVALID", "ASK_USER", "ask_user"
			if message:lower():find("unsupported", 1, true) then code = "UNSUPPORTED_REQUEST" end
			restore()
			return nil, errorEnvelope(code, recovery, "config_override", message, nextAction)
		end
		applied.configOverrides = { provenance = "explicit_override", keys = {} }
		for key in pairs(appliedConfig) do applied.configOverrides.keys[#applied.configOverrides.keys + 1] = key end
		table.sort(applied.configOverrides.keys)
	end
	local snapshot, snapshotErr = capture(build, applied)
	if not snapshot then restore(); return nil, snapshotErr end
	local result, err
	if type(dispatcher) == "function" then
		local ok, first, second = pcall(dispatcher, build, request.tool, args)
		if ok then result, err = first, second
		else result, err = nil, errorEnvelope("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", tostring(first), "report_error") end
		restore()
	else
	local handler = tools and tools[request.tool]
	if type(handler) ~= "function" then restore(); return nil, errorEnvelope("TOOL_NOT_FOUND", "REPAIR_INPUT", "tool_dispatch", "read-only tool is not registered", "repair_input") end
	local function invokeHandler()
		if request.tool == "resolve_skill_context" or request.tool == "get_support_links" or request.tool == "get_skill_chain" or request.tool == "get_socket_order" or request.tool == "get_curse_application_order" then
			return handler(build, args.skillSetSelector, args.skillName)
		elseif request.tool == "compare_support_effect" or request.tool == "explain_damage_change" then
			return handler(build, args.skillSetSelector, args.skillName, args.supportName)
		elseif request.tool == "get_item_modifiers" then return handler(build, args.itemId)
		elseif request.tool == "get_duration" then return handler(build, args.skillIndex, args.durationType)
		elseif request.tool == "explain_stat" then return handler(build, args.stat, args.skillIndex)
		else return handler(build, args.skillIndex) end
	end
	local ok, first, second = pcall(invokeHandler)
	if ok then result, err = first, second
	else result, err = nil, errorEnvelope("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", tostring(first), "report_error") end
	restore()
	end
	if not result then
		if type(err) == "table" then err.error_ref = err.error_ref or ErrorRegistry.parent(err.code) end
		return nil, type(err) == "table" and err or errorEnvelope("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "tool_execution", tostring(err or "PoB tool failed"), "report_error")
	end
	result.snapshotRevision = snapshot.snapshotRevision
	result.conditions = result.conditions or { context = snapshot.context, contextProvenance = snapshot.contextProvenance }
	result.contextProvenance = snapshot.contextProvenance
	result.liveMode = snapshot.mode
	return result
end

return { capture = capture, dispatch = dispatch, isReadOnly = function(tool) return readOnlyTools[tool] == true end, clear = function() revisions = setmetatable({}, { __mode = "k" }) end }
