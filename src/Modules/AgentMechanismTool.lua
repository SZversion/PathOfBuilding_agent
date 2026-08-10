-- Read-only mechanism facts from PoB's calculated in-memory state.
local type = type
local tostring = tostring

local agentTool = (LoadModule and LoadModule("Modules/AgentTool")) or dofile("src/Modules/AgentTool.lua")

local function calculatedOutput(player, skill)
	local output = skill and skill.output or { }
	if next(output) == nil and player and player.mainSkill and player.mainSkill.actor then
		output = player.mainSkill.actor.output or output
	end
	return output
end

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
			output = scalarTable(calculatedOutput(player, skill)),
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
		if calculatedOutput(player, skill).ProjectileCount ~= nil then
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

local function skillSetFor(build, selector)
	local tab = build and build.skillsTab
	if not tab or not tab.skillSets then return nil, "Skill Set state is unavailable" end
	local id
	if selector == nil then
		id = tab.activeSkillSetId or (tab.skillSetOrderList and tab.skillSetOrderList[1])
	elseif type(selector) == "number" then
		id = tab.skillSets[selector] and selector or (tab.skillSetOrderList and tab.skillSetOrderList[selector])
	elseif type(selector) == "string" then
		local needle = selector:lower()
		for candidateId, set in pairs(tab.skillSets) do
			if type(set.title) == "string" and set.title:lower() == needle then
				if id then return nil, "Skill Set selector is ambiguous" end
				id = candidateId
			end
		end
	end
	if not id or not tab.skillSets[id] then return nil, "Skill Set was not found" end
	return tab.skillSets[id], id
end

