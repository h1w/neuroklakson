# Markov Noise Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent random Latin/import garbage from appearing in Markov output while preserving absurd chaos.

**Architecture:** Keep noise detection in `markchain.py`, generic formatting cleanup in `services/text.py`, and source weighting in `repositories/messages.py`. `GenerationService` will use the weighted generation corpus method.

**Tech Stack:** Python 3.11, pytest via `uv run pytest`, ruff via `uv run ruff`.

---

## Tasks

- [ ] Add failing tests for Latin noise rejection and source-message filtering in `tests/test_markchain.py`.
- [ ] Add failing tests for `@` cleanup and prompt token cleanup in `tests/test_text_services.py`.
- [ ] Add failing repository/service tests for weighted generation corpus.
- [ ] Implement noise helpers and apply them before chain construction and candidate selection.
- [ ] Implement weighted corpus retrieval and route `GenerationService` through it.
- [ ] Run `uv run pytest -q`, `uv run ruff check .`, and `docker compose config --quiet`.
- [ ] Rebuild/restart the bot container.
