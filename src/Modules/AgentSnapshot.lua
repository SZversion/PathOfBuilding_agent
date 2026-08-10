-- PoB Agent snapshot bridge.
-- Captures the already-calculated build state; it does not reimplement PoB math.
local pairs = pairs
local type = type
local tostring = tostring
local io = io

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
			snapshot.skills[index] = {
				name = skill.activeEffect and skill.activeEffect.grantedEffect and skill.activeEffect.grantedEffect.name,
				skillPart = skill.skillPartName,
				trigger = skill.infoTrigger,
				output = scalarTable(skill.output),
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

return {
	capture = capture,
	save = save,
}
