# Tool Response Envelope

Every Tool and evidence-bearing response uses the same logical envelope:

```json
{
  "status": "calculated",
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

`gamePatch`, `pobVersion`, and `dataRevision` may be `null` or `not_applicable` when not relevant. `status` may be `calculated`, `partial`, `unavailable`, `not_simulated`, `conflict`, or `rejected`.

- `facts`: final values, metadata, and conditions
- `trace`: ordered calculation operations and intermediate values
- `sources`: PoB paths, rule IDs, or external references
- `version`: applicable version context
- `evidenceGraph`: nodes, mathematical stages/order, and causal source edges
- `uncertainty`: missing, conflicting, external, inferred, or version-warning evidence

The response must distinguish PoB-calculated values, local rule evidence, `temporary_evidence`, and model explanation. `conflict` never becomes one merged value. `not_simulated` never becomes a claim that PoB simulated the behavior.
