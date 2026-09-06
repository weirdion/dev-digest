Dev Digest Agent Context
========================

This directory is the durable state for the Dev Digest weekly publishing workflow.
A fresh agent in a new session should be able to read these files and resume the
work without losing institutional knowledge.

Files in this directory
-----------------------
- `system.md` — codebase architecture, CLI surface, configuration knobs (stable).
- `editorial.md` — editorial priorities, section routing rules, recurring patterns.
- `publish.md` — weekly publishing workflow + Substack Playwright runbook.
- `preferences-log.md` — chronological log of heuristic / editorial changes and
  hard-won learnings. Append-only.

Current state (as of 2026-09-06)
--------------------------------
The system is stable and the weekly cadence is:

1. **Generate** — `uv run dev-digest run -d --no-ai --days 7 -wf`
2. **Curate** — Walk the user through the markdown in `out/<date>/` section by
   section. Apply the rules in `editorial.md` before suggesting cuts/moves.
3. **Convert** — `uv run dev-digest publish out/<date>/<file>.md` writes
   `<same-dir>/<file>.html` for Substack.
4. **Publish** — Drive Substack via Playwright MCP using the runbook in
   `publish.md`. STOP at "Send to everyone now" — user verifies and publishes
   manually.

Recently verified (so a fresh session does not re-discover):

- **Playwright profile path in `.mcp.json`** — uses an absolute path
  (`/Users/ankitpatterson/.playwright-profiles/substack`) as of 2026-09-06.
  `$HOME` in argv does NOT expand (Playwright CLI treats it as a literal
  directory name), which silently created `./\$HOME/.playwright-profiles/` in
  the repo root for months. That stray dir is gitignored (`$HOME/`,
  `\$HOME/`) and being retired. Username in the path is not sensitive —
  already public in git commits.
- **New-post URL shortcut** (2026-06-21): `browser_navigate` to
  `https://weirdion.substack.com/publish/post?type=newsletter` creates a fresh
  draft and redirects to `/publish/post/<id>`. Preferred over the Create →
  Article dropdown which sometimes fails to render the menu item. See
  `publish.md` Step 2.
- **Substack DOM churn** (2026-07-26) — three selector changes now live in
  `publish.md`:
  - Continue button: `[data-testid="publish-button"]` (text-match no longer
    reliable).
  - Tags input: `[role="dialog"] input[role="combobox"]` (placeholder attribute
    was removed).
  - Tag click: per-tag filter loop. The dropdown no longer renders all 69+
    existing options after typing one tag — it filters aggressively. The batch
    scan returns 0. New approach iterates tags, sets combobox value via the
    native `HTMLInputElement.value` setter (so React sees the change), polls
    `[role="option"]`, clicks, then clears. Full loop in `publish.md` Step 7.
  - Cover image: click the first thumbnail in social preview; still needs an
    explicit click even though Substack picks one automatically.
- **Do NOT press Escape after the tag batch** — it closes the entire Publish
  dialog. Click the dialog heading or a neutral DOM element to dismiss the
  dropdown without losing the publish dialog state.
- **The standardized tag set** lives in `src/dev_digest/utility/constants.py` as
  `SUBSTACK_TAGS` (34 tags). The same list goes on every post.
- **AWS security bulletins date extraction** (2026-06-07): the feed's `pubDate`
  is the same for every entry, so the real date is parsed from the description
  body. If extraction fails, the bulletin is dropped. See
  `FeedHandler._extract_bulletin_date` and `preferences-log.md` entry for
  details.
- **Bad summaries in top picks** — some feeds (CNCF, Kubernetes Blog) produce
  descriptions like `"1."` or single-word content when the article's opening
  is a numbered list. Seen on `ingress-NGINX retirement` and `Kubernetes
  Dashboard → Headlamp`. If a top-pick item lands with a nonsense one-line
  summary, hand-write a better blurb before publishing.
- **Anthropic feed** — Anthropic does NOT publish RSS/Atom for news, research,
  or engineering (verified 2026-06-21: all common paths 404, no
  `<link rel="alternate">`, sitemap has no feed URLs). Options if the user
  asks: skip, use an RSS bridge like RSSHub, or write a custom scraper.
- **Runbook stability** (2026-08 → 2026-09-06): five consecutive weekly runs
  first-try clean with the current `publish.md` selectors. No new Substack DOM
  churn since the 2026-07-26 fixes. If a future run breaks, expect a testid or
  role attribute to have shifted again.

When starting a new conversation
--------------------------------
- If the user says "new run" or "new week", jump to `publish.md` Step 1.
- If the user asks about routing or a specific recurring pattern, check
  `editorial.md` first, then `preferences-log.md` for chronology.
- If the user reports unexpected behavior on Substack, check the "Known
  symptoms" section of `publish.md` before assuming a regression.

When making changes
-------------------
- Heuristic / scoring code changes go in `src/dev_digest/utility/` and
  `src/dev_digest/handler/DeterministicDigest.py`. Always document the change
  in `preferences-log.md` with date and intent.
- Editorial rule changes go in `editorial.md`. Cross-link to a
  `preferences-log.md` entry that explains the why.
- New Substack quirks go in `publish.md` under "Known symptoms" + a
  `preferences-log.md` entry.
