import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dev_digest.utility.tools import canonicalize_url, normalize_text
from dev_digest.utility.security import strip_html_to_text
from dev_digest.utility.constants import (
    PERFORMANCE_TERMS,
    LANGUAGE_FEATURE_TERMS,
    IAC_HIGH_SIGNAL_TERMS,
)


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


class DeterministicDigest:
    def __init__(self,
                 per_section_cap: int = 8,
                 max_total: int = 50,
                 top_picks: int = 2) -> None:
        self.per_section_cap = per_section_cap
        self.max_total = max_total
        self.top_picks = top_picks

    # ---------- heuristics ----------
    def _heuristic_score(self, title: str, summary: str, source: str) -> float:
        t = (title or "").lower()
        s = (source or "").lower()
        suml = (summary or "").lower()
        score = 0.0

        if any(k in t for k in ["generally available", "ga ", "ga:", "stable release", "v1.0"]):
            score += 28
        if any(k in t for k in ["preview", "public preview", "beta"]):
            score += 16
        if any(k in t for k in ["postmortem", "incident", "outage", "root cause"]):
            score += 32
        if "cve-" in t or "cve-" in suml or "0-day" in t or "security" in t:
            score += 26
        if any(k in t for k in ["deprecate", "breaking change", "removed", "end of support"]):
            score += 24
        if any(k in t for k in PERFORMANCE_TERMS):
            score += 18
        if any(k in s for k in ["cloudflare", "github", "google", "microsoft"]):
            score += 6
        if any(k in t for k in ["open source", "oss", "released", "announce"]):
            score += 10

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
        if any(k in t for k in IAC_HIGH_SIGNAL_TERMS) and (
            re.search(r"\bv\d+\.\d+\b", t) or "release" in t or "changelog" in t or "what's new" in t
        ):
            score += 16

        if any(k in t for k in ["webinar", "podcast", "training", "certification", "partner", "regional"]):
            score -= 30
        if any(k in t for k in [
            "unlocking", "next-generation", "game-changing", "supercharge", "ultimate", "transformative",
            "revolutionize", "revolutionizing", "seamless", "empower", "unleash"
        ]):
            score -= 14
        return max(0.0, min(100.0, score))

    # ---------- helpers ----------
    def _short_summary(self, text: str, max_words: int = 30) -> str:
        txt = (text or "").strip()
        parts = re.split(r"(?<=[.!?])\s+", txt)
        candidate = parts[0] if parts and parts[0] else txt
        words = candidate.split()
        if len(words) > max_words:
            candidate = " ".join(words[:max_words])
        return candidate.strip()

    def _infer_category(self, title: str, source: str) -> str:
        t = (title or "").lower()
        s = (source or "").lower()
        if ("security" in s) or ("security" in t) or ("cve" in t) or any(
            k in t for k in ["honeypot", "malware", "ransomware", "exploit", "vulnerability", "attack", "zero-day", "0-day"]
        ):
            return "Security Alerts"
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

    def _ts(self, iso: str | None) -> float:
        if not iso:
            return 0.0
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _topic_tokens(self, title: str) -> set[str]:
        t = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
        stop = {"the", "and", "for", "with", "into", "your", "our", "are", "was", "were", "this", "that", "from", "you", "now", "new", "aws", "blog"}
        return {w for w in t.split() if len(w) > 2 and w not in stop}

    # ---------- pipeline ----------
    def generate(self, items: List[Dict[str, Any]], run_dir: Path) -> Tuple[str, List[Dict[str, Any]]]:
        run_date = run_dir.name.split("_", 1)[0] if "_" in run_dir.name else datetime.now(timezone.utc).date().isoformat()

        # Normalize and de-dupe
        norm_items: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        diagnostics: List[Dict[str, Any]] = []

        for raw in items:
            title = normalize_text(strip_html_to_text(raw.get("title") or ""))
            url = (raw.get("link") or raw.get("url") or "").strip()
            canon = canonicalize_url(url)
            source = normalize_text((raw.get("source") or "").strip())
            summary = normalize_text(strip_html_to_text(raw.get("summary") or ""))
            published_dt = raw.get("published")
            published = published_dt.isoformat() if isinstance(published_dt, datetime) else (
                (published_dt or None)
            )

            title_key = title.casefold()
            if not title and not canon:
                diagnostics.append({"title": title, "source": source, "published": published, "link": url,
                                   "canonical_url": canon, "category_suggested": None,
                                   "heuristic_score": 0, "model_score": 0, "combined_score": 0,
                                   "included": False, "reason": "dedupe", "section": None,
                                   "position_in_section": None, "featured_top_pick": False})
                continue
            if canon in seen_urls or title_key in seen_titles:
                diagnostics.append({"title": title, "source": source, "published": published, "link": url,
                                   "canonical_url": canon, "category_suggested": None,
                                   "heuristic_score": 0, "model_score": 0, "combined_score": 0,
                                   "included": False, "reason": "dedupe", "section": None,
                                   "position_in_section": None, "featured_top_pick": False})
                continue
            seen_urls.add(canon)
            seen_titles.add(title_key)

            norm_items.append({
                "title": title, "link": url, "canon": canon, "source": source,
                "summary": summary, "published": published
            })

        # Score, categorize, summarize
        for it in norm_items:
            h = self._heuristic_score(it["title"], it["summary"], it["source"])
            it["heuristic_score"] = round(h, 3)
            it["model_score"] = round(h, 3)
            it["combined_score"] = round(min(100.0, max(0.0, 0.6 * h + 0.4 * h)), 3)
            it["short_summary"] = self._short_summary(it["summary"], 30)
            it["category"] = self._infer_category(it["title"], it["source"])

        # Selection per section with near-duplicate merge
        sections: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for it in norm_items:
            sections[it["category"]].append(it)

        for cat, arr in list(sections.items()):
            arr.sort(key=lambda x: (x["combined_score"], self._ts(x["published"]), x["canon"]), reverse=True)
            taken = [False] * len(arr)
            merged: List[Dict[str, Any]] = []
            for i, it in enumerate(arr):
                if taken[i]:
                    continue
                toks_i = self._topic_tokens(it["title"])
                best = it
                for j in range(i + 1, len(arr)):
                    if taken[j]:
                        continue
                    tj = self._topic_tokens(arr[j]["title"])
                    if not toks_i or not tj:
                        continue
                    inter = len(toks_i & tj)
                    union = len(toks_i | tj)
                    sim = inter / union if union else 0.0
                    same_host = True
                    try:
                        h1 = canonicalize_url(it.get("link") or "").split("//", 1)[-1].split("/", 1)[0]
                        h2 = canonicalize_url(arr[j].get("link") or "").split("//", 1)[-1].split("/", 1)[0]
                        same_host = h1 == h2
                    except Exception:
                        pass
                    if sim >= 0.6 and same_host:
                        diagnostics.append({
                            "title": arr[j]["title"], "source": arr[j]["source"], "published": arr[j]["published"],
                            "link": arr[j]["link"], "canonical_url": arr[j]["canon"], "category_suggested": cat,
                            "heuristic_score": arr[j]["heuristic_score"], "model_score": arr[j]["model_score"],
                            "combined_score": arr[j]["combined_score"], "included": False, "reason": "merged_duplicate",
                            "section": None, "position_in_section": None, "featured_top_pick": False,
                        })
                        if self._ts(arr[j]["published"]) >= self._ts(best["published"]):
                            best = arr[j]
                        taken[j] = True
                merged.append(best)
                taken[i] = True
            if len(merged) > self.per_section_cap:
                for it in merged[self.per_section_cap:]:
                    diagnostics.append({
                        "title": it["title"], "source": it["source"], "published": it["published"], "link": it["link"],
                        "canonical_url": it["canon"], "category_suggested": cat, "heuristic_score": it["heuristic_score"],
                        "model_score": it["model_score"], "combined_score": it["combined_score"], "included": False,
                        "reason": "per_section_cap", "section": None, "position_in_section": None, "featured_top_pick": False,
                    })
                merged = merged[: self.per_section_cap]
            sections[cat] = merged

        # Global cap
        all_items = [it for cat in SECTION_ORDER for it in sections.get(cat, [])]
        if len(all_items) > self.max_total:
            all_items.sort(key=lambda x: (x["combined_score"], self._ts(x["published"])))
            keep_ids = set(id(x) for x in all_items[-self.max_total:])
            new_sections: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for cat in SECTION_ORDER:
                for it in sections.get(cat, []):
                    if id(it) in keep_ids:
                        new_sections[cat].append(it)
                    else:
                        diagnostics.append({
                            "title": it["title"], "source": it["source"], "published": it["published"], "link": it["link"],
                            "canonical_url": it["canon"], "category_suggested": cat, "heuristic_score": it["heuristic_score"],
                            "model_score": it["model_score"], "combined_score": it["combined_score"], "included": False,
                            "reason": "global_cap", "section": None, "position_in_section": None, "featured_top_pick": False,
                        })
            sections = new_sections

        # Top picks selection (exclude AWS What's New; exclude generic releases; allow IaC release exception)
        def is_release_like(title_l: str) -> bool:
            return bool(re.search(r"kubernetes v\d+\.\d+", title_l) or
                        re.search(r"\brelease notes\b", title_l) or
                        re.search(r"graduates to (beta|stable)", title_l) or
                        re.search(r"\bintroducing\b", title_l) or
                        re.search(r"now available", title_l))

        flat_sorted = sorted([it for cat in SECTION_ORDER for it in sections.get(cat, [])],
                             key=lambda x: (x["combined_score"],
                                            ("rust" in x.get("title", "").lower() or "memory safety" in x.get("title", "").lower()),
                                            self._ts(x["published"])), reverse=True)
        featured: List[Dict[str, Any]] = []
        seen_hosts: set[str] = set()
        for it in flat_sorted:
            src = (it.get("source") or "").strip().lower()
            if src == "recent announcements":
                continue
            tl = (it.get("title") or "").lower()
            if is_release_like(tl) and not any(k in tl for k in IAC_HIGH_SIGNAL_TERMS):
                continue
            host = canonicalize_url(it.get("link") or "").split("//", 1)[-1].split("/", 1)[0]
            if host in seen_hosts:
                continue
            featured.append(it)
            seen_hosts.add(host)
            if len(featured) >= max(1, self.top_picks):
                break

        # Remove featured from sections and render
        featured_canons = {it["canon"] for it in featured}
        for cat in list(sections.keys()):
            sections[cat] = [it for it in sections[cat] if it["canon"] not in featured_canons]

        lines: List[str] = []
        lines.append(f"# Dev Digest — Week of {run_date}")
        lines.append("")
        if featured:
            lines.append("## Interesting Reads")
            for it in featured:
                title = it["title"].strip()
                source = it["source"].strip()
                link = it["link"]
                date_str = run_date
                if it["published"]:
                    try:
                        date_str = datetime.fromisoformat(str(it["published"]).replace("Z", "+00:00")).date().isoformat()
                    except Exception:
                        pass
                summ = it["short_summary"].strip()
                words = summ.split()
                if len(words) > 30:
                    summ = " ".join(words[:30])
                if not summ.endswith((".", "!", "?")):
                    summ = summ + "."
                head = f"**{title} ({source})**" if source else f"**{title}**"
                read_more = f" Read: {link}" if link else ""
                lines.append(f"- ⭐ {head} — {date_str}: {summ}{read_more}")
            lines.append("")

        for cat in SECTION_ORDER:
            arr = sections.get(cat, [])
            if not arr:
                continue
            lines.append(f"## {cat}")
            for pos, it in enumerate(arr):
                title = it["title"].strip()
                source = it["source"].strip()
                link = it["link"]
                date_str = run_date
                if it["published"]:
                    try:
                        date_str = datetime.fromisoformat(str(it["published"]).replace("Z", "+00:00")).date().isoformat()
                    except Exception:
                        pass
                summ = it["short_summary"].strip()
                words = summ.split()
                if len(words) > 30:
                    summ = " ".join(words[:30])
                if not summ.endswith((".", "!", "?")):
                    summ = summ + "."
                head = f"**{title} ({source})**" if source else f"**{title}**"
                read_more = f" Read: {link}" if link else ""
                lines.append(f"- {head} — {date_str}: {summ}{read_more}")
                diagnostics.append({
                    "title": title, "source": source, "published": it["published"], "link": link, "canonical_url": it["canon"],
                    "category_suggested": cat, "heuristic_score": it["heuristic_score"], "model_score": it["model_score"],
                    "combined_score": it["combined_score"], "included": True, "reason": "included", "section": cat,
                    "position_in_section": pos, "featured_top_pick": False,
                })

        for it in featured:
            diagnostics.append({
                "title": it["title"], "source": it["source"], "published": it["published"], "link": it["link"],
                "canonical_url": it["canon"], "category_suggested": "Interesting Reads",
                "heuristic_score": it["heuristic_score"], "model_score": it["model_score"], "combined_score": it["combined_score"],
                "included": True, "reason": "included", "section": "Interesting Reads", "position_in_section": None,
                "featured_top_pick": True,
            })

        markdown = "\n".join(lines).rstrip() + "\n"
        return markdown, diagnostics

    # ---------- IO helpers ----------
    def write_outputs(self, run_dir: Path, markdown: str, diagnostics: List[Dict[str, Any]], debug: bool = False) -> Path:
        # Digest
        run_date = run_dir.name.split("_", 1)[0] if "_" in run_dir.name else datetime.now(timezone.utc).date().isoformat()
        digest_file = run_dir / f"dev_digest_newsletter_{run_date.replace('-', '_')}.md"
        digest_file.write_text(markdown, encoding="utf-8")

        # Diagnostics (only in debug mode)
        if debug:
            debug_json = run_dir / "debug_ranking.json"
            debug_json.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

            # CSV
            cols = [
                "title", "source", "published", "link", "canonical_url", "category_suggested", "heuristic_score",
                "model_score", "combined_score", "included", "reason", "section", "position_in_section", "featured_top_pick",
            ]
            debug_csv = run_dir / "debug_ranking.csv"
            with debug_csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for row in diagnostics:
                    w.writerow({k: row.get(k, "") for k in cols})

            # Markdown summary
            by_host = Counter(canonicalize_url(d.get("link", "")).split("//", 1)[-1].split("/", 1)[0] for d in diagnostics if d.get("included"))
            by_section = Counter(d.get("section", "") for d in diagnostics if d.get("included"))
            top10 = sorted(
                [d for d in diagnostics if d.get("included")],
                key=lambda x: (x.get("combined_score", 0), self._ts(x.get("published"))), reverse=True
            )[:10]
            discarded_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for d in diagnostics:
                if not d.get("included"):
                    discarded_groups[d.get("reason", "other")].append(d)

            lines_md: List[str] = []
            lines_md.append("# Debug Ranking Summary")
            lines_md.append("")
            lines_md.append("## Included counts by host")
            for h, c in by_host.most_common():
                lines_md.append(f"- {h or '(unknown)'}: {c}")
            lines_md.append("")
            lines_md.append("## Included counts by section")
            for s, c in by_section.most_common():
                lines_md.append(f"- {s or '(none)'}: {c}")
            lines_md.append("")
            lines_md.append("## Top 10 included by score")
            for r in top10:
                lines_md.append(f"- {r['combined_score']:>5} — {r['title']} ({r['source']})")
            lines_md.append("")
            lines_md.append("## Discarded items by reason")
            for reason, arr in discarded_groups.items():
                lines_md.append(f"### {reason}")
                for r in sorted(arr, key=lambda x: (x.get('combined_score', 0), self._ts(x.get('published'))), reverse=True)[:30]:
                    lines_md.append(f"- {r.get('combined_score', 0):>5} — {r.get('title', '')} ({r.get('source', '')})")

            (run_dir / "debug_ranking.md").write_text("\n".join(lines_md) + "\n", encoding="utf-8")

        return digest_file
