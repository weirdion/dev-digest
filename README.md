# dev-digest

A minimal, maintainable Python CLI using the `src/` layout, built with `uv_build`, and linted/formatted with `ruff`.

## Recommended Structure

- `pyproject.toml` — project metadata, build system, and console script entry point
- `src/dev_digest/` — package with CLI code

## Development

- Install dependencies (including dev tools):
  - `uv sync --group dev`
- Run the CLI:
  - `uv run dev-digest`
- Lint and format with ruff:
  - Check: `uv run ruff check .`
  - Format: `uv run ruff format .`
- Build artifacts (sdist/wheel):
  - `uv build`

## Notes:
- Uses the `src/` layout to avoid import path ambiguity during development.
- `uv_build` is configured under `[build-system]` for packaging.
- `ruff` is configured in `pyproject.toml` under `[tool.ruff]`.
