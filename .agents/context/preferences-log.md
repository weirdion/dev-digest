Preferences Log
===============

Chronological log of heuristic / editorial changes and hard-won learnings.
Append new entries at the bottom with the date and the *why*. Cross-link to
`editorial.md` or `publish.md` when adding durable rules.

2026-03-02 — Initial heuristic tuning
-------------------------------------
- Added `"senator"` to `AI_POLICY_TERMS` — `\bsenate\b` does not match
  "senators" (plural). Gap caught items like "Senators want US energy agency to
  monitor data centers".
- Added `ml_ai_policy_filter` hard post-processing block in
  `DeterministicDigest.py`. Score penalties alone were insufficient because the
  freshness floor gives 2-3 day old items ~24-27 combined score regardless of
  heuristic penalty.
- Added `event_promo_filter` global block for CNCF / KubeCon event promos
  (`"co-located event"`, `"summer of code"`, `"kcds"`, `"kubecon"`). Caught
  5-6 items per week consistently.
- Added `exclude_hosts=("realpython.com",)` to the Infrastructure section.
  Real Python tutorials were routing there via the "command line" keyword in
  summaries.
- Removed `"government"` from `GOVERNMENT_TERMS` — was giving +8 boost to
  political stories.
- **Known bypass**: OpenAI policy items that contain AWS / Amazon keywords
  route to `aws_cloud` (order=20) before `ml_ai` (order=40), so
  `ml_ai_policy_filter` never sees them. Handle manually; too sparse to
  heuristic-fix.

2026-03-15 — Misroute patterns documented
-----------------------------------------
- AWS DevOps Agent blog posts ("incident response" in body) repeatedly
  misroute to Security section — `security_required_terms` matches "incident"
  as a false positive. Recurring pattern; manual move to Infrastructure each
  week.
