-- In-process adapter: reads the currently displayed PoB build without XML reloads.
local type = type

local tools = (LoadModule and LoadModule("Modules/AgentTool")) or dofile("src/Modules/AgentTool.lua")
local snapshot = (LoadModule and LoadModule("Modules/AgentSnapshot")) or dofile("src/Modules/AgentSnapshot.lua")
local context = (LoadModule and LoadModule("Modules/AgentContext")) or dofile("src/Modules/AgentContext.lua")

local function currentBuild()
	if type(build) ~= "table" then return nil, "current PoB build is unavailable" end
	if not build.calcsTab or not build.calcsTab.mainEnv then return nil, "current PoB calculation state is unavailable" end
	return build
end

local function currentSkillIndex(current, name)
	if type(name) ~= "string" or name == "" then return nil, "skill name is required" end
	local canonical, aliasErr = context.resolve_skill_alias(name)
	if not canonical then return nil, aliasErr end
	local needle = context.normalize_name(canonical)
	local found
	for index, skill in ipairs(current.calcsTab.mainEnv.player and current.calcsTab.mainEnv.player.activeSkillList or { }) do
		local effect = skill.activeEffect and skill.activeEffect.grantedEffect
		local value = effect and effect.name or skill.name or skill.baseName
		if type(value) == "string" and context.normalize_name(value) == needle then
			if found then return nil, "skill name is ambiguous in current PoB state" end
			found = index
		end
	end
	return found, found and nil or "skill was not found in current PoB state"
end

local function dispatch(name, args)
	local current, err = currentBuild()
	if not current then return nil, err end
	args = args or { }
	if args.skillName and not args.skillIndex then
		args.skillIndex, err = currentSkillIndex(current, args.skillName)
		if not args.skillIndex then return nil, err end
	end
	local tool = tools[name]
	if name == "capture_snapshot" then return snapshot.capture(current) end
	if type(tool) ~= "function" then return nil, "unknown PoB tool: " .. tostring(name) end
	if name == "get_item_modifiers" then return tool(current, args.itemId) end
	if name == "get_duration" then return tool(current, args.skillIndex, args.durationType) end
	if name == "explain_stat" then return tool(current, args.stat, args.skillIndex) end
	if name == "get_curse_limit" or name == "get_character_stats" or name == "get_highest_dps_skill" then return tool(current) end
	if name == "resolve_skill_context" or name == "get_socket_order" or name == "get_skill_chain" or name == "get_support_links" or name == "get_curse_application_order" then
		return tool(current, args.skillSetSelector, args.skillName)
	end
	if name == "compare_support_effect" or name == "explain_damage_change" then
		return tool(current, args.skillSetSelector, args.skillName, args.supportName)
	end
	return tool(current, args.skillIndex)
end

return { dispatch = dispatch, currentBuild = currentBuild }
