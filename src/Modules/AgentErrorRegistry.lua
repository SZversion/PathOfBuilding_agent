-- Stable parent references shared by the in-process PoB boundary.
local parent = {
	USER_CONTEXT_MISSING = "MISSING_CONTEXT",
	AMBIGUOUS_ALIAS = "AMBIGUOUS_CONTEXT",
	SNAPSHOT_REVISION_CONFLICT = "CONFLICTING_CONTEXT",
	CONTENT_CONFLICT = "CONFLICTING_CONTEXT",
	GROUNDING_CONFLICT = "CONFLICTING_CONTEXT",
	UNSUPPORTED_REQUEST = "UNSUPPORTED_REQUEST",
}

return { parent = function(code) return parent[code] or code end }
