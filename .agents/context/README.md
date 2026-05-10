Dev Digest Agent Context
========================

Purpose
- Generate a weekly developer-focused digest that filters RSS/Atom feeds and produces curated Markdown ready for publication.
- Act as both repository maintainer and newsletter consumer: look for signal-rich, senior-engineer-worthy content.

System Overview
- CLI entry point: `uv run dev-digest run` shells into `src/dev_digest/cli.py` which calls the digest command.
- Deterministic pipeline (`handler/DeterministicDigest`) ranks, dedupes, sections, and renders Markdown plus diagnostics.
- Feed ingestion (`handler/FeedHandler`) normalizes AWS sources, sanitizes HTML, respects lookback windows, and supports cached re-runs via `out/<date>/tmp`.
- AI-assisted path (`handler/StrandsAgent`) uses Strands Agents for short summaries/impact scores while keeping formatting deterministic and logging token usage.
- Configuration knobs live under `utility/` (feeds, keywords, scoring heuristics, section definitions, constants).
- Diagnostics (`debug_ranking.json/csv/md`) must stay aligned with ranking decisions whenever content selection logic changes.

Editorial Priorities
- High-signal stories: GA/stable launches, deprecations/breaking changes, security/CVE/incident write-ups, deep technical postmortems, performance/memory wins, IaC releases (Terraform/CDK/Pulumi), infrastructure/observability deep dives.
- Keep AWS "Recent Announcements" but classify by severity; limit low-signal regional or quota updates.
- Treat AWS instance family/size/class launches and console/admin UX tweaks as low-impact RA items.
- Deprioritize webinars, podcasts, partner fluff, regional availability notes, clickbait, and low-action TLS/policy updates.
- Deduplicate by canonical URL/title and merge near-duplicates from the same host/topic.
- Top picks need host diversity, exclude low-signal release notes unless IaC high-signal, and avoid AWS RA entries.
- Top picks should skip AWS security bulletins, conference/event recaps, and other hype-y announcements even if they score well.
- Security & Alerts should center on incidents/advisories; conference recaps can be moved to Misc if signal is weak.
- Security section additionally requires incident markers (CVE, exploit, attack, malware, breach, patch, etc.); operational how-tos default back to AWS & Cloud.
- Heuristics now boost “real-world”/case-study style posts (e.g., Kubernetes RBAC deep dives) so practical content doesn’t get trimmed by per-section caps.
- If a practical post still exceeds a section cap, we overflow it into Misc rather than dropping it outright.
- ML & AI section applies penalties to politics/grant-heavy posts from repeat offenders (Ars Technica policy pieces, OpenAI press updates) so technical launches/studies stay visible.
- ML & AI also applies a small finance/earnings penalty (earnings, revenue, shares, stock, valuation, quarterly terms) for those same hosts; IPO/guidance are intentionally excluded.

Workflow Expectations
- Honor CLI flags: `--no-ai` for deterministic runs, `--ai` to engage Strands agent; `--overwrite` rotates run directories safely.
- Default window is 7 days; configurable via `--days`.
- Tests in `tests/` mock `feedparser` and cover scoring, section routing, diagnostics, and CLI smoke runs. Run `uv run pytest` before shipping behavioral changes.
- Respect existing change sets; never revert unrelated user edits.
- When running commands, prefer `rg` for searches; always set `workdir` in CLI harness.
- Local-only note: sandbox blocks `uv run pytest`, so validation requires running the test suite locally.
- Weekly review discipline: always evaluate against the exact run directory under `out/YYYY-MM-DD` currently under discussion and avoid mixing stories across weeks.
- In light-news weeks, bias toward manual newsletter trims/reorganization over permanent scoring changes to avoid overtuning the model to sparse data.
- When section quality is weak, treat clearly non-engineering ML/AI items (ads, lawsuits, personality/political stories) as easy cut candidates unless they contain direct engineering impact.

Security & Data Hygiene
- Validate feed URLs, sanitize/strip HTML, limit text length.
- Canonicalize URLs (remove tracking params/fragments) before dedupe or diagnostics.
- Keep outputs ASCII unless a file already uses Unicode.
- Sandbox note: `uv run pytest` and similar tooling don’t execute here; run tests locally when validating scoring/section changes.

