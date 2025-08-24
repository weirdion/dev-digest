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

# Generate newsletter for last 7 days
uv run dev-digest run --days 7

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

## Architecture

- **Strands Agents**: AI workflow orchestration with custom tools
- **Security-First**: Input validation and sanitization throughout
- **Minimal Dependencies**: Only essential packages for maintainability
- **Test Coverage**: Unit tests for complex business logic
