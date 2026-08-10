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

local function calculatedOutput(player, skill)
	local output = skill and skill.output or { }
	if next(output) == nil and player and player.mainSkill and player.mainSkill.actor then
		output = player.mainSkill.actor.output or output
	end
	return output
end

local function finalTrace(skill, stat, value)
	local result = { }
	for _, entry in ipairs((skill and skill.breakdown and skill.breakdown[stat]) or { }) do result[#result + 1] = entry end
	result[#result + 1] = { operation = "FINAL_OUTPUT", stat = stat, value = value, source = "PoB calculated output" }
	return result
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

local function gemFacts(skill)
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
	local output = calculatedOutput(player, skill)
	return envelope(build, {
		skillIndex = skillIndex,
		name = effect and effect.name,
		skillPart = skill.skillPartName,
		gems = gemFacts(skill),
		trigger = skill.infoTrigger,
		output = scalarTable(output),
	}, { "PoB:CalcsTab.mainEnv.player.activeSkillList" })
end

local function skillName(skill)
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return effect and effect.name or skill.name or skill.baseName
end

local function modifierTrace(skill, stat)
	local trace = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
	return trace.collectCombined(skill, stat, "BASE"), trace.collectCombined(skill, stat, "MORE")
end

local function get_skill_dps(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local value = output.TotalDPS
	if type(value) ~= "number" then return nil, "TotalDPS is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), value = value }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output.TotalDPS" }, (skill.breakdown and skill.breakdown.TotalDPS) or { })
end

local function get_highest_dps_skill(build)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local bestIndex, bestValue
	for index, skill in ipairs(player.activeSkillList or { }) do
		local value = calculatedOutput(player, skill).TotalDPS
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

local function get_projectile_behavior(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local values = { }
	for _, key in ipairs({ "ProjectileCount", "PierceCount", "Chain", "ChainMax", "ChainRemaining", "ForkCount", "SplitCount" }) do
		if type(output[key]) == "number" then values[key] = output[key] end
	end
	if next(values) == nil then return nil, "projectile behavior is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output" }, finalTrace(skill, "ProjectileBehavior", values))
end

local function get_trigger_sequence(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local infoTrigger = type(skill.infoTrigger) == "string" and skill.infoTrigger or nil
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), trigger = infoTrigger, infoTrigger = infoTrigger, triggered = skill.triggered == true }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.infoTrigger" })
end

local function get_curse_application_order(build, skillSetSelector, skillNameValue)
	local mechanism = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	local order, err = mechanism.get_socket_order(build, skillSetSelector, skillNameValue)
	if not order then return nil, err end
	return envelope(build, { status = "not_simulated", basis = "socket order only", gems = order.facts.gems }, order.sources, { "Curse application timing is not simulated" })
end

local function get_ailment_effect(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local values = { }
	for key, value in pairs(calculatedOutput(player, skill)) do
		if type(key) == "string" and type(value) == "number" and (key:lower():find("chance", 1, true) or key:lower():find("ailment", 1, true)) then values[key] = value end
	end
	if next(values) == nil then return nil, "ailment effect is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output" }, finalTrace(skill, "Ailment", values))
end

local function get_damage_breakdown(build, skillIndex)
	return get_skill_breakdown(build, skillIndex)
end

local function get_conversion_chain(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local tableValue = skill.conversionTable
	if type(tableValue) ~= "table" then return nil, "conversionTable is unavailable for this skill" end
	local values = { }
	for damageType, entry in pairs(tableValue) do
		if type(entry) == "table" then
			local item = { conversion = { }, gain = { }, mult = entry.mult }
			for key, value in pairs(entry.conversion or { }) do if type(value) == "number" then item.conversion[key] = value end end
			for key, value in pairs(entry.gain or { }) do if type(value) == "number" then item.gain[key] = value end end
			values[damageType] = item
		end
	end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, status = "calculated", values = values }, { "PoB:Modules/CalcOffence.lua:1879-1926" })
end

