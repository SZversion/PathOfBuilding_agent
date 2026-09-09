local mutation = dofile("src/Modules/AgentMutation.lua")
mutation.clear()
local calls, recalculations = 0, 0
local build = { snapshotRevision = "rev-1", value = 10, calcsTab = { BuildOutput = function() recalculations = recalculations + 1 end } }
local request = { expectedSnapshotRevision = "rev-1", idempotencyKey = "k1", fingerprint = "item:a" }
local committed = assert(mutation.run(build, request, function(state) calls = calls + 1; state.value = 20 end, function(state) return state.value == 20 end))
assert(committed.status == "committed" and committed.side_effect == "in_memory" and committed.saved == false)
assert(build.value == 20 and build.snapshotRevision ~= "rev-1" and calls == 1 and recalculations == 1)
local duplicate = assert(mutation.run(build, request, function() calls = calls + 1 end))
assert(duplicate == committed and calls == 1)
local otherBuild = { buildId = "other-build", snapshotRevision = build.snapshotRevision, value = 10 }
local other = assert(mutation.run(otherBuild, { expectedSnapshotRevision = otherBuild.snapshotRevision, idempotencyKey = "k1", fingerprint = "item:a" }, function(state) state.value = 30 end))
assert(other.status == "committed" and otherBuild.value == 30)
local stale, staleErr = mutation.run(build, { expectedSnapshotRevision = "rev-1", idempotencyKey = "k2", fingerprint = "item:b" }, function(state) state.value = 99 end)
assert(stale == nil and staleErr.code == "SNAPSHOT_REVISION_CONFLICT" and build.value == 20)
local failed, failedErr = mutation.run(build, { expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "k3", fingerprint = "item:c" }, function(state) state.value = 99 end, function() return false end)
assert(failed == nil and failedErr.code == "MUTATION_FAILED" and build.value == 20)
local timeout, timeoutErr = mutation.run(build, { expectedSnapshotRevision = build.snapshotRevision, idempotencyKey = "k4", fingerprint = "item:d" }, function() error("timeout") end)
assert(timeout == nil and timeoutErr.code == "MUTATION_FAILED" and build.value == 20)
print("agent mutation transaction self-check passed")