Communication & Tone
- Be concise, factual, collaborative—like a senior teammate.
- When reviewing, list findings before summaries; call out risks and testing gaps explicitly.
- Suggest logical next steps (tests, commits, lint) only when relevant.
- Summarize command output; avoid dumping entire logs.

Operational Notes
- Latest run artifacts live under `out/YYYY-MM-DD*`; re-use cached feeds unless `--overwrite`.
- Markdown digest file naming: `dev_digest_newsletter_yyyy_mm_dd.md`; diagnostics share the same directory.
- Respect environment constraints: workspace-write sandbox, restricted network, approval-on-request for escalations.

Weekly Publish Workflow
1. Generate:  `uv run dev-digest run -d --no-ai --days 7 -wf`
2. Curate:    evaluate output in `out/<date>/dev_digest_newsletter_<date>.md`, trim/move items section by section.
3. Convert:   `uv run dev-digest publish out/<date>/dev_digest_newsletter_<date>.md` → writes `<same-dir>/<same-name>.html`
4. Publish:   Use Playwright MCP tools to drive Substack (see sequence below). ALWAYS stop before "Send to everyone now" — user verifies and publishes manually.

Substack Playwright Publish Sequence
Pre-condition: Substack session is live via persistent profile at `~/.playwright-profiles/substack` (configured in `.mcp.json`).

Step 1 — Navigate to dashboard
  browser_navigate → https://weirdion.substack.com/publish/home

