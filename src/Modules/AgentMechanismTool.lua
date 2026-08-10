-- Read-only mechanism facts from PoB's calculated in-memory state.
local type = type
local tostring = tostring

local agentTool = (LoadModule and LoadModule("Modules/AgentTool")) or dofile("src/Modules/AgentTool.lua")

local function scalarTable(source)
	local result = { }
	if type(source) ~= "table" then return result end
	for key, value in pairs(source) do
		if type(value) == "number" or type(value) == "string" or type(value) == "boolean" then
			result[key] = value
		end
	end
	return result
end

local function traceValue(source)
	if type(source) == "number" or type(source) == "string" or type(source) == "boolean" then return { source } end
	if type(source) ~= "table" then return nil end
	local result = { }
	for index, value in ipairs(source) do
		if type(value) == "number" or type(value) == "string" or type(value) == "boolean" then
			result[index] = value
		end
	end
	return result
end

local function breakdownTable(source)
	if type(source) ~= "table" then return { status = "unavailable" } end
	local result = { status = "calculated", values = { } }
	for key, value in pairs(source) do
		local trace = traceValue(value)
		if trace and next(trace) then result.values[key] = trace end
	end
	return result
end

local function selectedItem(build, slotName)
	local itemsTab = build.itemsTab
	local slot = itemsTab and itemsTab.slots and itemsTab.slots[slotName]
	local item = slot and itemsTab.items and itemsTab.items[slot.selItemId]
	return slot, item
end

local function socketGroups(build)
	local result = { }
	local groups = build.skillsTab and build.skillsTab.socketGroupList or { }
	for index, group in ipairs(groups) do
		local slot, item = selectedItem(build, group.slot)
		local gems = { }
		for gemIndex, gem in ipairs(group.gemList or { }) do
			gems[gemIndex] = {
				index = gemIndex,
				name = gem.name,
				baseName = gem.baseName,
				triggered = gem.triggered == true,
				skillPart = gem.skillPart,
			}
		end
		result[index] = {
			index = index,
			slot = group.slot,
			item = item and { name = item.name, baseName = item.baseName },
			enabled = group.enabled == true,
			slotEnabled = group.slotEnabled ~= false and (not slot or slot.inactive ~= true),
			mainActiveSkill = group.mainActiveSkill,
			gemOrder = gems,
		}
	end
	return result
end

local function skills(player)
	local result = { }
	for index, skill in ipairs(player.activeSkillList or { }) do
		local effect = skill.activeEffect and skill.activeEffect.grantedEffect
		result[index] = {
			index = index,
			name = effect and effect.name,
			skillPart = skill.skillPartName,
			trigger = skill.infoTrigger,
			output = scalarTable(skill.output),
			breakdown = breakdownTable(skill.breakdown),
		}
	end
	return result
end

local function get_mechanism_snapshot(build)
	local player = build and build.calcsTab and build.calcsTab.mainEnv and build.calcsTab.mainEnv.player
	if not player then return nil, "PoB calculation state is unavailable" end

	local projectileValues = { }
	for index, skill in ipairs(player.activeSkillList or { }) do
		if skill.output and skill.output.ProjectileCount ~= nil then
			local projectile, projectileErr = agentTool.get_projectile_count(build, index)
			if not projectile then return nil, projectileErr end
			projectileValues[#projectileValues + 1] = { skillIndex = index, value = projectile.facts.value }
		end
	end
	local curse, curseErr = agentTool.get_curse_limit(build)
	local curseFact = curse and { status = "calculated", value = curse.facts.value } or { status = "unavailable", error = curseErr }
	local projectileFact = #projectileValues > 0 and { status = "calculated", values = projectileValues } or { status = "unavailable" }

	return {
		calculationVersion = tostring(build.targetVersion or "unknown"),
		facts = {
			socketGroups = socketGroups(build),
			skills = skills(player),
			projectile = projectileFact,
			curse = curseFact,
			breakdown = breakdownTable(player.breakdown),
			simulations = {
				curseApplicationOrder = { status = "not_simulated", basis = "socket order only" },
				triggerSequence = { status = "not_simulated" },
				combatOutcome = { status = "not_simulated" },
			},
		},
		sources = {
			"PoB:SkillsTab.socketGroupList",
			"PoB:ItemsTab.slots/items",
			"PoB:CalcsTab.mainEnv.player",
		},
		trace = { },
	}
end

return { get_mechanism_snapshot = get_mechanism_snapshot }
