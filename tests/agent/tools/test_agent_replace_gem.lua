package.path = "runtime/lua/?.lua;" .. package.path

local tools = dofile("src/Modules/AgentTool.lua")

local fireball = { id = "SkillGemFireball", name = "Fireball", grantedEffectId = "Fireball", grantedEffect = { name = "Fireball", support = false } }
local volley = { id = "SupportGreaterVolley", name = "Greater Volley", grantedEffectId = "GreaterVolley", grantedEffect = { name = "Greater Volley", support = true } }
local build = {
	buildId = "gem-fixture",
	snapshotRevision = "rev-1",
	data = { gems = { fireball, volley } },
	skillsTab = { socketGroupList = {
		{ gemList = {
			{ nameSpec = "Fireball", gemData = fireball, grantedEffect = fireball.grantedEffect, level = 20, quality = 20, enabled = true },
			{ nameSpec = "Greater Volley", gemData = volley, grantedEffect = volley.grantedEffect, level = 20, quality = 20, enabled = true },
		} },
		{ sourceItem = { name = "Doomed Crown" }, gemList = { { nameSpec = "Impending Doom", fromItem = true, level = 20, quality = 0 } } },
	} },
	calcsTab = { mainEnv = { player = { output = { TotalDPS = 100, Duration = 4, ProjectileCount = 3, Chain = 1 } } } },
}
function build.calcsTab:BuildOutput()
	local active = build.skillsTab.socketGroupList[1].gemList[1]
	self.mainEnv.player.output.TotalDPS = active.level * 5 + active.quality
	self.mainEnv.player.output.Duration = 4 + active.quality / 100
end

local result, err = tools.replace_gem(build, {
	socketGroup = 1, gemIndex = 1, gemIdentity = "Fireball", level = 21, quality = 23,
	alternateQuality = "Anomalous", enabled = true, expectedSnapshotRevision = "rev-1",
	idempotencyKey = "gem-1", fingerprint = "fireball-21-23-anomalous",
})
assert(result and not err, err and err.message or "replace_gem should succeed")
assert(result.facts.after.gems[1].level == 21)
assert(result.facts.after.gems[1].quality == 23)
assert(result.facts.after.gems[1].enabled == true)
assert(result.facts.delta.TotalDPS == 28)
assert(result.side_effect == "in_memory" and result.facts.saved == false)
assert(build.skillsTab.socketGroupList[1].gemList[1].qualityId == "Anomalous")

local stale, staleErr = tools.replace_gem(build, {
	socketGroup = 1, gemIndex = 1, gemIdentity = "Fireball", level = 22, quality = 23,
	expectedSnapshotRevision = "rev-1", idempotencyKey = "gem-stale", fingerprint = "stale",
})
assert(not stale and staleErr.code == "SNAPSHOT_REVISION_CONFLICT")

local itemResult, itemErr = tools.replace_gem(build, {
	socketGroup = 2, gemIndex = 1, gemIdentity = "Fireball", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-item", fingerprint = "item",
})
assert(not itemResult and itemErr.code == "ITEM_GRANTED_SKILL")

local mismatch, mismatchErr = tools.replace_gem(build, {
	socketGroup = 1, gemIndex = 1, gemIdentity = "Greater Volley", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-support-mismatch", fingerprint = "mismatch",
})
assert(not mismatch and mismatchErr.code == "GEM_LINK_INCOMPATIBLE")

local invalidArgs, invalidArgsErr = tools.replace_gem(build, "not-a-table")
assert(not invalidArgs and invalidArgsErr.code == "INPUT_INVALID" and invalidArgsErr.recovery_class == "REPAIR_INPUT" and invalidArgsErr.stage == "gem_validation" and invalidArgsErr.next_action == "repair_input")

local invalidGroup, invalidGroupErr = tools.replace_gem(build, {
	socketGroup = 1.5, gemIdentity = "Fireball", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-invalid-group", fingerprint = "invalid-group",
})
assert(not invalidGroup and invalidGroupErr.code == "INPUT_INVALID" and invalidGroupErr.stage == "gem_validation")

local missingGroup, missingGroupErr = tools.replace_gem(build, {
	socketGroup = 99, gemIdentity = "Fireball", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-missing-group", fingerprint = "missing-group",
})
assert(not missingGroup and missingGroupErr.code == "INPUT_INVALID" and missingGroupErr.recovery_class == "REPAIR_INPUT")

local parsedMismatch, parsedMismatchErr = tools.replace_gem(build, {
	socketGroup = 1, gemIndex = 1, gemIdentity = "Arc", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-mismatch", fingerprint = "mismatch-input",
})
assert(not parsedMismatch and parsedMismatchErr.code == "INPUT_INVALID" and parsedMismatchErr.stage == "gem_validation" and parsedMismatchErr.next_action == "repair_input")

local unknown, unknownErr = tools.replace_gem(build, {
	socketGroup = 1, gemIndex = 1, gemIdentity = "Definitely Not A PoE Gem", level = 20, quality = 0,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "gem-unknown", fingerprint = "unknown-input",
})
assert(not unknown and unknownErr.code == "USER_CONTEXT_MISSING" and unknownErr.recovery_class == "ASK_USER" and unknownErr.stage == "gem_alias" and unknownErr.next_action == "ask_user" and unknownErr.retryable == false)

print("test_agent_replace_gem: ok")
