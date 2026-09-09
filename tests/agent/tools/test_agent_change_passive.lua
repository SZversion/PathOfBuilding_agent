package.path = "runtime/lua/?.lua;" .. package.path

local tools = dofile("src/Modules/AgentTool.lua")

local function makeNode(id, name, path, nodeType)
	return { id = id, name = name, type = nodeType or "Notable", path = path, alloc = false, linked = {}, depends = {} }
end
local first = makeNode(100, "Life Node", { true })
local disconnected = makeNode(200, "Disconnected", nil)
local socket = makeNode(300, "Cluster Socket", {}, "Socket")
local spec = { nodes = { [100] = first, [200] = disconnected, [300] = socket }, allocNodes = {}, jewels = {}, availablePoints = 2 }
function spec:CountAllocNodes()
	local used = 0
	for _, node in pairs(self.allocNodes) do if node.type ~= "ClassStart" then used = used + 1 end end
	return used, 0, 0, 0
end
function spec:AllocNode(node)
	node.alloc = true; self.allocNodes[node.id] = node
end
function spec:DeallocNode(node)
	node.alloc = false; self.allocNodes[node.id] = nil
end
function spec:BuildClusterJewelGraphs() self.clusterGraphsRebuilt = true end

local build = {
	buildId = "passive-fixture", snapshotRevision = "rev-1", spec = spec,
	itemsTab = { items = { [7] = { id = 7, type = "Jewel", baseName = "Large Cluster Jewel", clusterJewel = { size = "Large" } }, [1] = { id = 1, type = "Jewel", baseName = "Unnatural Instinct" } } },
	calcsTab = { mainEnv = { player = { output = { TotalDPS = 100, Life = 1000 } } } },
}
function build.calcsTab:BuildOutput()
	self.mainEnv.player.output.Life = 1000 + (build.spec.allocNodes[100] and 100 or 0)
	self.mainEnv.player.output.TotalDPS = 100 + (build.spec.jewels[300] and 25 or 0)
end

local allocated, allocErr = tools.change_passive(build, {
	operation = "allocate", nodeId = 100, expectedSnapshotRevision = "rev-1",
	idempotencyKey = "passive-allocate", fingerprint = "allocate-100",
})
assert(allocated and not allocErr and allocated.facts.after.tree.pointsUsed == 1)
assert(allocated.facts.delta.Life == 100 and allocated.side_effect == "in_memory")

local invalidPath, invalidPathErr = tools.change_passive(build, {
	operation = "allocate", nodeId = 200, expectedSnapshotRevision = build.snapshotRevision,
	idempotencyKey = "passive-path", fingerprint = "path-200",
})
assert(not invalidPath and invalidPathErr.code == "INVALID_PASSIVE_PATH")

local jewel, jewelErr = tools.change_passive(build, {
	operation = "replace_cluster_jewel", socketNodeId = 300, itemId = 7,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "cluster-1", fingerprint = "cluster-7",
})
assert(jewel and not jewelErr and build.spec.jewels[300] == 7 and spec.clusterGraphsRebuilt)
assert(jewel.facts.delta.TotalDPS == 25)

local ordinary, ordinaryErr = tools.change_passive(build, {
	operation = "replace_cluster_jewel", socketNodeId = 300, itemId = 1,
	expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "cluster-ordinary", fingerprint = "unnatural-instinct",
})
assert(not ordinary and ordinaryErr.code == "INPUT_INVALID" and ordinaryErr.recovery_class == "REPAIR_INPUT" and ordinaryErr.stage == "passive_validation")

local stale, staleErr = tools.change_passive(build, {
	operation = "deallocate", nodeId = 100, expectedSnapshotRevision = "rev-1",
	idempotencyKey = "passive-stale", fingerprint = "stale",
})
assert(not stale and staleErr.code == "SNAPSHOT_REVISION_CONFLICT")

print("test_agent_change_passive: ok")