- Political / policy Ars Technica stories ("Trump data center", "Perplexity
  lawsuit") route to Infrastructure or AWS&Cloud when they contain cloud /
  infra keywords. `ml_ai_policy_filter` only covers the `ml_ai` bucket.
  Manual cut.

2026-03-22 — Light-news week patterns
-------------------------------------
- Holdover items from prior week (published 7+ days ago) re-appear in the
  subsequent run. Age them out manually if already featured.
- Beginner / tutorial Real Python content (note-taking, Git basics, OOP intro)
  repeatedly surfaces in Dev Tools — cut on sight.
- Vendor case studies (Reco, Halliburton, Oldcastle, etc. using Bedrock /
  SageMaker) flood AWS&Cloud — cut unless there's a concrete benchmark or
  architectural decision (DocumentDB Graviton4 63% Sysbench is keep;
  "Halliburton seismic workflow" is cut).

2026-03-29 — More routing
-------------------------
- Kubernetes blog posts misroute to Dev Tools or ML&AI — move to
  Kubernetes/Containers on sight.
- Nova ML tutorials (video semantic search, text-to-SQL, hyper-personalized
  viewer) consistently land in Infrastructure or AWS&Cloud — cut; marketing
  tutorials.

2026-04-19 — Partner program noise
----------------------------------
- "Partner Revenue Measurement" / "Partner Central" RA entries are partner
  program noise — cut from Low Impact on sight.

2026-05-10 — Substack publish pipeline established
--------------------------------------------------
- Confirmed via Playwright: section is "Developer Newsletter"; title from
  markdown H1; subtitle from the line below H1; body pasted as HTML (not
  plain text). Publish dialog requires tags.
- **Standardized tag set** (now in `src/dev_digest/utility/constants.py` as
  `SUBSTACK_TAGS`): AWS, DevOps, Kubernetes, Security, Python, IaC,
  Containers, News, ML, MLOps, Agentic AI, AI, Bedrock, CDK, CI/CD, CLI,
  Claude, Cloud Engineering, Data Engineering, Data Pipeline, developers,
  Disaster Recovery, ETL, GenAI, Gemini, Github, GPT, Infrastructure As Code,
  SageMaker, Serverless, Software Engineering, software development,
  technology, Terraform.
- Substack editor (ProseMirror) IGNORES markdown on paste — must paste as
  HTML via `ClipboardItem` with `text/html` type. `h2`/`h3`/`ul`/`li`/`strong`/`a`
  all render correctly.
- Newsletter item link format: title is the hyperlink (sources already
  embedded in title text provide transparency). The raw "Read: URL" pattern
  is dropped in HTML output. Footer line is kept and converted (markdown
  links → html anchors).
- `.mcp.json` added with Playwright MCP config using `--user-data-dir
  ~/.playwright-profiles/substack` for persistent Substack session across
  Claude Code sessions.

2026-05-17 — Tag click pattern resolved + $HOME path
----------------------------------------------------
- **`.mcp.json` `$HOME` path expansion works correctly** — verified by
  successful Substack auth across restarts. Use `$HOME/.playwright-profiles/<name>`
  in the args array instead of an absolute path.
- **Tag batch-click via `browser_evaluate` is the documented happy path.**
  When the loop reports `clicked: N`, all N tags are saved server-side EVEN IF
  the chip UI only renders 1-2 of them. Verified by refreshing the page and
  reopening the Publish dialog — all chips render correctly.
- **DO NOT retry the batch click.** The second batch triggers Substack's
  `"Tag already set"` alert flood (a synchronous `window.alert()` per
  duplicate). Once the alerts start queuing, they need many `browser_handle_dialog`
  calls to drain before any other browser tool can run.

2026-05-31 — Escape closes the Publish dialog
---------------------------------------------
- After the tag batch click, the dropdown is still open. Pressing Escape
  closes BOTH the dropdown AND the Publish dialog. You then have to click
  Continue again to re-open it.
- Use a neutral DOM click instead: `document.querySelector('[role="dialog"]
  h2')?.click()` dismisses the dropdown without losing dialog state.
- Documented in `publish.md` Step 8.

2026-05-31 — Agent context overhauled
-------------------------------------
- Split the single README into multiple focused files (`system.md`,
  `editorial.md`, `publish.md`, `preferences-log.md`).
- Goal: a fresh agent in a new conversation can resume the weekly workflow
  without re-discovering institutional knowledge.
- The `prompt.md` now directs the agent to read context files at session
  start.

2026-06-07 — AWS security bulletins date extraction
---------------------------------------------------
- **Problem**: every entry in the AWS Security Bulletins RSS feed
  (`https://aws.amazon.com/security/security-bulletins/feed/`) has the same
  `pubDate` set to the feed's `lastBuildDate`. All bulletins look fresh on
  every fetch regardless of their real publish date. The Security section
  spent 3+ weeks recycling old CVEs (CVE-2026-8838 Redshift driver from
  2026-05-17, SageMaker SDK CVEs from 2026-05-24, etc.).
- **Fix**: parse the actual `Publication Date` from the description body in
  `FeedHandler._entry_dt()`. Handles both `YYYY/MM/DD` and `MM/DD/YYYY`
  formats, AM/PM and 24h time, PDT/PST/UTC/GMT timezones, and the bogus
  `15:30 PM PDT` (24h with redundant PM) format AWS sometimes ships.
- **Hard-fail policy**: if extraction fails for a known-broken source (e.g.
  typo like `06/025/2026`), return None to drop the item rather than fall
  back to the always-stale feed pubDate. Caught a real typo in
  CVE-2026-11400/11401 (Aurora PostgreSQL) on the 2026-06-07 run.
- Tests in `tests/test_feedhandler.py` cover both date formats, the 24h-with-
  PM edge case, PST offset, missing date, and the malformed-date drop.

2026-06-21 — Direct URL for new-post creation
---------------------------------------------
- **Problem**: clicking `Create` on the Substack dashboard sometimes does not
  render the dropdown's `Article` menu item (the dropdown opens but the items
  don't materialize). Lost a few tool calls on 2026-06-21 chasing it.
- **Fix**: navigate directly to
  `https://weirdion.substack.com/publish/post?type=newsletter`. Substack
  creates a fresh draft and redirects to `/publish/post/<id>`.
- Documented in `publish.md` Step 2 as the preferred path with the Create
  dropdown demoted to a fallback.

How to add a new entry
----------------------
- Date the entry (YYYY-MM-DD) and give it a short heading.
- State what changed and the *why*. Link to a file path or PR if relevant.
- If the entry establishes a new durable rule, mirror it into `editorial.md`
  or `publish.md` so it's discoverable from the runbook.
