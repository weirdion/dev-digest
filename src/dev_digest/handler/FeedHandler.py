from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser

from dev_digest.utility.constants import (
    MAX_PER_FEED,
    MAX_STORIES_TOTAL,
    KEYWORDS_TO_IGNORE,
)
from dev_digest.utility.tools import normalize_text, within_window


class FeedHandler:
    def __init__(self) -> None:
        pass

    def _entry_dt(self, entry: Any) -> datetime | None:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if not t:
            return None
        # published_parsed is a time.struct_time in UTC for most feeds
        return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

    def fetch_recent(self, feed_urls: List[str], now_utc: datetime) -> List[Dict[str, Any]]:
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
                if total >= MAX_STORIES_TOTAL or count_for_feed >= MAX_PER_FEED:
                    break

                published_dt = self._entry_dt(entry)
                if not within_window(published_dt, now_utc):
                    continue

                title = normalize_text(entry.get("title") or "")
                link = (entry.get("link") or "").strip()
                summary = normalize_text(entry.get("summary") or entry.get("description") or "")

                # Filter by keywords to ignore
                tl = title.lower()
                if any(k in tl for k in ignore_lc):
                    continue

                results.append(
                    {
                        "title": title,
                        "link": link,
                        "published": published_dt,
                        "source": parsed.feed.get("title", url),
                        "summary": summary,
                    }
                )
                count_for_feed += 1
                total += 1

        return results