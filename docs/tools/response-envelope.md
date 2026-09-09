# Tool Response Envelope

Every Tool and evidence-bearing response uses the same logical envelope:

```json
{
  "status": "calculated",
  "snapshotRevision": "rev-123",
  "side_effect": "none",
  "operator_message": null,
  "facts": {},
  "conditions": [],
  "trace": [],
  "sources": [],
  "version": {
    "gamePatch": "3.29",
    "pobVersion": null,
    "dataRevision": null
  },
  "evidenceGraph": {
    "nodes": [],
    "stages": [],
    "sourceEdges": []
  },
  "uncertainty": {
    "level": "none",
    "reasons": [],
    "missingEvidence": [],
    "temporaryEvidence": false
  }
}
```

`snapshotRevision` identifies the authoritative PoB state used by the result and is repeated on trace entries. `side_effect` is one of `none`, `in_memory`, `persisted`, or `unknown`; read-only Tools always return `none`. `operator_message` is a nullable maintainer-facing message and is never used as the user answer.

`gamePatch`, `pobVersion`, and `dataRevision` may be `null` or `not_applicable` when not relevant. `status` may be `calculated`, `partial`, `unavailable`, `not_simulated`, `conflict`, or `rejected`.

- `facts`: final values, metadata, and conditions
- `trace`: ordered calculation operations and intermediate values
- `sources`: PoB paths, rule IDs, or external references
- `version`: applicable version context
- `evidenceGraph`: nodes, mathematical stages/order, and causal source edges
- `uncertainty`: missing, conflicting, external, inferred, or version-warning evidence

The response must distinguish PoB-calculated values, local rule evidence, `temporary_evidence`, and model explanation. `conflict` never becomes one merged value. `not_simulated` never becomes a claim that PoB simulated the behavior.
