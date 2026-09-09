-- Common in-memory mutation transaction. Concrete mutation Tools are layered on
-- top of this module; this module never writes PoB files or retries changes.
local type, pairs, tostring = type, pairs, tostring
local snapshot = (LoadModule and LoadModule("Modules/AgentSnapshot")) or dofile("src/Modules/AgentSnapshot.lua")
local seen = {}

local function clone(value, visited)
	if type(value) ~= "table" then return value end
	visited = visited or {}
	if visited[value] then return visited[value] end
	local result = {}
	visited[value] = result
	for key, child in pairs(value) do result[clone(key, visited)] = clone(child, visited) end
	return result
end

local function restore(target, source)
	for key in pairs(target) do target[key] = nil end
	for key, value in pairs(source) do target[key] = clone(value) end
end

local function errorResult(code, recovery, stage, message, extra)
	local result = { code = code, recovery_class = recovery, stage = stage, retryable = false,
		attempt = 1, max_attempts = 1, message = message, details = {},
		next_action = recovery == "REFRESH_CONTEXT" and "recapture_snapshot" or "reject_request",
		secondary_causes = {}, side_effect = "none", operator_message = nil }
	for key, value in pairs(extra or {}) do result[key] = value end
	return result
end

local function nextRevision(value, fingerprint)
	local number = tonumber(value)
	if number then return tostring(number + 1) end
	return tostring(value or "unknown") .. ":mutation:" .. tostring(fingerprint)
end

local function buildIdentity(build)
	local id = build and (build.buildId or build.id or build.snapshotId)
	return id ~= nil and tostring(id) or tostring(build)
end

local function run(build, request, mutate, validate)
	if type(build) ~= "table" or type(request) ~= "table" then
		return nil, errorResult("INPUT_INVALID", "REPAIR_INPUT", "mutation_validation", "build and request are required")
	end
	if type(mutate) ~= "function" then
		return nil, errorResult("INTERNAL_INVARIANT_VIOLATION", "FATAL_INTERNAL", "mutation_setup", "mutation callback is unavailable")
	end
	if type(request.idempotencyKey) ~= "string" or request.idempotencyKey == "" or type(request.fingerprint) ~= "string" or request.fingerprint == "" then
		return nil, errorResult("INPUT_INVALID", "REPAIR_INPUT", "mutation_validation", "idempotencyKey and fingerprint are required")
	end
	local seenKey = buildIdentity(build) .. "::" .. request.idempotencyKey
	local previous = seen[seenKey]
	if previous then
		if previous.fingerprint == request.fingerprint then return previous.result end
		return nil, errorResult("CONTENT_CONFLICT", "REPAIR_INPUT", "idempotency", "idempotency key was reused with a different fingerprint")
	end
	local beforeRevision = snapshot.snapshotRevision(build)
	local revisionOk, revisionErr = snapshot.assertRevision(build, request.expectedSnapshotRevision)
	if not revisionOk then return nil, revisionErr end
	local before = clone(build)
	local function rollback(code, recovery, stage, message)
		restore(build, before)
		return nil, errorResult(code, recovery, stage, message, { snapshotRevision = beforeRevision })
	end
	local changed, mutationErr = pcall(mutate, build)
	if not changed then return rollback("MUTATION_FAILED", "REJECT", "mutation_apply", tostring(mutationErr)) end
	if build.calcsTab and type(build.calcsTab.BuildOutput) == "function" then
		local calculated, calculationErr = pcall(build.calcsTab.BuildOutput, build.calcsTab)
		if not calculated then return rollback("POB_CALCULATION_ERROR", "FATAL_INTERNAL", "mutation_recalculate", tostring(calculationErr)) end
	end
	if validate then
		local valid, validationResult = pcall(validate, build)
		if not valid or validationResult == false then return rollback("MUTATION_FAILED", "REJECT", "mutation_validate", valid and "mutation validation failed" or tostring(validationResult)) end
	end
	build.snapshotRevision = nextRevision(beforeRevision, request.fingerprint)
	local result = { status = "committed", side_effect = "in_memory", operator_message = "Changed in memory; PoB Save/Save As was not invoked.",
		saved = false, idempotencyKey = request.idempotencyKey, fingerprint = request.fingerprint,
		beforeSnapshotRevision = beforeRevision, snapshotRevision = build.snapshotRevision }
	seen[seenKey] = { fingerprint = request.fingerprint, result = result }
	return result
end

return { run = run, clear = function() seen = {} end }
