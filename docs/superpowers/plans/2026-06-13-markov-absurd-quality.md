# Markov Absurd Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `/gm` output so it is more absurd and funny while rejecting unreadable garbage.

**Architecture:** Keep generation in `markchain.py`. Add candidate generation, garbage rejection, candidate scoring, and mode profiles around the existing Markov chain; keep text cleanup in `services/text.py` focused on formatting.

**Tech Stack:** Python 3.11, pytest via `uv run pytest`, ruff via `uv run ruff`.

---

## Files

- Modify: `markchain.py` for candidate scoring, filtering, mode profiles, and reranking.
- Modify: `services/text.py` for final dangling-word trimming.
- Modify: `tests/test_markchain.py` for scoring/filtering/generation behavior.
- Modify: `tests/test_text_services.py` for formatting cleanup.

## Task 1: Formatting Filters

- [ ] Add failing tests in `tests/test_text_services.py` for trimming dangling endings and excessive repeated service words.
- [ ] Run those tests with `uv run pytest tests/test_text_services.py -q` and confirm they fail.
- [ ] Implement focused cleanup in `services/text.py`.
- [ ] Re-run `uv run pytest tests/test_text_services.py -q` and confirm pass.

## Task 2: Candidate Scoring And Garbage Rejection

- [ ] Add failing tests in `tests/test_markchain.py` for `_is_garbage_candidate` and `_score_candidate`.
- [ ] Run targeted markchain tests and confirm they fail.
- [ ] Add service-word sets, garbage filter, word-frequency helper, and score function in `markchain.py`.
- [ ] Re-run targeted markchain tests and confirm pass.

## Task 3: Reranked Generation

- [ ] Add failing test that `generate_markov_text` can use multiple candidates and still respects `max_words` across modes.
- [ ] Implement `ModeProfile`, candidate count per mode, candidate walk helper, and best-candidate selection.
- [ ] Re-run `uv run pytest tests/test_markchain.py -q` and confirm pass.

## Task 4: Full Verification

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `docker compose config --quiet`.
- [ ] Inspect `git diff --stat`.

## Notes

- Do not add canned joke templates in this iteration.
- Keep command/API behavior unchanged.
- Do not commit unless explicitly requested.
