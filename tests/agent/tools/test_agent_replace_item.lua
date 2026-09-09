local previousNew = new
package.path = "runtime/lua/?.lua;" .. package.path
new = function(_, raw)
	return { raw = raw, name = "Storm Grip, Vaal Regalia", baseName = "Vaal Regalia", rarity = "RARE", base = { type = "Body Armour" } }
end
local tools = dofile("src/Modules/AgentTool.lua")
local build = {
	buildId = "replace-fixture", snapshotRevision = "rev-1",
	itemsTab = { activeItemSet = { ["Body Armour"] = { selItemId = 1 }, ["Helmet"] = { selItemId = 0 } }, items = { [1] = { id = 1, name = "Old Armour", baseName = "Vaal Regalia" } }, slots = { ["Body Armour"] = {}, ["Helmet"] = {} }, PopulateSlots = function() end },
	calcsTab = { mainEnv = { player = { output = { TotalDPS = 100 } } } },
}
build.calcsTab.BuildOutput = function() build.calcsTab.mainEnv.player.output.TotalDPS = build.itemsTab.items[build.itemsTab.activeItemSet["Body Armour"].selItemId].name == "Storm Grip, Vaal Regalia" and 125 or 100 end
local result = assert(tools.replace_item(build, { slot = "Body Armour", itemIdentity = "Vaal Regalia", itemText = "Storm Grip, Vaal Regalia", expectedSnapshotRevision = "rev-1", idempotencyKey = "replace-1", fingerprint = "body:storm-grip" }))
assert(result.side_effect == "in_memory" and result.facts.saved == false and result.facts.delta.TotalDPS == 25)
assert(build.itemsTab.items[build.itemsTab.activeItemSet["Body Armour"].selItemId].name == "Storm Grip, Vaal Regalia")
local stale, err = tools.replace_item(build, { slot = "Body Armour", itemIdentity = "Vaal Regalia", itemText = "Storm Grip, Vaal Regalia", expectedSnapshotRevision = "rev-1", idempotencyKey = "replace-2", fingerprint = "body:other" })
assert(stale == nil and err.code == "SNAPSHOT_REVISION_CONFLICT")
local unknown, unknownErr = tools.replace_item(build, { slot = "Body Armour", itemIdentity = "Unknown Item", itemText = "Storm Grip, Vaal Regalia", expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "replace-3", fingerprint = "body:unknown" })
assert(unknown == nil and unknownErr.code == "USER_CONTEXT_MISSING" and build.itemsTab.items[build.itemsTab.activeItemSet["Body Armour"].selItemId].name == "Storm Grip, Vaal Regalia")
local mismatch, mismatchErr = tools.replace_item(build, { slot = "Helmet", itemIdentity = "Vaal Regalia", itemText = "Storm Grip, Vaal Regalia", expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "replace-4", fingerprint = "helmet:wrong" })
assert(mismatch == nil and mismatchErr.code == "INPUT_INVALID")
new = previousNew
print("agent replace item self-check passed")



