local type = type
local tostring = tostring

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

local function lower(value)
	return type(value) == "string" and value:lower() or nil
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
			if lower(candidate.title) == lower(selector) then
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
	local needle = name:lower()
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
			if lower(effect_name(activeSkill)) == needle then skillMatch = skillIndex end
		end
		if lower(gem_name(first) or (first and first.grantedEffect and first.grantedEffect.name)) == needle or skillMatch then
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
		if (skill == selected or (not selected and lower(effect_name(skill)) == needle)) and (not skill.socketGroup or skill.socketGroup == group) then
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

return { load_xml_file = load_xml_file, find_skill = find_skill }
