import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, DefaultDict, Set
from collections import defaultdict

from strands import Agent
from strands.agent import AgentResult
from dev_digest.utility.constants import (
    PER_SECTION_CAP,
    TOP_PICKS_COUNT,
    MAX_STORIES_TOTAL,
    MODEL_PROFILES,
    DEFAULT_MODEL_KEY,
    CLICKBAIT_TERMS,
    AWS_WHATS_NEW_LOW_SIGNAL,
    AWS_REGION_TERMS,
    PERFORMANCE_TERMS,
    LANGUAGE_FEATURE_TERMS,
    IAC_HIGH_SIGNAL_TERMS,
)
from dev_digest.utility.metrics import usage_summary
from dev_digest.utility.tools import canonicalize_url
from dev_digest.utility.security import strip_html_to_text


SECTION_ORDER = [
    "Security & Alerts",
    "AWS & Cloud",
    "ML & AI",
    "Infrastructure as Code",
    "DevOps",
    "Python",
    "Kubernetes/Containers",
    "CLI & Dev Tools",
    "Misc",
]


def _infer_category(title: str, source: str) -> str:
    t = (title or "").lower()
    s = (source or "").lower()
    if (
        "security" in s
        or "security" in t
        or "cve" in t
        or any(k in t for k in ["honeypot", "malware", "ransomware", "exploit", "vulnerability", "attack", "zero-day", "0-day"])  # noqa: E501
    ):
        return "Security & Alerts"
    if "aws" in s or "aws" in t or "cloud" in t:
        return "AWS & Cloud"
    if any(k in t for k in ["terraform", "pulumi", "cdk", "infrastructure as code"]):
        return "Infrastructure as Code"
    if any(k in t for k in ["kubernetes", "k8s", "helm", "istio", "cncf", "container"]):
        return "Kubernetes/Containers"
    if "python" in s or "python" in t:
        return "Python"
    if any(k in t for k in ["devops", "cicd", "ci/cd", "sre"]):
        return "DevOps"
    if any(k in t for k in ["cli", "tool", "github", "git", "terminal"]):
        return "CLI & Dev Tools"
    if any(k in t for k in ["ai", "ml", "machine learning", "llm"]):
        return "ML & AI"
    return "Misc"


def _clip_words(text: str, max_words: int) -> str:
    parts = (text or "").split()
    if len(parts) <= max_words:
        return " ".join(parts)
    return " ".join(parts[:max_words])


