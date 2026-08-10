local function collectFrom(list, cfg, stat, wantedType, scope)
	local result = { }
	if not list or type(list.Tabulate) ~= "function" then return result end
	for _, modType in ipairs({ "BASE", "INC", "RED", "MORE", "OVERRIDE" }) do
		if not wantedType or wantedType == modType then
		for _, entry in ipairs(list:Tabulate(modType, cfg, stat)) do
			local mod = entry.mod or { }
			result[#result + 1] = {
				operation = modType,
				value = entry.value,
				source = mod.source or "unknown",
				scope = scope,
				stat = stat,
			}
		end
		end
	end
	return result
end

local function collect(skill, stat, wantedType)
	return collectFrom(skill and skill.skillModList, skill and skill.skillCfg, stat, wantedType, "skill")
end

local function collectCombined(skill, stat, wantedType)
	local result = collect(skill, stat, wantedType)
	local actor = skill and skill.actor
	local actorDB = actor and actor.modDB
	if actorDB and actorDB ~= (skill and skill.skillModList) then
		local actorTerms = collectFrom(actorDB, nil, stat, wantedType, "actor")
		for _, entry in ipairs(actorTerms) do
			local duplicate
			for _, existing in ipairs(result) do
				if existing.operation == entry.operation and existing.value == entry.value and existing.source == entry.source and existing.stat == entry.stat then
					duplicate = existing
					break
				end
			end
			if duplicate then duplicate.scope = "skill+actor" else result[#result + 1] = entry end
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

return { collect = collect, collectCombined = collectCombined, sum = sum }
