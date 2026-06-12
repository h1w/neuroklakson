# Markov Noise Filter Design

## Goal

Keep `chaos` absurd, but stop generated messages from containing obvious garbage such as random long Latin strings, prompt/instruction tokens, standalone `@` separators, and imported paste blocks.

## Approach

Filter bad source messages before building the Markov chain, reject noisy generated candidates, and score only normal Cyrillic rare words as funny. Latin words are allowed only when short/common (`vpn`, `ai`, `youtube`), not when they look like random keyboard spam.

## Source Balance

Generation should not let imported 2ch text dominate the chat's own voice. The repository will provide a weighted generation corpus: ordinary chat messages get the highest weight, forwarded messages medium weight, imports low weight.

## Rules

- Reject source messages and candidates with long Latin tokens.
- Reject source messages and candidates with too little Cyrillic content.
- Reject known prompt/noise tokens such as `instructions`.
- Remove standalone `@` separators during text cleanup.
- Give rare-word score only to Cyrillic content words.
- Keep existing command behavior unchanged.

## Testing

Add unit tests for source-message filtering, candidate rejection, scoring penalties, source weighting, and generation output that avoids Latin garbage.
