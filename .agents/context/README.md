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

Current state (as of 2026-05-31)
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

- **$HOME path in `.mcp.json`** — works correctly for the persistent Playwright
  profile (`~/.playwright-profiles/substack`). No need for an absolute path.
- **Tag batch-click via `browser_evaluate`** — happy path for adding the 34 tags
  in `SUBSTACK_TAGS` in one shot. TRUST the return value; do NOT retry. The chip
  UI does not re-render after rapid synchronous `.click()` calls, but tags ARE
  saved server-side. Confirmed across multiple sessions.
- **Do NOT press Escape after the tag batch** — it closes the entire Publish
  dialog. Click the dialog heading or a neutral DOM element to dismiss the
  dropdown without losing the publish dialog state.
- **The standardized tag set** lives in `src/dev_digest/utility/constants.py` as
  `SUBSTACK_TAGS` (34 tags). The same list goes on every post.

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
