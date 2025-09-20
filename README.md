# dev-digest

Newsletter generator (optionally AI-powered) that fetches RSS/Atom feeds, discovers additional content via agentic search,
deduplicates articles, and outputs a curated weekly digest in Markdown.

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

# Generate newsletter for last 7 days (AI summarization; default model: sonnet-3.7)
uv run dev-digest run --days 7

# Use Sonnet 4 profile
uv run dev-digest run --days 7 --model-key sonnet-4

# Deterministic (no AI) pipeline
uv run dev-digest run --days 7 --no-ai

# Append a footer line
uv run dev-digest run --days 7 --no-ai --debug --with-footer

# Output will be in out/YYYY-MM-DD/
# Subsequent runs on the same day reuse that folder by default.
# Use --overwrite to clear it first.

# Help menu
uv run dev-digest run --help

Usage: dev-digest run [OPTIONS]

  Run dev-digest

Options:
  -d, --debug                     Enable debug mode
  --days INTEGER                  Number of days to look back for items.
                                  [default: 7]
  --model-key [sonnet-3.7|sonnet-4]
                                  Model profile to use for summarization and
                                  cost.  [default: sonnet-3.7]
  --ai / --no-ai                  Use deterministic pipeline (or AI)
                                  [default: no-ai]
  -wf, --with-footer              Include footer
  --overwrite                     If today's output folder exists, clear it
                                  before running.  [default: False]
  --help                          Show this message and exit.
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

## Cost Estimation and Diagnostics

Cost is estimated automatically from built‑in pricing profiles in `MODEL_PROFILES` (see `src/dev_digest/utility/constants.py`). Choose the profile via `--model-key`.

When you run with `--debug`:
- AI path: writes `tmp/metrics.json` with token counts and estimated cost, and logs a summary line.
- Deterministic path: writes ranking diagnostics (`debug_ranking.json`, `debug_ranking.csv`, `debug_ranking.md`) in the run folder.

## Architecture

- **Strands Agents**: AI workflow orchestration with custom tools
- **Security-First**: Input validation and sanitization throughout
- **Minimal Dependencies**: Only essential packages for maintainability
- **Test Coverage**: Unit tests for complex business logic
