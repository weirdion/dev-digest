from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(slots=True)
class FeedEntry:
    """Normalized feed article returned by ingestion."""

    title: str
    link: str
    summary: str
    source: str
    published: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "summary": self.summary,
            "source": self.source,
            "published": self.published,
        }


@dataclass(slots=True)
class DigestCandidate:
    """Feed entry augmented with canonical URL used for scoring and dedupe."""

    title: str
    link: str
    canonical_url: str
    source: str
    summary: str
    published: Optional[datetime] = None

    @classmethod
    def from_feed_entry(cls, entry: FeedEntry, canonical_url: str) -> "DigestCandidate":
        return cls(
            title=entry.title,
            link=entry.link,
            canonical_url=canonical_url,
            source=entry.source,
            summary=entry.summary,
            published=entry.published,
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "canonical_url": self.canonical_url,
            "source": self.source,
            "summary": self.summary,
            "published": self.published,
        }


@dataclass(slots=True)
class DigestItem:
    """Scored digest entry ready for rendering."""

    title: str
    link: str
    canonical_url: str
    source: str
    summary: str
    published: Optional[datetime]
    short_summary: str
    category: str
    heuristic_score: float
    model_score: float
    combined_score: float

    @classmethod
    def from_candidate(
        cls,
        candidate: DigestCandidate,
        short_summary: str,
        category: str,
        heuristic_score: float,
        model_score: float,
        combined_score: float,
    ) -> "DigestItem":
        return cls(
            title=candidate.title,
            link=candidate.link,
            canonical_url=candidate.canonical_url,
            source=candidate.source,
            summary=candidate.summary,
            published=candidate.published,
            short_summary=short_summary,
            category=category,
            heuristic_score=heuristic_score,
            model_score=model_score,
            combined_score=combined_score,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class DiagnosticRecord:
    """Diagnostic entry describing inclusion/exclusion decisions."""

    title: str
    source: str
    published: Optional[datetime]
    link: str
    canonical_url: str
    category_suggested: Optional[str]
    heuristic_score: float
    model_score: float
    combined_score: float
    included: bool
    reason: str
    section: Optional[str] = None
    position_in_section: Optional[int] = None
    featured_top_pick: bool = False
    aws_severity: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "published": self.published,
            "link": self.link,
            "canonical_url": self.canonical_url,
            "category_suggested": self.category_suggested,
            "heuristic_score": self.heuristic_score,
            "model_score": self.model_score,
            "combined_score": self.combined_score,
            "included": self.included,
            "reason": self.reason,
            "section": self.section,
            "position_in_section": self.position_in_section,
            "featured_top_pick": self.featured_top_pick,
            "aws_severity": self.aws_severity,
        }


@dataclass(slots=True)
class ContentItem:
    title: str
    url: str
    summary: str
    source: str
    published: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ContentItem":
        return cls(
            title=data.get("title", ""),
            url=data.get("url", "") or data.get("link", ""),
            summary=data.get("summary", ""),
            source=data.get("source", ""),
            published=data.get("published"),
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "published": self.published,
        }


@dataclass(slots=True)
class SearchResult:
    items: List[ContentItem]

    @classmethod
    def from_json(cls, json_str: str) -> "SearchResult":
        import json
        import re

        items: List[ContentItem] = []
        try:
            match = re.search(r"(\[\s*\{.*\}\s*\])", json_str, re.DOTALL)
            blob = match.group(1) if match else json_str
            data = json.loads(blob)
            for item in data if isinstance(data, list) else []:
                if isinstance(item, dict):
                    content_item = ContentItem.from_dict(item)
                    if content_item.title and content_item.url:
                        items.append(content_item)
        except Exception:
            for match in re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", json_str):
                title, url = match.group(1).strip(), match.group(2).strip()
                items.append(
                    ContentItem(
                        title=title,
                        url=url,
                        summary="",
                        source="strands-search",
                    )
                )
        return cls(items=items)

    def filter_items(self, keywords_to_ignore: List[str]) -> "SearchResult":
        ignore_terms = {
            term.lower().replace("-", " ") for term in keywords_to_ignore
        }
        filtered_items = []
        for item in self.items:
            text = f"{item.title} {item.url}".lower()
            if not any(term in text for term in ignore_terms):
                filtered_items.append(item)
        return SearchResult(items=filtered_items)


__all__ = [
    "FeedEntry",
    "DigestCandidate",
    "DigestItem",
    "DiagnosticRecord",
    "ContentItem",
    "SearchResult",
]
