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
    PRACTICAL_TERMS,
)
from dev_digest.utility.security import strip_html_to_text
from dev_digest.utility.tools import canonicalize_url, normalize_text
from dev_digest.utility.scoring import (
    classify_recent_announcement,
    get_profile,
    score_candidate,
)
from dev_digest.utility.sections import ordered_sections, resolve_section
from dev_digest.utility.filters import should_exclude_link
from dev_digest.utility.transform import format_release_title

FRESHNESS_WINDOW_DAYS = 14


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
        self.scoring_profile = get_profile("deterministic")
        self.ra_section_caps: Dict[str, int | None] = {
            "critical": 5,
            "high": 6,
            "medium": 6,
            "low": 4,
        }

    # ---------- helpers ----------
    def _short_summary(self, text: str, max_words: int = 30) -> str:
        txt = (text or "").strip()
        parts = re.split(r"(?<=[.!?])\s+", txt)
        candidate = parts[0] if parts and parts[0] else txt
        words = candidate.split()
        if len(words) > max_words:
            candidate = " ".join(words[:max_words])
        return candidate.strip()

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

    def _has_practical_signal(self, item: DigestItem) -> bool:
        text = f"{item.title} {item.summary}".lower()
        return any(term in text for term in PRACTICAL_TERMS)

    def _freshness_score(self, published: datetime | None, run_dt: datetime) -> float:
        if not isinstance(published, datetime):
            return 0.0
        try:
            delta_days = (run_dt.date() - published.date()).days
        except Exception:
            return 0.0
        if delta_days <= 0:
            return 100.0
        if delta_days >= FRESHNESS_WINDOW_DAYS:
            return 0.0
        return round(100.0 * (1 - (delta_days / FRESHNESS_WINDOW_DAYS)), 3)

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
        aws_severity: str | None = None,
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
                aws_severity=aws_severity,
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
            aws_severity=aws_severity,
        )

    # ---------- pipeline ----------
    def generate(self, items: List[FeedEntry], run_dir: Path) -> Tuple[str, List[DiagnosticRecord]]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", run_dir.name)
        run_date = m.group(1) if m else datetime.now(timezone.utc).date().isoformat()

        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        diagnostics: List[DiagnosticRecord] = []
        candidates: List[DigestCandidate] = []
        run_dt = datetime.fromisoformat(run_date)
        section_defs = ordered_sections()

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

            if should_exclude_link(link):
                diagnostics.append(
                    self._diagnostic(
                        candidate=candidate,
                        item=None,
                        included=False,
                        reason="path_filter",
                        section=None,
                    )
                )
                continue

            candidates.append(candidate)

        scored: List[DigestItem] = []
        aws_recent_announcements: List[tuple[DigestItem, str]] = []

        for candidate in candidates:
            release_info = format_release_title(candidate.title, candidate.link)
            if release_info.is_release:
                candidate.title = release_info.title
                if release_info.is_prerelease:
                    diagnostics.append(
                        self._diagnostic(
                            candidate=candidate,
                            item=None,
                            included=False,
                            reason="release_prerelease",
                            section=None,
                        )
                    )
                    continue

            freshness = self._freshness_score(candidate.published, run_dt)
            heuristic, model_score, combined = score_candidate(
                candidate,
                self.scoring_profile,
                model_score=freshness,
            )
            short_summary = self._short_summary(candidate.summary, 30)
            section_meta = resolve_section(candidate.title, candidate.source, candidate.link, candidate.summary)
            item = DigestItem.from_candidate(
                candidate,
                short_summary=short_summary,
                category=section_meta.title,
                heuristic_score=heuristic,
                model_score=model_score,
                combined_score=combined,
            )

            if candidate.source.strip().lower() == "recent announcements":
                severity = classify_recent_announcement(candidate)
                aws_recent_announcements.append((item, severity))
                diagnostics.append(
                    self._diagnostic(
                        candidate=None,
                        item=item,
                        included=False,
                        reason="aws_ra_section",
                        category="AWS Recent Announcements",
                        section=None,
                        aws_severity=severity,
                    )
                )
                continue
            scored.append(item)

        ra_severity_map = {item.canonical_url: severity for item, severity in aws_recent_announcements}

        sections_map: DefaultDict[str, List[DigestItem]] = defaultdict(list)
        for item in scored:
            section_slug = resolve_section(item.title, item.source, item.link, item.summary).slug
            sections_map[section_slug].append(item)

        # Keep Security & Alerts focused on actionable incidents/advisories.
        security_required_terms = (
            "cve",
            "vulnerab",
            "exploit",
            "attack",
            "malware",
            "ransom",
            "breach",
            "zero-day",
            "0-day",
            "patch",
            "security bulletin",
            "incident",
            "compromise",
            "leak",
        )
        security_items = sections_map.get("security") or []
        if security_items:
            kept: List[DigestItem] = []
            reassigned: List[DigestItem] = []
            for item in security_items:
                text = f"{item.title} {item.summary}".lower()
                if any(term in text for term in security_required_terms):
                    kept.append(item)
                else:
                    reassigned.append(item)
            sections_map["security"] = kept
            if reassigned:
                sections_map.setdefault("aws_cloud", []).extend(reassigned)

        overflow_to_misc: List[DigestItem] = []
        for section_meta in ordered_sections():
            arr = sections_map.get(section_meta.slug, [])
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
                                category=section_meta.title,
                                section=None,
                            )
                        )
                        if self._ts(other.published) >= self._ts(best.published):
                            best = other
                        taken[j] = True
                merged.append(best)
                taken[idx] = True
            cap = section_meta.max_items
            if self.per_section_cap:
                cap = min(cap, self.per_section_cap)
            if len(merged) > cap:
                overflow = merged[cap:]
                keep = merged[:cap]
                for item in overflow:
                    if self._has_practical_signal(item):
                        overflow_to_misc.append(item)
                    else:
                        diagnostics.append(
                            self._diagnostic(
                                candidate=None,
                                item=item,
                                included=False,
                                reason="per_section_cap",
                                category=section_meta.title,
                                section=None,
                            )
                        )
                merged = keep
            sections_map[section_meta.slug] = merged

        if overflow_to_misc:
            sections_map.setdefault("misc", []).extend(overflow_to_misc)

        all_items = [it for section_meta in section_defs for it in sections_map.get(section_meta.slug, [])]
        if len(all_items) > self.max_total:
            sorted_items = sorted(all_items, key=lambda x: (x.combined_score, self._ts(x.published)))
            keep_ids = {id(item) for item in sorted_items[-self.max_total:]}
            new_sections: DefaultDict[str, List[DigestItem]] = defaultdict(list)
            for section_meta in section_defs:
                for item in sections_map.get(section_meta.slug, []):
                    if id(item) in keep_ids:
                        new_sections[section_meta.slug].append(item)
                    else:
                        diagnostics.append(
                            self._diagnostic(
                                candidate=None,
                                item=item,
                                included=False,
                                reason="global_cap",
                                category=section_meta.title,
                                section=None,
                            )
                        )
            sections_map = new_sections

        def is_release_like(title_l: str) -> bool:
            return bool(
                re.search(r"kubernetes v\d+\.\d+", title_l)
                or re.search(r"\brelease notes\b", title_l)
                or re.search(r"graduates to (beta|stable)", title_l)
                or re.search(r"\bintroducing\b", title_l)
                or re.search(r"now available", title_l)
            )

        flat_sorted = sorted(
            [it for section_meta in section_defs for it in sections_map.get(section_meta.slug, [])],
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

        high_severity_ra = [it for it, sev in aws_recent_announcements if sev in {"critical", "high"}]
        flat_sorted.extend(high_severity_ra)

        featured: List[DigestItem] = []
        seen_hosts: set[str] = set()
        for item in flat_sorted:
            src = item.source.strip().lower()
            if src == "recent announcements":
                continue
            if "security bulletin" in src or "security bulletins" in src:
                continue
            title_lower = item.title.lower()
            if "(release notes" in title_lower or "(pre-release" in title_lower:
                continue
            if is_release_like(title_lower) and not any(k in title_lower for k in IAC_HIGH_SIGNAL_TERMS):
                continue
            if any(k in title_lower for k in ["primer", "beginner", "how to", "tutorial", "introduction", "introduct"]):
                continue
            if any(term in title_lower for term in ["kubecon", "cloudnativecon", "conference", "summit", "event day", "open source securitycon"]):
                continue
            host = canonicalize_url(item.link).split("//", 1)[-1].split("/", 1)[0]
            if host in seen_hosts:
                continue
            featured.append(item)
            seen_hosts.add(host)
            if len(featured) >= max(1, self.top_picks):
                break

        featured_canons = {it.canonical_url for it in featured}
        for section_meta in section_defs:
            if section_meta.slug in sections_map:
                sections_map[section_meta.slug] = [
                    item for item in sections_map[section_meta.slug] if item.canonical_url not in featured_canons
                ]

        lines: List[str] = []
        lines.append(f"# Dev Digest — Week of {run_date}")
        lines.append("")
        lines.append("Aggregated tech stuff that happened this week without the marketing noise.")
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
                lines.append(f"- {head} — {date_str}: {summary}{read_more}")
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
                        aws_severity=ra_severity_map.get(item.canonical_url),
                    )
                )
            lines.append("")

        # AWS Recent Announcements section
        severity_order = ["critical", "high", "medium", "low"]
        severity_labels = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        selected_ra: Dict[str, List[DigestItem]] = {}
        for severity in severity_order:
            items = [item for item, sev in aws_recent_announcements if sev == severity]
            if not items:
                continue
            items.sort(key=lambda x: self._ts(x.published), reverse=True)
            cap = self.ra_section_caps.get(severity)
            if cap is not None and cap >= 0:
                trimmed = items[cap:]
                for item in trimmed:
                    diagnostics.append(
                        self._diagnostic(
                            candidate=None,
                            item=item,
                            included=False,
                            reason="aws_ra_cap",
                            category="AWS Recent Announcements",
                            section=None,
                            aws_severity=severity,
                        )
                    )
                items = items[:cap]
            if items:
                selected_ra[severity] = items

        if selected_ra:
            lines.append("## AWS Recent Announcements")
            impact_labels = {
                "critical": "Critical Impact",
                "high": "High Impact",
                "medium": "Medium Impact",
                "low": "Low Impact",
            }
            order_counter = 0
            for severity in severity_order:
                group = selected_ra.get(severity)
                if not group:
                    continue
                lines.append(f"### {impact_labels[severity]}")
                for item in group:
                    date_str = run_date
                    if isinstance(item.published, datetime):
                        date_str = item.published.date().isoformat()
                    title = item.title.strip()
                    link = item.link
                    bullet = f"- {date_str} — [{title}]({link})" if link else f"- {date_str} — {title}"
                    lines.append(bullet)
                    diagnostics.append(
                        self._diagnostic(
                            candidate=None,
                            item=item,
                            included=True,
                            reason="included",
                            category="AWS Recent Announcements",
                            section="AWS Recent Announcements",
                            position=order_counter,
                            featured=False,
                            aws_severity=severity,
                        )
                    )
                    order_counter += 1
                lines.append("")

        for section_meta in section_defs:
            arr = sections_map.get(section_meta.slug, [])
            if not arr:
                continue
            lines.append(f"## {section_meta.title}")
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
                        category=section_meta.title,
                        section=section_meta.title,
                        position=pos,
                        featured=False,
                        aws_severity=ra_severity_map.get(item.canonical_url),
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
            by_severity = Counter(d.aws_severity or "" for d in included if d.aws_severity)
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
            if by_severity:
                lines_md.append("## AWS Recent Announcements by severity")
                for severity, count in by_severity.most_common():
                    lines_md.append(f"- {severity}: {count}")
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
