# Path of Exile 1 Game Rules

This directory stores **Path of Exile 1 game-system rules**, separate from current character values calculated by PoB.

## Authoring rules

- Record `patchRange`, `sources`, and `verification` for every numeric rule.
- Do not copy current character values into this directory; query them through PoB tools.
- The agent must not use a `draft` rule as the sole evidence for a final answer.
- Add a versioned rule when a patch changes behavior instead of silently overwriting history.
- All canonical knowledge in this directory is written in English. Korean aliases belong in a separate alias file.

## Core categories

- `damage-type`: physical, fire, cold, lightning, chaos
- `delivery`: hit, damage over time
- `ailment`: damaging and non-damaging ailments
- `campaign`: campaign progression rules
- `curse`: curse limits and curse interactions

## PoB source validation

`validation-report.md` is the human-readable comparison report. `poe1-pob-validation.json` stores the corresponding per-rule status and source references (`confirmed`, `partial`, or `not_confirmed`).
