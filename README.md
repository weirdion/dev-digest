# dev-digest

AI-powered newsletter generator that fetches RSS/Atom feeds, discovers additional content via agentic search, deduplicates articles, and outputs a curated weekly digest in Markdown.

## Features

- **RSS/Atom Feed Processing**: Fetches from AWS, Kubernetes, Python, and backend engineering feeds
- **AI Content Discovery**: Uses Strands Agents to find additional relevant articles
- **Smart Deduplication**: Removes duplicate content by URL and title normalization
- **Security**: Input validation and sanitization for all external content
- **Markdown Output**: Generates newsletter ready for publishing

## Quick Start

```bash
# Install dependencies
uv sync --group dev

# Generate newsletter for last 7 days (default model: sonnet-3.7)
uv run dev-digest run --days 7

# Use Sonnet 4 profile
uv run dev-digest run --days 7 --model-key sonnet-4

# Output will be in out/YYYY-MM-DD_HH-MM-SS/digest.md
```

## Configuration

- **Feeds**: Edit `src/dev_digest/utility/feeds.py` to add/remove RSS feeds
- **Keywords**: Modify `KEYWORDS_TO_IGNORE` in `src/dev_digest/utility/constants.py`
- **Time Window**: Default 7 days, configurable via `--days` parameter

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Build package
uv build
```

## Cost Estimation

Cost is estimated automatically from built‑in pricing profiles in `MODEL_PROFILES` (see `src/dev_digest/utility/constants.py`). Choose the profile via `--model-key`. When you run with `--debug`, the tool writes `metrics.json` with token counts and estimated cost to the run’s `tmp/` folder and also logs a summary line.

## Architecture

- **Strands Agents**: AI workflow orchestration with custom tools
- **Security-First**: Input validation and sanitization throughout
- **Minimal Dependencies**: Only essential packages for maintainability
- **Test Coverage**: Unit tests for complex business logic
