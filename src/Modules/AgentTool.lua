-- Read-only Agent tools over PoB's calculated in-memory state.
local pairs = pairs
local type = type
local tostring = tostring

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

local function envelope(build, facts, sources, trace)
	return {
		calculationVersion = tostring(build and build.targetVersion or "unknown"),
		facts = facts,
		sources = sources,
		trace = trace or { },
	}
end

local function get_character_stats(build)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	return envelope(build, scalarTable(player.output), { "PoB:CalcsTab.mainEnv.player.output" })
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
	return envelope(build, {
		skillIndex = skillIndex,
		name = effect and effect.name,
		skillPart = skill.skillPartName,
		trigger = skill.infoTrigger,
		output = scalarTable(skill.output),
	}, { "PoB:CalcsTab.mainEnv.player.activeSkillList" })
end

local function skillName(skill)
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return effect and effect.name or skill.name or skill.baseName
end

local function get_skill_dps(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local value = skill.output and skill.output.TotalDPS
	if type(value) ~= "number" then return nil, "TotalDPS is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), value = value }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output.TotalDPS" })
end

local function get_highest_dps_skill(build)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local bestIndex, bestValue
	for index, skill in ipairs(player.activeSkillList or { }) do
		local value = skill.output and skill.output.TotalDPS
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

local function get_projectile_count(build, skillIndex)
	local player, err = playerFor(build)
	if not player then
		return nil, err
	end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then
		return nil, skillErr
	end
	local value = skill.output and skill.output.ProjectileCount
	if value == nil then
		return nil, "ProjectileCount is unavailable for this skill"
	end
	return envelope(build, { skillIndex = skillIndex, value = value }, { "PoB:Modules/CalcOffence.lua:1054-1062" })
end

local function get_elemental_penetration(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = skill.output and skill.output.ElementalPenetration or { }
	local values = { }
	for _, damageType in ipairs({ "Fire", "Cold", "Lightning" }) do
		if output[damageType] ~= nil then values[damageType] = output[damageType] end
	end
	if next(values) == nil then return nil, "ElementalPenetration is unavailable for this skill" end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, values = values }, { "PoB:Modules/CalcOffence.lua:3466-3475" })
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
	return envelope(build, { value = value }, { "PoB:Modules/CalcPerform.lua:3156-3158" })
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
	return envelope(build, { stat = stat, value = explanation.value }, { explanation.source }, explanation.trace or { })
end

return {
	get_character_stats = get_character_stats,
	get_skill_stats = get_skill_stats,
	get_skill_dps = get_skill_dps,
	get_highest_dps_skill = get_highest_dps_skill,
	get_skill_breakdown = get_skill_breakdown,
	get_item_modifiers = get_item_modifiers,
	get_projectile_count = get_projectile_count,
	get_elemental_penetration = get_elemental_penetration,
	get_curse_limit = get_curse_limit,
	explain_stat = explain_stat,
}