Step 2 — Create new article
  browser_click → text=Create
  browser_click → text=Article
  (new draft URL: https://weirdion.substack.com/publish/post/<id>)

Step 3 — Set section
  browser_click → text=Choose a section
  browser_click → text=Developer Newsletter
  Close the sidebar that opens: browser_evaluate → `() => document.querySelector('.file-sidebar-header-button')?.click()`

Step 4 — Fill title and subtitle
  browser_type → [data-testid="post-title"] with "Dev Digest — Week of YYYY-MM-DD"
  browser_type → [placeholder="Add a subtitle…"] with "Aggregated tech stuff that happened this week without the marketing noise."

Step 5 — Paste HTML body
  Read the HTML file from `out/<date>/<name>.html`.
  browser_evaluate → set clipboard via `navigator.clipboard.write([new ClipboardItem({ 'text/html': new Blob([html], {type:'text/html'}) })])`
  browser_click → [data-testid="editor"]
  browser_press_key → Meta+v
  browser_wait_for → time: 3 seconds

Step 6 — Open publish dialog
  browser_click → button:has-text("Continue")  [use the one in the editor toolbar, not any sidebar button]
  browser_wait_for → time: 2 seconds

Step 7 — Add tags
  Use type-and-select per tag — do NOT rely on snapshot ref IDs, they change every session.
  The combobox has a stable role selector: `getByRole('combobox', { name: 'Select or create tags' })` or `[placeholder="Select or create tags"]`.
  For each tag in SUBSTACK_TAGS (see `src/dev_digest/utility/constants.py`):
    browser_type → target: `[placeholder="Select or create tags"]`, text: <tag name>  (fills combobox, triggers dropdown)
    browser_wait_for → time: 0.5 (let options render)
    browser_click → target: `[role="option"]:has-text("<tag name>")` with exact match  (selects from listbox)
  The combobox clears automatically after each selection — no need to clear it manually.
  If an option doesn't appear (tag not yet created), it can be created by pressing Enter on the typed text.

Step 8 — Set social preview image
  browser_click → button "Social preview" (inside the publish dialog)
  A sub-dialog opens with title "Edit social preview".
  At the bottom are two image thumbnails — first is the newsletter cover image.
  browser_evaluate → `() => { const imgs = document.querySelectorAll('dialog img, [role="dialog"] img'); imgs[0].closest('[role="button"],button,a')?.click() ?? imgs[0].click(); }`
  browser_click → text="Save"  (use exact match to avoid hitting the "Saved" status button)
  NOTE: if "Save" is ambiguous use `getByRole('button', { name: 'Save' })` or the exact ref from snapshot.

Step 9 — STOP
  Confirm the publish dialog shows: correct title/subtitle in social preview, all tags visible, cover image set, "Send to everyone now" button present.
  Do NOT click "Send to everyone now". Hand off to user for final review and publish.

Recent Preference Log
- Added because weekly tuning is iterative and a fresh chat agent needs quick chronology, not just static rules.
- Keep this as short bullets with date and intent whenever heuristics or editorial priorities change.
- 2026-03-02: Added `"senator"` to AI_POLICY_TERMS — `\bsenate\b` does not match "senators" (plural); gap caught items like "Senators want US energy agency to monitor data centers".
- 2026-03-02: Added `ml_ai_policy_filter` hard post-processing block in DeterministicDigest — score penalties alone insufficient because freshness floor gives 2-3 day old items ~24-27 combined score regardless of heuristic penalty.
- 2026-03-02: Added `event_promo_filter` global block for CNCF/KubeCon event promos ("co-located event", "summer of code", "kcds", "kubecon") — caught 5-6 items per week consistently.
- 2026-03-02: Added `exclude_hosts=("realpython.com",)` to Infrastructure section — Real Python tutorials were routing there via "command line" keyword in summaries.
- 2026-03-02: Removed `"government"` from GOVERNMENT_TERMS — was giving +8 boost to political stories.
- 2026-03-02: OpenAI policy items bypass ml_ai_policy_filter when they contain AWS/Amazon keywords — they route to aws_cloud (order=20) before ml_ai (order=40). Handle manually; too sparse to heuristic-fix.
- 2026-03-15: AWS DevOps Agent blog posts ("incident response" in body) repeatedly misroute to Security section — the security_required_terms filter matches "incident" as a false positive. Recurring pattern; watch for heuristic fix opportunity.
- 2026-03-15: Political/policy Ars Technica stories ("Trump data center", "Perplexity lawsuit") route to Infrastructure or AWS&Cloud when they contain cloud/infra keywords — ml_ai_policy_filter only covers the ml_ai bucket. Handle manually for now.
- 2026-03-22: Holeover items from prior week (published 7+ days ago) re-appear in subsequent run — age them out manually if they were already featured.
- 2026-03-22: Beginner/tutorial Real Python content (note-taking, Git basics, OOP intro) repeatedly surfaces in Dev Tools — cut on sight; not senior-engineer-worthy.
- 2026-03-22: Vendor case studies (Reco, Halliburton, Oldcastle, etc. using Bedrock/SageMaker) flood AWS&Cloud — cut unless there is a concrete benchmark or architectural decision worth noting (e.g. DocumentDB Graviton4 63% Sysbench improvement is keep; "Halliburton seismic workflow" is cut).
- 2026-03-29: Kubernetes blog posts misroute to Dev Tools or ML&AI — move to Kubernetes/Containers on sight.
- 2026-03-29: Nova ML tutorials (video semantic search, text-to-SQL, hyper-personalized viewer) consistently land in Infrastructure or AWS&Cloud — cut; they are marketing tutorials.
- 2026-04-19: "Partner Revenue Measurement" RA entries are partner program noise — cut from Low Impact on sight.
- 2026-05-10: Substack publish workflow confirmed via Playwright: section set to "Developer Newsletter", title/subtitle populated from markdown H1 and subtitle line, body pasted as HTML (not plain text). Publish dialog requires tags to be set; standardized tag set: AWS, DevOps, Kubernetes, Security, Python, IaC, Containers, News, ML, MLOps, Agentic AI, AI, Bedrock, CDK, CI/CD, CLI, Claude, Cloud Engineering, Data Engineering, Data Pipeline, developers, Disaster Recovery, ETL, GenAI, Gemini, Github, GPT, Infrastructure As Code, SageMaker, Serverless, Software Engineering, software development, technology, Terraform.
- 2026-05-10: Substack editor (ProseMirror) ignores markdown on paste — must paste as HTML via ClipboardItem with text/html type. h2/h3/ul/li/strong/a all render correctly.
- 2026-05-10: Newsletter item links: title should be the hyperlink (Option A pattern), with source publication already embedded in title text providing transparency. Raw "Read: URL" pattern dropped in HTML output. Footer line kept and converted (markdown links → html anchors).
- 2026-05-10: .mcp.json added to repo with Playwright MCP config using --user-data-dir ~/.playwright-profiles/substack for persistent Substack session across Claude Code sessions.
