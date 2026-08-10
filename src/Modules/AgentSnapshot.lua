-- PoB Agent snapshot bridge.
-- Captures the already-calculated build state; it does not reimplement PoB math.
local pairs = pairs
local type = type
local tostring = tostring
local io = io

local function calculatedOutput(player, skill)
	local output = skill and skill.output or { }
	if next(output) == nil and player and player.mainSkill and player.mainSkill.actor then
		output = player.mainSkill.actor.output or output
	end
	return output
end

local function gemSnapshot(skill)
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

local function copyTrace(value, depth)
	if depth > 4 then
		return "[trace depth limit]"
	end
	local valueType = type(value)
	if valueType == "number" or valueType == "string" or valueType == "boolean" then
		return value
	end
	if valueType ~= "table" then
		return nil
	end
	local result = { }
	for key, child in pairs(value) do
		local copied = copyTrace(child, depth + 1)
		if copied ~= nil then
			result[key] = copied
		end
	end
	return result
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

local function capture(build)
	local calcsTab = build and build.calcsTab
	local env = calcsTab and calcsTab.mainEnv
	local player = env and env.player
	local snapshot = {
		schemaVersion = 1,
		calculationVersion = tostring(build and build.targetVersion or "unknown"),
		characterLevel = build and build.characterLevel,
		mainSkillIndex = build and build.mainSocketGroup,
		outputs = scalarTable(player and player.output),
		skills = { },
		sources = { "PoB:CalcsTab.mainEnv.player.output" },
	}

	if player and player.activeSkillList then
		for index, skill in ipairs(player.activeSkillList) do
			local output = calculatedOutput(player, skill)
			snapshot.skills[index] = {
				name = skill.activeEffect and skill.activeEffect.grantedEffect and skill.activeEffect.grantedEffect.name,
				skillPart = skill.skillPartName,
				trigger = skill.infoTrigger,
				gems = gemSnapshot(skill),
				output = scalarTable(output),
				breakdown = copyTrace(skill.breakdown or (skill.actor and skill.actor.breakdown) or { }, 0),
			}
		end
	end

	return snapshot
end

local function save(snapshot, fileName)
	if type(fileName) ~= "string" or fileName == "" then
		return nil, "snapshot file path is required"
	end
	local dkjson = require "dkjson"
	local encoded = dkjson.encode(snapshot)
	local file, err = io.open(fileName, "w")
	if not file then
		return nil, err
	end
	local ok, writeErr = file:write(encoded)
	file:close()
	if not ok then
		return nil, writeErr
	end
	return true
end

local function explain(build, stat, skillIndex)
	if type(stat) ~= "string" or stat == "" then
		return nil, "stat is required"
	end
	local calcsTab = build and build.calcsTab
	local env = calcsTab and calcsTab.mainEnv
	local player = env and env.player
	local subject = player
	if skillIndex then
		subject = player and player.activeSkillList and player.activeSkillList[skillIndex]
	end
	if not subject then
		return nil, "calculation subject not found"
	end
	local output = calculatedOutput(player, subject)
	local breakdown = subject.breakdown or (subject.actor and subject.actor.breakdown) or { }
	local modifierSources = { }
	local traceTool = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
	for _, entry in ipairs(traceTool.collectCombined(subject, stat)) do modifierSources[#modifierSources + 1] = entry end
	return {
		schemaVersion = 1,
		calculationVersion = tostring(build and build.targetVersion or "unknown"),
		stat = stat,
		value = output[stat],
		trace = copyTrace(breakdown[stat], 0),
		modifierSources = modifierSources,
		source = skillIndex and "PoB:CalcsTab.mainEnv.player.activeSkillList" or "PoB:CalcsTab.mainEnv.player",
	}, nil
end

return {
	capture = capture,
	explain = explain,
	save = save,
}
