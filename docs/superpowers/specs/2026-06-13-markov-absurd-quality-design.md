# Markov Absurd Quality Design

## Goal

Improve generated messages toward maximum absurd humor while avoiding unreadable garbage.

## Design

Generation will stop returning the first random Markov walk. Instead, it will generate multiple candidates, reject garbage, score the survivors, and return the highest-scoring result.

## Mode Behavior

- `normal`: more coherent, fewer context resets, lower candidate count.
- `absurd`: stronger topic jumps, candidate reranking favors rare words and surprising transitions.
- `chaos`: highest reset rate and candidate count, but still filtered so output is not just particles, repeated words, dangling prepositions, or punctuation noise.

## Garbage Filters

Reject candidates that are too short, contain too many service words, start or end with dangling words, repeat tokens excessively, or have too little lexical substance. Service words are not globally banned because they are part of chat style; they are limited when they dominate the output.

## Scoring

Score candidates by readable length, lexical variety, rare-word presence, topic-switch energy, and absurdity. Penalize repeated words, weak starts/ends, too many service words, and low-content text. This keeps the style chaotic but avoids useless output.

## Formatting

Keep existing punctuation cleanup and add final trimming for dangling endings. Do not add canned jokes yet; first make the base generator better.

## Testing

Add unit tests for garbage rejection, candidate scoring preferences, dangling-word trimming, and mode generation still respecting `max_words`.
