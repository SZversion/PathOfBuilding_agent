# Agent Orchestration

## Flow

```text
user question
  → external AI JSON plan
  → Bridge validates plan and revision
  → local Tool / RAG / approved search execution
  → PoB recalculation and Evidence Graph
  → external AI final Korean answer
```

The external AI can plan multiple sequential operations, but one request is capped at eight Tool/search steps and duplicate identical calls are rejected. The Bridge executes each step and feeds its structured result into the next step.

## Search order

PoB output and breakdown are authoritative for current-build numbers. Local RAG supplies English canonical rules and aliases. If local evidence is insufficient, the Bridge may perform temporary searches against PoE Wiki, PoEDB, the official Path of Exile site, PoB Community GitHub, or Craft of Exile. External results are session-only and are not automatically promoted to the knowledge base.

## Answer contract

The final answer separates calculated values, applied effects, rules, sources, and uncertainty. It is Korean by default. Missing user context triggers a question; missing evidence after allowed search rejects a definitive answer.
