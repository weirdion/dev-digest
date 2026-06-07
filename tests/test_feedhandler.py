import sys
import types
from datetime import datetime, timezone


def _stub_feedparser():
    if "feedparser" not in sys.modules:
        sys.modules["feedparser"] = types.SimpleNamespace(
            parse=lambda url: types.SimpleNamespace(entries=[], feed={"title": url})
        )


def test_extract_bulletin_date_mmddyyyy():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import _extract_bulletin_date

    text = "<b>Publication Date:</b> 05/13/2026 10:00 PM PDT"
    dt = _extract_bulletin_date(text)
    # 10 PM PDT (UTC-7) on 5/13 = 5 AM UTC on 5/14
    assert dt == datetime(2026, 5, 14, 5, 0, tzinfo=timezone.utc)


def test_extract_bulletin_date_yyyymmdd():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import _extract_bulletin_date

    text = "Publication Date: 2026/04/20 12:45 PM PDT"
    dt = _extract_bulletin_date(text)
    # 12:45 PM PDT (UTC-7) on 4/20 = 7:45 PM UTC same day
    assert dt == datetime(2026, 4, 20, 19, 45, tzinfo=timezone.utc)


def test_extract_bulletin_date_handles_bogus_24h_with_pm():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import _extract_bulletin_date

    # AWS sometimes writes "15:30 PM PDT" — 24h with redundant PM
    text = "Publication Date: 2026/04/07 15:30 PM PDT"
    dt = _extract_bulletin_date(text)
    # 15:30 PDT (UTC-7) = 22:30 UTC
    assert dt == datetime(2026, 4, 7, 22, 30, tzinfo=timezone.utc)


def test_extract_bulletin_date_pst_offset():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import _extract_bulletin_date

    text = "Publication Date: 2025/12/15 11:45 AM PST"
    dt = _extract_bulletin_date(text)
    # 11:45 AM PST (UTC-8) = 19:45 UTC
    assert dt == datetime(2025, 12, 15, 19, 45, tzinfo=timezone.utc)


def test_extract_bulletin_date_returns_none_when_missing():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import _extract_bulletin_date

    assert _extract_bulletin_date("") is None
    assert _extract_bulletin_date("no date here") is None
    assert _extract_bulletin_date("Publication Date: invalid") is None


def test_entry_dt_uses_bulletin_date_for_security_links():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import FeedHandler

    fh = FeedHandler()
    entry = {
        "link": "https://aws.amazon.com/security/security-bulletins/rss/2026-031-aws/",
        "summary": "<b>Publication Date:</b> 05/14/2026 13:00 PM PDT",
        # Simulate the broken feed-level pubDate (lastBuildDate of feed)
        "published_parsed": (2026, 6, 5, 19, 19, 25, 4, 156, 0),
    }
    dt = fh._entry_dt(entry)
    # Should use the description date (5/14 PDT), not the feed pubDate (6/5)
    assert dt is not None
    assert dt.month == 5 and dt.day == 14


def test_entry_dt_drops_bulletin_with_malformed_date():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import FeedHandler

    fh = FeedHandler()
    entry = {
        "link": "https://aws.amazon.com/security/security-bulletins/rss/2026-039-aws/",
        # AWS occasionally publishes typos like "06/025/2026" — should not be
        # rescued by the always-stale feed-level pubDate.
        "summary": "<b>Publication Date:</b> 06/025/2026 12:15 PM PDT",
        "published_parsed": (2026, 6, 5, 19, 19, 25, 4, 156, 0),
    }
    assert fh._entry_dt(entry) is None


def test_entry_dt_falls_back_to_published_parsed_for_non_bulletin_links():
    _stub_feedparser()
    from dev_digest.handler.FeedHandler import FeedHandler

    fh = FeedHandler()
    entry = {
        "link": "https://aws.amazon.com/blogs/database/some-post/",
        "summary": "<b>Publication Date:</b> 05/14/2026 13:00 PM PDT",
        "published_parsed": (2026, 6, 5, 12, 0, 0, 4, 156, 0),
    }
    dt = fh._entry_dt(entry)
    # Non-bulletin link should use published_parsed (6/5), not the description date
    assert dt is not None
    assert dt.month == 6 and dt.day == 5


def test_normalize_source_aws_paths():
    # Stub feedparser before importing FeedHandler
    if "feedparser" not in sys.modules:
        sys.modules["feedparser"] = types.SimpleNamespace(parse=lambda url: types.SimpleNamespace(entries=[], feed={"title": url}))

    from dev_digest.handler.FeedHandler import FeedHandler

    fh = FeedHandler()
    # What's New
    assert fh._normalize_source("https://aws.amazon.com/about-aws/whats-new/2024/", "fallback").lower() == "recent announcements"
    # Security bulletins
    assert fh._normalize_source("https://aws.amazon.com/security/security-bulletins/", "fb").lower() == "security bulletins"
    # Blogs mapping
    assert fh._normalize_source("https://aws.amazon.com/blogs/ai/", "fb") == "AWS Blog - Artificial Intelligence"
    assert fh._normalize_source("https://aws.amazon.com/blogs/machine-learning/xyz", "fb") == "AWS Machine Learning Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/compute/", "fb") == "AWS Compute Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/database/", "fb") == "AWS Database Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/containers/", "fb") == "AWS Containers Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/devops/", "fb") == "AWS DevOps & Developer Productivity Blog"
    assert fh._normalize_source("https://aws.amazon.com/blogs/networking-and-content-delivery/", "fb") == "Networking & Content Delivery"
    assert fh._normalize_source("https://aws.amazon.com/blogs/architecture/", "fb") == "AWS Architecture Blog"
