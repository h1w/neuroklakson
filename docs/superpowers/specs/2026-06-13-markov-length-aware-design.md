# Markov Length-Aware Generation Design

## Goal

Stop generating long text and cutting it after the fact. Generate candidates that already fit the desired format length and select the funniest coherent candidate inside the range.

## Presets

Limits are about 10% higher than the initial proposal:

- `/gm chaos`: min 5, target 10, max 15.
- `/gm absurd`: min 7, target 14, max 22.
- `/gm normal`: min 10, target 20, max 33.
- demotivator top: min 2, target 5, max 8.
- demotivator bottom: min 3, target 8, max 12.
- bugurt line: min 2, target 6, max 9.

## Approach

`generate_markov_text` will accept optional `min_words` and `target_words` in addition to `max_words`. Candidate generation will use the target length, reject candidates outside the range, and score candidates by closeness to target length. Final cleanup will not truncate a valid candidate except as a last safety guard.

## Bugurt

Bugurt should move toward generating separate lines instead of generating one long text and slicing it. The first implementation can keep the existing output format while using shorter line-shaped candidates.
