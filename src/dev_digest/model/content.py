from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ContentItem:
    title: str
    url: str
    summary: str
    source: str
    published: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> ContentItem:
        return cls(
            title=data.get("title", ""),
            url=data.get("url", "") or data.get("link", ""),
            summary=data.get("summary", ""),
            source=data.get("source", ""),
            published=data.get("published")
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "published": self.published
        }


@dataclass
class SearchResult:
    items: List[ContentItem]

    @classmethod
    def from_json(cls, json_str: str) -> SearchResult:
        import json
        import re
        
        items = []
        
        # Try JSON parsing first
        try:
            # Extract JSON array if wrapped in markdown
            match = re.search(r"(\[\s*\{.*\}\s*\])", json_str, re.DOTALL)
            blob = match.group(1) if match else json_str
            
            data = json.loads(blob)
            for item in (data if isinstance(data, list) else []):
                if isinstance(item, dict):
                    content_item = ContentItem.from_dict(item)
                    if content_item.title and content_item.url:
                        items.append(content_item)
        except Exception:
            # Fallback: parse markdown links
            for match in re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", json_str):
                title, url = match.group(1).strip(), match.group(2).strip()
                items.append(ContentItem(
                    title=title,
                    url=url,
                    summary="",
                    source="strands-search"
                ))
        
        return cls(items=items)
    
    def filter_items(self, keywords_to_ignore: List[str]) -> SearchResult:
        """Filter out items containing ignored keywords."""
        ignore_terms = {
            term.lower().replace("-", " ") 
            for term in keywords_to_ignore
        }
        
        filtered_items = []
        for item in self.items:
            text = f"{item.title} {item.url}".lower()
            if not any(term in text for term in ignore_terms):
                filtered_items.append(item)
        
        return SearchResult(items=filtered_items)