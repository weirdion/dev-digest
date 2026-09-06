Editorial Rules
===============

The newsletter's voice: senior cloud engineer, signal over hype. If a senior
engineer wouldn't open the link, it shouldn't be in the digest.

High-signal content
-------------------
Always keep:
- GA / stable launches with concrete user impact (e.g., Aurora MySQL 8.4 GA).
- Deprecations and breaking changes (CDK / Terraform release notes, Kubernetes
  deprecations).
- Security incidents: real CVEs, active exploits, supply chain attacks,
  ransomware events.
- Deep technical postmortems and engineering deep dives (GitHub Issues
  performance, NetEase Games LLM cold starts).
- Performance / memory wins with quantified impact (e.g., DocumentDB Graviton4
  63% Sysbench improvement).
- IaC releases — Terraform, CDK, Pulumi.
- Infrastructure / observability deep dives.

Top picks (Interesting Reads, 2 items)
--------------------------------------
- Need host diversity (avoid 2 from same source).
- AVOID: AWS RA entries, AWS security bulletins, conference / event recaps,
  hype-y product announcements (even if they score well).
- AVOID: AWS DevOps Agent product blogs — they're a recurring offender
  (the model loves them; the reader does not). Cut every time, move to
  Infrastructure if the content is genuinely useful.
- **Prefer engineer-focused stories over security-blog picks** (user pref,
  2026-08-03). Real architecture / performance / release deep dives win;
  security news is fine but goes in Security & Alerts, not top picks, unless
  it's genuinely cross-industry (post-quantum crypto attack tier).
- **Fix bad `"1."` / single-fragment summaries before publishing** — some
  CNCF and Kubernetes Blog posts arrive with a description that's just `"1."`
  or a nav-crumb because the article's opening is a numbered list. Seen on
  `ingress-NGINX retirement` (2026-07-12) and `Kubernetes Dashboard to
  Headlamp` (2026-07-19). Rewrite the blurb by hand before pasting.

Section routing rules
---------------------
Sections are ordered (see `sections.py`); items route to the first match by
keyword + host rules. Recurring misroute patterns to fix manually each week:

- **AWS DevOps Agent posts → Security**: "incident response" in the body
  matches Security's `security_required_terms`. Move to Infrastructure.
- **Kubernetes posts → Dev Tools or ML&AI**: any K8s release / blog content
  belongs in `Kubernetes/Containers`.
- **Istio / service mesh posts**: belong in Kubernetes/Containers.
- **OpenAI / DeepMind posts with AWS keywords → AWS&Cloud**: bypass the
  `ml_ai_policy_filter` (which only covers `ml_ai`). Manual cut/move.
- **Ars Technica policy stories with cloud keywords → Infrastructure /
  AWS&Cloud**: same bypass — manual cut.
- **CNCF event promos**: caught by `event_promo_filter` — should not appear.
  If one slips through, add the term to the filter.

Section caps and overflow
- Per-section cap is in `constants.PER_SECTION_CAP` (8).
- If a practical / engineering post exceeds the cap, it overflows to Misc
  rather than getting dropped.

Cut on sight (recurring noise patterns)
----------------------------------------
These have appeared week after week. Cut them every time unless they have a
concrete benchmark or architectural decision:

