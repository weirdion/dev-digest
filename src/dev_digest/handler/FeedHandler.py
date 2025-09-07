import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

import feedparser

from dev_digest.utility.constants import (
    KEYWORDS_TO_IGNORE
)
from dev_digest.utility.tools import normalize_text, within_window
from dev_digest.utility.security import sanitize_text, strip_html_to_text

log = logging.getLogger("dev-digest")

class FeedHandler:
    def __init__(self) -> None:
        pass

    def _normalize_source(self, link: str, fallback: str) -> str:
        """Derive a stable, human-friendly source name from the link path when possible."""
        try:
            u = urlparse(link or "")
            host = (u.netloc or "").lower()
            path = (u.path or "/").lower()
        except Exception:
            host, path = "", ""

        if host == "aws.amazon.com":
            # AWS blogs and portals
            if "/about-aws/whats-new" in path:
                return "Recent Announcements"
            if "/security/security-bulletins" in path:
                return "Security Bulletins"
            if "/blogs/ai/" in path or "/blogs/ai" == path.rstrip("/"):
                return "AWS Blog - Artificial Intelligence"
            if "/blogs/machine-learning" in path:
                return "AWS Machine Learning Blog"
            if "/blogs/compute" in path:
                return "AWS Compute Blog"
            if "/blogs/database" in path:
                return "AWS Database Blog"
            if "/blogs/containers" in path:
                return "AWS Containers Blog"
            if "/blogs/devops" in path:
                return "AWS DevOps & Developer Productivity Blog"
            if "/blogs/networking-and-content-delivery" in path:
                return "Networking & Content Delivery"
            if "/blogs/architecture" in path:
                return "AWS Architecture Blog"

        return fallback or host or link

    def _entry_dt(self, entry: Any) -> datetime | None:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if not t:
            return None
        # published_parsed is a time.struct_time in UTC for most feeds
        return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

    def fetch_recent(self, feed_urls: List[str], now_utc: datetime, window_days: int) -> List[Dict[str, Any]]:
        """
        Fetch and filter recent posts from a list of feeds within the time window.
        Returns a list of dicts: {title, link, published, source}
        """
        results: List[Dict[str, Any]] = []
        total = 0
        ignore_lc = [k.lower() for k in KEYWORDS_TO_IGNORE]

        for url in feed_urls:
            parsed = feedparser.parse(url)
            count_for_feed = 0
            for entry in parsed.entries:
                published_dt = self._entry_dt(entry)
                if not within_window(published_dt, now_utc, window_days):
                    continue

                raw_title = entry.get("title") or ""
                title = sanitize_text(normalize_text(strip_html_to_text(raw_title)))
                link = sanitize_text((entry.get("link") or "").strip())
                raw_summary = entry.get("summary") or entry.get("description") or ""
                summary = sanitize_text(normalize_text(strip_html_to_text(raw_summary)))

                # Filter by keywords to ignore
                tl = title.lower()
                if any(k in tl for k in ignore_lc):
                    continue

                results.append(
                    {
                        "title": title,
                        "link": link,
                        "published": published_dt,
                        "source": self._normalize_source(link, parsed.feed.get("title", url)),
                        "summary": summary,
                    }
                )
                count_for_feed += 1
                total += 1

            log.info(f"Found {count_for_feed} items from {parsed.feed.get('title', url)}")

        return results
