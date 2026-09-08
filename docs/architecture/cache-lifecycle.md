# Build-Scoped Cache Lifecycle

## Storage

Conversation history, normalized snapshots, change records, Evidence Graph references, and version metadata are cached on the user's PC per build. The external AI server is stateless and does not retain them permanently. API keys are never stored in the cache, prompt, snapshot, or logs.

## Lifecycle

1. Opening a conversation resolves the current canonical build ID and loads its cache.
2. The Bridge checks current game, PoB, and knowledge versions and attempts a fresh recalculation.
3. Successful recalculation replaces the cached calculated state atomically.
4. If update/recalculation fails but the major version matches, the cache may be reused with a warning.
5. A major-version mismatch prevents calculation and answer generation.
6. Each completed request stores only the new conversation and state revision.

## Save and Save As

Agent mutations affect the current in-memory PoB build immediately. The user must press PoB `Save` or `Save As` to persist them.

After a successful `Save As`, create a new canonical build ID and atomically copy the source build's conversation, snapshot, and version metadata cache. A failed copy creates no new cache. From that point, the two build caches update independently.