- **Beginner Real Python tutorials** (note-taking, Git basics, OOP intro, "How
  to flatten a list", plt.scatter, etc.) — not senior-engineer-worthy. The
  Real Python *monthly news* roundup IS worth keeping when it appears.
- **RealPython "AI model vibe check" posts** (2026-09 pattern: "GPT-6 Astra
  Draws a Python Reading a Book", "Claude Fable 5.1 Draws a Python Reading a
  Book"). Fun but not senior-engineer content. Cut every time. Real Python's
  Python 3.15 preview series and monthly news roundups ARE keeps.
- **Vendor case studies using Bedrock / SageMaker / Nova** (Reco, Halliburton,
  Oldcastle, Synthesia, Aigen, Workhuman, NarrateAI for SMGS, etc.). KEEP only
  if there's a concrete benchmark (DocumentDB Graviton4 63% wins, HotelTrader
  95% / 49%, Motorway 1-in-8 → 1-in-50, Outpost VFX 8x, etc.).
- **Strands Agents / Bedrock AgentCore vendor case studies** — a recurring
  bucket by mid-2026 (KTern SAP, Cohere Health clinical, Jefferies trading,
  Stripe compliance, TReNDS RCA, Rocket Close, LendingTree mortgage,
  monday.com AI Teammates, Thrad.ai, Smartsheet MCP, Loka Nova 2 voice, etc.).
  Cut unless there's a concrete number (see above). Do keep AgentCore
  *platform* posts (harness GA, runtime instances, temporal policies).
- **AWS Nova ML tutorials** (video semantic search, text-to-SQL, hyper-
  personalized viewer, Stream Vision Agents). Marketing tutorials — cut.
- **Partner Revenue Measurement / Partner Central RA entries**. Partner
  program noise.
- **Regional-only RA entries** (new Local Zones, Keyspaces in Malaysia /
  Thailand, Redshift Serverless in N more regions). Cut from Low Impact per
  the README rule on regional updates.
- **Holdover from prior week**: items that scored well last week often re-
  appear (release notes with stable URLs). Age them out — verify the user has
  not already seen them.

Borderline (judgment calls)
---------------------------
- **OpenAI / DeepMind product launches**: keep if there's a technical angle
  (e.g., voice AI WebRTC deep dive, GPT-5.5 launch). Cut if it's a partnership /
  PR / press release (Malta partnership, Education for Countries, NVIDIA-Codex).
- **AWS RA Aurora / DynamoDB Global Tables / S3 Vectors blog posts**: keep if
  there's a concrete architecture or trade-off discussed; cut if it's a getting-
  started walkthrough.
- **Kubernetes release notes**: bundle all v1.X items under
  `Kubernetes/Containers`; sometimes the major release post belongs in
  Interesting Reads if the headline feature is significant (e.g.,
  User Namespaces GA).

ML & AI section — the noise bucket
-----------------------------------
This section attracts the most noise. Cut aggressively:

- Politics / policy stories (energy regulation, lawsuits, government contracts).
- Sensational consumer stories (deepfakes, dead-pilot voice clones).
- Corporate gossip (OpenAI / Apple drama, Anthropic settlement details).
- PR / partnership announcements.
- Pricing / tier announcements.

Keep:
- Major model launches with technical detail (Gemma 4 Apache 2.0, GPT-5.5).
- Research findings relevant to engineers (LLMs believe false statements,
  cognitive surrender research).
- AI infrastructure deep dives (better placed in Infra or Kubernetes when
  possible, e.g., OpenAI voice AI WebRTC stack).
- Engineering-relevant agent / Codex updates with substance.

Security section — incident-driven only
---------------------------------------
- Items MUST have an incident marker (CVE, exploit, attack, malware, breach,
  patch). Operational how-tos default back to AWS & Cloud.
- AWS DevOps Agent operational posts: cut on sight (recurring misroute).
- Long-form security architecture guides (cyber resilience reference, DR
  approaches): move to Infrastructure.
- **MCP-server + prompt-injection CVE clusters** — by mid-2026 AWS is
  publishing 5-8 real CVEs per week around Strands Agents, AgentCore harness,
  and MCP servers (DocumentDB, Transform, Amazon MQ, etc.). Keep all of them
  during heavy weeks; the pattern itself is useful signal to the reader.
- **Vendor "AI security" PR** (OpenAI Daybreak, Patch the Planet, Microsoft
  AI security tools launches) — cut, or downgrade to a top pick only if it
  covers a real disclosed incident (e.g., OpenAI/Hugging Face model eval
  incident writeup).

AWS Recent Announcements
------------------------
- Classify by severity (Critical / High / Medium / Low) rather than cutting.
- Limit pure-regional updates (new Local Zones, region expansions) — Low or cut.
- Limit quota updates — Low.
- Niche Contact Center / Connect updates — Low or cut.
- Instance family / size / class launches and console UX tweaks — Low.
