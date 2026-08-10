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

local function find_skill(build, selector, name)
	if type(name) ~= "string" or name == "" then return nil, "skill name is required" end
	local set, setId = skill_set(build, selector)
	if not set then return nil, setId end
	local needle = name:lower()
	local groupIndex
	for index, group in ipairs(set.socketGroupList or { }) do
		for _, gem in ipairs(group.gemList or { }) do
			if lower(gem_name(gem)) == needle then
				if groupIndex then return nil, "skill name is ambiguous in Skill Set" end
				groupIndex = index
			end
		end
	end
	if not groupIndex then return nil, "skill was not found in Skill Set" end
	local tab, calcs = build.skillsTab, build.calcsTab
	if type(tab.SetActiveSkillSet) ~= "function" or not calcs or type(calcs.BuildOutput) ~= "function" then
		return nil, "PoB calculation context cannot be switched"
	end
	tab:SetActiveSkillSet(setId)
	build.mainSocketGroup = groupIndex
	calcs.input = calcs.input or { }
	calcs.input.skill_number = groupIndex
	calcs:BuildOutput()
	local found
	for index, skill in ipairs(calcs.mainEnv and calcs.mainEnv.player and calcs.mainEnv.player.activeSkillList or { }) do
		local effect = skill.activeEffect and skill.activeEffect.grantedEffect
		local skillName = effect and effect.name or skill.name or skill.baseName
		if lower(skillName) == needle then
			if found then return nil, "calculated skill is ambiguous" end
			found = index
		end
	end
	if not found then return nil, "calculated skill was not found" end
	return { skillSet = { id = setId, title = set.title or "Default" }, socketGroup = groupIndex, skillIndex = found, name = name }
end

return { load_xml_file = load_xml_file, find_skill = find_skill }
