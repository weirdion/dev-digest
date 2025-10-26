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

Workflow Expectations
- Honor CLI flags: `--no-ai` for deterministic runs, `--ai` to engage Strands agent; `--overwrite` rotates run directories safely.
- Default window is 7 days; configurable via `--days`.
- Tests in `tests/` mock `feedparser` and cover scoring, section routing, diagnostics, and CLI smoke runs. Run `uv run pytest` before shipping behavioral changes.
- Respect existing change sets; never revert unrelated user edits.
- When running commands, prefer `rg` for searches; always set `workdir` in CLI harness.
- Local-only note: sandbox blocks `uv run pytest`, so validation requires running the test suite locally.

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
