from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Tuple

from dev_digest.model import DigestCandidate, DigestItem, DiagnosticRecord, FeedEntry
from dev_digest.utility.constants import (
    PERFORMANCE_TERMS,
    LANGUAGE_FEATURE_TERMS,
    IAC_HIGH_SIGNAL_TERMS,
    AWS_WHATS_NEW_LOW_SIGNAL,
    AWS_REGION_TERMS,
)
from dev_digest.utility.security import strip_html_to_text
from dev_digest.utility.tools import canonicalize_url, normalize_text


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


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


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

    def _ts(self, published: datetime | str | None) -> float:
        if isinstance(published, datetime):
            try:
                return published.timestamp()
            except Exception:
                return 0.0
        if isinstance(published, str) and published:
            try:
                return datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0.0
        return 0.0

    def _topic_tokens(self, title: str) -> set[str]:
        t = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
        stop = {"the", "and", "for", "with", "into", "your", "our", "are", "was", "were", "this", "that", "from", "you", "now", "new", "aws", "blog"}
        return {w for w in t.split() if len(w) > 2 and w not in stop}

    def _diagnostic(
        self,
        *,
        candidate: DigestCandidate | None,
        item: DigestItem | None,
        included: bool,
        reason: str,
        category: str | None = None,
        section: str | None = None,
        position: int | None = None,
        featured: bool = False,
    ) -> DiagnosticRecord:
        if item is not None:
            return DiagnosticRecord(
                title=item.title,
                source=item.source,
                published=item.published,
                link=item.link,
                canonical_url=item.canonical_url,
                category_suggested=category,
                heuristic_score=item.heuristic_score,
                model_score=item.model_score,
                combined_score=item.combined_score,
                included=included,
                reason=reason,
                section=section,
                position_in_section=position,
                featured_top_pick=featured,
            )
        assert candidate is not None
        return DiagnosticRecord(
            title=candidate.title,
            source=candidate.source,
            published=candidate.published,
            link=candidate.link,
            canonical_url=candidate.canonical_url,
            category_suggested=category,
            heuristic_score=0.0,
            model_score=0.0,
            combined_score=0.0,
            included=included,
            reason=reason,
            section=section,
            position_in_section=position,
            featured_top_pick=featured,
        )

    # ---------- pipeline ----------
    def generate(self, items: List[FeedEntry], run_dir: Path) -> Tuple[str, List[DiagnosticRecord]]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", run_dir.name)
        run_date = m.group(1) if m else datetime.now(timezone.utc).date().isoformat()

        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        diagnostics: List[DiagnosticRecord] = []
        candidates: List[DigestCandidate] = []

        for raw in items:
            title = normalize_text(strip_html_to_text(raw.title))
            link = (raw.link or "").strip()
            summary = normalize_text(strip_html_to_text(raw.summary))
            source = normalize_text(raw.source)
            published = raw.published
            canon = canonicalize_url(link)
            title_key = title.casefold()

            candidate = DigestCandidate(
                title=title,
                link=link,
                canonical_url=canon,
                source=source,
                summary=summary,
                published=published,
            )

            tl = title.lower()
            if source.lower() == "recent announcements" and (
                any(k in tl for k in AWS_WHATS_NEW_LOW_SIGNAL)
                or any(term.lower() in tl for term in AWS_REGION_TERMS)
            ):
                diagnostics.append(
                    self._diagnostic(
                        candidate=candidate,
                        item=None,
                        included=False,
                        reason="low_signal",
                        section=None,
                    )
                )
                continue

            if not title and not canon:
                diagnostics.append(
                    self._diagnostic(
                        candidate=candidate,
                        item=None,
                        included=False,
                        reason="dedupe",
                        section=None,
                    )
                )
                continue

            if canon in seen_urls or title_key in seen_titles:
                diagnostics.append(
                    self._diagnostic(
                        candidate=candidate,
                        item=None,
                        included=False,
                        reason="dedupe",
                        section=None,
                    )
                )
                continue

            seen_urls.add(canon)
            seen_titles.add(title_key)

            candidates.append(candidate)

        scored: List[DigestItem] = []
        for candidate in candidates:
            heuristic = round(self._heuristic_score(candidate.title, candidate.summary, candidate.source), 3)
            model_score = round(heuristic, 3)
            combined = round(min(100.0, max(0.0, 0.6 * heuristic + 0.4 * model_score)), 3)
            short_summary = self._short_summary(candidate.summary, 30)
            category = self._infer_category(candidate.title, candidate.source)
            scored.append(
                DigestItem.from_candidate(
                    candidate,
                    short_summary=short_summary,
                    category=category,
                    heuristic_score=heuristic,
                    model_score=model_score,
                    combined_score=combined,
                )
            )

        sections: DefaultDict[str, List[DigestItem]] = defaultdict(list)
        for item in scored:
            sections[item.category].append(item)

        for cat, arr in list(sections.items()):
            arr.sort(key=lambda x: (x.combined_score, self._ts(x.published), x.canonical_url), reverse=True)
            taken = [False] * len(arr)
            merged: List[DigestItem] = []
            for idx, item in enumerate(arr):
                if taken[idx]:
                    continue
                tokens_i = self._topic_tokens(item.title)
                best = item
                for j in range(idx + 1, len(arr)):
                    if taken[j]:
                        continue
                    other = arr[j]
                    tokens_j = self._topic_tokens(other.title)
                    if not tokens_i or not tokens_j:
                        continue
                    intersection = len(tokens_i & tokens_j)
                    union = len(tokens_i | tokens_j)
                    similarity = intersection / union if union else 0.0
                    try:
                        host_a = canonicalize_url(item.link).split("//", 1)[-1].split("/", 1)[0]
                        host_b = canonicalize_url(other.link).split("//", 1)[-1].split("/", 1)[0]
                        same_host = host_a == host_b
                    except Exception:
                        same_host = True
                    if similarity >= 0.6 and same_host:
                        diagnostics.append(
                            self._diagnostic(
                                candidate=None,
                                item=other,
                                included=False,
                                reason="merged_duplicate",
                                category=cat,
                                section=None,
                            )
                        )
                        if self._ts(other.published) >= self._ts(best.published):
                            best = other
                        taken[j] = True
                merged.append(best)
                taken[idx] = True
            if len(merged) > self.per_section_cap:
                for item in merged[self.per_section_cap:]:
                    diagnostics.append(
                        self._diagnostic(
                            candidate=None,
                            item=item,
                            included=False,
                            reason="per_section_cap",
                            category=cat,
                            section=None,
                        )
                    )
                merged = merged[: self.per_section_cap]
            sections[cat] = merged

        aws_items = sections.get("AWS & Cloud", [])
        if aws_items:
            non_ra = [it for it in aws_items if it.source.strip().lower() != "recent announcements"]
            ra_items = [it for it in aws_items if it.source.strip().lower() == "recent announcements"]
            max_ra = 2
            capped = non_ra + ra_items[:max_ra]
            for item in ra_items[max_ra:]:
                diagnostics.append(
                    self._diagnostic(
                        candidate=None,
                        item=item,
                        included=False,
                        reason="ra_microcap",
                        category="AWS & Cloud",
                        section=None,
                    )
                )
            sections["AWS & Cloud"] = capped[: self.per_section_cap]

        all_items = [it for cat in SECTION_ORDER for it in sections.get(cat, [])]
        if len(all_items) > self.max_total:
            sorted_items = sorted(all_items, key=lambda x: (x.combined_score, self._ts(x.published)))
            keep_ids = {id(item) for item in sorted_items[-self.max_total:]}
            new_sections: DefaultDict[str, List[DigestItem]] = defaultdict(list)
            for cat in SECTION_ORDER:
                for item in sections.get(cat, []):
                    if id(item) in keep_ids:
                        new_sections[cat].append(item)
                    else:
                        diagnostics.append(
                            self._diagnostic(
                                candidate=None,
                                item=item,
                                included=False,
                                reason="global_cap",
                                category=cat,
                                section=None,
                            )
                        )
            sections = new_sections

        def is_release_like(title_l: str) -> bool:
            return bool(
                re.search(r"kubernetes v\d+\.\d+", title_l)
                or re.search(r"\brelease notes\b", title_l)
                or re.search(r"graduates to (beta|stable)", title_l)
                or re.search(r"\bintroducing\b", title_l)
                or re.search(r"now available", title_l)
            )

        flat_sorted = sorted(
            [it for cat in SECTION_ORDER for it in sections.get(cat, [])],
            key=lambda it: (
                it.combined_score,
                (
                    ("rust" in it.title.lower() or "memory safety" in it.title.lower())
                    or any(term in it.title.lower() for term in PERFORMANCE_TERMS)
                    or any(term in it.title.lower() for term in IAC_HIGH_SIGNAL_TERMS)
                ),
                self._ts(it.published),
            ),
            reverse=True,
        )

        featured: List[DigestItem] = []
        seen_hosts: set[str] = set()
        for item in flat_sorted:
            src = item.source.strip().lower()
            if src == "recent announcements":
                continue
            title_lower = item.title.lower()
            if is_release_like(title_lower) and not any(k in title_lower for k in IAC_HIGH_SIGNAL_TERMS):
                continue
            if any(k in title_lower for k in ["primer", "beginner", "how to", "tutorial", "introduction", "introduct"]):
                continue
            host = canonicalize_url(item.link).split("//", 1)[-1].split("/", 1)[0]
            if host in seen_hosts:
                continue
            featured.append(item)
            seen_hosts.add(host)
            if len(featured) >= max(1, self.top_picks):
                break

        featured_canons = {it.canonical_url for it in featured}
        for cat in list(sections.keys()):
            sections[cat] = [it for it in sections[cat] if it.canonical_url not in featured_canons]

        lines: List[str] = []
        lines.append(f"# Dev Digest — Week of {run_date}")
        lines.append("")
        if featured:
            lines.append("## Interesting Reads")
            for item in featured:
                title = item.title.strip()
                source = item.source.strip()
                link = item.link
                date_str = run_date
                if isinstance(item.published, datetime):
                    date_str = item.published.date().isoformat()
                summary = item.short_summary.strip()
                words = summary.split()
                if len(words) > 30:
                    summary = " ".join(words[:30])
                if summary and not summary.endswith((".", "!", "?")):
                    summary += "."
                head = f"**{title} ({source})**" if source else f"**{title}**"
                read_more = f" Read: {link}" if link else ""
                lines.append(f"- ⭐ {head} — {date_str}: {summary}{read_more}")
                diagnostics.append(
                    self._diagnostic(
                        candidate=None,
                        item=item,
                        included=True,
                        reason="included",
                        category="Interesting Reads",
                        section="Interesting Reads",
                        position=None,
                        featured=True,
                    )
                )
            lines.append("")

        for cat in SECTION_ORDER:
            arr = sections.get(cat, [])
            if not arr:
                continue
            lines.append(f"## {cat}")
            for pos, item in enumerate(arr):
                title = item.title.strip()
                source = item.source.strip()
                link = item.link
                date_str = run_date
                if isinstance(item.published, datetime):
                    date_str = item.published.date().isoformat()
                summary = item.short_summary.strip()
                words = summary.split()
                if len(words) > 30:
                    summary = " ".join(words[:30])
                if summary and not summary.endswith((".", "!", "?")):
                    summary += "."
                head = f"**{title} ({source})**" if source else f"**{title}**"
                read_more = f" Read: {link}" if link else ""
                lines.append(f"- {head} — {date_str}: {summary}{read_more}")
                diagnostics.append(
                    self._diagnostic(
                        candidate=None,
                        item=item,
                        included=True,
                        reason="included",
                        category=cat,
                        section=cat,
                        position=pos,
                        featured=False,
                    )
                )

        markdown = "\n".join(lines).rstrip() + "\n"
        return markdown, diagnostics

    # ---------- IO helpers ----------
    def write_outputs(self, run_dir: Path, markdown: str, diagnostics: List[DiagnosticRecord], debug: bool = False) -> Path:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", run_dir.name)
        run_date = m.group(1) if m else datetime.now(timezone.utc).date().isoformat()
        digest_file = run_dir / f"dev_digest_newsletter_{run_date.replace('-', '_')}.md"
        digest_file.write_text(markdown, encoding="utf-8")

        if debug:
            diag_dicts = [d.to_dict() for d in diagnostics]

            debug_json = run_dir / "debug_ranking.json"
            debug_json.write_text(json.dumps(diag_dicts, default=_json_default, indent=2), encoding="utf-8")

            cols = [
                "title",
                "source",
                "published",
                "link",
                "canonical_url",
                "category_suggested",
                "heuristic_score",
                "model_score",
                "combined_score",
                "included",
                "reason",
                "section",
                "position_in_section",
                "featured_top_pick",
            ]
            debug_csv = run_dir / "debug_ranking.csv"
            with debug_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                for row in diag_dicts:
                    writer.writerow({k: row.get(k, "") for k in cols})

            included = [d for d in diagnostics if d.included]
            by_host = Counter(
                canonicalize_url(d.link).split("//", 1)[-1].split("/", 1)[0]
                for d in included
            )
            by_section = Counter(d.section or "" for d in included)
            top10 = sorted(
                included,
                key=lambda x: (x.combined_score, self._ts(x.published)),
                reverse=True,
            )[:10]
            discarded: Dict[str, List[DiagnosticRecord]] = defaultdict(list)
            for d in diagnostics:
                if not d.included:
                    discarded[d.reason or "other"].append(d)

            lines_md: List[str] = []
            lines_md.append("# Debug Ranking Summary")
            lines_md.append("")
            lines_md.append("## Included counts by host")
            for host, count in by_host.most_common():
                lines_md.append(f"- {host or '(unknown)'}: {count}")
            lines_md.append("")
            lines_md.append("## Included counts by section")
            for section, count in by_section.most_common():
                lines_md.append(f"- {section or '(none)'}: {count}")
            lines_md.append("")
            lines_md.append("## Top 10 included by score")
            for record in top10:
                lines_md.append(f"- {record.combined_score:>5} — {record.title} ({record.source})")
            lines_md.append("")
            lines_md.append("## Discarded items by reason")
            for reason, entries in discarded.items():
                lines_md.append(f"### {reason}")
                for record in sorted(entries, key=lambda x: (x.combined_score, self._ts(x.published)), reverse=True)[:30]:
                    lines_md.append(f"- {record.combined_score:>5} — {record.title} ({record.source})")

            (run_dir / "debug_ranking.md").write_text("\n".join(lines_md) + "\n", encoding="utf-8")

        return digest_file
