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

Current state (as of 2026-11-22)
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
  (`/Users/ankitpatterson/.playwright-profiles/substack`). Verified working
  2026-09-20 and 2026-09-27 (session persisted, no re-login). The stray
  in-repo `./\$HOME/` dir has been deleted; the `.gitignore` entries
  (`$HOME/`, `\$HOME/`) stay as belt-and-suspenders. `$HOME` in argv does NOT
  expand — Playwright treats it as a literal directory name. Username in the
  path is not sensitive — already public in git commits.
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
- **Runbook stability** — the eight-run clean streak (2026-08 → 2026-09-27)
  ENDED on 2026-10-11 with two breakages: the section selector moved out of
  the editor into the Publish dialog as a native `<select>`, and the Playwright
  MCP arg shape changed from `ref` to `target`. Both are documented in
  `publish.md` (Step 7b, Phase 4 preamble). 2026-10-18 and 2026-10-26 both
  ran clean on all selectors including the new Step 7b — two runs, so the
  fixes hold, but still short of the old eight-run streak. Keep verifying the
  Publish dialog visually rather than trusting selector success.
- **Real Python tutorials are down-ranked in code** (2026-10-11, `201d0a7`) —
  `realpython_tutorial_penalty` in `scoring.py`. Lowers rank only; does not
  reduce item count. Manual trims still needed. See `editorial.md` for the
  rule and why a score floor was rejected. **The leaking title shapes change
  week to week** (3 of 8 caught on 2026-10-26; a different set leaked than on
  2026-10-18), so plan on manual RP cuts every week and do not add more
  regexes — see `editorial.md` for the host-level rule to switch to if it
  recurs.
- **Top picks now gate on `is_realpython_tutorial`** (2026-10-26) — the loop
  in `DeterministicDigest.py` previously used only an ad-hoc keyword list, and
  a "Part 3" Real Python tutorial led the 2026-10-26 digest. Covered by
  `test_tutorial_never_takes_a_top_pick_slot`.
- **Caps drop the minority source in a mixed-source section** — `aws_ra_cap`
  on 2026-10-18, `PER_SECTION_CAP` on Security on 2026-10-26 and again on
  2026-11-09 (every Ars Technica incident cut in favour of AWS bulletins all
  three times). Always check `debug_ranking.json` exclusions before accepting
  a capped section — still required weekly.
- **Two mechanisms added 2026-11-09** after the cap failed a third time:
  `PER_SOURCE_SECTION_SHARE = 5` bounds one source inside a section cap
  (`_apply_section_cap`), and incident scoring
  (`SECURITY_INCIDENT_TERMS`, `SECURITY_SCALE_PATTERNS`, `security_scale=8`)
  lets a plain-English incident headline earn the security bonus without a
  literal CVE token. The cap was a symptom; the scorer was the cause — see
  `editorial.md` and the 2026-11-09 `preferences-log.md` entry. Round-robin-
  by-source was backtested and **rejected**; do not revive it.
- **Fifth consecutive clean runbook run** (2026-10-18 → 2026-11-22) on all
  selectors including Step 7b. Still verify the Publish dialog visually.
- **The RA cap selected by date, not score** — fixed 2026-11-22. A single
  `sort(key=published)` in `DeterministicDigest.py` chose both what survived
  the cap and the render order, so the cap kept the newest N per severity and
  dropped everything older regardless of score (Aurora MySQL 8.4.12 GA at 39.7
  cut for a 27.9 console refresh 22h newer). **Four weeks of log entries
  blamed the severity classifier and "service-family flooding" instead** —
  both wrong. Selection is now by score, display re-sorted by date.
  Lesson: read the code path before writing the pattern narrative.
- **`AWS_REGION_TERMS` contains the bare token `MO`** and was substring
  matched, so any title containing "mo" (mode, monitoring, DynamoDB, model,
  moves) was treated as a regional announcement — 10 RA items forced to low
  severity on 2026-11-22, and a 16-point `region_penalty` applied in `--ai`
  runs. Now word-boundary matched. **Check for other short tokens before
  adding to that list.**
- **Raising a cap is not how you reduce fluff** (2026-11-22) — 43 of 92 RA
  items scored identically (25.7), so extra slots buy one keeper per piece of
  noise. Fix ordering and classification instead.
- **Top-pick mis-ordering is real, measured, and deliberately NOT fixed in
  code** (backtested 2026-11-22 over six weeks). Every hand-promoted pick
  scored below every rejected one — 81 of 81 pairs — and GitHub Blog appeared
  5 times in 6 weeks without the scorer ever choosing it. But three candidate
  fixes were tested and all failed (source tier, announcement shape 11/21,
  quantified outcome 9/21), no token separates the classes, and on
  `heuristic_score` alone the bands overlap. 21 labelled examples cannot
  support a classifier. **The weekly manual check of GitHub Blog and the CNCF
  deep-dives is the fix** — see `editorial.md`. Do not re-propose a scoring
  change here without new evidence.
- **Substack tag loop needs polling, not a fixed wait** (2026-11-22) — the
  documented 120ms sleep clicked 16 of 33 with the misses in a contiguous run.
  Retrying only the `missing` tags is safe and is the correct recovery; only
  re-adding tags that already succeeded triggers the alert flood. See
  `publish.md` Step 7.
- **Screenshots are now confined to the repo / `.playwright-mcp/`**
  (2026-10-18) — `browser_take_screenshot` rejects absolute paths outside
  those roots, so the 2026-10-11 repo-root leak can no longer happen that
  way. Write to `.playwright-mcp/` (gitignored) and still check
  `git status --short` before finishing.
- **Paste verification** — after `Meta+v`, counting
  `h2`/`h3`/`li` inside `[data-testid="editor"]` confirms the paste landed
  before opening the publish dialog. Cheaper than a snapshot and catches a
  silently-failed clipboard write. See `publish.md` Step 5.
- **Tag chips now render fully** (2026-09-20, 2026-09-27) — all 34 chips
  appear after the batch loop, not just the first two. The old "only 2 chips
  visible" symptom appears to be gone, but the rule still stands: trust the
  `clicked: N` return value and never retry.

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
