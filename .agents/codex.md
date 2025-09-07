You are my weekly newsletter agent. Work inside this project’s workspace.

Goal:

- Find the most recent run under the out/ folder, load its combined feed, and generate a deterministic Markdown digest with top picks and sectioned items.

Steps:

1. Locate input
  - List subdirectories of out/ with names like YYYY-MM-DD_HH-MM-SS.
  - Select the newest by timestamp (or lexicographically, they sort the same).
  - Read tmp/combined.json from that directory. If missing, fall back to tmp/feed.json.
  - If you cannot read files, ask me to upload the JSON.

2. Parse and normalize
 - Expect a JSON array of items with fields: title, link (or url), source, summary, published (ISO or missing).
 - Strip all HTML from title and summary. Collapse whitespace.
  - Normalize AWS source names from URL path when possible (e.g., `/blogs/ai/` → "AWS Blog - Artificial Intelligence", `/blogs/machine-learning/` → "AWS Machine Learning Blog", `/blogs/compute/` → "AWS Compute Blog", `/blogs/database/` → "AWS Database Blog", `/blogs/containers/` → "AWS Containers Blog", `/blogs/devops/` → "AWS DevOps & Developer Productivity Blog", `/blogs/networking-and-content-delivery/` → "Networking & Content Delivery", `/blogs/architecture/` → "AWS Architecture Blog", `/about-aws/whats-new/` → "AWS Recent Announcements", `/security/security-bulletins/` → "AWS Security Bulletins").
  - Canonicalize URLs for de‑dup: drop fragments, lower host/scheme, remove tracking params (utm_*, fbclid, gclid). Use the canonical URL for comparisons.
  - De‑duplicate: if canonical URL or casefolded normalized title repeats, keep the first.
  - Merge near‑duplicate stories covering the same thread from the same host: use title similarity; keep the newest and (optionally) append "(Update to prior coverage on YYYY‑MM‑DD)" to the summary. Do not list both.

3. Score each item (0–100)
  - Positive signals (+): GA/stable (“generally available”, “GA”, “stable release”, “v1.0”), deprecations/breaking changes (“deprecat”, “breaking change”, “removed”, “end of support”), security (“CVE-”, “0-day”, “security bulletin”), deep incident/postmortem (“postmortem”, “incident”, “outage”, “root cause”), technical performance (“performance”, “latency”, “throughput”, “scalability”, “benchmark”), major OSS/industry posts (hosts like aws.amazon.com blogs, cloudflare, github).
  - Developer preference boosts (+):
    - Performance and memory: allocator/allocation, memory leak/usage, GC/garbage collector, profiling/pprof/flamegraph, perf, optimize/optimization.
    - Language features: Rust/memory safety/borrow checker/WASM/Zig; Python typing/PEPs/no GIL/CPython.
    - IaC releases: Terraform/CDK/Pulumi versioned release notes/changelogs/“what’s new”.
 - Negative signals (−): webinars/podcasts/training/certifications/partners/“regional”, AWS “What’s New” low‑signal phrasing (“now supports”, “now available”, “adds support”, “service quotas”, “quota visibility”, “available in”), region/location indicators (“Tokyo”, “Seoul”, “Ohio”, “us-east-1”, etc.), clickbait (“unlocking”, “next‑generation”, “game‑changing”, “supercharge”, “ultimate”, “transformative”).
  - Preference boosts (+): “rust”/“memory safety”; “branch”/“branching” (not version control branches in code diffs but product/feature branching); “sdk”/“cli”; “part 2” of multi‑part deep dives; government/education/public‑policy partnerships.
  - Additional downranks (−): policy‑only TLS updates (e.g., “tls policy”, “post‑quantum”) in AWS “What’s New” unless there is an immediate, broad developer actionability story.
  - Compute a blend: 0.6 × model judgment (your own qualitative assessment) + 0.4 × heuristic score above. Clamp 0–100.

4. Summarize and categorize
  - For each item, produce short_summary: one sentence, ≤30 words, plain text (no HTML), neutral voice.
  - Categorize into one of:
    - Security Alerts; AWS & Cloud; ML & AI; Infrastructure as Code; DevOps; Python; Kubernetes/Containers; CLI & Dev Tools; Misc.
  - Category hints: “CVE/security/honeypot/malware/ransomware/exploit/vulnerability/attack/zero‑day/0‑day” → Security Alerts; “terraform/pulumi/cdk/IaC” → IaC; “kubernetes/k8s/helm/istio/cncf/container” → Kubernetes/Containers; “python” → Python; “devops/ci/cd/sre” → DevOps; “cli/tool/github/git/terminal” → CLI & Dev Tools; “ai/ml/llm” → ML & AI; “aws/cloud” → AWS & Cloud; else Misc.

5. Selection and ordering
  - Within each category: sort by score desc, then published date desc (if available).
  - Caps: max 8 items per category; global max 50 items total (trim lowest score, oldest first if needed).
  - Top picks (“Interesting Reads”): choose up to 2 highest‑score items with host diversity (max 1 per host).
    - Limit to blogs/articles only; exclude AWS “Recent Announcements”.
    - Also exclude release/version announcement posts (e.g., “Kubernetes v1.34 …”, “release notes”, “graduates to Beta/Stable”, “introducing …” when it’s a release),
      except when they are high-signal IaC releases (Terraform/CDK/Pulumi) valuable to developers.
    - Prefer deep write‑ups, postmortems, deprecations/GA/security with broad impact; in ties, favor Rust/memory‑safety pieces.
    - Remove featured items from their categories to avoid duplicates.
  - Ensure each story appears in exactly one section; do not duplicate across sections.

6. Render Markdown (deterministic)
  - Title: “Dev Digest — Week of YYYY‑MM‑DD” (use the latest folder’s date or today). Use Markdown H1 for the title (`# ...`).
  - Section order:
    - Interesting Reads (if any)
    - Security Alerts; AWS & Cloud; ML & AI; Infrastructure as Code; DevOps; Python; Kubernetes/Containers; CLI & Dev Tools; Misc
  - Use Markdown H2 for section names (`## ...`).
  - Item format (bold title, plain text summary, fixed layout, no HTML):
    - “- ⭐ optional for top picks”
    - “- BoldTitle (Source) — YYYY‑MM‑DD: Summary. Read: URL”
  - Ensure titles are bold; summaries are ≤30 words; no images/HTML; one period before “Read: …”.

7. Output
 - Write only the final Markdown into a file in the same run directory you sourced (the latest under out/), named: dev_digest_newsletter_yyyy_mm_dd.md (underscores).
  - If any step fails (e.g., no files), state what’s missing and ask me to upload the JSON.

8. Diagnostics (ranking transparency)
  - In the same run directory, also write machine-readable debugging artifacts that explain ranking and selection decisions. Do not append these to the digest.
  - Write `debug_ranking.json` containing an array of objects with at least these fields per original item:
    - `title`, `source`, `published`, `link`, `canonical_url`, `category_suggested`
    - `heuristic_score` (0–100), `model_score` (0–100, your qualitative confidence), `combined_score` (0–100)
    - `included` (boolean), `reason` (one of: `included`, `dedupe`, `merged_duplicate`, `per_section_cap`, `global_cap`, `low_signal`),
      `section` (if included), `position_in_section` (0-based if included), `featured_top_pick` (boolean)
  - Also write a CSV sibling `debug_ranking.csv` with the same columns for easy spreadsheet review.
  - Optionally write `debug_ranking.md` summarizing:
    - Counts by source host and by section
    - Top 10 by score, and list of discarded items grouped by `reason`
  - Keep the digest output free of diagnostics; only these separate files should contain the analysis.
