local function collect(skill, stat, wantedType)
	local result = { }
	local list, cfg = skill and skill.skillModList, skill and skill.skillCfg
	if not list or type(list.Tabulate) ~= "function" then return result end
	for _, modType in ipairs({ "BASE", "INC", "RED", "MORE", "OVERRIDE" }) do
		if not wantedType or wantedType == modType then
		for _, entry in ipairs(list:Tabulate(modType, cfg, stat)) do
			local mod = entry.mod or { }
			result[#result + 1] = {
				operation = modType,
				value = entry.value,
				source = mod.source or "unknown",
				stat = stat,
			}
		end
		end
	end
	return result
end

local function sum(entries, operation)
	local value = operation == "MORE" and 1 or 0
	for _, entry in ipairs(entries or { }) do
		if entry.operation == operation then
			if operation == "MORE" then value = value * (1 + entry.value / 100) else value = value + entry.value end
		end
	end
	return value
end

return { collect = collect, sum = sum }
