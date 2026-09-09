local type = type
local tostring = tostring
local aliasEntries

local function load_xml_file(path, name)
	if type(path) ~= "string" or path == "" then return nil, "XML path is required" end
	local file, openErr = io.open(path, "r")
	if not file then return nil, openErr or "could not open XML build" end
	local xml = file:read("*a")
	file:close()
	if type(loadBuildFromXML) ~= "function" then return nil, "PoB XML loader is unavailable" end
	local ok, err = pcall(loadBuildFromXML, xml, name or path)
	if not ok then return nil, err end
	if type(runCallback) == "function" then
		local frameOk, frameErr = pcall(runCallback, "OnFrame")
		if not frameOk then return nil, frameErr end
	end
	if not build then return nil, "PoB build was not created" end
	return build
end

local function normalize_name(value)
	if type(value) ~= "string" then return nil end
	return value:match("^%s*(.-)%s*$"):gsub("%s+", " "):lower()
end

local function resolve_skill_alias(value)
	local normalized = normalize_name(value)
	if not normalized then return nil, { code = "INPUT_INVALID", recovery_class = "REPAIR_INPUT", stage = "context_resolution", retryable = false, next_action = "repair_input", message = "skill name is required" } end
	if not aliasEntries then
		local file
	for _, path in ipairs({ "agent/knowledge/aliases/ko/skills-3.29.json", "../agent/knowledge/aliases/ko/skills-3.29.json" }) do
			file = io.open(path, "r")
			if file then break end
		end
		if file then
			local content = file:read("*a")
			file:close()
			local ok, decoder = pcall(require, "dkjson")
			if ok and decoder then
				local parsed = decoder.decode(content)
				aliasEntries = parsed and parsed.entries or { }
			else aliasEntries = { } end
		else aliasEntries = { } end
	end
	local matches = { }
	for _, entry in ipairs(aliasEntries) do
		if normalize_name(entry.korean) == normalized or normalize_name(entry.english) == normalized then matches[#matches + 1] = entry.english end
	end
	if #matches > 1 then return nil, { code = "AMBIGUOUS_ALIAS", recovery_class = "ASK_USER", stage = "context_resolution", retryable = false, next_action = "ask_user", message = "skill alias is ambiguous" } end
	return matches[1] or value
end

-- Resolve and apply the three pieces of PoB state that affect a calculation.
-- Set ids are stable keys in PoB's tables; numeric selectors therefore prefer
-- an id and fall back to the corresponding position in the ordered list.
local function resolve_title_selector(value, entries, order, label)
	local function invalid(message)
		return nil, message or (label .. " selector is invalid")
	end
	if value == nil then
		local id = order and order[1]
		return id and entries[id], id or invalid(label .. " is not available")
	end
	local id
	if type(value) == "number" then
		id = entries[value] and value or (order and order[value])
	elseif type(value) == "string" then
		local numeric = tonumber(value)
		if numeric then
			id = entries[numeric] and numeric or (order and order[numeric])
		end
		local needle = normalize_name(value)
		for candidateId, candidate in pairs(entries or {}) do
			if normalize_name(candidate and candidate.title) == needle then
				if id and id ~= candidateId then return invalid(label .. " selector is ambiguous") end
				id = candidateId
			end
		end
	else
		return invalid()
	end
	if not id or not entries[id] then return invalid(label .. " was not found") end
	return entries[id], id
end

local function resolve_spec_selector(value, treeTab)
	local specs = treeTab and treeTab.specList
	if type(specs) ~= "table" then return nil, "Tree Spec state is unavailable" end
	if value == nil then
		local id = treeTab.activeSpec or 1
		return specs[id], id
	end
	local id
	if type(value) == "number" then
		id = value
	elseif type(value) == "string" then
		id = tonumber(value)
		local needle = normalize_name(value)
		for candidateId, candidate in ipairs(specs) do
			if normalize_name(candidate and candidate.title) == needle then
				if id and id ~= candidateId then return nil, "Tree Spec selector is ambiguous" end
				id = candidateId
			end
		end
	else
		return nil, "Tree Spec selector is invalid"
	end
	if not id or not specs[id] then return nil, "Tree Spec was not found" end
	return specs[id], id
end

local function apply_calculation_context(build, selectors)
	if type(build) ~= "table" then return nil, "PoB build is unavailable" end
	selectors = selectors or {}
	local treeTab, skillsTab, itemsTab = build.treeTab, build.skillsTab, build.itemsTab
	local selected = {}
	if treeTab then
		local spec, specId = resolve_spec_selector(selectors.activeSpec, treeTab)
		if not spec then return nil, specId end
		selected.activeSpec = { id = specId, title = spec.title or "Default" }
	end
	if selectors.activeSpec ~= nil then
		if not treeTab then return nil, "Tree Spec state is unavailable" end
		if type(treeTab.SetActiveSpec) ~= "function" then return nil, "Tree Spec selector cannot be applied" end
		treeTab:SetActiveSpec(selected.activeSpec.id)
	end
	if skillsTab then
		local skillSet, skillId = resolve_title_selector(selectors.activeSkillSet, skillsTab.skillSets, skillsTab.skillSetOrderList, "Skill Set")
		if not skillSet then return nil, skillId end
		selected.activeSkillSet = { id = skillId, title = skillSet.title or "Default" }
	end
	if selectors.activeSkillSet ~= nil then
		if not skillsTab then return nil, "Skill Set state is unavailable" end
		if type(skillsTab.SetActiveSkillSet) ~= "function" then return nil, "Skill Set selector cannot be applied" end
		skillsTab:SetActiveSkillSet(selected.activeSkillSet.id)
	end
	if itemsTab then
		local itemSet, itemId = resolve_title_selector(selectors.activeItemSet, itemsTab.itemSets, itemsTab.itemSetOrderList, "Item Set")
		if not itemSet then return nil, itemId end
		selected.activeItemSet = { id = itemId, title = itemSet.title or "Default" }
	end
	if selectors.activeItemSet ~= nil then
		if not itemsTab then return nil, "Item Set state is unavailable" end
		if type(itemsTab.SetActiveItemSet) ~= "function" then return nil, "Item Set selector cannot be applied" end
		itemsTab:SetActiveItemSet(selected.activeItemSet.id)
	end
	return selected
end

local function skill_set(build, selector)
	local tab = build and build.skillsTab
	if not tab or not tab.skillSets then return nil, "Skill Set state is unavailable" end
	local id
	if selector == nil then
		id = tab.activeSkillSetId or (tab.skillSetOrderList and tab.skillSetOrderList[1])
	elseif type(selector) == "number" then
		id = tab.skillSetOrderList and tab.skillSetOrderList[selector]
	elseif type(selector) == "string" then
		local numeric = tonumber(selector)
		if numeric then id = tab.skillSetOrderList and tab.skillSetOrderList[numeric] end
		for candidateId, candidate in pairs(tab.skillSets) do
			if normalize_name(candidate.title) == normalize_name(selector) then
				if id and id ~= candidateId then return nil, "Skill Set selector is ambiguous" end
				id = candidateId
			end
		end
	else
		return nil, "Skill Set selector is invalid"
	end
	if not id or not tab.skillSets[id] then return nil, "Skill Set was not found" end
	return tab.skillSets[id], id
end

local function gem_name(gem)
	return gem and (gem.nameSpec or gem.name or gem.baseName)
end

local function effect_name(skill)
	local effect = skill and skill.activeEffect and skill.activeEffect.grantedEffect
	return effect and effect.name or skill and skill.name or skill and skill.baseName
end

local function summarize_item(item)
	if type(item) ~= "table" then return nil end
	local result = {}
	if type(item.name) == "string" then result.name = item.name end
	if type(item.baseName) == "string" then result.baseName = item.baseName end
	return next(result) and result or nil
end

local function effective_gems(group)
	if type(group.displayGemList) == "table" and #group.displayGemList > 0 then
		return group.displayGemList
	end
	return group.gemList or { }
end

local function support_name(gem)
	local effect = gem and gem.grantedEffect
	local dataEffect = gem and gem.gemData and gem.gemData.grantedEffect
	if not ((effect and effect.support) or (dataEffect and dataEffect.support) or (gem and gem.support)) then return nil end
	return gem_name(gem) or (effect and effect.name) or (dataEffect and dataEffect.name)
end

local function provenance(group, firstGem)
	if group.sourceItem or (firstGem and firstGem.fromItem) then
		return "item_granted", summarize_item(group.sourceItem)
	end
	if group.sourceNode ~= nil then
		local node = group.sourceNode
		if type(node) == "table" then node = node.id or node.dn or node.name end
		return "tree_granted", node
	end
	if group.source ~= nil then return "generated", nil end
	return "socketed", nil
end

local function find_skill(build, selector, name)
	if type(name) ~= "string" or name == "" then return nil, "skill name is required" end
	local set, setId = skill_set(build, selector)
	if not set then return nil, setId end
	local canonical, aliasErr = resolve_skill_alias(name)
	if not canonical then return nil, aliasErr end
	local needle = normalize_name(canonical)
	local tab, calcs = build.skillsTab, build.calcsTab
	if type(tab.SetActiveSkillSet) ~= "function" or not calcs or type(calcs.BuildOutput) ~= "function" then
		return nil, "PoB calculation context cannot be switched"
	end
	tab:SetActiveSkillSet(setId)
	-- PoB rebuilds this list from the selected Skill Set, including item/tree grants.
	if type(tab.socketGroupList) ~= "table" then tab.socketGroupList = { } end
	calcs.input = calcs.input or { }
	calcs:BuildOutput()
	local matches = {}
	for groupIndex, group in ipairs(tab.socketGroupList or { }) do
		local gems = effective_gems(group)
		local first = gems[1]
		local skillMatch
		for skillIndex, activeSkill in ipairs(group.displaySkillList or { }) do
			if normalize_name(effect_name(activeSkill)) == needle then skillMatch = skillIndex end
		end
		if normalize_name(gem_name(first) or (first and first.grantedEffect and first.grantedEffect.name)) == needle or skillMatch then
			local sourceType, sourceValue = provenance(group, first)
			local supports = {}
			for index = 2, #gems do
				local support = support_name(gems[index])
				if support then supports[#supports + 1] = support end
			end
			matches[#matches + 1] = { groupIndex, group, first, sourceType, sourceValue, supports, #gems, skillMatch }
		end
	end
	if #matches == 0 then return nil, "skill was not found in calculated Skill Set" end
	if #matches > 1 then return nil, "skill name is ambiguous in Skill Set" end
	local match = matches[1]
	local groupIndex, group, first, sourceType, sourceValue, supports, linkCount, requestedSkillIndex = unpack(match)
	build.mainSocketGroup = groupIndex
	calcs.input.skill_number = groupIndex
	calcs:BuildOutput()
	group = tab.socketGroupList[groupIndex] or group
	local selected = group.displaySkillList and group.displaySkillList[requestedSkillIndex or group.mainActiveSkill or 1]
	local found
	for index, skill in ipairs(calcs.mainEnv and calcs.mainEnv.player and calcs.mainEnv.player.activeSkillList or { }) do
		if (skill == selected or (not selected and normalize_name(effect_name(skill)) == needle)) and (not skill.socketGroup or skill.socketGroup == group) then
			if found then return nil, "calculated skill is ambiguous" end
			found = index
		end
	end
	if not found then return nil, "calculated skill was not found" end
	return {
		skillSet = { id = setId, title = set.title or "Default" }, socketGroup = groupIndex,
		skillIndex = found, name = name, effectName = effect_name(selected), sourceType = sourceType,
		sourceItem = sourceType == "item_granted" and sourceValue or nil,
		sourceNode = sourceType == "tree_granted" and sourceValue or nil,
		slot = group.slot, supports = supports, linkCount = linkCount,
		enabled = group.enabled ~= false and (not first or first.enabled ~= false),
	}
end

	return { load_xml_file = load_xml_file, find_skill = find_skill, normalize_name = normalize_name, resolve_skill_alias = resolve_skill_alias, apply_calculation_context = apply_calculation_context }