def _render_markdown(sections: Dict[str, List[Dict[str, Any]]]) -> str:
    now = datetime.now(tz=timezone.utc).date().isoformat()
    lines: List[str] = []
    lines.append(f"# Dev Digest — Week of {now}")
    lines.append("")

    # Top picks section if present
    top_items = sections.get("TOP_PICKS") or []
    if top_items:
        lines.append("## Interesting Reads")
        for it in top_items:
            title = it.get("title", "").strip()
            source = it.get("source", "").strip()
            link = it.get("link") or it.get("url") or ""
            published = it.get("published")
            if isinstance(published, datetime):
                date_str = published.date().isoformat()
            else:
                date_str = ""
            summary = _clip_words(strip_html_to_text((it.get("short_summary") or it.get("summary") or "").strip()), 30)
            head = f"**{title} ({source})**" if source else f"**{title}**"
            date_part = f" — {date_str}" if date_str else ""
            read_more = f" Read: {link}" if link else ""
            lines.append(f"- ⭐ {head}{date_part}: {summary}.{read_more}")
        lines.append("")

    for section in SECTION_ORDER:
        items = sections.get(section) or []
        if not items:
            continue
        lines.append(f"## {section}")
        for it in items:
            title = it.get("title", "").strip()
            source = it.get("source", "").strip()
            link = it.get("link") or it.get("url") or ""
            published = it.get("published")
            if isinstance(published, datetime):
                date_str = published.date().isoformat()
            else:
                date_str = ""
            summary = _clip_words(strip_html_to_text((it.get("short_summary") or it.get("summary") or "").strip()), 30)
            head = f"**{title} ({source})**" if source else f"**{title}**"
            date_part = f" — {date_str}" if date_str else ""
            read_more = f" Read: {link}" if link else ""
            lines.append(f"- {head}{date_part}: {summary}.{read_more}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


class StrandsAgent:
    def __init__(self, model_key: str = DEFAULT_MODEL_KEY) -> None:
        # Keep the agent focused on concise summaries only. Markdown is rendered deterministically in code.
        profile = MODEL_PROFILES.get(model_key) or MODEL_PROFILES[DEFAULT_MODEL_KEY]
        self.model_key = model_key if model_key in MODEL_PROFILES else DEFAULT_MODEL_KEY
        self.model_id = str(profile.get("model_id") or MODEL_PROFILES[DEFAULT_MODEL_KEY]["model_id"])  # type: ignore[index]

        self.summary_agent = Agent(
            model=self.model_id,
            callback_handler=None,
            name="SummaryAgent",
            system_prompt=(
                "You are a senior cloud engineer summarizing and scoring a weekly list of posts. "
                "For EACH item, return: a single concise one-sentence summary (max 30 words) and an impact score 0-100. "
                "Scoring guidance: prioritize impactful launches (GA/stable), critical security issues (CVE, 0-day), deep technical write-ups, postmortems, novel performance/architecture insights, major OSS releases. "
                "De-prioritize routine region expansions, partner news, webinars/podcasts, basic tutorials, training/certs. "
                "Respond ONLY as JSON array with objects: {index, short_summary, impact_score}. No markdown or code fences."
            ),
        )
        self.last_usage: Dict[str, Any] | None = None
        self.last_usage: Dict[str, Any] | None = None

    def summarize_markdown(self, items: List[Dict[str, Any]]) -> str:
        """
        Generate a deterministic markdown newsletter from items.
        The LLM is used only to produce short summaries as JSON; we handle
        categorization and formatting in code for stability.
        """
        if not items:
            return "# Dev Digest — Week of (no data)\n\n_No items found._\n"

        # Build a compact, index-addressable list to prompt the model
        indexed: List[Tuple[int, Dict[str, Any]]] = list(enumerate(items))
        def _safe_str(x: Any) -> str:
            return str(x) if x is not None else ""

        prompt_lines = [
            "Summarize each item (<=30 words) and provide an impact score 0-100.",
            "Return JSON only: [{\"index\": <int>, \"short_summary\": \"...\", \"impact_score\": <int>}]. Include all indices.",
            "Items:",
        ]
        for idx, it in indexed:
            title = _safe_str(it.get("title"))
            source = _safe_str(it.get("source"))
            link = _safe_str(it.get("link") or it.get("url"))
            published = it.get("published")
            pub_str = published.isoformat() if isinstance(published, datetime) else _safe_str(published)
            # Keep each item on a single line to reduce prompt variance
            prompt_lines.append(
                json.dumps({
                    "index": idx,
                    "title": title,
                    "source": source,
                    "published": pub_str,
                    "link": link,
                    "summary": _safe_str(it.get("summary")),
                }, ensure_ascii=False)
            )

        prompt = "\n".join(prompt_lines)
        result: AgentResult = self.summary_agent(prompt)
        # Capture usage for cost estimation/logging
        try:
            self.last_usage = usage_summary(result, model_key=self.model_key, model_id=self.model_id)
        except Exception:
            self.last_usage = None
        text = ""
        try:
            text = result.message.get("content", [{}])[0].get("text", "")  # type: ignore[index]
        except Exception:
            text = ""

        # Extract JSON array from the model response
        json_blob = text
        # Strip code fences if present
        json_blob = re.sub(r"^```(?:json)?\n|\n```$", "", json_blob.strip(), flags=re.MULTILINE)
        # If wrapped, try to find an array
        match = re.search(r"(\[\s*\{.*\}\s*\])", json_blob, flags=re.DOTALL)
        if match:
            json_blob = match.group(1)

        summaries: Dict[int, str] = {}
        llm_scores: Dict[int, float] = {}
        try:
            data = json.loads(json_blob)
            if isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict) and "index" in obj:
                        try:
                            idx = int(obj["index"])
                            if "short_summary" in obj:
                                summaries[idx] = str(obj["short_summary"]).strip()
                            if "impact_score" in obj:
                                llm_scores[idx] = float(obj["impact_score"])
                        except Exception:
                            continue
        except Exception:
            # Fallback: empty summaries
            summaries = {}
            llm_scores = {}

        def _heuristic_score(title: str, summary: str, source: str) -> float:
            t = (title or "").lower()
            s = (source or "").lower()
            suml = (summary or "").lower()
            score = 0.0
            # Positive signals
            if any(k in t for k in ["generally available", "ga ", "ga:", "stable release", "v1.0"]):
                score += 28
            if any(k in t for k in ["preview", "public preview", "beta"]):
                score += 16
            if any(k in t for k in ["postmortem", "incident", "outage", "root cause"]):
                score += 32
            if "cve-" in t or "cve-" in suml or "0-day" in t:
                score += 26
            if any(k in t for k in ["deprecate", "breaking change", "removed", "end of support"]):
                score += 24
            if any(k in t for k in PERFORMANCE_TERMS):
                score += 18
            if any(k in s for k in ["aws", "cloudflare", "github", "google", "microsoft"]):
                score += 6
            if any(k in t for k in ["open source", "oss", "released", "announce"]):
                score += 10
            # Preference signals from feedback
            if any(k in t for k in LANGUAGE_FEATURE_TERMS):
                score += 16
            if any(k in t for k in ["branch", "branching"]):
                score += 8
            if any(k in t for k in ["sdk", "cli"]):
                score += 6
            if "part 2" in t:
                score += 6
            if any(k in t for k in ["government", "education", "schools", "policy", "partnership"]):
                score += 8
            # IaC (Terraform/CDK/Pulumi) release notes are important for developers
            if any(k in t for k in IAC_HIGH_SIGNAL_TERMS) and (
                re.search(r"\bv\d+\.\d+\b", t) or "release" in t or "changelog" in t or "what's new" in t
            ):
                score += 16
            # Negative signals
            if any(k in t for k in ["webinar", "podcast", "training", "certification", "partner", "regional"]):
                score -= 30
            if any(k in t for k in CLICKBAIT_TERMS):
                score -= 14
            # De-prioritize lightweight What's New unless strong positives
            if s == "recent announcements" and not any(x in t for x in ["ga", "generally available", "security", "cve", "deprecat", "breaking"]):
                score -= 18
            if any(k in t for k in AWS_WHATS_NEW_LOW_SIGNAL):
                score -= 18
            if any(term.lower() in t for term in AWS_REGION_TERMS):
                score -= 16
            # Downweight policy-only TLS updates that are not broadly actionable this week
            if any(k in t for k in ["tls policy", "post-quantum"]) and s == "recent announcements":
                score -= 10
            # Clamp
            return max(0.0, min(100.0, score))

        def _ts(d: Any) -> float:
            if isinstance(d, datetime):
                try:
                    return d.timestamp()
                except Exception:
                    return 0.0
            return 0.0

        def _combine_score(idx: int, title: str, summary: str, source: str) -> float:
            h = _heuristic_score(title, summary, source)
            l = llm_scores.get(idx, 0.0)
            combined = 0.6 * l + 0.4 * h
            if math.isnan(combined) or math.isinf(combined):
                combined = h or l or 0.0
            return max(0.0, min(100.0, combined))

        # Build sections deterministically
        sections: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        for idx, it in indexed:
            enriched = dict(it)
            enriched["short_summary"] = summaries.get(idx, (it.get("summary") or "").strip())
            title = enriched.get("title", "")
            source = enriched.get("source", "")
            enriched["score"] = _combine_score(idx, title, enriched["short_summary"], source)
            cat = _infer_category(title, source)
            enriched["category"] = cat
            sections[cat].append(enriched)

        # Sort by score then date, merge near-duplicate stories per section, then enforce per-section cap
        def _topic_tokens(title: str) -> set[str]:
            t = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
            words = [w for w in t.split() if len(w) > 2 and w not in {"the","and","for","with","into","your","our","are","was","were","this","that","from","you","now","new","aws","blog"}]
            return set(words)

        def _merge_near_duplicates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            merged: List[Dict[str, Any]] = []
            taken = [False]*len(items)
            for i, it in enumerate(items):
                if taken[i]:
                    continue
                toks_i = _topic_tokens(it.get("title", ""))
                best = it
                for j in range(i+1, len(items)):
                    if taken[j]:
                        continue
                    tj = _topic_tokens(items[j].get("title", ""))
                    if not toks_i or not tj:
                        continue
                    inter = len(toks_i & tj)
                    union = len(toks_i | tj)
                    sim = inter/union if union else 0.0
                    same_host = True
                    try:
                        h1 = canonicalize_url(it.get("link") or it.get("url") or "").split("//",1)[-1].split("/",1)[0]
                        h2 = canonicalize_url(items[j].get("link") or items[j].get("url") or "").split("//",1)[-1].split("/",1)[0]
                        same_host = (h1 == h2)
                    except Exception:
                        pass
                    if sim >= 0.6 and same_host:
                        # Keep newer by published timestamp
                        if _ts(items[j].get("published")) >= _ts(best.get("published")):
                            best = items[j]
                        taken[j] = True
                merged.append(best)
                taken[i] = True
            return merged

        for cat, arr in sections.items():
            arr.sort(key=lambda x: (float(x.get("score", 0.0)), _ts(x.get("published"))), reverse=True)
            arr = _merge_near_duplicates(arr)
            if PER_SECTION_CAP and len(arr) > PER_SECTION_CAP:
                arr = arr[:PER_SECTION_CAP]
            sections[cat] = arr

        # Enforce global cap by trimming lowest-score, oldest items across sections
        if MAX_STORIES_TOTAL:
            total = sum(len(v) for v in sections.values())
            if total > MAX_STORIES_TOTAL:
                # Build candidate list (score asc, date asc)
                candidates: List[Tuple[float, float, str, int]] = []
                for cat, arr in sections.items():
                    for i, it in enumerate(arr):
                        candidates.append((float(it.get("score", 0.0)), _ts(it.get("published")), cat, i))
                candidates.sort(key=lambda x: (x[0], x[1]))
                to_remove = total - MAX_STORIES_TOTAL
                removed_by_cat: DefaultDict[str, set[int]] = defaultdict(set)
                for _, _, cat, i in candidates:
                    if to_remove <= 0:
                        break
                    if i in removed_by_cat[cat]:
                        continue
                    removed_by_cat[cat].add(i)
                    to_remove -= 1
                for cat, idxs in removed_by_cat.items():
                    sections[cat] = [it for j, it in enumerate(sections[cat]) if j not in idxs]

        # Compute top picks with host diversity, exclude low-signal & release posts, and remove duplicates from sections
        flat_items: List[Dict[str, Any]] = [it for arr in sections.values() for it in arr]
        def _is_release_like(title_l: str, source_l: str) -> bool:
            if "kubernetes v" in title_l:
                return True
            if re.search(r"\bv\d+\.\d+\b", title_l):
                return True
            if any(k in title_l for k in ["release notes", "released", "introducing", "graduates to beta", "graduates to stable", "now available"]):
                return True
            return False
        def _is_high_signal_release(title_l: str) -> bool:
            # Allow IaC release notes (Terraform/CDK/Pulumi) as high-signal exceptions
            return any(k in title_l for k in IAC_HIGH_SIGNAL_TERMS)
        def _rust_pref(title_l: str) -> int:
            return 1 if ("rust" in title_l or "memory safety" in title_l) else 0
        flat_items.sort(key=lambda x: (float(x.get("score", 0.0)), _rust_pref((x.get("title") or "").lower()), _ts(x.get("published"))), reverse=True)
        featured: List[Dict[str, Any]] = []
        seen_hosts: Set[str] = set()
        for it in flat_items:
            link = it.get("link") or it.get("url") or ""
            try:
                host = canonicalize_url(link).split("//", 1)[-1].split("/", 1)[0]
            except Exception:
                host = ""
            if host in seen_hosts:
                continue
            src = (it.get("source") or "").strip().lower()
            title_l = (it.get("title") or "").lower()
            # Top picks limited to blogs/articles; exclude AWS What's New entirely
            if src == "recent announcements":
                continue
            # Exclude release/version announcements from top picks as well
            if _is_release_like(title_l, src) and not _is_high_signal_release(title_l):
                continue
            featured.append(it)
            seen_hosts.add(host)
            if len(featured) >= max(1, TOP_PICKS_COUNT):
                break
        if featured:
            sections["TOP_PICKS"] = featured
            # Exclude featured items from their sections to avoid duplicates
            feat_keys = {canonicalize_url((it.get("link") or it.get("url") or "")) for it in featured}
            for cat, arr in list(sections.items()):
                if cat == "TOP_PICKS":
                    continue
                sections[cat] = [it for it in arr if canonicalize_url((it.get("link") or it.get("url") or "")) not in feat_keys]

        return _render_markdown(sections)
