# Markov Morphology Polish Design

## Goal

Improve readability of generated Russian absurd text by correcting obvious noun endings after prepositions without replacing words or changing sentence structure.

## Scope

Use a conservative post-processing pass after Markov candidate selection. Only change the word immediately after selected prepositions when morphological analysis is confident.

## Rules

- `с`, `со` -> instrumental (`ablt`): `с чубайс` -> `с чубайсом`.
- `у`, `без`, `для`, `от` -> genitive (`gent`): `без кабачок` -> `без кабачка`.
- `к` -> dative (`datv`): `к автобус` -> `к автобусу`.
- Preserve all-uppercase words.
- Do not touch words with Latin characters, punctuation-only tokens, unknown parses, or ambiguous unsafe cases.
- Do not rewrite roots, word order, slang, profanity, or jokes.

## Non-Goals

- Full grammar correction.
- Agreement across whole sentence.
- Replacing words with synonyms.
- LLM-based rewriting.