local function get_effective_resistance(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local values = { }
	for _, key in ipairs({ "PhysicalEffMult", "FireEffMult", "ColdEffMult", "LightningEffMult", "ChaosEffMult" }) do
		if type(calculatedOutput(player, skill)[key]) == "number" then values[key] = calculatedOutput(player, skill)[key] end
	end
	if next(values) == nil then return nil, "effective resistance multipliers are unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), values = values }, { "PoB:Modules/CalcOffence.lua:3515-3522" }, finalTrace(skill, "EffectiveResistance", values))
end

local function get_support_links(build, skillSetSelector, skillNameValue)
	local mechanism = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	return mechanism.get_socket_order(build, skillSetSelector, skillNameValue)
end

local function resolve_skill_context(build, skillSetSelector, skillNameValue)
	local context = (LoadModule and LoadModule("Modules/AgentContext")) or dofile("src/Modules/AgentContext.lua")
	local result, err = context.find_skill(build, skillSetSelector, skillNameValue)
	if not result then return nil, err end
	return envelope(build, result, { "PoB:Modules/AgentContext.lua:find_skill" })
end

local function compare_build_states(buildA, buildB, skillIndexA, skillIndexB)
	local playerA, errA = playerFor(buildA)
	if not playerA then return nil, errA end
	local playerB, errB = playerFor(buildB)
	if not playerB then return nil, errB end
	local skillA, skillErrA = skillFor(playerA, skillIndexA)
	if not skillA then return nil, skillErrA end
	local skillB, skillErrB = skillFor(playerB, skillIndexB)
	if not skillB then return nil, skillErrB end
	local before, after, delta = scalarTable(calculatedOutput(playerA, skillA)), scalarTable(calculatedOutput(playerB, skillB)), { }
	for key, value in pairs(before) do
		if type(value) == "number" and type(after[key]) == "number" then delta[key] = after[key] - value end
	end
	return envelope(buildB, { before = before, after = after, delta = delta }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output" })
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
	local output = calculatedOutput(player, skill)
	local value = output.ProjectileCount
	if value == nil then
		return nil, "ProjectileCount is unavailable for this skill"
	end
	local baseTerms, moreTerms = modifierTrace(skill, "ProjectileCount")
	return envelope(build, { skillIndex = skillIndex, value = value }, { "PoB:Modules/CalcOffence.lua:1054-1062" }, {
		{ operation = "PROJECTILE_COUNT", value = value, inputs = { base = baseTerms, more = moreTerms }, formula = "floor(SUM_BASE(ProjectileCount) * PRODUCT_MORE(ProjectileCount))" },
	})
end

local function get_elemental_penetration(build, skillIndex)
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill).ElementalPenetration or { }
	local values = { }
	for _, damageType in ipairs({ "Fire", "Cold", "Lightning" }) do
		if output[damageType] ~= nil then values[damageType] = output[damageType] end
	end
	if next(values) == nil then return nil, "ElementalPenetration is unavailable for this skill" end
	local effect = skill.activeEffect and skill.activeEffect.grantedEffect
	return envelope(build, { skillIndex = skillIndex, name = effect and effect.name, values = values }, { "PoB:Modules/CalcOffence.lua:3466-3475" }, finalTrace(skill, "ElementalPenetration", values))
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
	return envelope(build, { value = value }, { "PoB:Modules/CalcPerform.lua:3156-3158" }, finalTrace(player, "EnemyCurseLimit", value))
end

local function get_duration(build, skillIndex, durationType)
	if type(durationType) ~= "string" or durationType == "" then return nil, "durationType is required" end
	local player, err = playerFor(build)
	if not player then return nil, err end
	local skill, skillErr = skillFor(player, skillIndex)
	if not skill then return nil, skillErr end
	local output = calculatedOutput(player, skill)
	local outputKey = ({ skill_effect = "Duration", secondary = "DurationSecondary", tertiary = "DurationTertiary", aura = "AuraDuration", reserve = "ReserveDuration", totem = "TotemDuration" })[durationType]
	if outputKey and type(output[outputKey]) == "number" then
		local trace = { }
		local breakdown = skill.breakdown or (skill.actor and skill.actor.breakdown) or { }
		for _, entry in ipairs(breakdown[outputKey] or breakdown.DurationMod or { }) do trace[#trace + 1] = entry end
		local traceTool = (LoadModule and LoadModule("Modules/AgentTrace")) or dofile("src/Modules/AgentTrace.lua")
		local modifierTerms = traceTool.collectCombined(skill, "Duration")
		for _, term in ipairs(modifierTerms) do
			trace[#trace + 1] = {
				operation = "DURATION_MODIFIER_SOURCE",
				stat = term.stat,
				modifierType = term.operation,
				value = term.value,
				source = term.source,
				scope = term.scope,
			}
		end
		trace[#trace + 1] = { operation = "FINAL_DURATION", stat = outputKey, value = output[outputKey], modifier = output.DurationMod, source = "PoB output", gems = gemFacts(skill) }
		return envelope(build, { skillIndex = skillIndex, name = skillName(skill), durationType = durationType, value = output[outputKey], modifier = output.DurationMod, unit = "seconds", status = "calculated", gems = gemFacts(skill), modifierTerms = modifierTerms }, { "PoB:CalcsTab.mainEnv.player.activeSkillList.output." .. outputKey, "PoB:CalcsTab.mainEnv.player.activeSkillList.breakdown." .. outputKey }, trace)
	end
	if durationType ~= "trauma" then return nil, "duration is unavailable for this skill and durationType" end
	if not skill.skillModList or not skill.skillCfg then return nil, "TraumaDuration modifiers are unavailable" end
	local baseTerms = (LoadModule and LoadModule("Modules/AgentTrace") or dofile("src/Modules/AgentTrace.lua")).collectCombined(skill, "TraumaDuration", "BASE")
	local durationTerms = (LoadModule and LoadModule("Modules/AgentTrace") or dofile("src/Modules/AgentTrace.lua")).collectCombined(skill, "Duration")
	local base = 0
	for _, term in ipairs(baseTerms) do base = base + (term.value or 0) end
	local inc, red, more = 0, 0, 1
	for _, term in ipairs(durationTerms) do
		if term.operation == "INC" then inc = inc + term.value elseif term.operation == "RED" then red = red + term.value elseif term.operation == "MORE" then more = more * (1 + term.value / 100) end
	end
	local multiplier = more * (1 + inc / 100) * (1 + red / 100)
	local value = base * multiplier
	if base <= 0 then return nil, "TraumaDuration is unavailable for this skill" end
	return envelope(build, { skillIndex = skillIndex, name = skillName(skill), durationType = durationType, value = value, unit = "seconds", status = "calculated", gems = gemFacts(skill) }, { "PoB:Modules/CalcOffence.lua:2252" }, {
		{ operation = "SUM_BASE", stat = "TraumaDuration", value = base, inputs = baseTerms },
		{ operation = "DURATION_MODIFIER", stat = "Duration", value = multiplier, inputs = durationTerms },
		{ operation = "FINAL_DURATION", value = value, formula = "SUM_BASE(TraumaDuration) * calcLib.mod(Duration)" },
	})
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

local function mechanism(name, build, skillSetSelector, skillNameValue, supportName)
	local module = (LoadModule and LoadModule("Modules/AgentMechanismTool")) or dofile("src/Modules/AgentMechanismTool.lua")
	return module[name](build, skillSetSelector, skillNameValue, supportName)
end

local function get_skill_chain(build, skillSetSelector, skillNameValue)
	return mechanism("get_skill_chain", build, skillSetSelector, skillNameValue)
end

local function get_socket_order(build, skillSetSelector, skillNameValue)
	return mechanism("get_socket_order", build, skillSetSelector, skillNameValue)
end

local function compare_support_effect(build, skillSetSelector, skillNameValue, supportName)
	return mechanism("compare_support_effect", build, skillSetSelector, skillNameValue, supportName)
end

local function explain_damage_change(build, skillSetSelector, skillNameValue, supportName)
	return mechanism("explain_damage_change", build, skillSetSelector, skillNameValue, supportName)
end

return {
	get_character_stats = get_character_stats,
	get_skill_stats = get_skill_stats,
	get_skill_dps = get_skill_dps,
	get_highest_dps_skill = get_highest_dps_skill,
	get_skill_breakdown = get_skill_breakdown,
	get_item_modifiers = get_item_modifiers,
	get_projectile_behavior = get_projectile_behavior,
	get_trigger_sequence = get_trigger_sequence,
	get_curse_application_order = get_curse_application_order,
	get_ailment_effect = get_ailment_effect,
	get_damage_breakdown = get_damage_breakdown,
	get_conversion_chain = get_conversion_chain,
	get_effective_resistance = get_effective_resistance,
	get_support_links = get_support_links,
	get_skill_chain = get_skill_chain,
	get_socket_order = get_socket_order,
	compare_support_effect = compare_support_effect,
	explain_damage_change = explain_damage_change,
	resolve_skill_context = resolve_skill_context,
	compare_build_states = compare_build_states,
	get_projectile_count = get_projectile_count,
	get_elemental_penetration = get_elemental_penetration,
	get_curse_limit = get_curse_limit,
	get_duration = get_duration,
	explain_stat = explain_stat,
}
