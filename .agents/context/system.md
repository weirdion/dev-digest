System Overview
===============

Codebase
--------
- **CLI entry**: `uv run dev-digest <subcommand>` → `src/dev_digest/cli.py`.
  - `run` — generate the weekly digest.
  - `publish` — convert a curated markdown file to Substack-ready HTML.
- **Deterministic pipeline**: `src/dev_digest/handler/DeterministicDigest.py`.
  Ranks, dedupes, sections, renders markdown + diagnostics.
- **Feed ingestion**: `src/dev_digest/handler/FeedHandler.py`. Normalizes AWS
  sources, sanitizes HTML, respects lookback windows, caches feeds under
  `out/<date>/tmp` for re-runs without re-fetching.
- **AI-assisted path** (optional): `src/dev_digest/handler/StrandsAgent.py`.
  Uses Strands Agents for short summaries / impact scores while keeping
  formatting deterministic. Logs token usage.
- **Markdown → HTML converter**: `src/dev_digest/utility/substack_html.py` (drives the
  `publish` CLI subcommand). Title becomes hyperlink; "Read: URL" dropped from
  bullets; footer link tags preserved.
- **Tests**: `tests/` mock `feedparser` and cover scoring, section routing,
  diagnostics, and CLI smoke runs. Run `uv run pytest` before shipping behavioral
  changes (sandbox blocks it; user runs locally).

Configuration knobs (`src/dev_digest/utility/`)
-----------------------------------------------
- `constants.py` — feed window, per-section cap, top-picks count, model
  profiles, AWS region/keyword denylists, AI policy/finance penalty terms,
  `SUBSTACK_TAGS` for the publish step.
- `feeds.py` — RSS/Atom source list, per-feed normalization.
- `scoring.py` — heuristic scoring helpers and term tuples
  (`GOVERNMENT_TERMS`, `NEG_WEBINAR_TERMS`, `RA_STRONG_TERMS`, etc.).
- `sections.py` — section definitions with order, slug, host
  include/exclude rules (e.g. Infrastructure has `exclude_hosts=("realpython.com",)`).

Output artifacts (`out/YYYY-MM-DD/`)
------------------------------------
- `dev_digest_newsletter_yyyy_mm_dd.md` — primary markdown digest.
- `dev_digest_newsletter_yyyy_mm_dd.html` — Substack-ready HTML (from `publish` cmd).
- `debug_ranking.json` / `.csv` / `.md` — diagnostics for ranking decisions.
- `tmp/` — cached feed payloads (re-used unless `--overwrite`).

CLI flags worth remembering
---------------------------
- `--no-ai` / `--ai` — deterministic pipeline vs Strands Agents.
- `--days N` — lookback window (default 7).
- `-wf` — include the markdown footer.
- `-d` — enable debug diagnostics.
- `--overwrite` — clear today's output folder before running.

Environment & sandbox
---------------------
- Workspace-write sandbox; restricted network for tooling.
- `uv run pytest` does NOT run in the sandbox — user runs the test suite locally
  when validating scoring/section changes.
- When running shell commands, prefer `rg` for searches and always set the
  correct working directory.

Heuristic post-processing (in `DeterministicDigest.py`)
-------------------------------------------------------
Several filters run after section assignment and before per-section capping:

- **`ml_ai_policy_filter`** — Drops political/policy items from known policy
  hosts (`AI_POLICY_HOSTS`: `arstechnica.com`, `openai.com`) when their title +
  summary matches a term in `AI_POLICY_TERMS` via word-boundary regex. Only
  processes `sections_map["ml_ai"]`.
- **`event_promo_filter`** — Global filter across all sections; drops CNCF /
  KubeCon event promos (terms: `"co-located event"`, `"summer of code"`,
  `"kcds"`, `"kubecon"`).
- **`security_required_terms`** — Items in the Security section without an
  incident marker (CVE, exploit, attack, malware, breach, patch, etc.) get
  reassigned back to `aws_cloud`.
- **`aws_ra_overflow_to_interesting`** — RA items with practical/performance
  signals that exceed per-severity caps get added to the featured candidate pool
  (still blocked by `is_release_like()` for Interesting Reads).

Important freshness behavior
----------------------------
In `--no-ai` runs, `model_score` = freshness (0–100 based on recency). The
combined ranking is `0.7 * heuristic + 0.3 * freshness`. A 2-day-old item
scores ~27 from freshness alone even with heuristic = 0. **Score penalties
alone are insufficient to drop fresh items** — use hard post-processing filters
(like `ml_ai_policy_filter`) for must-drop classes.