local function get_skill_set(build, selector)
	local set, id = skillSetFor(build, selector)
	if not set then return nil, id end
	local order
	for index, candidateId in ipairs(build.skillsTab.skillSetOrderList or { }) do
		if candidateId == id then order = index break end
	end
	return {
		calculationVersion = tostring(build.targetVersion or "unknown"),
		facts = { id = id, title = set.title or "Default", order = order, socketGroupCount = #(set.socketGroupList or { }) },
		sources = { "PoB:SkillsTab.skillSets" },
		trace = { },
	}
end

local function skillName(skill)
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return (effect and effect.name) or skill.name or skill.baseName
end

local function skillGroupFor(set, name)
	local needle = name:lower()
	local found
	for index, group in ipairs(set.socketGroupList or { }) do
		for _, gem in ipairs(group.gemList or { }) do
			local gemName = gem.nameSpec or gem.name or gem.baseName
			if type(gemName) == "string" and gemName:lower() == needle then
				if found then return nil, "skill name is ambiguous in Skill Set" end
				found = index
			end
		end
	end
	return found
end

local cachedSkillOutput

local function get_skill_chain(build, skillSetSelector, name)
	if type(name) ~= "string" or name == "" then return nil, "skill name is required" end
	local target, targetId = skillSetFor(build, skillSetSelector)
	if not target then return nil, targetId end
	local tab = build.skillsTab
	local calcs = build.calcsTab
	if not tab.SetActiveSkillSet or not calcs or not calcs.BuildOutput then return nil, "PoB calculation context cannot be switched" end
	local oldId, oldGroup = tab.activeSkillSetId, build.mainSocketGroup
	local oldInput = calcs.input and calcs.input.skill_number
	local function restore()
		tab:SetActiveSkillSet(oldId)
		build.mainSocketGroup = oldGroup
		if calcs.input then calcs.input.skill_number = oldInput end
		calcs:BuildOutput()
	end
	local ok, result, err = pcall(function()
		local context = (LoadModule and LoadModule("Modules/AgentContext")) or dofile("src/Modules/AgentContext.lua")
		local resolved, resolveErr = context.find_skill(build, skillSetSelector, name)
		if not resolved then return nil, resolveErr end
		local player = calcs.mainEnv and calcs.mainEnv.player
		local skill = player and player.activeSkillList and player.activeSkillList[resolved.skillIndex]
		if not skill then return nil, "calculated skill was not found" end
		if skill.disableReason then return nil, "skill is disabled: " .. skill.disableReason end
		local output = calculatedOutput(player, skill)
		if output.Chain == nil and output.ChainMax == nil and output.ChainRemaining == nil and output.ChainMaxString == nil then
			return nil, "chain output is unavailable for selected skill"
		end
		local traceTool = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
		local maxTerms = traceTool.collectCombined(skill, "ChainCountMax", "BASE")
		local moreTerms = traceTool.collectCombined(skill, "ChainCountMax", "MORE")
		local chainTerms = traceTool.collectCombined(skill, "ChainCount", "BASE")
		local baseMax = traceTool.sum(maxTerms, "BASE")
		local moreMax = traceTool.sum(moreTerms, "MORE")
		local addedProjectiles = 0
		local projectileTerms = { }
		if skill.skillModList and skill.skillCfg and skill.skillModList:Flag(skill.skillCfg, "AdditionalProjectilesAddChainsInstead") and not skill.skillModList:Flag(skill.skillCfg, "SingleProjectile") then
			local projectileBase = skill.skillModList:Sum("BASE", skill.skillCfg, "ProjectileCount")
			local projectileMore = skill.skillModList:More(skill.skillCfg, "ProjectileCount")
			addedProjectiles = math.floor((projectileBase - 1) * projectileMore)
			projectileTerms = {
				{ operation = "SUM_BASE", stat = "ProjectileCount", value = projectileBase },
				{ operation = "PRODUCT_MORE", stat = "ProjectileCount", value = projectileMore },
				{ operation = "PROJECTILE_TO_CHAIN", value = addedProjectiles },
			}
		end
		local globalChainAddition = output.BeidatAdditionalBeamChains or 0
		local globalTerms = globalChainAddition ~= 0 and { { operation = "GLOBAL_ADD", source = "Pact of Beidat", value = globalChainAddition } } or { }
		return {
			calculationVersion = tostring(build.targetVersion or "unknown"),
			facts = { skillSet = resolved.skillSet, skill = { name = resolved.effectName or name, socketGroup = resolved.socketGroup, skillIndex = resolved.skillIndex }, chain = { Chain = output.Chain, ChainMax = output.ChainMax, ChainRemaining = output.ChainRemaining, ChainMaxString = output.ChainMaxString } },
			sources = { "PoB:Modules/CalcOffence.lua:1032-1044" },
			trace = {
				{ operation = "SUM_BASE", stat = "ChainCountMax", value = baseMax, inputs = maxTerms },
				{ operation = "PRODUCT_MORE", stat = "ChainCountMax", value = moreMax, inputs = moreTerms },
				{ operation = "SUM_BASE", stat = "ChainCount", value = traceTool.sum(chainTerms, "BASE"), inputs = chainTerms },
				{ operation = "PROJECTILE_TO_CHAIN", value = addedProjectiles, inputs = projectileTerms },
				{ operation = "GLOBAL_ADD", stat = "ChainMax", value = globalChainAddition, inputs = globalTerms },
				{ operation = "FINAL_CHAIN_MAX", value = output.ChainMax, formula = "(SUM_BASE(ChainCountMax) + PROJECTILE_TO_CHAIN) * PRODUCT_MORE(ChainCountMax) + GLOBAL_ADD" },
			},
		}
	end)
	local restored, restoreErr = pcall(restore)
	if not restored then return nil, restoreErr end
	if not ok then return nil, result end
	if not result then return nil, err end
	return result
end

cachedSkillOutput = function(name)
	local cache = GlobalCache and GlobalCache.cachedData and GlobalCache.cachedData.MAIN
	for _, entry in pairs(cache or { }) do
		if entry.Name and entry.Name:lower() == name:lower() then
			return entry.Env and entry.Env.player and entry.Env.player.output
		end
	end
    return nil
end

local function scalarOutput(source)
	local result = { }
	for key, value in pairs(source or { }) do
		if type(value) == "number" or type(value) == "string" or type(value) == "boolean" then result[key] = value end
	end
	return result
end

local function compare_support_effect(build, skillSetSelector, skillNameValue, supportName)
	if type(skillNameValue) ~= "string" or skillNameValue == "" then return nil, "skill name is required" end
	if type(supportName) ~= "string" or supportName == "" then return nil, "support name is required" end
	local target, targetId = skillSetFor(build, skillSetSelector)
	if not target then return nil, targetId end
	local groupIndex, groupErr = skillGroupFor(target, skillNameValue)
	if not groupIndex then return nil, groupErr or "skill was not found in Skill Set" end
	local support
	for _, gem in ipairs(target.socketGroupList[groupIndex].gemList or { }) do
		local gemName = gem.nameSpec or gem.name or gem.baseName
		if type(gemName) == "string" and gemName:lower() == supportName:lower() then
			if support then return nil, "support name is ambiguous in Skill Set" end
			support = gem
		end
	end
	if not support then return nil, "support was not found in Skill Set" end
	local tab, calcs = build.skillsTab, build.calcsTab
	if not tab.SetActiveSkillSet or not calcs or not calcs.BuildOutput then return nil, "PoB calculation context cannot be switched" end
	local oldId, oldGroup, oldInput, oldEnabled = tab.activeSkillSetId, build.mainSocketGroup, calcs.input and calcs.input.skill_number, support.enabled
	local function restore()
		support.enabled = oldEnabled
		tab:SetActiveSkillSet(oldId)
		build.mainSocketGroup = oldGroup
		if calcs.input then calcs.input.skill_number = oldInput end
		if wipeGlobalCache then wipeGlobalCache() end
		calcs:BuildOutput()
	end
	local function state(enabled)
		support.enabled = enabled
		if wipeGlobalCache then wipeGlobalCache() end
		calcs:BuildOutput()
		local output = cachedSkillOutput(skillNameValue)
		return output and { status = "calculated", output = scalarOutput(output) } or { status = "unavailable" }
	end
	local ok, enabledState, disabledState = pcall(function()
		tab:SetActiveSkillSet(targetId)
		build.mainSocketGroup = groupIndex
		calcs.input = calcs.input or { }
		calcs.input.skill_number = groupIndex
		return state(true), state(false)
	end)
	local restored, restoreErr = pcall(restore)
	if not restored then return nil, restoreErr end
	if not ok then return nil, enabledState end
	local delta = { }
	for key, value in pairs(enabledState.output or { }) do
		if type(value) == "number" and type(disabledState.output and disabledState.output[key]) == "number" then delta[key] = value - disabledState.output[key] end
	end
	return {
		calculationVersion = tostring(build.targetVersion or "unknown"),
		facts = {
			skillSet = { id = targetId, title = target.title },
			skill = { name = skillNameValue, socketGroup = groupIndex },
			support = { name = supportName, enabledBefore = oldEnabled },
			enabled = enabledState,
			disabled = disabledState,
			delta = delta,
		},
		sources = { "PoB:GlobalCache.cachedData.MAIN", "PoB:Modules/Calcs.lua:428-438" },
		trace = { },
	}
end

local function get_socket_order(build, skillSetSelector, skillNameValue)
	if type(skillNameValue) ~= "string" or skillNameValue == "" then return nil, "skill name is required" end
	local target, targetId = skillSetFor(build, skillSetSelector)
	if not target then return nil, targetId end
	local groupIndex, groupErr = skillGroupFor(target, skillNameValue)
	if not groupIndex then return nil, groupErr or "skill was not found in Skill Set" end
	local gems = { }
	for index, gem in ipairs(target.socketGroupList[groupIndex].gemList or { }) do
		gems[index] = { index = index, name = gem.nameSpec or gem.name or gem.baseName, enabled = gem.enabled ~= false, triggered = gem.triggered == true }
	end
	return {
		calculationVersion = tostring(build.targetVersion or "unknown"),
		facts = { skillSet = { id = targetId, title = target.title }, skill = { name = skillNameValue, socketGroup = groupIndex }, gems = gems },
		sources = { "PoB:SkillsTab.skillSets.socketGroupList.gemList" },
		trace = { },
	}
end

local function explain_damage_change(build, skillSetSelector, skillNameValue, supportName)
	local result, err = compare_support_effect(build, skillSetSelector, skillNameValue, supportName)
	if not result then return nil, err end
	result.trace = {
		"Support enabled: " .. supportName,
		"Compare against support disabled state",
		"Numeric deltas are enabled minus disabled",
	}
	result.sources[#result.sources + 1] = "PoB:GlobalCache.cachedData.MAIN[*].Env.player.output"
	return result
end

return { get_mechanism_snapshot = get_mechanism_snapshot, get_skill_set = get_skill_set, get_skill_chain = get_skill_chain, compare_support_effect = compare_support_effect, get_socket_order = get_socket_order, explain_damage_change = explain_damage_change }
